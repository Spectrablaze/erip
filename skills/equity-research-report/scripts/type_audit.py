"""type_audit.py — minimum legible type, measured where it lands on the page.

A chart authored at 9px is not 9px on paper. The SVG is scaled to its column,
so the honest measure is the intrinsic font size multiplied by the ratio of
display width to intrinsic width. This walks every SVG the report embeds, works
out which column it sits in, and reports the smallest type that actually prints.

CSS is checked the same way, straight from the declared point size.

Usage:
    python type_audit.py reports/<T>/report.html [--min 7.0] [--json out.json]
"""
from __future__ import annotations
import argparse, json, os, re, sys

PX_TO_PT = 0.75
# page geometry from report.css: A4 less 15mm margins each side
BODY_MM = 180.0
# a .split column: (180 - 6mm gap) / 2
COL_MM = 87.0
MM_PER_IN = 25.4

# CSS rules whose type prints as words a reader has to read. Decorative rules
# (badges, corner labels) are listed so they are reported, not skipped.
CSS_RE = re.compile(r"([^{}]+)\{([^{}]*)\}", re.S)
SIZE_RE = re.compile(r"font-size:\s*([\d.]+)pt")


def css_findings(css_path, minimum):
    out = []
    css = open(css_path, encoding="utf-8").read()
    for sel, body in CSS_RE.findall(css):
        m = SIZE_RE.search(body)
        if not m:
            continue
        pt = float(m.group(1))
        if pt < minimum:
            out.append({"selector": " ".join(sel.split()), "pt": pt})
    return out


def svg_widths(svg_path):
    """(intrinsic width in inches, [font sizes in px]) for one SVG."""
    s = open(svg_path, encoding="utf-8").read()
    m = re.search(r'<svg[^>]*\swidth="([\d.]+)"', s)
    w_px = float(m.group(1)) if m else 0.0
    sizes = [float(x) for x in re.findall(r'font-size[:=]"?\s*([\d.]+)', s)]
    return w_px / 96.0, sizes


def embed_columns(html):
    """Map each embedded chart to the width it is displayed at.

    A chart inside one half of a .split renders in a column; anything else
    spans the body. Blocks, figures and columns are all divs, so this needs a
    real stack: counting `</div>` without one takes the depth to zero on the
    first inner close and reports every chart as full width.
    """
    out, stack = {}, []
    tok = re.compile(r'<div\b([^>]*)>|</div>|charts/([a-z0-9_]+)\.svg')
    for m in tok.finditer(html):
        if m.group(1) is not None:
            cls = re.search(r'class="([^"]*)"', m.group(1))
            stack.append("split" in (cls.group(1) if cls else ""))
        elif m.group(2):
            out.setdefault(m.group(2), COL_MM if any(stack) else BODY_MM)
        elif stack:
            stack.pop()
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("html")
    ap.add_argument("--min", type=float, default=7.0)
    ap.add_argument("--json")
    a = ap.parse_args()

    root = os.path.dirname(os.path.abspath(a.html))
    html = open(a.html, encoding="utf-8").read()
    cols = embed_columns(html)

    charts = []
    for name, disp_mm in sorted(cols.items()):
        p = os.path.join(root, "charts", name + ".svg")
        if not os.path.exists(p):
            continue
        intrinsic_in, sizes = svg_widths(p)
        if not intrinsic_in or not sizes:
            continue
        scale = (disp_mm / MM_PER_IN) / intrinsic_in
        pts = sorted({round(s * scale * PX_TO_PT, 2) for s in sizes})
        charts.append({"chart": name, "display_mm": disp_mm,
                       "intrinsic_in": round(intrinsic_in, 2),
                       "scale": round(scale, 3), "min_pt": pts[0],
                       "sizes_pt": pts,
                       "authored_px": sorted({round(s, 1) for s in sizes})})

    css = css_findings(os.path.join(root, "report.css"), a.min)
    bad_charts = [c for c in charts if c["min_pt"] < a.min]
    # A canvas built at one width and displayed at another is a defect in both
    # directions: scaling down shrinks the labels, scaling up inflates the
    # height so the block stops fitting anywhere. Either way the spec's `place`
    # disagrees with where the report actually puts the chart.
    misplaced = [c for c in charts if not 0.92 <= c["scale"] <= 1.08]

    print("=" * 78)
    print(f"TYPE AUDIT  —  minimum {a.min}pt")
    print("=" * 78)
    print(f"  charts   {len(charts)} embedded, {len(bad_charts)} below the floor, "
          f"{len(misplaced)} rescaled by the page")
    print(f"  css      {len(css)} rule(s) below the floor")
    print()
    for c in charts:
        flag = ("  FAIL" if c["min_pt"] < a.min else
                "  SCAL" if not 0.92 <= c["scale"] <= 1.08 else "      ")
        print(f"{flag} {c['chart']:<26} {c['display_mm']:>5.0f}mm  x{c['scale']:<5.3f} "
              f"min {c['min_pt']:>5.2f}pt   px {c['authored_px']}")
    print()
    for r in css:
        print(f"  FAIL css  {r['selector']:<46} {r['pt']}pt")
    print()
    for c in misplaced:
        where = "wider than" if c["scale"] < 1 else "narrower than"
        print(f'  FAIL scale {c["chart"]:<24} canvas is {where} its slot '
              f'(x{c["scale"]:.3f}); declare place="{"column" if c["display_mm"] < 100 else "body"}"')
    print()
    n = len(bad_charts) + len(css) + len(misplaced)
    print(f"{n} violation(s)")
    if a.json:
        json.dump({"charts": charts, "css": css, "min": a.min},
                  open(a.json, "w", encoding="utf-8"), indent=2)
    return 1 if n else 0


if __name__ == "__main__":
    sys.exit(main())
