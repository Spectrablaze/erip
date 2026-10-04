#!/usr/bin/env python3
"""Stage 1 - parse an annual report PDF with Marker into resumable page chunks.

Loads the Marker models once, then walks the PDF in fixed-size page chunks. Each
chunk is built into a Document a single time and rendered twice:

  * MarkdownRenderer (paginate_output=True) -> text with ``{page}`` markers
  * JSONRenderer                            -> block structure, bbox, section
                                               hierarchy, per-page OCR stats

Rendering twice off one build is deliberate: the build (layout + OCR) is ~99% of
the cost, the renders are nearly free, and the two formats carry different
information that later stages both need.

Image pixels are pulled straight off the Document blocks rather than from the
renderer, because JSONRenderer discards images and MarkdownRenderer names files
after block ids only - neither preserves the page attribution the knowledge base
is built around.

Chunk artifacts land in <work>/chunks/ and completed chunks are recorded in
<work>/state.json, so re-running resumes instead of restarting. This matters:
an 855-page report on CPU runs for hours.

Usage:
    python parse_pdf.py REPORT.pdf --work "<Company> Annual Report/_work"
    python parse_pdf.py REPORT.pdf --work ... --pages 0-19   # smoke test
    python parse_pdf.py REPORT.pdf --work ... --force        # ignore state
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import traceback
from pathlib import Path

os.environ.setdefault("GRPC_VERBOSITY", "ERROR")
os.environ.setdefault("GLOG_minloglevel", "2")
os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

IMAGE_TYPES = {"Picture", "Figure", "Diagram"}


def log(msg: str) -> None:
    print(f"[parse] {msg}", flush=True)


def human_time(sec: float) -> str:
    sec = int(sec)
    if sec < 60:
        return f"{sec}s"
    if sec < 3600:
        return f"{sec // 60}m{sec % 60:02d}s"
    return f"{sec // 3600}h{(sec % 3600) // 60:02d}m"


# --------------------------------------------------------------------------
# state
# --------------------------------------------------------------------------
class State:
    def __init__(self, path: Path):
        self.path = path
        self.data = {"done": [], "failed": [], "pdf": None, "total_pages": None}
        if path.exists():
            try:
                self.data.update(json.loads(path.read_text(encoding="utf-8")))
            except Exception:
                log("state.json unreadable - starting fresh")

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, indent=2), encoding="utf-8")

    def is_done(self, name: str) -> bool:
        return name in self.data["done"]

    def mark_done(self, name: str) -> None:
        if name not in self.data["done"]:
            self.data["done"].append(name)
        self.data["failed"] = [f for f in self.data["failed"] if f.get("chunk") != name]
        self.save()

    def mark_failed(self, name: str, err: str) -> None:
        self.data["failed"] = [f for f in self.data["failed"] if f.get("chunk") != name]
        self.data["failed"].append({"chunk": name, "error": err})
        self.save()


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def parse_pages_arg(spec: str | None, total: int) -> list[int]:
    """Expand '0-19,30,40-45' into a sorted list of 0-based page indices."""
    if not spec:
        return list(range(total))
    out: set[int] = set()
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            out.update(range(int(a), int(b) + 1))
        else:
            out.add(int(part))
    return sorted(p for p in out if 0 <= p < total)


def walk_blocks(block: dict, page_id: int):
    """Yield every block dict in a JSONRenderer page subtree, depth-first."""
    for child in block.get("children") or []:
        yield page_id, child
        yield from walk_blocks(child, page_id)


def bbox_of(b: dict) -> list[float]:
    bb = b.get("bbox") or [0, 0, 0, 0]
    return [round(float(x), 1) for x in bb]


def html_to_text(html: str) -> str:
    from bs4 import BeautifulSoup

    return BeautifulSoup(html or "", "html.parser").get_text(" ", strip=True)


def nearest_caption(img_bbox, captions):
    """Pick the caption block whose vertical gap to the image is smallest."""
    if not captions:
        return None
    ix0, iy0, ix1, iy1 = img_bbox
    best, best_d = None, 1e9
    for c in captions:
        cx0, cy0, cx1, cy1 = c["bbox"]
        # vertical gap (caption above or below), plus horizontal misalignment
        if cy0 >= iy1:
            gap = cy0 - iy1
        elif cy1 <= iy0:
            gap = iy0 - cy1
        else:
            gap = 0.0
        icx, ccx = (ix0 + ix1) / 2, (cx0 + cx1) / 2
        d = gap + abs(icx - ccx) * 0.25
        if d < best_d:
            best, best_d = c, d
    # ignore captions far from the image (likely belongs to something else)
    return best if best_d < 250 else None


def table_html_to_markdown(html: str) -> str:
    """Flatten an HTML table to GitHub-flavoured markdown.

    Spans are expanded by repeating the cell value so column counts stay
    rectangular - equity models care about the numbers lining up, not about
    faithfully reproducing merged-cell presentation.
    """
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html or "", "html.parser")
    table = soup.find("table") or soup
    rows = table.find_all("tr")
    if not rows:
        return ""

    grid: list[list[str]] = []
    pending: dict[tuple[int, int], str] = {}
    for r_i, tr in enumerate(rows):
        row: list[str] = []
        c_i = 0
        while (r_i, c_i) in pending:
            row.append(pending.pop((r_i, c_i)))
            c_i += 1
        for cell in tr.find_all(["td", "th"]):
            text = cell.get_text(" ", strip=True).replace("|", "\\|")
            try:
                cs = int(cell.get("colspan", 1) or 1)
                rs = int(cell.get("rowspan", 1) or 1)
            except ValueError:
                cs = rs = 1
            cs, rs = max(1, min(cs, 40)), max(1, min(rs, 100))
            for k in range(cs):
                row.append(text)
                for extra in range(1, rs):
                    pending[(r_i + extra, c_i + k)] = text
                c_i += 1
                while (r_i, c_i) in pending:
                    row.append(pending.pop((r_i, c_i)))
                    c_i += 1
        grid.append(row)

    width = max(len(r) for r in grid)
    grid = [r + [""] * (width - len(r)) for r in grid]

    head, body = grid[0], grid[1:]
    lines = ["| " + " | ".join(head) + " |",
             "|" + "|".join(["---"] * width) + "|"]
    lines += ["| " + " | ".join(r) + " |" for r in body]
    return "\n".join(lines)


def resolve_page_ids(rendered_pages: list[dict], requested: list[int]) -> dict[int, int]:
    """Map JSON page index -> absolute PDF page number (0-based).

    Marker normally keeps original page ids when page_range is set. Verify that
    rather than trusting it: if the ids come back 0-based-local, fall back to
    positional mapping against the requested range.
    """
    ids = []
    for p in rendered_pages:
        pid = p.get("id", "")
        try:
            ids.append(int(str(pid).split("/")[2]))
        except (IndexError, ValueError):
            ids.append(None)
    if all(i is not None for i in ids) and set(ids) == set(requested[: len(ids)]):
        return {i: v for i, v in enumerate(ids)}
    return {i: requested[i] for i in range(min(len(rendered_pages), len(requested)))}


# --------------------------------------------------------------------------
# chunk processing
# --------------------------------------------------------------------------
def process_chunk(converter, pdf, pages, work: Path, name: str, img_dir: Path) -> dict:
    from marker.renderers.json import JSONRenderer
    from marker.renderers.markdown import MarkdownRenderer

    converter.config["page_range"] = pages
    doc = converter.build_document(str(pdf))

    md_out = converter.resolve_dependencies(MarkdownRenderer)(doc)
    json_out = converter.resolve_dependencies(JSONRenderer)(doc)
    jd = json.loads(json_out.model_dump_json())

    pagemap = resolve_page_ids(jd.get("children", []), pages)

    # ---- structural pass over the JSON render ----------------------------
    blocks_by_page: dict[int, list[dict]] = {}
    for idx, page in enumerate(jd.get("children", [])):
        abs_page = pagemap.get(idx, pages[idx] if idx < len(pages) else -1)
        collected = []
        for _, b in walk_blocks(page, abs_page):
            bt = b.get("block_type")
            if bt in ("Line", "Span", "Char", "TableCell"):
                continue
            collected.append(b)
        blocks_by_page[abs_page] = collected

    # section_hierarchy maps level -> the *block id* of the governing header
    # (e.g. "/page/20/SectionHeader/12"), not its text. Resolve ids to titles
    # first so tables and images carry a human-readable section name.
    header_text_by_id: dict[str, str] = {}
    for abs_page, blocks in blocks_by_page.items():
        for b in blocks:
            if b.get("block_type") == "SectionHeader":
                header_text_by_id[str(b.get("id"))] = html_to_text(b.get("html", ""))

    def section_name_of(b: dict) -> str:
        sect = b.get("section_hierarchy") or {}
        if not sect:
            return ""
        deepest = max((int(k) for k in sect), default=None)
        if deepest is None:
            return ""
        ref = str(sect.get(str(deepest), ""))
        return header_text_by_id.get(ref, "") or ""

    headers, tables, image_meta = [], [], []
    for abs_page, blocks in blocks_by_page.items():
        captions = [
            {"bbox": bbox_of(b), "text": html_to_text(b.get("html", ""))}
            for b in blocks
            if b.get("block_type") == "Caption"
        ]
        page_text = " ".join(
            html_to_text(b.get("html", ""))
            for b in blocks
            if b.get("block_type") in ("Text", "TextInlineMath", "ListItem")
        )[:600]

        for b in blocks:
            bt = b.get("block_type")
            sect_name = section_name_of(b)

            if bt == "SectionHeader":
                headers.append({
                    "page": abs_page,
                    "text": html_to_text(b.get("html", "")),
                    "bbox": bbox_of(b),
                    "id": b.get("id"),
                })
            elif bt == "Table":
                md = table_html_to_markdown(b.get("html", ""))
                tables.append({
                    "id": b.get("id"),
                    "page": abs_page,
                    "section": sect_name,
                    "bbox": bbox_of(b),
                    "markdown": md,
                    # A detected table with no reconstructable grid - usually an
                    # infographic laid out as a table, or (with --disable-ocr) one
                    # the pdftext heuristics could not resolve. Its text still
                    # appears in the page markdown, so record it rather than drop it.
                    "extracted": bool(md.strip()),
                    "n_rows": md.count("\n") - 1 if md else 0,
                    "caption": (nearest_caption(bbox_of(b), captions) or {}).get("text", ""),
                })
            elif bt in IMAGE_TYPES:
                cap = nearest_caption(bbox_of(b), captions) or {}
                image_meta.append({
                    "id": b.get("id"),
                    "page": abs_page,
                    "block_type": bt,
                    "bbox": bbox_of(b),
                    "section": sect_name,
                    "caption": cap.get("text", ""),
                    "page_text_snippet": page_text,
                })

    # ---- image pixels straight off the Document --------------------------
    img_dir.mkdir(parents=True, exist_ok=True)
    by_id = {m["id"]: m for m in image_meta}
    saved = 0
    for page in doc.pages:
        for blk in page.children or []:
            bt = str(blk.block_type)
            if bt not in IMAGE_TYPES:
                continue
            bid = str(blk.id)
            meta = by_id.get(bid)
            abs_page = meta["page"] if meta else page.page_id
            fname = f"p{abs_page:04d}_{bt.lower()}_{blk.block_id}.jpg"
            try:
                im = blk.get_image(doc, highres=True)
                if im is None:
                    continue
                if im.mode != "RGB":
                    im = im.convert("RGB")
                if im.width < 8 or im.height < 8:
                    continue
                im.save(img_dir / fname, "JPEG", quality=88)
                saved += 1
                if meta is not None:
                    meta["file"] = f"_raw/{fname}"
                    meta["width"], meta["height"] = im.width, im.height
            except Exception as e:  # noqa: BLE001 - one bad crop must not kill the chunk
                log(f"  ! image {bid} failed: {e}")

    image_meta = [m for m in image_meta if m.get("file")]

    # ---- persist ---------------------------------------------------------
    cdir = work / "chunks"
    cdir.mkdir(parents=True, exist_ok=True)
    (cdir / f"{name}.md").write_text(md_out.markdown, encoding="utf-8")

    page_stats = json_out.metadata.get("page_stats", [])
    for i, ps in enumerate(page_stats):
        ps["abs_page"] = pagemap.get(i, ps.get("page_id"))

    payload = {
        "chunk": name,
        "pages": pages,
        "headers": headers,
        "tables": tables,
        "images": image_meta,
        "page_stats": page_stats,
        "toc": [t if isinstance(t, dict) else dict(t) for t in (json_out.metadata.get("table_of_contents") or [])],
    }
    (cdir / f"{name}.json").write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")

    return {"pages": len(pages), "tables": len(tables), "images": saved,
            "headers": len(headers), "md_chars": len(md_out.markdown)}


# --------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description="Marker parse of an annual report, in resumable chunks")
    ap.add_argument("pdf")
    ap.add_argument("--work", required=True, help="working directory for chunk artifacts")
    ap.add_argument("--chunk-size", type=int, default=25)
    ap.add_argument("--pages", default=None, help="page subset, e.g. 0-19 (0-based)")
    ap.add_argument("--mode", choices=["fast", "balanced"], default=None)
    ap.add_argument("--force", action="store_true", help="reprocess chunks already done")
    ap.add_argument(
        "--disable-ocr",
        action="store_true",
        help="text-layer only: skip every VLM/OCR call. Required when no surya "
             "inference backend is usable (no Docker for vllm, no llama-server "
             "binary). Only valid for digital PDFs - run preflight.py first.",
    )
    args = ap.parse_args()

    pdf = Path(args.pdf).expanduser().resolve()
    if not pdf.exists():
        log(f"ERROR: no such PDF: {pdf}")
        return 2
    work = Path(args.work).expanduser().resolve()
    work.mkdir(parents=True, exist_ok=True)
    img_dir = work / "images" / "_raw"

    import pypdfium2

    total = len(pypdfium2.PdfDocument(str(pdf)))
    wanted = parse_pages_arg(args.pages, total)
    log(f"{pdf.name}: {total} pages, processing {len(wanted)}")

    state = State(work / "state.json")
    if args.force:
        state.data["done"] = []
    state.data["pdf"] = str(pdf)
    state.data["total_pages"] = total
    state.save()

    t0 = time.time()
    from marker.models import create_model_dict
    from marker.converters.pdf import PdfConverter
    from marker.settings import settings

    log(f"device={settings.TORCH_DEVICE_MODEL}  loading models...")
    models = create_model_dict()
    mode = args.mode or ("balanced" if settings.TORCH_DEVICE_MODEL == "cuda" else "fast")
    log(f"models loaded in {human_time(time.time() - t0)}, mode={mode}")

    cfg = {"paginate_output": True, "mode": mode, "output_format": "markdown"}
    if args.disable_ocr:
        # Applies to both LineBuilder (keep the PDF text layer, never OCR) and
        # TableProcessor (skip the recognition-model fallback). Without this,
        # any page the heuristics can't resolve reaches the surya VLM backend.
        cfg["disable_ocr"] = True
        log("disable_ocr=True - text-layer only, no VLM calls")

    converter = PdfConverter(artifact_dict=models, config=cfg)

    chunks = [wanted[i:i + args.chunk_size] for i in range(0, len(wanted), args.chunk_size)]
    totals = {"pages": 0, "tables": 0, "images": 0, "headers": 0}
    t_start, done_pages = time.time(), 0

    for ci, pages in enumerate(chunks):
        name = f"chunk_{pages[0]:04d}_{pages[-1]:04d}"
        if state.is_done(name) and not args.force:
            log(f"[{ci + 1}/{len(chunks)}] {name} - cached")
            continue
        log(f"[{ci + 1}/{len(chunks)}] {name} - pages {pages[0]}-{pages[-1]}")
        ct = time.time()
        try:
            res = process_chunk(converter, pdf, pages, work, name, img_dir)
            for k in totals:
                totals[k] += res.get(k, 0)
            state.mark_done(name)
            done_pages += len(pages)
            rate = (time.time() - t_start) / max(done_pages, 1)
            left = sum(len(c) for c in chunks[ci + 1:])
            log(f"    ok in {human_time(time.time() - ct)} "
                f"({res['tables']} tables, {res['images']} images) "
                f"| {rate:.1f}s/page, ~{human_time(rate * left)} left")
        except Exception as e:  # noqa: BLE001 - keep going, record the gap
            state.mark_failed(name, f"{type(e).__name__}: {e}")
            log(f"    FAILED: {e}")
            traceback.print_exc(limit=3)

    log(f"done in {human_time(time.time() - t_start)}: {totals}")
    if state.data["failed"]:
        log(f"WARNING: {len(state.data['failed'])} chunk(s) failed - rerun to retry")
    return 0


if __name__ == "__main__":
    sys.exit(main())
