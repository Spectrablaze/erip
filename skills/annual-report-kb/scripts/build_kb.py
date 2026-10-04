#!/usr/bin/env python3
"""Stage 2 - assemble the deterministic half of the knowledge base.

Consumes the chunk artifacts written by parse_pdf.py and produces everything
that can be derived without judgement:

    metadata/pages.json          per-page extraction method, counts, char totals
    metadata/toc.json            Marker's outline plus every detected header
    tables/table_pNNNN_K.md      one markdown file per table, with provenance
    metadata/table_index.json    table catalogue
    pages/page_NNNN.md           per-page markdown (the read-one-page-at-a-time unit)
    _work/section_candidates.json  header list for the agent to turn into a plan
    _work/image_candidates.json    image list + caption/context for classification

Section naming and image classification are judgement calls and are left to the
agent; this script only assembles the evidence for them. apply_plan.py writes
the results back.

Usage:
    python build_kb.py --work "<Company> AR/_work" --out "<Company> AR"
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

PAGE_MARKER = re.compile(r"\{(\d+)\}-{10,}")


def log(msg: str) -> None:
    print(f"[build] {msg}", flush=True)


def slug(text: str, maxlen: int = 60) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "_", (text or "").strip().lower()).strip("_")
    return (s[:maxlen].rstrip("_") or "untitled")


def load_chunks(work: Path) -> tuple[list[dict], dict[int, str]]:
    """Return (chunk payloads sorted by first page, {abs_page: markdown})."""
    cdir = work / "chunks"
    if not cdir.exists():
        log(f"ERROR: no chunks directory at {cdir} - run parse_pdf.py first")
        sys.exit(2)

    payloads, page_md = [], {}
    for jf in sorted(cdir.glob("chunk_*.json")):
        try:
            payloads.append(json.loads(jf.read_text(encoding="utf-8")))
        except Exception as e:  # noqa: BLE001
            log(f"WARNING: unreadable {jf.name}: {e}")
            continue
        mf = jf.with_suffix(".md")
        if not mf.exists():
            continue
        text = mf.read_text(encoding="utf-8")
        marks = list(PAGE_MARKER.finditer(text))
        for i, m in enumerate(marks):
            end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
            body = text[m.end():end].strip()
            page_md[int(m.group(1))] = body
    payloads.sort(key=lambda p: (p.get("pages") or [0])[0])
    return payloads, page_md


def main() -> int:
    ap = argparse.ArgumentParser(description="Assemble the deterministic knowledge base")
    ap.add_argument("--work", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    work = Path(args.work).expanduser().resolve()
    out = Path(args.out).expanduser().resolve()
    for sub in ("context", "sections", "tables", "entities", "metadata", "pages"):
        (out / sub).mkdir(parents=True, exist_ok=True)

    payloads, page_md = load_chunks(work)
    if not payloads:
        log("ERROR: no chunk payloads found")
        return 2

    state = {}
    sf = work / "state.json"
    if sf.exists():
        state = json.loads(sf.read_text(encoding="utf-8"))
    total_pages = state.get("total_pages")

    headers, tables, images, page_stats, toc_raw = [], [], [], [], []
    for p in payloads:
        headers += p.get("headers", [])
        tables += p.get("tables", [])
        images += p.get("images", [])
        page_stats += p.get("page_stats", [])
        toc_raw += p.get("toc", [])
    headers.sort(key=lambda h: (h["page"], h.get("bbox", [0, 0])[1]))
    tables.sort(key=lambda t: (t["page"], t.get("bbox", [0, 0])[1]))
    images.sort(key=lambda i: (i["page"], i.get("bbox", [0, 0])[1]))

    # ---- per-page markdown ------------------------------------------------
    pages_dir = out / "pages"
    for pg, md in sorted(page_md.items()):
        (pages_dir / f"page_{pg:04d}.md").write_text(
            f"<!-- page {pg} (0-based) | pdf page {pg + 1} -->\n\n{md}\n",
            encoding="utf-8",
        )
    log(f"wrote {len(page_md)} page files")

    # ---- pages.json -------------------------------------------------------
    stat_by_page = {}
    for ps in page_stats:
        ap_ = ps.get("abs_page", ps.get("page_id"))
        if ap_ is not None:
            stat_by_page[int(ap_)] = ps
    tbl_by_page, img_by_page = Counter(t["page"] for t in tables), Counter(i["page"] for i in images)

    pages_json = []
    parsed = sorted(page_md)
    for pg in parsed:
        ps = stat_by_page.get(pg, {})
        body = page_md.get(pg, "")
        pages_json.append({
            "page": pg,
            "pdf_page": pg + 1,
            "file": f"pages/page_{pg:04d}.md",
            "chars": len(body),
            "text_extraction_method": ps.get("text_extraction_method"),
            "block_counts": dict(ps.get("block_counts") or []),
            "tables": tbl_by_page.get(pg, 0),
            "images": img_by_page.get(pg, 0),
            "empty": len(body.strip()) < 40,
        })
    (out / "metadata" / "pages.json").write_text(
        json.dumps({"total_pdf_pages": total_pages, "parsed_pages": len(pages_json),
                    "pages": pages_json}, indent=2), encoding="utf-8")

    # ---- toc.json ---------------------------------------------------------
    seen, toc_items = set(), []
    for t in toc_raw:
        # Outline titles routinely carry hard line breaks from the source layout;
        # collapse them so one entry stays one line.
        key = (re.sub(r"\s+", " ", str(t.get("title", ""))).strip(), t.get("page_id"))
        if key in seen or not key[0]:
            continue
        seen.add(key)
        toc_items.append({"title": key[0], "page": t.get("page_id"), "level": t.get("heading_level")})
    (out / "metadata" / "toc.json").write_text(
        json.dumps({"outline_from_pdf": toc_items,
                    "detected_headers": [{"page": h["page"], "text": h["text"]} for h in headers]},
                   indent=2), encoding="utf-8")
    log(f"toc: {len(toc_items)} outline entries, {len(headers)} detected headers")

    # ---- tables -----------------------------------------------------------
    tdir, tindex, per_page = out / "tables", [], Counter()
    unextracted = 0
    for t in tables:
        if not (t.get("markdown") or "").strip():
            # Detected but not reconstructable. Point at the page so the numbers
            # are still findable - they remain in the page markdown.
            unextracted += 1
            tindex.append({
                "file": None, "page": t["page"], "pdf_page": t["page"] + 1,
                "section": t.get("section", ""), "caption": t.get("caption", ""),
                "extracted": False,
                "note": "table detected but no grid reconstructed; text is in "
                        f"pages/page_{t['page']:04d}.md",
                "source_page_file": f"pages/page_{t['page']:04d}.md",
            })
            continue
        per_page[t["page"]] += 1
        name = f"table_p{t['page']:04d}_{per_page[t['page']]}"
        title = t.get("caption") or t.get("section") or ""
        fm = [
            "---",
            f"page: {t['page']}",
            f"pdf_page: {t['page'] + 1}",
            f"section: {json.dumps(t.get('section', ''))}",
            f"caption: {json.dumps(title)}",
            f"source: pages/page_{t['page']:04d}.md",
            "---",
            "",
            f"# {title or name}",
            "",
            t["markdown"],
            "",
        ]
        (tdir / f"{name}.md").write_text("\n".join(fm), encoding="utf-8")
        tindex.append({
            "file": f"tables/{name}.md", "page": t["page"], "pdf_page": t["page"] + 1,
            "section": t.get("section", ""), "caption": title,
            "n_rows": t.get("n_rows", 0), "extracted": True,
            "source_page_file": f"pages/page_{t['page']:04d}.md",
        })
    written = sum(1 for t in tindex if t.get("extracted"))
    (out / "metadata" / "table_index.json").write_text(
        json.dumps({"count": len(tindex), "extracted": written,
                    "detected_not_extracted": unextracted, "tables": tindex},
                   indent=2), encoding="utf-8")
    log(f"wrote {written} tables ({unextracted} detected but not reconstructable)")

    # ---- candidates for the agent ----------------------------------------
    cand_sections = [{
        "page": h["page"], "pdf_page": h["page"] + 1,
        "text": re.sub(r"\s+", " ", h["text"]).strip(),
    } for h in headers if (h.get("text") or "").strip()]
    (work / "section_candidates.json").write_text(
        json.dumps({
            "note": "Turn these into _work/section_plan.json - see references/pipeline.md",
            "outline_from_pdf": toc_items,
            "headers": cand_sections,
        }, indent=2), encoding="utf-8")

    # A long report yields thousands of headers; the JSON above is far too heavy
    # to read into context just to choose section boundaries. Emit a compact
    # listing - one line per header - and prefer it when planning sections.
    outline_pages = {t["page"] for t in toc_items if t.get("page") is not None}
    lines = [
        f"# Section candidates ({len(cand_sections)} headers over "
        f"{len(page_md)} parsed pages)",
        "",
        "`*` marks a page that also appears in the PDF's own outline - those are",
        "the strongest section boundaries. Page numbers are 0-based.",
        "",
    ]
    if toc_items:
        lines += ["## PDF outline", ""]
        lines += [f"- p{t['page']} | {t['title']}"
                  for t in toc_items if t.get("page") is not None]
        lines += ["", "## All detected headers", ""]
    prev = None
    for h in cand_sections:
        if h["page"] != prev:
            prev = h["page"]
        mark = "*" if h["page"] in outline_pages else " "
        lines.append(f"{mark} p{h['page']:<5} {h['text'][:95]}")
    (work / "section_candidates.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    for im in images:
        im["pdf_page"] = im["page"] + 1
    (work / "image_candidates.json").write_text(
        json.dumps({
            "note": "Classify each into _work/image_plan.json - see references/pipeline.md",
            "images": images,
        }, indent=2), encoding="utf-8")
    log(f"candidates: {len(cand_sections)} headers, {len(images)} images")

    # ---- manifest skeleton ------------------------------------------------
    (out / "metadata" / "build_stats.json").write_text(json.dumps({
        "total_pdf_pages": total_pages,
        "parsed_pages": len(pages_json),
        "tables": len(tindex),
        "images": len(images),
        "headers": len(headers),
        "failed_chunks": state.get("failed", []),
        "ocr_pages": sum(1 for p in pages_json if (p.get("text_extraction_method") or "") == "surya"),
        "empty_pages": sum(1 for p in pages_json if p["empty"]),
    }, indent=2), encoding="utf-8")

    log("stage 2 complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
