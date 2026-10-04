"""layout_qa.py — report layout and pagination QA.

An SVG passing its own checks says nothing about whether the document reads
well. This measures the rendered PDF for composition faults:

  occupied extent % per page    <65% error, 65-80% warning, >80% acceptable
  orphan headings               a heading with no content beneath it on its page
  separated exhibits            a chart/table title split from its visual
  isolated continuation pages   a table tail occupying <40% of a page
  large whitespace regions      a contiguous empty vertical band
  overflow / clipping           glyphs outside the printable box
  duplicate exhibits            the same visual embedded twice outside a recap

Usage:
    python layout_qa.py <report.pdf> [--html report.html] [--before N]
                        [--json out.json] [--removed "SWOT,Porter"]
"""
from __future__ import annotations
import argparse, collections, json, os, re, sys

import pypdfium2 as pdfium

A4_W, A4_H = 595.276, 841.89
# Thresholds for the extent measure (how far down the body box the content
# reaches). They are not the old ink-density numbers: a page ending two-thirds
# of the way down leaves a third of the sheet blank, which is the point at
# which a reader notices. 65% errors, 80% warns.
ERR_FILL, WARN_FILL = 65.0, 80.0
CONT_PAGE_MIN = 45.0            # a continuation page below this should pull content up
BAND_GAP_PT = 150.0             # a contiguous empty band worth reporting
MM = 72 / 25.4                  # report.css @page margin: 13mm top, 14mm bottom;
TOP_PT, BOT_PT = 13 * MM, 14 * MM   # the header and folio sit in these
BODY_PT = A4_H - TOP_PT - BOT_PT

# Pages allowed to be sparse by design. Anchored on whole words: an unanchored
# "cover" also matches "Coverage", which silently exempted the leverage page.
EXEMPT_RE = re.compile(r"\b(analyst certification|disclaimer)\b", re.I)


def occupied_bands(page, bands=120):
    """How much of the page height the content actually spans.

    Two numbers come out of this. The reported occupancy is the *extent*: from
    the first inked band to the last, as a share of the page. That is what a
    reader means by a full page — a chart with white inside it still occupies
    the space it sits in, and counting inked bands alone marked such pages
    half-empty. The density (share of bands with any ink) is kept as a
    secondary signal and drives the whitespace-band warning.
    """
    full = page.render(scale=0.55).to_pil().convert("L")
    W, H = full.size
    # Crop to the body box. The running header and the page number live in the
    # page margins and are on every page, so measuring the whole sheet reports
    # every page as full.
    y0c = int(round(H * TOP_PT / A4_H))
    y1c = H - int(round(H * BOT_PT / A4_H))
    bmp = full.crop((0, y0c, W, y1c))
    w, h = bmp.size
    px = bmp.load()
    step = max(1, h // bands)
    filled, rows = 0, 0
    band_state = []
    for y0 in range(0, h, step):
        rows += 1
        hit = False
        for y in range(y0, min(y0 + step, h), 2):
            for x in range(0, w, 3):
                if px[x, y] < 205:
                    hit = True
                    break
            if hit:
                break
        band_state.append(hit)
        filled += 1 if hit else 0
    inked = [i for i, b in enumerate(band_state) if b]
    extent = ((inked[-1] - inked[0] + 1) / rows * 100.0) if inked else 0.0
    density = filled / rows * 100.0 if rows else 0.0
    return extent, density, band_state, step, h


def largest_gap(band_state, step, page_h_px, page_h_pt=BODY_PT):
    """Longest run of empty bands, in points."""
    best = run = 0
    for b in band_state:
        run = 0 if b else run + 1
        best = max(best, run)
    return best * step / page_h_px * page_h_pt


def page_lines(page):
    tp = page.get_textpage()
    return [l.strip() for l in tp.get_text_range().split("\n") if l.strip()]


def analyse(pdf_path, html_path=None, before=None, removed=None):
    doc = pdfium.PdfDocument(pdf_path)
    NP = len(doc)
    html = open(html_path, encoding="utf-8").read() if html_path else ""
    headings = re.findall(r"<h2[^>]*>(.*?)</h2>", html, re.S)
    headings = [re.sub(r"<[^>]+>", "", h).strip() for h in headings]

    pages, errors, warnings = [], [], []
    for i in range(NP):
        page = doc[i]
        fill, density, bands, step, hpx = occupied_bands(page)
        gap = largest_gap(bands, step, hpx)
        lines = page_lines(page)
        body = " ".join(lines)
        # Scan the whole page, not its opening. The boilerplate can carry over
        # from the previous page, so the certification or disclaimer heading is
        # often well down the sheet; matching only the first 400 characters
        # left the legal tail page reported as a composition fault.
        exempt = bool(EXEMPT_RE.search(body)) or i == 0

        # clipping
        tp = page.get_textpage()
        off = 0
        maxr = 0.0
        for c in range(tp.count_chars()):
            try:
                l, b, r, t = tp.get_charbox(c, loose=False)
            except Exception:
                continue
            maxr = max(maxr, r)
            if r < -2 or l > A4_W + 2 or t < -2 or b > A4_H + 2:
                off += 1

        rec = {"page": i + 1, "occupied_pct": round(fill, 1),
               "ink_density_pct": round(density, 1),
               "largest_gap_pt": round(gap), "lines": len(lines),
               "clipped_glyphs": off, "max_x_pt": round(maxr),
               "exempt": exempt,
               "first_line": (lines[1] if len(lines) > 1 else (lines[0] if lines else ""))[:60]}
        pages.append(rec)

        if off:
            errors.append((i + 1, "clipping", f"{off} glyph(s) outside the page box"))
        if maxr > A4_W - 12:
            errors.append((i + 1, "overflow", f"content reaches x={maxr:.0f}pt"))
        if not exempt:
            if fill < ERR_FILL:
                errors.append((i + 1, "underfilled", f"{fill:.0f}% occupied, below the {ERR_FILL:.0f}% floor"))
            elif fill < WARN_FILL:
                warnings.append((i + 1, "light", f"{fill:.0f}% occupied"))
        if gap > BAND_GAP_PT and not exempt:
            warnings.append((i + 1, "whitespace_band", f"{gap:.0f}pt contiguous empty band"))

        # orphan heading: a page whose only content is a heading line
        if len(lines) <= 3 and i < NP - 1 and not exempt:
            errors.append((i + 1, "orphan_page", f"only {len(lines)} line(s) on the page"))
        # heading last on a page, content overleaf
        if lines:
            tail = lines[-1]
            if any(tail.lower().startswith(h.lower()[:18]) for h in headings if len(h) > 6):
                errors.append((i + 1, "orphan_heading", f'heading "{tail[:40]}" ends the page'))

        # isolated continuation: a short page that begins mid-table
        if i and fill < CONT_PAGE_MIN and len(lines) > 3 and not exempt:
            errors.append((i + 1, "isolated_continuation",
                           f"continuation page only {fill:.0f}% occupied"))

    # separated exhibit titles: a fig-title on one page, its image on the next
    sep = []
    for i in range(NP - 1):
        last = page_lines(doc[i])[-1:] or [""]
        if re.match(r"^(Source:|Read-through)", last[0]):
            sep.append(i + 1)
    if sep:
        for p in sep:
            warnings.append((p, "separated_exhibit", "source/read-through split from its visual"))

    # duplicate exhibits outside a recap section
    recap = re.findall(r'<section[^>]*data-recap="1".*?</section>', html, re.S)
    body_html = html
    for r in recap:
        body_html = body_html.replace(r, "")
    refs = re.findall(r"charts/([a-z0-9_]+)\.svg", body_html)
    dupes = [k for k, v in collections.Counter(refs).items() if v > 1]
    if dupes:
        errors.append((0, "duplicate_exhibit", f"embedded twice outside a recap: {dupes}"))

    doc.close()
    return {"pdf": os.path.basename(pdf_path), "pages_before": before, "pages_after": NP,
            "removed_sections": (removed or "").split(",") if removed else [],
            "pages": pages, "errors": errors, "warnings": warnings,
            "mean_occupied": round(sum(p["occupied_pct"] for p in pages) / NP, 1)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--html")
    ap.add_argument("--before", type=int)
    ap.add_argument("--removed")
    ap.add_argument("--json")
    a = ap.parse_args()
    r = analyse(a.pdf, a.html, a.before, a.removed)

    print("=" * 78)
    print(f"LAYOUT QA  —  {r['pdf']}")
    print("=" * 78)
    if r["pages_before"]:
        print(f"  page count   {r['pages_before']} -> {r['pages_after']}")
    else:
        print(f"  page count   {r['pages_after']}")
    if r["removed_sections"]:
        print(f"  removed      {', '.join(x for x in r['removed_sections'] if x)}")
    print(f"  occupied     mean {r['mean_occupied']}%   "
          f"min {min(p['occupied_pct'] for p in r['pages'])}%")
    print()
    print(f"  {'pg':>3} {'occ%':>6} {'gap':>5}  page")
    for p in r["pages"]:
        flag = ("  ERR " if (p["occupied_pct"] < ERR_FILL and not p["exempt"])
                else "  warn" if (p["occupied_pct"] < WARN_FILL and not p["exempt"]) else "      ")
        print(f"  {p['page']:>3} {p['occupied_pct']:>6} {p['largest_gap_pt']:>5}{flag} {p['first_line']}")
    print()
    for pg, k, d in r["errors"]:
        print(f"  ERROR  p{pg:<3} {k:<22} {d}")
    for pg, k, d in r["warnings"]:
        print(f"  warn   p{pg:<3} {k:<22} {d}")
    print()
    print(f"{len(r['errors'])} error(s), {len(r['warnings'])} warning(s)")
    if a.json:
        json.dump(r, open(a.json, "w", encoding="utf-8"), indent=2)
        print("json ->", a.json)
    return 1 if r["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
