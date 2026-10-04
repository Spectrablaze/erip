"""page_plan.py — where every block actually lands, and what it costs.

layout_qa.py measures the symptom (a page is 45% full). This measures the
cause: for each atomic block, the page it landed on, its height, and the space
left at the foot of the page it could not fit into. That turns "reflow adjacent
content" from a guess into an instruction — you can see which block is 40pt too
tall for the gap above it.

Run under an interpreter that has WeasyPrint (WSL on this machine).

Usage:
    python3 page_plan.py reports/<T>/report.html [--json out.json] [--under 55]
"""
from __future__ import annotations
import argparse, collections, json, os, sys

from weasyprint import HTML

A4_H = 841.89
MM = 72 / 25.4
TOP, BOT = 13 * MM, 14 * MM    # report.css @page margin: 13mm top, 14mm bottom


def _text(el):
    """WeasyPrint hands back plain ElementTree nodes, which have no
    text_content(); gather the subtree's text by hand."""
    if el is None:
        return ""
    return "".join(el.itertext())


def walk(box, page_no, out, depth=0):
    el = getattr(box, "element_tag", None)
    cls = ""
    if getattr(box, "element", None) is not None:
        cls = box.element.get("class", "") or ""
    # A <section> is a container that spans pages, so its height says nothing
    # about what sits on this page. Record only things that occupy a page: the
    # atomic blocks, headings and loose paragraphs.
    if el in ("h2", "h3", "h4", "p", "ul", "img", "table") or "block" in cls.split() \
            or cls.split() and cls.split()[0] in ("split", "split-r", "kpis", "people", "photo-grid"):
        h = round(box.height, 1) if box.height is not None else 0.0
        out.append({
            "page": page_no, "tag": el, "cls": cls,
            "y0": round(box.position_y, 1), "h": h,
            "atomic": "block" in cls.split() or cls.startswith(("split", "kpis")),
            "text": " ".join(_text(box.element).split())[:58],
        })
        if "block" in cls.split():
            return          # do not descend into an atomic block
    for child in getattr(box, "children", ()):
        walk(child, page_no, out, depth + 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("html")
    ap.add_argument("--json")
    ap.add_argument("--under", type=float, default=55.0,
                    help="only detail pages filled below this %%")
    ap.add_argument("--qa", required=True,
                    help="layout_qa.py --json output; supplies measured occupancy")
    a = ap.parse_args()

    doc = HTML(filename=a.html).render()
    blocks = []
    for i, page in enumerate(doc.pages, 1):
        walk(page._page_box, i, blocks)

    body_h = A4_H - TOP - BOT
    by_page = collections.defaultdict(list)
    for b in blocks:
        by_page[b["page"]].append(b)

    # foot of the used area on each page, from the deepest block on it
    # Occupancy comes from layout_qa's rasterised measurement, not from the box
    # tree: a grid item reports its position within its track rather than the
    # page, so summing box extents overstates the fill. The box tree is used
    # for the one thing rasterising cannot give — how tall each block is.
    fill = {}
    if a.qa:
        for rec in json.load(open(a.qa, encoding="utf-8"))["pages"]:
            fill[rec["page"]] = rec["occupied_pct"]

    print("=" * 78)
    print(f"PAGE PLAN  —  {os.path.basename(a.html)}   {len(doc.pages)} pages")
    print("=" * 78)
    rows = []
    for p in sorted(by_page):
        pct = fill.get(p)
        if pct is None:
            continue
        free = body_h * (100 - pct) / 100
        # What would not fit here is not the next block alone. Headings are glued
        # to the block beneath them, so the unit that had to move is everything
        # from the top of the next page down to the foot of its first atomic
        # block — heading, lead-in prose and all.
        nxt = sorted(by_page.get(p + 1, []), key=lambda b: b["y0"])
        blocker = next((b for b in nxt if b["atomic"]), None)
        unit = round(blocker["y0"] + blocker["h"] - TOP) if blocker else 0
        rows.append({"page": p, "pct": round(pct, 1), "free_pt": round(free),
                     "blocker": (blocker or {}).get("text", ""),
                     "blocker_h": (blocker or {}).get("h", 0),
                     "unit_h": unit,
                     "shortfall": round(unit - free)})
        flag = "  UNDER" if pct < a.under else "       "
        print(f"{flag} p{p:<3} {pct:>5.1f}%  free {free:>4.0f}pt   "
              f"unit {unit:>5}pt (block {(blocker or {}).get('h', 0):>5.0f}pt)  "
              f"short {rows[-1]['shortfall']:>5}pt  {(blocker or {}).get('text','')[:34]}")

    print()
    under = [r for r in rows if r["pct"] < a.under]
    print(f"{len(under)} page(s) below {a.under:.0f}%")
    for r in under:
        print(f"  p{r['page']}: {r['free_pt']}pt free; the next heading-plus-block unit is "
              f"{r['unit_h']}pt, {r['shortfall']}pt too tall — \"{r['blocker'][:48]}\"")
    if a.json:
        json.dump({"pages": rows, "blocks": blocks}, open(a.json, "w", encoding="utf-8"), indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
