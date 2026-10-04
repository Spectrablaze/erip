#!/usr/bin/env python3
"""Stage 3 - apply the agent's section plan and image classification.

The agent decides *what* the sections are and *what* each image shows; this
script does the mechanical work of building those decisions into the knowledge
base, so the agent never has to copy page text or move files by hand.

Inputs (both optional - run with whichever exists):

  _work/section_plan.json
      {"sections": [
          {"name": "Letter to Shareholders", "start_page": 8, "end_page": 13},
          {"name": "Management Discussion & Analysis", "start_page": 60, "end_page": 118}
       ]}
      Pages are 0-based and inclusive. Ranges may not overlap; any page not
      covered is swept into sections/99_remaining_sections.md so nothing is lost.

  _work/image_plan.json
      {"images": [
          {"file": "_raw/p0123_picture_4.jpg", "category": "plants",
           "name": "dahej_manufacturing_facility",
           "caption": "Dahej Plant", "description": "Manufacturing facility"}
       ]}
      Unlisted images are filed under images/other/ with their raw name.

Usage:
    python apply_plan.py --work "<Company> AR/_work" --out "<Company> AR"
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

CATEGORIES = ["directors", "executives", "plants", "factories", "products",
              "brands", "maps", "charts", "diagrams", "logos", "other"]

# Marker writes image refs named after the block id, e.g. `_page_18_Picture_9.jpeg`
# (BlockId "/page/18/Picture/9" with "/" -> "_"). parse_pdf.py saves the same crop
# as `p0018_picture_9.jpg`, so the two names map onto each other exactly.
MARKER_IMG_RE = re.compile(r"!\[([^\]]*)\]\(\s*_page_(\d+)_([A-Za-z]+)_(\d+)\.(?:jpeg|jpg|png)\s*\)")


def log(msg: str) -> None:
    print(f"[apply] {msg}", flush=True)


def slug(text: str, maxlen: int = 60) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "_", (text or "").strip().lower()).strip("_")
    return (s[:maxlen].rstrip("_") or "untitled")


def load(path: Path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        log(f"ERROR: {path.name} is not valid JSON: {e}")
        sys.exit(2)


def read_page(out: Path, pg: int) -> str:
    f = out / "pages" / f"page_{pg:04d}.md"
    if not f.exists():
        return ""
    text = f.read_text(encoding="utf-8")
    return re.sub(r"^<!--.*?-->\n+", "", text, count=1, flags=re.S).strip()


# --------------------------------------------------------------------------
def build_sections(plan: dict, out: Path, index: list) -> None:
    sections = plan.get("sections") or []
    if not sections:
        log("section_plan.json has no sections")
        return

    available = sorted(
        int(p.stem.split("_")[1]) for p in (out / "pages").glob("page_*.md")
    )
    if not available:
        log("ERROR: no page files - run build_kb.py first")
        sys.exit(2)

    # validate + sort
    clean = []
    for s in sections:
        try:
            a, b = int(s["start_page"]), int(s["end_page"])
        except (KeyError, TypeError, ValueError):
            log(f"skipping malformed section: {s}")
            continue
        if b < a:
            a, b = b, a
        clean.append({"name": str(s.get("name") or "Untitled"), "start": a, "end": b,
                      "summary": s.get("summary", "")})
    clean.sort(key=lambda s: s["start"])

    prev_end = -1
    for s in clean:
        if s["start"] <= prev_end:
            log(f"WARNING: '{s['name']}' starts at {s['start']} but previous section "
                f"ended at {prev_end} - overlapping pages will be duplicated")
        prev_end = max(prev_end, s["end"])

    covered = set()
    sdir = out / "sections"
    for i, s in enumerate(clean, start=1):
        pages = [p for p in available if s["start"] <= p <= s["end"]]
        covered.update(pages)
        name = f"{i:02d}_{slug(s['name'])}.md"
        parts = [
            "---",
            f"section: {json.dumps(s['name'])}",
            f"start_page: {s['start']}",
            f"end_page: {s['end']}",
            f"pdf_pages: {s['start'] + 1}-{s['end'] + 1}",
            f"page_count: {len(pages)}",
            "---",
            "",
            f"# {s['name']}",
            "",
        ]
        if s["summary"]:
            parts += [f"> {s['summary']}", ""]
        for pg in pages:
            body = read_page(out, pg)
            if not body:
                continue
            parts += [f"\n<!-- page {pg} | pdf page {pg + 1} -->", "", body, ""]
        (sdir / name).write_text("\n".join(parts), encoding="utf-8")
        index.append({"file": f"sections/{name}", "section": s["name"],
                      "start_page": s["start"], "end_page": s["end"],
                      "page_count": len(pages)})
        log(f"  {name}  pages {s['start']}-{s['end']} ({len(pages)})")

    leftover = [p for p in available if p not in covered]
    if leftover:
        parts = ["---", "section: \"Remaining Sections\"",
                 f"page_count: {len(leftover)}", "---", "",
                 "# Remaining Sections", "",
                 "Pages not assigned to a named section by the section plan.", ""]
        for pg in leftover:
            body = read_page(out, pg)
            if not body:
                continue
            parts += [f"\n<!-- page {pg} | pdf page {pg + 1} -->", "", body, ""]
        (sdir / "99_remaining_sections.md").write_text("\n".join(parts), encoding="utf-8")
        index.append({"file": "sections/99_remaining_sections.md",
                      "section": "Remaining Sections", "page_count": len(leftover)})
        log(f"  99_remaining_sections.md ({len(leftover)} unassigned pages)")


# --------------------------------------------------------------------------
def build_images(plan: dict | None, work: Path, out: Path) -> list:
    raw_dir = work / "images" / "_raw"
    if not raw_dir.exists():
        log("no extracted images")
        return []

    cands = load(work / "image_candidates.json") or {}
    meta_by_file = {c["file"]: c for c in cands.get("images", [])}

    decisions = {}
    for d in ((plan or {}).get("images") or []):
        f = str(d.get("file", ""))
        key = f if f.startswith("_raw/") else f"_raw/{Path(f).name}"
        decisions[key] = d

    for c in CATEGORIES:
        (out / "images" / c).mkdir(parents=True, exist_ok=True)

    index, used = [], set()
    for img in sorted(raw_dir.glob("*.jpg")):
        key = f"_raw/{img.name}"
        d = decisions.get(key, {})
        meta = meta_by_file.get(key, {})
        cat = str(d.get("category") or "other").lower().strip()
        if cat not in CATEGORIES:
            cat = "other"
        base = slug(d.get("name") or "") if d.get("name") else img.stem
        page = meta.get("page")
        target = f"{base}.jpg"
        n = 2
        while (cat, target) in used:
            target = f"{base}_{n}.jpg"
            n += 1
        used.add((cat, target))

        shutil.copy2(img, out / "images" / cat / target)
        entry = {
            "file": f"images/{cat}/{target}",
            "raw_name": img.name,
            "page": page,
            "pdf_page": (page + 1) if isinstance(page, int) else None,
            "category": cat,
            "section": d.get("section", meta.get("section", "")),
            "caption": d.get("caption", meta.get("caption", "")),
            "description": d.get("description", ""),
            "source_page_file": f"pages/page_{page:04d}.md" if isinstance(page, int) else None,
            "classified": key in decisions,
        }
        index.append(entry)

    (out / "metadata" / "image_index.json").write_text(
        json.dumps({"count": len(index),
                    "classified": sum(1 for e in index if e["classified"]),
                    "images": index}, indent=2), encoding="utf-8")

    for c in CATEGORIES:
        d = out / "images" / c
        if d.exists() and not any(d.iterdir()):
            d.rmdir()

    log(f"filed {len(index)} images ({sum(1 for e in index if e['classified'])} classified)")
    return index


# --------------------------------------------------------------------------
def rewrite_image_refs(out: Path, index: list) -> int:
    """Repoint Marker's image references at the filed, renamed images.

    Without this the page and section markdown links to `_page_18_Picture_9.jpeg`,
    which exists nowhere in the knowledge base - the text and its illustrations
    come apart, and every such link shows up as broken.
    """
    by_raw = {}
    for e in index:
        raw = (e.get("raw_name") or "").rsplit(".", 1)[0]
        if raw:
            by_raw[raw.lower()] = e

    def repl(m):
        alt, page, btype, bid = m.group(1), int(m.group(2)), m.group(3), m.group(4)
        entry = by_raw.get(f"p{page:04d}_{btype.lower()}_{bid}")
        if not entry:
            return m.group(0)
        caption = alt or entry.get("caption") or ""
        # pages/ and sections/ both sit one level below the root
        return f"![{caption}](../{entry['file']})"

    changed = 0
    for sub in ("pages", "sections"):
        for md in (out / sub).glob("*.md"):
            text = md.read_text(encoding="utf-8")
            new, n = MARKER_IMG_RE.subn(repl, text)
            if n:
                md.write_text(new, encoding="utf-8")
                changed += n
    return changed


def main() -> int:
    ap = argparse.ArgumentParser(description="Apply section plan and image classification")
    ap.add_argument("--work", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    work = Path(args.work).expanduser().resolve()
    out = Path(args.out).expanduser().resolve()

    # Images first: sections are concatenated from the page files, so the page
    # markdown must already point at the final image paths.
    index = build_images(load(work / "image_plan.json"), work, out)
    if index:
        n = rewrite_image_refs(out, index)
        log(f"repointed {n} image reference(s) to filed images")

    section_index: list = []
    sp = load(work / "section_plan.json")
    if sp:
        build_sections(sp, out, section_index)
        (out / "metadata" / "section_index.json").write_text(
            json.dumps({"count": len(section_index), "sections": section_index}, indent=2),
            encoding="utf-8")
    else:
        log("no section_plan.json - skipping sections")

    log("stage 3 complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
