#!/usr/bin/env python3
"""
strategy_probe.py — evidence gathering for the modeling strategy.

    python3 strategy_probe.py --kb reports/<T>/kb/annual_report \
                              --kb reports/<T>/kb/investor_presentation \
                              --financials reports/<T>/data/financials.json \
                              -o reports/<T>/data/strategy_probe.json

Scans an `annual-report-kb` knowledge base for the operating disclosures each
archetype needs, with page citations, and derives the arithmetic facts that
disqualify valuation methods.

It PROPOSES. It does not decide. Output is a ranked list of archetype candidates
with the page references behind each, so the analyst argues from evidence rather
than from sector instinct — and so an archetype with no disclosure behind it is
visibly unsupported instead of quietly plausible.

A signal is a term that appears in the company's own filings. Absence of a signal
is informative: it is the difference between "this is a capacity business" and
"this is a business I have decided is a capacity business".
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import valuation as VAL     # noqa: E402

# Terms whose presence is evidence FOR an archetype. Weighted: a term that only
# appears in one kind of business scores higher than a generic one.
SIGNALS: dict[str, list[tuple[str, int]]] = {
    "capacity_utilisation_realisation": [
        (r"installed capacit", 3), (r"capacity utili[sz]ation", 3),
        (r"\bMTPA\b", 3), (r"\bTPA\b", 2), (r"\bMW\b", 2),
        (r"plant utili[sz]ation", 3), (r"\bdebottleneck", 2),
        (r"commission(?:ed|ing)", 1), (r"realisation per", 2),
    ],
    "order_book_execution": [
        (r"order book", 4), (r"order inflow", 4), (r"unexecuted order", 4),
        (r"book[- ]to[- ]bill", 3), (r"order intake", 3),
        (r"\bL1\b", 2), (r"execution period", 2), (r"outstanding order", 3),
    ],
    "project_pipeline_completion": [
        (r"pre[- ]sales", 4), (r"bookings", 2), (r"collections", 2),
        (r"land bank", 3), (r"launch(?:ed|es) .{0,20}project", 2),
        (r"completion .{0,15}(?:certificate|schedule)", 3), (r"\bsaleable area\b", 3),
        (r"carpet area", 2),
    ],
    "stores_sales_per_store": [
        (r"same[- ]store sales", 4), (r"\bSSSG\b", 4), (r"store count", 3),
        (r"stores? (?:opened|added|network)", 3), (r"sales per (?:store|sq)", 4),
        (r"retail (?:outlets|footprint)", 2), (r"\bsq\.? ?ft\b", 1),
    ],
    "rooms_occupancy_arr": [
        (r"\bRevPAR\b", 4), (r"average room rate", 4), (r"\bARR\b", 2),
        (r"occupancy", 3), (r"\bkeys\b", 3), (r"room nights", 4),
        (r"managed (?:hotels|properties)", 2),
    ],
    "headcount_utilisation_realisation": [
        (r"utili[sz]ation rate", 3), (r"billable", 4), (r"attrition", 3),
        (r"revenue per employee", 4), (r"onsite", 3), (r"offshore", 3),
        (r"\bTCV\b", 3), (r"headcount", 2), (r"\bpyramid\b", 2),
    ],
    "subscribers_arpu": [
        (r"\bARPU\b", 4), (r"subscribers?", 3), (r"churn", 3),
        (r"net revenue retention", 4), (r"\bMRR\b", 3), (r"\bARR\b.{0,20}recurring", 3),
        (r"deferred revenue", 2), (r"subscription", 2),
    ],
    "customers_arpu": [
        (r"customer additions", 3), (r"active customers", 3), (r"churn", 2),
        (r"customer base", 2), (r"retention rate", 3),
    ],
    "production_realisation": [
        (r"realisation per (?:tonne|ton|kg|litre)", 4), (r"\bEBITDA per tonne\b", 4),
        (r"cost curve", 3), (r"benchmark price", 3), (r"\bLME\b", 4),
        (r"saleable production", 4), (r"despatch(?:es)?", 2), (r"spread over", 2),
    ],
    "volume_price": [
        (r"volume growth", 3), (r"price(?:/| and )mix", 4), (r"realisation", 2),
        (r"volumes? (?:of|grew|declined)", 2), (r"tonnes sold", 3),
        (r"units sold", 3),
    ],
    "units_asp": [
        (r"\bASP\b", 4), (r"average selling price", 4), (r"units (?:sold|shipped)", 3),
        (r"despatches", 2),
    ],
}

SEGMENT_SIGNALS = [
    (r"segment (?:revenue|results|information)", 4),
    (r"reportable segments?", 4),
    (r"business segments?", 3),
    (r"operating segments?", 3),
]

# Two tiers, because the weak ones alone used to condemn a port operator.
# CORE terms are regulatory vocabulary that essentially cannot appear in a
# non-financial annual report. WEAK terms corroborate but can never decide:
# every company buys insurance, many take customer deposits, and "NBFC" turns up
# in any deck glossary or in a group that merely owns one.
OUT_OF_SCOPE_CORE = [
    (r"net interest (?:income|margin)", 5), (r"NIM", 4),
    (r"GNPA", 5), (r"NNPA", 5), (r"CASA", 5),
    (r"capital adequacy", 4), (r"CRAR", 4), (r"CET ?1", 4),
    (r"gross advances", 4), (r"slippage ratio", 4),
    (r"provision coverage ratio", 4), (r"solvency ratio", 4),
]
OUT_OF_SCOPE_WEAK = [
    (r"deposits? from customers", 3), (r"NBFC", 2),
    (r"insurance premium", 2),
]
OUT_OF_SCOPE = OUT_OF_SCOPE_CORE + OUT_OF_SCOPE_WEAK
_CORE_TERMS = {pat for pat, _ in OUT_OF_SCOPE_CORE}


def _iter_pages(kb: str):
    """Yield (page_no, path, text) from an annual-report-kb knowledge base.

    Reads pages/ first; falls back to any markdown in the tree. Never loads
    _work/chunks/ — that is the raw intermediate and is enormous.
    """
    pdir = os.path.join(kb, "pages")
    if os.path.isdir(pdir):
        for fn in sorted(os.listdir(pdir)):
            if not fn.endswith(".md"):
                continue
            m = re.search(r"(\d+)", fn)
            no = int(m.group(1)) if m else None
            try:
                with open(os.path.join(pdir, fn), encoding="utf-8", errors="ignore") as f:
                    yield no, os.path.join("pages", fn), f.read()
            except OSError:
                continue
        return
    for root, dirs, files in os.walk(kb):
        dirs[:] = [d for d in dirs if d not in ("_work", "images")]
        for fn in files:
            if not fn.endswith(".md"):
                continue
            p = os.path.join(root, fn)
            try:
                with open(p, encoding="utf-8", errors="ignore") as f:
                    yield None, os.path.relpath(p, kb), f.read()
            except OSError:
                continue


def _scan(kbs: list[str], max_hits: int = 6) -> dict:
    scores: dict[str, int] = {}
    hits: dict[str, list[dict]] = {}
    seg_hits: list[dict] = []
    oos: list[dict] = []
    pages = 0

    compiled = {k: [(re.compile(p, re.I), w) for p, w in v] for k, v in SIGNALS.items()}
    seg_c = [(re.compile(p, re.I), w) for p, w in SEGMENT_SIGNALS]
    oos_c = [(re.compile(p, re.I), w) for p, w in OUT_OF_SCOPE]

    for kb in kbs:
        if not os.path.isdir(kb):
            continue
        name = os.path.basename(os.path.normpath(kb))
        for no, rel, text in _iter_pages(kb):
            pages += 1
            for akey, pats in compiled.items():
                for rx, w in pats:
                    m = rx.search(text)
                    if not m:
                        continue
                    scores[akey] = scores.get(akey, 0) + w
                    if len(hits.setdefault(akey, [])) < max_hits:
                        hits[akey].append({
                            "term": rx.pattern, "page": no,
                            "source": f"{name}/{rel}",
                            "quote": _snip(text, m.start())})
            for rx, w in seg_c:
                m = rx.search(text)
                if m and len(seg_hits) < max_hits:
                    seg_hits.append({"page": no, "source": f"{name}/{rel}",
                                     "quote": _snip(text, m.start())})
            for rx, w in oos_c:
                m = rx.search(text)
                if m:
                    oos.append({"term": rx.pattern, "weight": w, "page": no,
                                "source": f"{name}/{rel}",
                                "quote": _snip(text, m.start())})
    return {"pages_scanned": pages, "scores": scores, "hits": hits,
            "segment_disclosure": seg_hits, "out_of_scope_signals": oos}


def _snip(text: str, at: int, w: int = 110) -> str:
    s = max(0, at - w // 3)
    return " ".join(text[s:s + w].split())


def probe(kbs: list[str], fin: dict | None) -> dict:
    scan = _scan(kbs)
    facts = VAL._facts_from(fin)

    oos_weight = sum(h["weight"] for h in scan["out_of_scope_signals"])
    distinct = {h["term"] for h in scan["out_of_scope_signals"]}
    # A lender verdict needs at least two DISTINCT core regulatory terms.
    # Weight alone is not enough: 'war-risk insurance premiums', refundable
    # customer security deposits and the word NBFC in a glossary once summed
    # to exactly the old threshold on a port and marked every valuation
    # method NOT_APPROPRIATE.
    core_hits = {t for t in distinct if t in _CORE_TERMS}
    likely_financial = len(core_hits) >= 2 and oos_weight >= 8
    if likely_financial:
        facts["financial_sector"] = True

    ranked = sorted(scan["scores"].items(), key=lambda kv: -kv[1])
    candidates = [{
        "archetype": k, "score": v,
        "evidence": scan["hits"].get(k, []),
        "verdict": ("supported" if v >= 8 else
                    "weak — the disclosure may not carry it" if v >= 4 else
                    "trace only; not evidence"),
    } for k, v in ranked]

    return {
        "pages_scanned": scan["pages_scanned"],
        "likely_out_of_scope_financial": likely_financial,
        "out_of_scope_signals": scan["out_of_scope_signals"][:10],
        "segment_disclosure_found": bool(scan["segment_disclosure"]),
        "segment_disclosure": scan["segment_disclosure"],
        "archetype_candidates": candidates,
        "facts": facts,
        "method_proposal": VAL.assess(facts),
        "note": ("Signal counts are a search over the company's own filings, not a "
                 "classification. A high score means the disclosure exists to "
                 "support that architecture; it does not mean the architecture is "
                 "right. A low score on an archetype you were about to choose is "
                 "the finding worth acting on."),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kb", action="append", default=[],
                    help="knowledge base directory; repeatable")
    ap.add_argument("--financials")
    ap.add_argument("-o", "--out")
    a = ap.parse_args()

    fin = json.load(open(a.financials, encoding="utf-8")) if a.financials else None
    P = probe(a.kb, fin)

    if a.out:
        os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
        json.dump(P, open(a.out, "w", encoding="utf-8"), indent=1)
        print(f"wrote {a.out}")

    print(f"scanned {P['pages_scanned']} pages across {len(a.kb)} knowledge base(s)")
    if P["likely_out_of_scope_financial"]:
        print("\n  ** OUT OF SCOPE: lender/insurer disclosures detected "
              "(NIM/GNPA/CASA/CRAR class). This pipeline does not model banks, "
              "NBFCs or insurers. Confirm and stop. **")
        for h in P["out_of_scope_signals"][:5]:
            print(f"     p.{h['page']}  {h['quote'][:80]}")
        return
    print(f"segment disclosure found: {P['segment_disclosure_found']}")
    print("\narchetype candidates (evidence, not a decision):")
    for c in P["archetype_candidates"][:8]:
        print(f"  {c['score']:>3}  {c['archetype']:<36} {c['verdict']}")
        for e in c["evidence"][:2]:
            print(f"        [{e.get('term','?')}]  p.{e['page']}  {e['quote'][:62]}")
    print("  the bracketed term is what matched. Check the word sense: "
          "'offshore' once ranked headcount_utilisation top for a port by "
          "matching offshore marine vessels.")

    hard = {k: v for k, v in P["method_proposal"].items() if v.get("hard")}
    if hard:
        print("\nvaluation methods disqualified by arithmetic:")
        for k, v in hard.items():
            print(f"  {k:<16} {v['reason']}")


if __name__ == "__main__":
    main()
