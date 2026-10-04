#!/usr/bin/env python3
"""Profile a company knowledge base and pull cited evidence out of it.

Built for the layout `annual-report-kb` produces (context/, sections/, pages/,
tables/, entities/, metadata/) but works on any folder of markdown/text/JSON.

Three subcommands:

  profile   inventory the knowledge base: which document types are present,
            how many pages/tables/sections, and which assumption families it
            can and cannot support. Run this first - it decides which
            assumptions are answerable at all.

  find      search for evidence, with a page citation on every hit.
            Either a preset term pack for a named assumption, or free terms.

  presets   list the assumption keys `find --for` accepts.

Every hit is reported as `path:line  (p. N)  snippet`, where N is the 1-based
PDF page, recovered from `pages/page_0123.md`, `tables/table_p0210_1.md`, a
`page:` frontmatter field, or an inline `(p. 123)` citation.

Usage
    python kb_search.py profile --kb "ACME Annual Report"
    python kb_search.py find --kb "ACME Annual Report" --for revenue_growth
    python kb_search.py find --kb "ACME Annual Report" --terms "capex,capacity expansion"
    python kb_search.py find --kb KB --for tax_rate --json --max 40
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

TEXT_EXT = {".md", ".txt", ".json", ".csv"}
SKIP_DIRS = {"_work", "images", "__pycache__", ".git", "node_modules"}
MAX_FILE_BYTES = 4_000_000

# --------------------------------------------------------------------------
# preset search packs - one per assumption in references/catalog.md
# --------------------------------------------------------------------------
PRESETS: dict[str, list[str]] = {
    "revenue_growth": ["revenue growth", "revenue from operations", "top line",
                       "grew by", "growth of", "guidance", "outlook", "CAGR",
                       "double-digit", "order book", "demand outlook"],
    "volume_growth": ["volume", "tonnes", "MT ", "units sold", "throughput",
                      "capacity utilisation", "capacity utilization", "sold volume"],
    "pricing_growth": ["realisation", "realization", "price increase", "pricing",
                       "average selling price", "ASP", "price hike", "pass through"],
    "new_customers": ["new customers", "customer additions", "client additions",
                      "logos", "new clients", "wins", "customer base"],
    "customer_retention": ["retention", "churn", "repeat", "renewal",
                           "net revenue retention", "attrition", "repeat business"],
    "gross_margin": ["gross margin", "gross profit", "cost of goods",
                     "raw material cost", "material cost", "cost of materials"],
    "ebitda_margin": ["EBITDA", "operating margin", "EBITDA margin",
                      "operating profit", "margin expansion", "margin guidance"],
    "ebit_margin": ["EBIT", "operating profit", "profit before interest",
                    "depreciation", "operating income"],
    "sga": ["selling general", "SG&A", "other expenses", "administrative expenses",
            "overheads", "operating expenses"],
    "rnd": ["research and development", "R&D", "innovation spend",
            "product development", "technology investment"],
    "sales_marketing": ["advertising", "marketing spend", "A&P", "promotion",
                        "selling expenses", "brand investment", "ad spend"],
    "employee_cost": ["employee benefit", "employee cost", "staff cost",
                      "headcount", "wage", "salary", "manpower", "attrition"],
    "capex": ["capital expenditure", "capex", "expansion", "greenfield",
              "brownfield", "new plant", "commissioning", "capacity addition",
              "investment of", "outlay"],
    "depreciation": ["depreciation", "useful life", "gross block",
                     "property plant and equipment", "straight line"],
    "amortisation": ["amortisation", "amortization", "intangible",
                     "goodwill", "useful life of intangible"],
    "dso": ["trade receivables", "debtors", "receivable days", "credit period",
            "collection", "days sales outstanding"],
    "dio": ["inventory", "inventories", "stock", "inventory days",
            "finished goods", "raw material inventory"],
    "dpo": ["trade payables", "creditors", "payable days", "credit from suppliers",
            "supplier credit", "payment terms"],
    "tax_rate": ["tax rate", "effective tax", "deferred tax", "115BAA",
                 "MAT", "tax expense", "concessional tax"],
    "interest_rate": ["finance cost", "interest expense", "borrowing cost",
                      "cost of debt", "interest rate", "coupon", "refinanc"],
    "debt_growth": ["borrowings", "debt", "repayment", "deleverag", "net debt",
                    "debt reduction", "term loan", "working capital loan"],
    "terminal_growth": ["long term", "long-term growth", "steady state",
                        "industry growth", "GDP", "nominal growth", "inflation"],
    "wacc": ["cost of capital", "WACC", "beta", "risk free", "equity risk premium",
             "hurdle rate", "cost of equity"],
    "shares_out": ["equity shares", "shares outstanding", "share capital",
                   "face value", "ESOP", "dilution", "buyback"],
    "net_debt": ["net debt", "cash and cash equivalents", "total borrowings",
                 "gross debt", "liquid investments"],
    "segments": ["segment", "business segment", "revenue mix", "geograph",
                 "product mix", "segment result"],
    "risks": ["risk", "mitigation", "sensitivity", "contingent liabilit",
              "litigation", "regulatory", "dependence"],
    "guidance": ["guidance", "outlook", "we expect", "we aim", "target",
                 "aspire", "over the next", "by FY", "medium term"],
}

FAMILY_SOURCES = {
    "Revenue": ["management_discussion", "business", "segment", "guidance"],
    "Margins": ["financial", "management_discussion", "guidance"],
    "Expenses": ["financial", "notes"],
    "Capital": ["management_discussion", "manufacturing", "cashflow", "notes"],
    "Working capital": ["financial", "notes"],
    "Tax": ["notes", "financial"],
    "Financing": ["notes", "financial"],
    "Valuation": ["management_discussion", "external"],
}


# --------------------------------------------------------------------------

def _page_from_path(path: str) -> int | None:
    b = os.path.basename(path)
    m = re.search(r"page[_-](\d+)", b, re.I) or re.search(r"_p(\d{2,5})[_.]", b, re.I)
    return int(m.group(1)) + 1 if m else None       # stored 0-based, cite 1-based


def _page_from_text(lines: list[str], idx: int, base: int | None) -> int | None:
    """Nearest preceding inline (p. N) citation, else frontmatter, else base."""
    for j in range(idx, max(-1, idx - 25), -1):
        m = re.search(r"\(p\.\s*(\d+)\)", lines[j])
        if m:
            return int(m.group(1))
    for ln in lines[:15]:
        m = re.match(r"\s*[\"']?page[\"']?\s*[:=]\s*(\d+)", ln, re.I)
        if m:
            return int(m.group(1)) + 1
    return base


def _walk(kb: str):
    for root, dirs, files in os.walk(kb):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
        for f in sorted(files):
            if os.path.splitext(f)[1].lower() in TEXT_EXT:
                yield os.path.join(root, f)


def _read(path: str) -> list[str] | None:
    try:
        if os.path.getsize(path) > MAX_FILE_BYTES:
            return None
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read().splitlines()
    except OSError:
        return None


# --------------------------------------------------------------------------

def cmd_profile(kb: str) -> dict:
    counts = {"pages": 0, "sections": 0, "tables": 0, "context": 0,
              "entities": 0, "images": 0, "other_docs": 0}
    doc_types: dict[str, list[str]] = {}
    sections: list[str] = []

    for root, dirs, files in os.walk(kb):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
        rel = os.path.relpath(root, kb).replace("\\", "/")
        top = rel.split("/")[0]
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if top == "pages":
                counts["pages"] += 1
            elif top == "sections":
                counts["sections"] += 1
                sections.append(f)
            elif top == "tables":
                counts["tables"] += 1
            elif top == "context":
                counts["context"] += 1
            elif top == "entities":
                counts["entities"] += 1
            elif ext in {".jpg", ".jpeg", ".png", ".webp"}:
                counts["images"] += 1
            elif ext in TEXT_EXT or ext == ".pdf":
                counts["other_docs"] += 1
                lower = f.lower()
                for key, pat in (
                        ("annual_report", ("annual", "ar20", "ar_2")),
                        ("investor_presentation", ("investor", "presentation", "deck", "ppt")),
                        ("earnings_call", ("concall", "transcript", "earnings call", "call")),
                        ("quarterly_results", ("q1", "q2", "q3", "q4", "quarter", "results")),
                        ("filing", ("filing", "sec", "bse", "nse", "shareholding", "8-k", "10-k")),
                        ("industry_report", ("industry", "sector", "market report")),
                        ("press_release", ("press", "release", "news")),
                        ("financials", ("screener", "financial", "statement", "model"))):
                    if any(p in lower for p in pat):
                        doc_types.setdefault(key, []).append(
                            os.path.join(rel, f).replace("\\", "/").lstrip("./"))
                        break

    have_kb = counts["pages"] > 0 or counts["sections"] > 0
    coverage = {}
    for fam in FAMILY_SOURCES:
        if have_kb or doc_types:
            coverage[fam] = "searchable"
        else:
            coverage[fam] = "no text source found"

    gaps = []
    if not have_kb and not doc_types:
        gaps.append("No parsed text found. If the source is a PDF, build a knowledge "
                    "base first with the annual-report-kb skill.")
    if "earnings_call" not in doc_types:
        gaps.append("No earnings-call transcript detected - forward guidance "
                    "assumptions will rest on the annual report narrative only.")
    if "industry_report" not in doc_types:
        gaps.append("No industry report detected - terminal growth and market "
                    "growth claims will have no external anchor.")
    if "investor_presentation" not in doc_types:
        gaps.append("No investor presentation detected - volume/pricing splits and "
                    "capex schedules are often only in the deck.")

    return {"kb": os.path.abspath(kb), "counts": counts,
            "document_types": doc_types, "coverage": coverage,
            "sections": sorted(sections)[:40], "gaps": gaps,
            "layout": "annual-report-kb" if have_kb else "loose documents"}


def cmd_find(kb: str, terms: list[str], max_hits: int, context_first: bool) -> list[dict]:
    pats = [(t, re.compile(re.escape(t), re.I)) for t in terms]
    hits: list[dict] = []
    files = list(_walk(kb))
    if context_first:                       # summaries before raw pages
        rank = {"context": 0, "sections": 1, "tables": 2, "entities": 3, "pages": 5}
        files.sort(key=lambda p: rank.get(
            os.path.relpath(p, kb).replace("\\", "/").split("/")[0], 4))

    seen: set[tuple[str, int]] = set()
    for path in files:
        if len(hits) >= max_hits:
            break
        lines = _read(path)
        if lines is None:
            continue
        base = _page_from_path(path)
        rel = os.path.relpath(path, kb).replace("\\", "/")
        for i, line in enumerate(lines):
            if len(hits) >= max_hits:
                break
            s = line.strip()
            if len(s) < 8:
                continue
            matched = [t for t, p in pats if p.search(line)]
            if not matched:
                continue
            key = (rel, i)
            if key in seen:
                continue
            seen.add(key)
            hits.append({
                "file": rel, "line": i + 1,
                "page": _page_from_text(lines, i, base),
                "terms": matched,
                "snippet": (s[:300] + " ...") if len(s) > 300 else s,
            })
    return hits


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("profile", help="inventory the knowledge base")
    p.add_argument("--kb", required=True)
    p.add_argument("--json", action="store_true")
    p.add_argument("--out")

    f = sub.add_parser("find", help="search for cited evidence")
    f.add_argument("--kb", required=True)
    f.add_argument("--for", dest="preset", help="preset assumption key")
    f.add_argument("--terms", help="comma-separated free-text terms")
    f.add_argument("--max", type=int, default=25)
    f.add_argument("--all-files", action="store_true",
                   help="do not rank context/ and sections/ ahead of pages/")
    f.add_argument("--json", action="store_true")

    sub.add_parser("presets", help="list preset assumption keys")

    a = ap.parse_args()

    if a.cmd == "presets":
        for k in sorted(PRESETS):
            print(f"{k:22} {', '.join(PRESETS[k][:5])}")
        return 0

    if not os.path.isdir(a.kb):
        print(f"error: not a directory: {a.kb}", file=sys.stderr)
        return 2

    if a.cmd == "profile":
        pr = cmd_profile(a.kb)
        if a.out:
            json.dump(pr, open(a.out, "w", encoding="utf-8"), indent=2)
            print(f"wrote {a.out}")
        if a.json:
            print(json.dumps(pr, indent=2))
            return 0
        c = pr["counts"]
        print(f"# Knowledge base profile\n\n{pr['kb']}\nlayout: {pr['layout']}\n")
        print("| pages | sections | tables | context | entities | images | other |")
        print("|---|---|---|---|---|---|---|")
        print(f"| {c['pages']} | {c['sections']} | {c['tables']} | {c['context']} | "
              f"{c['entities']} | {c['images']} | {c['other_docs']} |")
        if pr["document_types"]:
            print("\n**Document types detected**")
            for k, v in sorted(pr["document_types"].items()):
                print(f"- {k}: {len(v)} file(s) - {', '.join(v[:4])}")
        if pr["sections"]:
            print("\n**Sections**: " + ", ".join(s.replace('.md', '')
                                                 for s in pr["sections"][:20]))
        if pr["gaps"]:
            print("\n**Evidence gaps to declare up front**")
            for g in pr["gaps"]:
                print(f"- {g}")
        return 0

    # find
    if a.preset and a.preset not in PRESETS:
        print(f"error: unknown preset '{a.preset}'. Run `presets` for the list.",
              file=sys.stderr)
        return 2
    terms = PRESETS[a.preset] if a.preset else []
    if a.terms:
        terms += [t.strip() for t in a.terms.split(",") if t.strip()]
    if not terms:
        print("error: give --for or --terms", file=sys.stderr)
        return 2

    hits = cmd_find(a.kb, terms, a.max, not a.all_files)
    if a.json:
        print(json.dumps(hits, indent=2))
        return 0
    if not hits:
        print(f"No hits for: {', '.join(terms[:8])}\n"
              "Treat this as insufficient evidence unless a wider search finds it.")
        return 0
    print(f"# {len(hits)} hit(s)"
          + (f" for `{a.preset}`" if a.preset else "") + "\n")
    for h in hits:
        pg = f"(p. {h['page']})" if h["page"] else "(page n/a)"
        print(f"- `{h['file']}:{h['line']}` {pg}  [{', '.join(h['terms'][:3])}]\n"
              f"  > {h['snippet']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
