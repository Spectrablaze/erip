#!/usr/bin/env python3
"""Stage 4 - validate the knowledge base and write manifest.json + parse_report.md.

Checks the things that silently ruin a downstream research pass: pages that
never got parsed, chunks that failed, pages that came back empty, OCR fallback
concentrations, duplicate images, context files left as stubs, and links that
point at files which do not exist.

Exit code is 0 even when warnings are present; it returns 1 only when the
knowledge base is structurally unusable (no pages, no sections). Warnings are
meant to be read, not to abort a 3-hour parse.

Usage:
    python validate_kb.py --work "<Company> AR/_work" --out "<Company> AR"
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
CONTEXT_FILES = [
    "company_overview.md", "business_model.md", "products.md", "business_segments.md",
    "manufacturing.md", "management.md", "directors.md", "subsidiaries.md",
    "risks.md", "sustainability.md", "financial_summary.md", "glossary.md",
]
ENTITY_FILES = ["directors.json", "executives.json", "subsidiaries.json",
                "plants.json", "products.json", "brands.json", "locations.json"]


def log(msg: str) -> None:
    print(f"[validate] {msg}", flush=True)


def load(p: Path, default=None):
    if not p.exists():
        return default
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return default


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate the knowledge base")
    ap.add_argument("--work", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--company", default=None)
    ap.add_argument("--year", default=None)
    args = ap.parse_args()

    work = Path(args.work).expanduser().resolve()
    out = Path(args.out).expanduser().resolve()
    warnings: list[str] = []
    errors: list[str] = []

    pages_meta = load(out / "metadata" / "pages.json", {}) or {}
    pages = pages_meta.get("pages", [])
    total_pdf = pages_meta.get("total_pdf_pages")
    state = load(work / "state.json", {}) or {}
    tindex = load(out / "metadata" / "table_index.json", {}) or {}
    iindex = load(out / "metadata" / "image_index.json", {}) or {}
    sindex = load(out / "metadata" / "section_index.json", {}) or {}

    if not pages:
        errors.append("metadata/pages.json is missing or empty - the parse produced nothing")
    if not sindex.get("sections"):
        warnings.append("no sections built - apply_plan.py has not run with a section_plan.json")

    # ---- coverage ---------------------------------------------------------
    parsed_nums = {p["page"] for p in pages}
    missing = []
    if isinstance(total_pdf, int) and total_pdf > 0:
        missing = [i for i in range(total_pdf) if i not in parsed_nums]
        if missing:
            rng = f"{missing[0]}-{missing[-1]}" if len(missing) > 3 else str(missing)
            warnings.append(f"{len(missing)} of {total_pdf} pages were never parsed (e.g. {rng})")

    for f in state.get("failed", []):
        errors.append(f"chunk {f.get('chunk')} failed: {f.get('error')}")

    empty = [p["page"] for p in pages if p.get("empty")]
    if empty:
        pct = 100.0 * len(empty) / max(len(pages), 1)
        msg = f"{len(empty)} parsed pages are empty/near-empty ({pct:.1f}%)"
        (warnings if pct < 25 else errors).append(msg)

    methods = Counter((p.get("text_extraction_method") or "unknown") for p in pages)
    ocr_pages = [p["page"] for p in pages
                 if (p.get("text_extraction_method") or "") not in ("pdftext", "hybrid", "")]
    if len(ocr_pages) > 0.5 * max(len(pages), 1):
        warnings.append(f"{len(ocr_pages)} pages fell back to OCR - scanned or image-heavy "
                        f"source; spot-check numbers in financial tables")

    n_tables = tindex.get("count", 0)
    n_unreconstructed = tindex.get("detected_not_extracted", 0)
    if n_tables and n_unreconstructed / n_tables > 0.3:
        warnings.append(
            f"{n_unreconstructed} of {n_tables} detected tables could not be "
            f"reconstructed into a grid. Their text is still in the page files. "
            f"If financial tables are affected, enable an OCR backend "
            f"(see references/troubleshooting.md) and re-run with --force")

    # ---- duplicate images -------------------------------------------------
    dup_groups = 0
    imgs = iindex.get("images", [])
    if imgs:
        by_hash = defaultdict(list)
        for e in imgs:
            f = out / e["file"]
            if not f.exists():
                errors.append(f"image_index references missing file: {e['file']}")
                continue
            try:
                by_hash[hashlib.md5(f.read_bytes()).hexdigest()].append(e["file"])
            except Exception:  # noqa: BLE001
                continue
        dups = {h: v for h, v in by_hash.items() if len(v) > 1}
        dup_groups = len(dups)
        if dups:
            n = sum(len(v) - 1 for v in dups.values())
            warnings.append(f"{n} duplicate image file(s) across {dup_groups} group(s) "
                            f"(logos/decorations repeat on every page)")
        unclassified = sum(1 for e in imgs if not e.get("classified"))
        if unclassified:
            warnings.append(f"{unclassified} of {len(imgs)} images were not classified "
                            f"(filed under images/other)")

    # ---- required files ---------------------------------------------------
    missing_ctx = [f for f in CONTEXT_FILES if not (out / "context" / f).exists()]
    if missing_ctx:
        warnings.append(f"context files not written: {', '.join(missing_ctx)}")
    stub_ctx = [f for f in CONTEXT_FILES
                if (out / "context" / f).exists() and len((out / "context" / f).read_text(encoding="utf-8").strip()) < 200]
    if stub_ctx:
        warnings.append(f"context files look like stubs (<200 chars): {', '.join(stub_ctx)}")

    missing_ent = [f for f in ENTITY_FILES if not (out / "entities" / f).exists()]
    if missing_ent:
        warnings.append(f"entity files not written: {', '.join(missing_ent)}")

    entity_counts = {}
    for f in ENTITY_FILES:
        data = load(out / "entities" / f)
        if data is None:
            continue
        items = data if isinstance(data, list) else (data.get(Path(f).stem) or data.get("items") or [])
        entity_counts[Path(f).stem] = len(items) if isinstance(items, list) else 0

    # ---- broken links -----------------------------------------------------
    broken = []
    for md in list(out.glob("*.md")) + list((out / "context").glob("*.md")):
        for m in LINK_RE.finditer(md.read_text(encoding="utf-8")):
            target = m.group(1).split("#")[0].strip()
            if not target or target.startswith(("http://", "https://", "mailto:")):
                continue
            if not (out / target).exists() and not (md.parent / target).exists():
                broken.append(f"{md.relative_to(out)} -> {target}")
    if broken:
        warnings.append(f"{len(broken)} broken internal link(s); first: {broken[0]}")

    # ---- manifest ---------------------------------------------------------
    company = args.company or out.name.replace(" Annual Report", "").strip()
    manifest = {
        "company_name": company,
        "report_year": args.year,
        "source_pdf": state.get("pdf"),
        "generated": date.today().isoformat(),
        "page_count": total_pdf,
        "pages_parsed": len(pages),
        "sections_created": len(sindex.get("sections", [])),
        "images_extracted": len(imgs),
        "images_classified": sum(1 for e in imgs if e.get("classified")),
        "tables_detected": tindex.get("count", 0),
        "tables_extracted": tindex.get("extracted", tindex.get("count", 0)),
        "tables_detected_not_extracted": tindex.get("detected_not_extracted", 0),
        "entities_extracted": entity_counts,
        "context_files_created": [f for f in CONTEXT_FILES if (out / "context" / f).exists()],
        "text_extraction_methods": dict(methods),
        "warnings": len(warnings),
        "errors": len(errors),
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    # ---- parse_report.md --------------------------------------------------
    lines = [
        f"# Parse Report - {company}", "",
        f"Generated {date.today().isoformat()} from `{Path(state.get('pdf') or '?').name}`.", "",
        "## Coverage", "",
        f"| Metric | Value |", "|---|---|",
        f"| Pages in PDF | {total_pdf if total_pdf is not None else 'unknown'} |",
        f"| Pages parsed | {len(pages)} |",
        f"| Pages never parsed | {len(missing)} |",
        f"| Empty / near-empty pages | {len(empty)} |",
        f"| Sections created | {len(sindex.get('sections', []))} |",
        f"| Tables extracted | {tindex.get('extracted', tindex.get('count', 0))} |",
        f"| Tables detected but not reconstructable | {tindex.get('detected_not_extracted', 0)} |",
        f"| Images extracted | {len(imgs)} |",
        f"| Images classified | {sum(1 for e in imgs if e.get('classified'))} |",
        f"| Duplicate image groups | {dup_groups} |",
        "",
        "## Text extraction methods", "",
        "| Method | Pages |", "|---|---|",
    ]
    lines += [f"| {k} | {v} |" for k, v in methods.most_common()]
    lines += ["", "## Entities", "", "| Type | Count |", "|---|---|"]
    lines += [f"| {k} | {v} |" for k, v in sorted(entity_counts.items())] or ["| (none) | 0 |"]

    lines += ["", "## Errors", ""]
    lines += [f"- {e}" for e in errors] or ["- none"]
    lines += ["", "## Warnings", ""]
    lines += [f"- {w}" for w in warnings] or ["- none"]

    if missing:
        lines += ["", "## Unparsed pages", "",
                  "Rerun `parse_pdf.py` (it resumes) to fill these:", "",
                  "```", ", ".join(str(m) for m in missing[:200]) +
                  (" ..." if len(missing) > 200 else ""), "```"]
    if broken:
        lines += ["", "## Broken links", ""] + [f"- {b}" for b in broken[:40]]

    (out / "parse_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    log(f"manifest.json + parse_report.md written")
    log(f"{len(errors)} error(s), {len(warnings)} warning(s)")
    for e in errors:
        log(f"  ERROR: {e}")
    for w in warnings:
        log(f"  warn: {w}")

    return 1 if (not pages) else 0


if __name__ == "__main__":
    sys.exit(main())
