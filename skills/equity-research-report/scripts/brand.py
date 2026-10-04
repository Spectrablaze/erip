#!/usr/bin/env python3
"""
brand.py — derive a per-company colour palette and wire it into the report.

    python3 brand.py reports/EICHERMOT
    python3 brand.py reports/EICHERMOT --brand "#1a4d2e" --accent "#d4a017"

Reads the company logo, extracts its dominant colours, enforces legibility, and
writes three files next to the report:

    brand.json          consumed by charts.py  (chart series colours)
    brand.css           :root override, linked AFTER report.css
    brand-preview.svg   swatch strip — show this to the user for approval

WHY CONTRAST IS ENFORCED
--brand fills table headers that carry white text, and is also used for headings
on white. Both directions need WCAG AA (4.5:1). A company whose logo is yellow,
lime or pale cyan would otherwise produce unreadable headers, so the extracted
hue is darkened until it passes. The hue is preserved — only lightness moves.
"""
from __future__ import annotations

import argparse
import colorsys
import json
import os
import sys

# Neutral fallbacks — used when a logo is monochrome or missing. These are the
# report.css defaults, so the output degrades to the house style rather than
# to something arbitrary.
DEFAULTS = {
    "brand": "#0b3d62", "brand_2": "#1173a8", "accent": "#c8801f",
    "ink": "#16202c", "ink_soft": "#52606d", "rule": "#c9d4de",
    "panel": "#eef3f7", "panel_2": "#f7fafc",
    "pos": "#1a7f4b", "neg": "#b3261e",
}

MIN_CONTRAST_TEXT = 4.5   # WCAG AA for normal text
MIN_CONTRAST_GRAPHIC = 3.0  # WCAG AA for graphical objects


# ------------------------------------------------------------------ colour math
def hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) != 6:
        raise ValueError(f"bad hex colour: {h!r}")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore


def rgb_to_hex(rgb) -> str:
    return "#%02x%02x%02x" % tuple(max(0, min(255, int(round(c)))) for c in rgb)


def _lin(c: float) -> float:
    c /= 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def luminance(rgb) -> float:
    r, g, b = (_lin(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b) -> float:
    """WCAG contrast ratio between two RGB tuples."""
    la, lb = luminance(a), luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def _set_lightness(rgb, light: float):
    h, _, s = colorsys.rgb_to_hls(*[c / 255 for c in rgb])
    r, g, b = colorsys.hls_to_rgb(h, max(0.0, min(1.0, light)), s)
    return (r * 255, g * 255, b * 255)


def _lightness(rgb) -> float:
    return colorsys.rgb_to_hls(*[c / 255 for c in rgb])[1]


def _tint(rgb, light: float, sat_cap: float):
    """A neutral tinted toward the brand hue.

    Hairlines and zebra fills must read as subtle greys. Lightening a saturated
    hue alone yields a pastel (lime -> #e0ffa3) that all but vanishes on white,
    so saturation is capped as well as lightness set.
    """
    h, _, s = colorsys.rgb_to_hls(*[c / 255 for c in rgb])
    r, g, b = colorsys.hls_to_rgb(h, light, min(s, sat_cap))
    return (r * 255, g * 255, b * 255)


def _saturation(rgb) -> float:
    return colorsys.rgb_to_hls(*[c / 255 for c in rgb])[2]


def enforce_contrast(rgb, against=(255, 255, 255), minimum=MIN_CONTRAST_TEXT):
    """Darken (or lighten) until the ratio passes, preserving hue and saturation."""
    if contrast(rgb, against) >= minimum:
        return rgb
    target_dark = luminance(against) > 0.5   # against white -> go darker
    light = _lightness(rgb)
    for _ in range(60):
        light += -0.015 if target_dark else 0.015
        if not 0.0 <= light <= 1.0:
            break
        candidate = _set_lightness(rgb, light)
        if contrast(candidate, against) >= minimum:
            return candidate
    return (0, 0, 0) if target_dark else (255, 255, 255)


# ------------------------------------------------------------ logo extraction
def extract_from_logo(path: str, n: int = 12) -> list[tuple[tuple, int]]:
    """Return [(rgb, count), ...] of meaningful logo colours, most common first.

    Drops the background (near-white / near-black) and unsaturated greys, which
    otherwise dominate the count on any logo with a plain backdrop.
    """
    try:
        from PIL import Image
    except ImportError:
        sys.exit("Pillow is required: pip install pillow")

    img = Image.open(path)
    # Composite transparency over white — logos are usually transparent PNGs,
    # and un-composited alpha reads as black.
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
        bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
        img = Image.alpha_composite(bg, img)
    img = img.convert("RGB")
    img.thumbnail((200, 200))

    quant = img.quantize(colors=n * 4, method=Image.Quantize.MEDIANCUT)
    pal = quant.getpalette() or []
    counts = sorted(quant.getcolors() or [], key=lambda t: -t[0])

    out = []
    for count, idx in counts:
        rgb = tuple(pal[idx * 3: idx * 3 + 3])
        if len(rgb) != 3:
            continue
        hi, lo = max(rgb), min(rgb)
        if hi > 240 and lo > 235:      # white backdrop
            continue
        if hi < 22:                    # pure black
            continue
        if hi - lo < 22 and not (hi < 90):   # grey, unless it is a dark neutral
            continue
        out.append((rgb, count))
        if len(out) >= n:
            break
    return out


def build_palette(logo: str | None, overrides: dict) -> tuple[dict, list[str]]:
    """Return (palette, notes). Explicit overrides always win over extraction."""
    notes: list[str] = []
    found: list[tuple] = []

    if logo and os.path.exists(logo):
        found = [rgb for rgb, _ in extract_from_logo(logo)]
        if not found:
            notes.append(f"{os.path.basename(logo)} is monochrome — "
                         "falling back to the house palette.")
    elif logo:
        notes.append(f"logo not found at {logo} — using the house palette.")

    def pick(key: str, default_hex: str, index: int):
        if overrides.get(key):
            return hex_to_rgb(overrides[key]), True
        if len(found) > index:
            return found[index], False
        return hex_to_rgb(default_hex), False

    brand_rgb, brand_manual = pick("brand", DEFAULTS["brand"], 0)

    # brand-2: prefer a second distinct hue from the logo, else lighten brand.
    if overrides.get("brand_2"):
        brand2_rgb = hex_to_rgb(overrides["brand_2"])
    else:
        brand2_rgb = None
        bh = colorsys.rgb_to_hls(*[c / 255 for c in brand_rgb])[0]
        for rgb in found[1:]:
            h = colorsys.rgb_to_hls(*[c / 255 for c in rgb])[0]
            if min(abs(h - bh), 1 - abs(h - bh)) > 0.04:
                brand2_rgb = rgb
                break
        if brand2_rgb is None:
            brand2_rgb = _set_lightness(brand_rgb, min(0.95, _lightness(brand_rgb) + 0.18))

    # accent: a hue far from brand AND distinct from brand-2. Without the second
    # test a two-colour logo yields accent == brand_2, which silently renders two
    # chart series in the same colour.
    accent_rgb = None
    if overrides.get("accent"):
        # Validate a user-supplied accent against the extracted logo colours and
        # reject it if it is perceptually close to one, so two chart series never
        # silently share a colour.
        accent_rgb = hex_to_rgb(overrides["accent"])
        uh = colorsys.rgb_to_hls(*[c / 255 for c in accent_rgb])[0]
        for rgb in found[1:]:
            fh, _, fs = colorsys.rgb_to_hls(*[c / 255 for c in rgb])
            if min(abs(uh - fh), 1 - abs(uh - fh)) < 0.06 and fs > 0.15:
                notes.append(f"accent {overrides['accent']} rejected — too close to a "
                             "logo house colour; falling back to auto-selection.")
                accent_rgb = None
                break
    if accent_rgb is None:
        bh = colorsys.rgb_to_hls(*[c / 255 for c in brand_rgb])[0]
        b2h = colorsys.rgb_to_hls(*[c / 255 for c in brand2_rgb])[0]
        for rgb in found[1:]:
            h, _, s = colorsys.rgb_to_hls(*[c / 255 for c in rgb])
            far_from_brand = min(abs(h - bh), 1 - abs(h - bh)) > 0.18
            far_from_brand2 = min(abs(h - b2h), 1 - abs(h - b2h)) > 0.08
            if far_from_brand and far_from_brand2 and s > 0.25:
                accent_rgb = rgb
                break
        if accent_rgb is None:
            h, l, s = colorsys.rgb_to_hls(*[c / 255 for c in brand_rgb])
            r, g, b = colorsys.hls_to_rgb((h + 0.5) % 1.0, 0.45, max(0.45, s))
            accent_rgb = (r * 255, g * 255, b * 255)
            notes.append("accent derived as the complement of the brand hue "
                         "(the logo had no second saturated colour).")

    # ---- legibility ----
    fixed_brand = enforce_contrast(brand_rgb, (255, 255, 255), MIN_CONTRAST_TEXT)
    if fixed_brand != brand_rgb:
        notes.append(f"brand darkened {rgb_to_hex(brand_rgb)} -> {rgb_to_hex(fixed_brand)} "
                     f"so white text on the table header reaches WCAG AA "
                     f"({contrast(fixed_brand, (255,255,255)):.1f}:1).")
    brand_rgb = fixed_brand

    for label, val in (("brand_2", brand2_rgb), ("accent", accent_rgb)):
        fixed = enforce_contrast(val, (255, 255, 255), MIN_CONTRAST_GRAPHIC)
        if fixed != val:
            notes.append(f"{label} darkened {rgb_to_hex(val)} -> {rgb_to_hex(fixed)} "
                         f"to stay visible on white.")
        if label == "brand_2":
            brand2_rgb = fixed
        else:
            accent_rgb = fixed

    # Ordered series palette for multi-series charts. Kept distinguishable by
    # alternating the three brand hues before falling back to neutrals.
    series = [rgb_to_hex(brand2_rgb), rgb_to_hex(accent_rgb), rgb_to_hex(brand_rgb),
              rgb_to_hex(_set_lightness(brand2_rgb, min(0.78, _lightness(brand2_rgb) + 0.25))),
              rgb_to_hex(_set_lightness(accent_rgb, max(0.28, _lightness(accent_rgb) - 0.16))),
              DEFAULTS["pos"], DEFAULTS["neg"], "#9aa7b3"]

    # Two identical series colours make a peer chart unreadable. Nudge lightness
    # apart rather than dropping the entry, so the series count stays stable.
    seen: dict[str, int] = {}
    for i, col in enumerate(series):
        if col in seen:
            rgb = hex_to_rgb(col)
            step = 0.16 * (seen[col])
            alt = _set_lightness(rgb, max(0.22, min(0.80, _lightness(rgb) + step)))
            series[i] = rgb_to_hex(alt)
            seen[col] += 1
            notes.append(f"series colour {col} appeared twice — "
                         f"second instance shifted to {series[i]}.")
        else:
            seen[col] = 1

    pal = dict(DEFAULTS)
    pal.update({
        "brand": rgb_to_hex(brand_rgb),
        "brand_2": rgb_to_hex(brand2_rgb),
        "accent": rgb_to_hex(accent_rgb),
        "panel": rgb_to_hex(_tint(brand_rgb, 0.955, 0.30)),
        "panel_2": rgb_to_hex(_tint(brand_rgb, 0.983, 0.30)),
        "rule": rgb_to_hex(_tint(brand_rgb, 0.80, 0.18)),
        "series": series,
    })
    return pal, notes


# ------------------------------------------------------------------- emitters
def write_css(pal: dict, path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write("/* brand.css — generated by brand.py. Link AFTER report.css. */\n")
        f.write(":root {\n")
        for key in ("ink", "ink_soft", "brand", "brand_2", "accent",
                    "rule", "panel", "panel_2", "pos", "neg"):
            f.write(f"  --{key.replace('_', '-')}: {pal[key]};\n")
        f.write("}\n")


def write_preview(pal: dict, path: str) -> None:
    order = [("brand", "headings / table header"), ("brand_2", "chart primary"),
             ("accent", "highlight"), ("panel", "sidebar fill"),
             ("pos", "positive"), ("neg", "negative")]
    w, h = 108, 66
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w*len(order)}" height="{h}">']
    for i, (key, label) in enumerate(order):
        x = i * w
        col = pal[key]
        txt = "#ffffff" if contrast(hex_to_rgb(col), (255, 255, 255)) >= 3 else "#16202c"
        parts.append(f'<rect x="{x}" y="0" width="{w}" height="{h}" fill="{col}"/>')
        parts.append(f'<text x="{x+8}" y="26" font-family="sans-serif" font-size="11" '
                     f'font-weight="bold" fill="{txt}">{col}</text>')
        parts.append(f'<text x="{x+8}" y="44" font-family="sans-serif" font-size="8.5" '
                     f'fill="{txt}">{label}</text>')
    parts.append("</svg>")
    open(path, "w", encoding="utf-8").write("\n".join(parts))


def main():
    ap = argparse.ArgumentParser(description="Derive a company palette from its logo.")
    ap.add_argument("root", help="report folder, e.g. reports/EICHERMOT")
    ap.add_argument("--logo", help="defaults to <root>/assets/logo.png")
    ap.add_argument("--brand", help="override the primary hex")
    ap.add_argument("--brand-2", dest="brand_2", help="override the secondary hex")
    ap.add_argument("--accent", help="override the accent hex")
    args = ap.parse_args()

    logo = args.logo or os.path.join(args.root, "assets", "logo.png")
    overrides = {k: v for k, v in
                 (("brand", args.brand), ("brand_2", args.brand_2), ("accent", args.accent))
                 if v}

    pal, notes = build_palette(logo, overrides)
    os.makedirs(args.root, exist_ok=True)

    json.dump(pal, open(os.path.join(args.root, "brand.json"), "w", encoding="utf-8"), indent=2)
    write_css(pal, os.path.join(args.root, "brand.css"))
    write_preview(pal, os.path.join(args.root, "brand-preview.svg"))

    print(f"palette for {args.root}")
    for key in ("brand", "brand_2", "accent"):
        rgb = hex_to_rgb(pal[key])
        print(f"  {key:<8} {pal[key]}   contrast on white {contrast(rgb,(255,255,255)):.1f}:1")
    print(f"  series   {', '.join(pal['series'][:5])} ...")
    for n in notes:
        print(f"  note: {n}")
    print("\nwrote brand.json, brand.css, brand-preview.svg")
    print("Link brand.css AFTER report.css, and show brand-preview.svg to the user.")


if __name__ == "__main__":
    main()
