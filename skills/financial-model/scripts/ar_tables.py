#!/usr/bin/env python3
"""
ar_tables.py - find the financial statement tables in an annual-report-kb
knowledge base, so the figures Screener does not carry can be read off the
annual report with a page citation.

    python ar_tables.py list  --kb "Acme Annual Report"
    python ar_tables.py find  --kb "Acme Annual Report" --for payables
    python ar_tables.py show  --kb "Acme Annual Report" --file tables/table_p0132_1.md
    python ar_tables.py presets

This finds candidates. Reading the numbers out of them is the analyst's job -
the figures go into `overrides.actuals` in overrides.json with the page in
`overrides.citations`, and `ingest.py` merges them over the Screener spine.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

PRESETS: dict[str, list[str]] = {
    "payables": ["trade payables", "trade and other payables", "sundry creditors",
                 "creditors", "payable ageing", "ageing of trade payables",
                 "micro and small enterprise"],
    "receivables": ["trade receivables", "sundry debtors", "receivable ageing",
                    "ageing of trade receivables", "allowance for expected credit loss"],
    "inventory": ["inventories", "raw materials", "work-in-progress",
                  "finished goods", "stores and spares"],
    "borrowings": ["borrowings", "long-term borrowings", "short-term borrowings",
                   "current maturities", "repayment schedule", "term loan",
                   "non-convertible debenture", "maturity profile", "interest rate"],
    "leases": ["lease liabilities", "right-of-use", "right of use asset",
               "maturity analysis of lease"],
    "ppe": ["property, plant and equipment", "gross block", "gross carrying amount",
            "accumulated depreciation", "capital work-in-progress",
            "additions", "disposals", "useful life"],
    "capex": ["capital commitments", "capital expenditure", "contracts remaining "
              "to be executed", "capital work-in-progress ageing"],
    "revenue": ["revenue from operations", "disaggregation of revenue",
                "segment revenue", "sale of products", "sale of services",
                "geographical", "contract balances"],
    "expenses": ["cost of materials consumed", "purchases of stock-in-trade",
                 "changes in inventories", "employee benefits expense",
                 "other expenses", "finance costs", "depreciation and amortisation"],
    "tax": ["tax expense", "deferred tax", "effective tax rate",
            "reconciliation of tax", "current tax", "MAT credit"],
    "equity": ["share capital", "other equity", "statement of changes in equity",
               "dividend", "buy-back", "reserves"],
    "otherincome": ["other income", "interest income", "dividend income",
                    "gain on fair value", "treasury"],
    "segments": ["segment", "operating segment", "segment results",
                 "segment assets", "reportable segment"],
    "statements": ["balance sheet", "statement of profit and loss",
                   "statement of cash flows", "cash flow statement"],
}

# The model row each preset most often feeds.
FEEDS = {
    "payables": "payables", "receivables": "receivables", "inventory": "inventory",
    "borrowings": "term_debt", "ppe": "net_block / capex", "capex": "capex",
    "revenue": "revenue", "expenses": "cogs / ebitda", "tax": "tax",
    "equity": "share_capital / reserves / dividends / shares",
    "otherincome": "other_income", "leases": "term_debt (if leases are capitalised)",
    "segments": "revenue (segment build)", "statements": "the whole spine",
}


def _kb_root(kb: str) -> str:
    for cand in (kb, os.path.join(os.getcwd(), kb)):
        if os.path.isdir(cand):
            return cand
    sys.exit(f"knowledge base not found: {kb}\n"
             "Build one first with the annual-report-kb skill.")


def _index(root: str) -> list[dict]:
    path = os.path.join(root, "metadata", "table_index.json")
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f).get("tables", [])
    # Fall back to whatever is on disk.
    tdir = os.path.join(root, "tables")
    if not os.path.isdir(tdir):
        return []
    out = []
    for name in sorted(os.listdir(tdir)):
        if not name.endswith(".md"):
            continue
        m = re.match(r"table_p(\d+)_", name)
        out.append({"file": f"tables/{name}", "page": int(m[1]) if m else 0,
                    "pdf_page": (int(m[1]) + 1) if m else 0,
                    "caption": "", "section": "", "extracted": True})
    return out


def _text(root: str, rel: str) -> str:
    p = os.path.join(root, rel.replace("/", os.sep))
    try:
        with open(p, encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def _score(hay: str, terms: list[str]) -> tuple[int, list[str]]:
    low = hay.lower()
    hit = [t for t in terms if t.lower() in low]
    return len(hit), hit


def cmd_list(root: str, limit: int) -> int:
    tables = _index(root)
    got = [t for t in tables if t.get("extracted")]
    print(f"{len(tables)} tables catalogued, {len(got)} with a reconstructed grid\n")
    print(f"{'pdf p.':>7}  {'rows':>5}  file / caption")
    for t in got[:limit]:
        cap = (t.get("caption") or t.get("section") or "").strip()[:70]
        print(f"{t.get('pdf_page', 0):>7}  {t.get('n_rows', 0):>5}  "
              f"{t.get('file', '')}  {cap}")
    if len(got) > limit:
        print(f"... {len(got) - limit} more; raise --limit")
    miss = [t for t in tables if not t.get("extracted")]
    if miss:
        print(f"\n{len(miss)} table(s) were detected but not reconstructed. Their "
              "numbers are still in the page markdown:")
        for t in miss[:10]:
            print(f"  pdf p.{t.get('pdf_page', 0)}  {t.get('source_page_file', '')}")
    return 0


def cmd_find(root: str, preset: str | None, terms: list[str], limit: int) -> int:
    if preset:
        terms = PRESETS[preset] + terms
    if not terms:
        sys.exit("give --for <preset> or --terms t1 t2")
    hits = []
    for t in _index(root):
        if not t.get("extracted") or not t.get("file"):
            continue
        body = _text(root, t["file"])
        meta = f"{t.get('caption', '')} {t.get('section', '')}"
        n_meta, _ = _score(meta, terms)
        n_body, words = _score(body, terms)
        if n_meta or n_body:
            hits.append((n_meta * 3 + n_body, t, words, body))
    hits.sort(key=lambda h: (-h[0], h[1].get("page", 0)))

    if preset:
        print(f"preset '{preset}' -> feeds the model row(s): {FEEDS.get(preset, '?')}\n")
    if not hits:
        print("no table matched. The figure may be in the page markdown rather than "
              "a reconstructed grid - search the pages with the "
              "financial-model-assumptions skill's kb_search.py.")
        return 0

    for score, t, words, body in hits[:limit]:
        print(f"--- pdf p.{t.get('pdf_page', 0)}  {t['file']}  (score {score})")
        cap = (t.get("caption") or t.get("section") or "").strip()
        if cap:
            print(f"    {cap}")
        print(f"    matched: {', '.join(sorted(set(words))[:6])}")
        rows = [ln for ln in body.splitlines()
                if ln.strip().startswith("|")][:6]
        for ln in rows:
            print("    " + ln.strip()[:150])
        print()
    print(f"{len(hits)} table(s) matched; showing {min(limit, len(hits))}.")
    print("Read one in full with:  ar_tables.py show --kb <kb> --file <file>")
    print("Then put the figures in overrides.actuals and the page in "
          "overrides.citations.")
    return 0


def cmd_show(root: str, rel: str) -> int:
    body = _text(root, rel)
    if not body:
        sys.exit(f"cannot read {rel} under {root}")
    print(body)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("list", "find", "show"):
        s = sub.add_parser(name)
        s.add_argument("--kb", required=True)
        if name == "find":
            s.add_argument("--for", dest="preset", choices=sorted(PRESETS))
            s.add_argument("--terms", nargs="*", default=[])
        if name == "show":
            s.add_argument("--file", required=True)
        if name in ("list", "find"):
            s.add_argument("--limit", type=int, default=12)
    sub.add_parser("presets")

    a = ap.parse_args()
    if a.cmd == "presets":
        print(f"{'preset':<14} feeds                              terms")
        for k in sorted(PRESETS):
            print(f"{k:<14} {FEEDS.get(k, ''):<34} {', '.join(PRESETS[k][:3])}")
        return 0

    root = _kb_root(a.kb)
    if a.cmd == "list":
        return cmd_list(root, a.limit)
    if a.cmd == "find":
        return cmd_find(root, a.preset, a.terms, a.limit)
    return cmd_show(root, a.file)


if __name__ == "__main__":
    raise SystemExit(main())
