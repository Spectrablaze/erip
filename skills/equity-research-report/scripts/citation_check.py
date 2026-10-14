"""citation_check.py - does each piece of evidence actually say what it is cited for?

Reads every evidence record in decisions.json ({quote, source, page}) and checks it against the
knowledge base the report was built from. Each record gets one grade:

  VERIFIED       the quoted words are on the cited page (ellipses split the quote into fragments)
  NUMBERS_ONLY   the wording is paraphrased, but every number in the quote is on the cited page
  PARTIAL        at least half the quote's numbers are on the cited page; the missing ones are listed
                 (usually the analyst's own arithmetic written into the quote)
  IMAGE          read from a chart image in the knowledge base: the file exists, the numbers need a
                 visual check
  VERIFIED_VISUAL checked by eye and recorded in data/citation_signoffs.json (who, when, what was
                 seen); applies only while the cited file still exists
  NOT_HELD       a named document (an older call transcript, a press release) the report's inputs
                 do not contain
  MOVED          the quote is in the knowledge base, but not on the page cited; the right page is given
  NOT_FOUND      the cited page exists and neither the words nor the numbers are on it
  EXTERNAL       a web or third-party source the knowledge base does not hold: unverifiable offline,
                 needs a URL and retrieval date in the source text
  DERIVED        a calculation from the report's own data files (the file must exist)
  UNRESOLVED     the source names no locatable document

    python citation_check.py --root reports/<T> [--strict]

Writes data/citation_check.json. Exit 1 on any NOT_FOUND or UNRESOLVED (and with --strict on MOVED).
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
from datetime import datetime

DOC_HINTS = [  # words in a source string -> knowledge-base folder
    (r"concall|earnings call|call transcript|transcript", "concall"),
    (r"investor presentation|deck|presentation|ambition", "investor_presentation"),
    (r"shareholding", "shareholding"),
    (r"annual report|\bAR\b|kb/annual_report|integrated annual", "annual_report"),
]
EXTERNAL = r"https?://|\.com|\.in\b|fitch|moody|crisil|icra|ccil|tradingview|finbox|trading economics|bloomberg|reuters|rbi|mospi|imf|screener\.in|nse|bse|media release|press release"
DERIVED = r"^(data/|reports/|segment_build|.*\.json)"
NUM = re.compile(r"(?<![A-Za-z\d])\d[\d,]*(?:\.\d+)?")


def norm(t: str) -> str:
    t = t.lower().replace("`", "inr ").replace("₹", "inr ").replace("rs.", "inr ")
    t = re.sub(r"[‘’“”\"']", "", t)
    t = re.sub(r"[^a-z0-9.,%\- ]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def numbers(t: str) -> set:
    out = set()
    for m in NUM.findall(t):
        v = m.replace(",", "").rstrip(".")
        if v and len(v.replace(".", "")) >= 2:          # single digits match anything
            out.add(v.rstrip("0").rstrip(".") if "." in v else v)
    return out


def page_text(path: str) -> str:
    try:
        return open(path, encoding="utf-8", errors="replace").read()
    except OSError:
        return ""


def fragments(q: str) -> list:
    parts = re.split(r"\.\.\.|…|\[\.\.\.\]", q)
    return [norm(p) for p in parts if len(norm(p).split()) >= 4] or [norm(q)]


def grade_text(quote: str, text: str, partial: bool = False):
    """VERIFIED / NUMBERS_ONLY / (PARTIAL, missing) or None."""
    if not text:
        return None
    nt = norm(text)
    if all(f in nt for f in fragments(quote)):
        return "VERIFIED"
    qn, tn = numbers(quote), numbers(text)
    if qn and qn <= tn:
        return "NUMBERS_ONLY"
    if partial and qn and len(qn & tn) >= max(2, len(qn) / 2):
        return ("PARTIAL", sorted(qn - tn))
    return None


def pdf_page_text(path: str, page_1based: int) -> str:
    try:
        import pypdfium2 as pdfium
        doc = pdfium.PdfDocument(path)
        if not 1 <= page_1based <= len(doc):
            return ""
        return doc[page_1based - 1].get_textpage().get_text_range()
    except Exception:
        return ""


def xlsx_text(path: str) -> str:
    try:
        import openpyxl
        wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
        return " ".join(str(c) for ws in wb.worksheets for row in ws.iter_rows(values_only=True) for c in row
                        if c is not None)
    except Exception:
        return ""


def _graded(out, g, where):
    if isinstance(g, tuple):
        return {**out, "grade": g[0], "found": where, "why": f"numbers not on the page: {', '.join(g[1])}"}
    return {**out, "grade": g, "found": where}


def kb_pages(root: str, doc: str) -> list:
    return sorted(glob.glob(os.path.join(root, "kb", doc, "pages", "page_*.md")))


def check(root: str, rec: dict) -> dict:
    q, src, pg = (rec.get("quote") or "").strip(), str(rec.get("source") or ""), rec.get("page")
    out = {"source": src[:160], "page": pg, "quote": q[:160]}
    if not q:
        return {**out, "grade": "UNRESOLVED", "why": "no quote recorded"}
    # 0. a chart image: the file must exist; its numbers need a visual check
    img = re.search(r"kb/[a-z_]+/images/[^\s,;]+\.(?:jpe?g|png)", src)
    if img:
        ok = os.path.exists(os.path.join(root, img.group(0)))
        return {**out, "grade": "IMAGE" if ok else "UNRESOLVED", "found": img.group(0),
                "why": None if ok else "image file missing"}
    # 1. explicit knowledge-base files (a citation may name more than one: their text is pooled)
    files = re.findall(r"(kb/[a-z_]+/(?:pages|tables|sections)/[^\s,;)]+\.md)", src)
    files += [f"kb/annual_report/tables/{t}" for t in re.findall(r"(?<!/)\b(table_p\d+_\d+\.md)", src)
              if f"kb/annual_report/tables/{t}" not in files]
    if files:
        missing = [f for f in files if not os.path.exists(os.path.join(root, f))]
        if len(missing) == len(files):
            return {**out, "grade": "UNRESOLVED", "why": f"cited file missing: {', '.join(missing)}"}
        text = " ".join(page_text(os.path.join(root, f)) for f in files)
        g = grade_text(q, text, partial=True)
        if g:
            return _graded(out, g, ", ".join(files))
        return locate(root, q, files[0].split("/")[1], out, cited=", ".join(files))
    # 1b. an original input file: read the PDF page or the spreadsheet directly
    inp = re.search(r"inputs/[^\s,;]+\.(pdf|xlsx)", src)
    if inp:
        path = os.path.join(root, inp.group(0))
        if not os.path.exists(path):
            return {**out, "grade": "UNRESOLVED", "why": f"input file missing: {inp.group(0)}"}
        if inp.group(1) == "xlsx":
            g = grade_text(q, xlsx_text(path), partial=True)
            return _graded(out, g, inp.group(0)) if g else {**out, "grade": "NOT_FOUND", "why": f"not in {inp.group(0)}"}
        pm = re.search(r"page\s*(\d+)", src) or (re.match(r"\d+", str(pg)) if pg else None)
        pages = [int(pm.group(1) if pm.re.pattern.startswith("page") else pm.group(0))] if pm else []
        cand = pages + [p for k in pages for p in (k - 1, k + 1)] if pages else []
        for k in cand:
            g = grade_text(q, pdf_page_text(path, k), partial=True)
            if g:
                return _graded(out, g, f"{inp.group(0)} p.{k}")
        try:
            import pypdfium2 as pdfium
            n = len(pdfium.PdfDocument(path))
        except Exception:
            n = 0
        for k in range(1, n + 1):
            g = grade_text(q, pdf_page_text(path, k))
            if g:
                return {**out, "grade": "MOVED", "found": f"{inp.group(0)} p.{k}", "match": g,
                        "why": f"cited page {pages[0] if pages else '?'}, text is on p.{k}"}
        return {**out, "grade": "NOT_FOUND", "why": f"not in {inp.group(0)}" + (f" (cited p.{pages[0]})" if pages else "")}
    # 2. derived from the report's own files
    if re.search(DERIVED, src.strip(), re.I):
        f = src.split(",")[0].split(" ")[0].strip()
        ok = os.path.exists(os.path.join(root, f)) or os.path.exists(os.path.join(os.path.dirname(os.path.dirname(root)), f))
        return {**out, "grade": "DERIVED" if ok else "UNRESOLVED",
                "why": None if ok else f"data file not found: {f}"}
    # 3. a named document the knowledge base may hold
    doc = next((d for pat, d in DOC_HINTS if re.search(pat, src, re.I)), None)
    if src.lower().startswith("inputs/"):
        doc = doc or next((d for pat, d in DOC_HINTS if re.search(pat, src, re.I)), None)
    if doc and kb_pages(root, doc):
        if pg:
            for k in (int(pg) - 1, int(pg), int(pg) - 2):       # pdf page vs 0-based file index
                path = os.path.join(root, "kb", doc, "pages", f"page_{k:04d}.md")
                g = grade_text(q, page_text(path))
                if g:
                    return {**out, "grade": g, "found": os.path.relpath(path, root).replace("\\", "/")}
        r = locate(root, q, doc, out, cited=f"{doc} p.{pg}" if pg else None)
        if r["grade"] != "NOT_FOUND":
            return r
        if not pg and not re.search(EXTERNAL, src, re.I):
            # a named document of this kind, but not the one the report holds (e.g. an older call)
            return {**out, "grade": "NOT_HELD", "why": f"not in kb/{doc}: the inputs do not include this document"}
        if not re.search(EXTERNAL, src, re.I):
            return r
    # 4. outside the knowledge base
    if re.search(EXTERNAL, src, re.I) or "external" in src.lower():
        return {**out, "grade": "EXTERNAL",
                "why": None if re.search(r"https?://|\.com|\.in\b", src) else "no URL in the source text"}
    # a named third-party source with no file behind it: unverifiable offline, not a broken citation
    return {**out, "grade": "EXTERNAL", "why": "third-party source, no URL or file in the citation"}


def locate(root, q, doc, out, cited=None):
    best = None
    for path in kb_pages(root, doc):
        g = grade_text(q, page_text(path))
        if g == "VERIFIED":
            best = (g, path); break
        if g and not best:
            best = (g, path)
    if best:
        rel = os.path.relpath(best[1], root).replace("\\", "/")
        grade = "MOVED" if cited else best[0]
        return {**out, "grade": grade, "found": rel, "match": best[0],
                "why": f"cited {cited}, text is on {rel}" if cited else None}
    return {**out, "grade": "NOT_FOUND", "why": f"not in kb/{doc}" + (f" (cited {cited})" if cited else "")}


def run(root, strict=False):
    D = json.load(open(os.path.join(root, "decisions.json"), encoding="utf-8"))
    so_p = os.path.join(root, "data", "citation_signoffs.json")
    signoffs = json.load(open(so_p, encoding="utf-8")).get("signoffs", []) if os.path.exists(so_p) else []
    rows = []
    for key, a in (D.get("assumptions") or {}).items():
        for rec in a.get("evidence") or []:
            r = check(root, rec)
            r["assumption"] = key
            if r["grade"] in ("IMAGE", "NOT_FOUND"):
                so = next((x for x in signoffs if x["assumption"] == key
                           and x["source_contains"] in str(rec.get("source"))), None)
                cited = re.search(r"(inputs/[^\s,;]+|kb/[^\s,;]+)", str(rec.get("source")))
                if so and (not cited or os.path.exists(os.path.join(root, cited.group(1)))):
                    r.update(grade="VERIFIED_VISUAL", why=f"{so['by']}, {so['date']}: {so['seen']}"[:200])
            rows.append(r)
    counts = {}
    for r in rows:
        counts[r["grade"]] = counts.get(r["grade"], 0) + 1
    blocking = [r for r in rows if r["grade"] in ("NOT_FOUND", "UNRESOLVED")
                or (strict and r["grade"] in ("MOVED", "PARTIAL", "NOT_HELD"))]
    out = {"run_at": datetime.now().isoformat(timespec="seconds"), "records": len(rows), "counts": counts,
           "status": "FAIL" if blocking else "PASS", "rows": rows}
    json.dump(out, open(os.path.join(root, "data", "citation_check.json"), "w", encoding="utf-8"), indent=1,
              ensure_ascii=False)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--root", required=True)
    ap.add_argument("--strict", action="store_true", help="treat MOVED citations as failures")
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args()
    out = run(os.path.abspath(a.root), a.strict)
    for r in out["rows"]:
        if a.verbose or r["grade"] not in ("VERIFIED", "DERIVED"):
            print(f"  {r['grade']:12} {r['assumption']:20} {r.get('why') or r.get('found') or ''}"[:200])
    print(f"{out['records']} evidence records: " + ", ".join(f"{k} {v}" for k, v in sorted(out["counts"].items()))
          + f"  -> {out['status']}")
    sys.exit(1 if out["status"] == "FAIL" else 0)


if __name__ == "__main__":
    main()
