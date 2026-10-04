#!/usr/bin/env python3
"""
charts.py — house-style chart factory for the equity research report.

Every chart archetype seen in the sample reports is here. All functions write an
SVG (vector, so it stays crisp in the PDF) and return the path.

Usage from Python:
    from charts import *
    set_outdir("companies/EICHERMOT/charts")
    bar_grouped("global_gdp", ["World","US","India"], {"2025A":[3.2,2.8,6.5], "2026P":[3.1,2.3,6.5]},
                horizontal=True)

NEVER pass title=. The title belongs in the HTML as <div class="fig-title">; passing
both prints it twice at two different sizes. title= exists only for standalone use
of this module outside the report pipeline.

Usage from CLI (JSON spec on stdin or as a file):
    python3 charts.py spec.json
    # spec.json = {"outdir": "...", "charts": [ {"fn": "bar_grouped", "args": {...}}, ... ]}
"""
from __future__ import annotations

import json
import os
import sys

import logging
import matplotlib
matplotlib.use("Agg")
# Carlito is present on Linux, Calibri on Windows — whichever is missing logs a
# findfont warning per text element. Silence it; the fallback chain is intentional.
logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.lines import Line2D

# ----------------------------------------------------------------- house style
INK, INK_SOFT = "#16202c", "#52606d"
BRAND, BRAND2, ACCENT = "#0b3d62", "#1173a8", "#c8801f"
POS, NEG, RULE = "#1a7f4b", "#b3261e", "#c9d4de"
# Ordered palette for multi-series charts (peer comparisons, multi-year bars)
PALETTE = [BRAND2, ACCENT, BRAND, "#7fb2d1", "#8c6d3f", POS, NEG, "#9aa7b3"]


def set_brand(brand_json: str) -> None:
    """Adopt a company palette written by brand.py.

    Charts and report.css must not drift, so both read the same brand.json.
    Call before generating charts, or set the EQR_BRAND env var to the path.
    """
    global INK, INK_SOFT, BRAND, BRAND2, ACCENT, POS, NEG, RULE, PALETTE
    with open(brand_json, encoding="utf-8") as f:
        b = json.load(f)

    # House style is the constant. The company's colour enters as an ACCENT only,
    # so every report in the series looks like it came from the same desk rather
    # than from the company being covered. Set EQR_BRAND_MODE=full for the old
    # behaviour, where brand.json drives the whole palette.
    mode = os.environ.get("EQR_BRAND_MODE", "accent").lower()
    if mode == "full":
        INK, INK_SOFT = b.get("ink", INK), b.get("ink_soft", INK_SOFT)
        BRAND = b.get("brand", BRAND)
        BRAND2 = b.get("brand_2", BRAND2)
        ACCENT = b.get("accent", ACCENT)
        POS, NEG = b.get("pos", POS), b.get("neg", NEG)
        RULE = b.get("rule", RULE)
        PALETTE = b.get("series") or [BRAND2, ACCENT, BRAND, POS, NEG, "#9aa7b3"]
    else:
        company = b.get("brand") or ACCENT
        ACCENT = company                      # company colour, used for emphasis
        PALETTE = [BRAND2, company, BRAND, "#7fb2d1", "#8c6d3f", POS, NEG, "#9aa7b3"]
        # INK, BRAND, RULE, POS, NEG stay at the house values
    plt.rcParams.update({
        "axes.edgecolor": RULE, "axes.labelcolor": INK_SOFT,
        "axes.titlecolor": BRAND2, "text.color": INK,
        "xtick.color": INK_SOFT, "ytick.color": INK_SOFT,
        "grid.color": RULE,
    })

plt.rcParams.update({
    "font.family":       ["Carlito", "Calibri", "DejaVu Sans"],
    "font.size":         7.2,
    "axes.edgecolor":    RULE,
    "axes.labelcolor":   INK_SOFT,
    "axes.titlesize":    8.6,
    "axes.titleweight":  "bold",
    "axes.titlecolor":   BRAND2,
    "axes.grid":         True,
    "grid.color":        RULE,
    "grid.linewidth":    0.4,
    "grid.alpha":        0.35,
    "xtick.color":       INK_SOFT,
    "ytick.color":       INK_SOFT,
    "xtick.labelsize":   6.6,
    "ytick.labelsize":   6.6,
    "legend.fontsize":   6.8,
    "legend.frameon":    False,
    "figure.dpi":        200,
    "savefig.bbox":      "tight",
    "savefig.pad_inches": 0.02,
    "svg.fonttype":      "none",   # keep text as text -> selectable + tiny files
})

_OUTDIR = "charts"


def set_outdir(path: str) -> None:
    global _OUTDIR
    _OUTDIR = path
    os.makedirs(path, exist_ok=True)


def _new(w=3.5, h=2.2):
    fig, ax = plt.subplots(figsize=(w, h))
    ax.set_axisbelow(True)
    # fewer, larger-spaced ticks read better at print size than a dense grid
    ax.yaxis.set_major_locator(mticker.MaxNLocator(nbins=4, prune="both"))
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.spines["left"].set_color(RULE)
    ax.spines["bottom"].set_color(RULE)
    return fig, ax


def _save(fig, name: str) -> str:
    os.makedirs(_OUTDIR, exist_ok=True)
    path = os.path.join(_OUTDIR, f"{name}.svg")
    fig.savefig(path, format="svg", transparent=True)
    plt.close(fig)
    print(f"  chart -> {path}")
    return path


def _fmt(v, pct=False, dec=1):
    if v is None:
        return ""
    if pct:
        return f"{v:.{dec}f}%"
    a = abs(v)
    if a >= 1_00_000:
        return f"{v/1_00_000:,.1f}L"
    if a >= 1000:
        return f"{v:,.0f}"
    s = f"{v:,.{dec}f}"
    # only trim a fractional tail; with dec=0 there is no ".", and rstrip("0")
    # would eat the integer's own trailing zeros (150 -> "15", 500 -> "5").
    return s.rstrip("0").rstrip(".") if "." in s else s


def _legend(ax, ncol=None, loc="upper center"):
    h, l = ax.get_legend_handles_labels()
    if len(l) > 1:
        ax.legend(h, l, loc=loc, bbox_to_anchor=(0.5, -0.14),
                  ncol=ncol or min(len(l), 4), handlelength=1.2, columnspacing=1.4)


# ------------------------------------------------------------------ archetypes
def bar_grouped(name, categories, series: dict, title="", horizontal=False,
                pct=False, labels=True, w=3.5, h=2.4, dec=1):
    """Grouped bars. `series` = {"2025A": [...], "2026P": [...]} aligned to categories.
    Set horizontal=True for the IMF-style Global GDP Projections chart."""
    n, k = len(categories), len(series)
    span = 0.8
    width = span / k
    fig, ax = _new(w, h)
    for i, (lab, vals) in enumerate(series.items()):
        off = -span / 2 + width * (i + 0.5)
        pos = [j + off for j in range(n)]
        c = PALETTE[i % len(PALETTE)]
        if horizontal:
            b = ax.barh(pos, vals, height=width * 0.92, label=lab, color=c)
        else:
            b = ax.bar(pos, vals, width=width * 0.92, label=lab, color=c)
        if labels:
            ax.bar_label(b, labels=[_fmt(v, pct, dec) for v in vals], fontsize=5.6,
                         padding=1.5, color=INK)
    if horizontal:
        ax.set_yticks(range(n)); ax.set_yticklabels(categories)
        ax.invert_yaxis(); ax.xaxis.grid(True); ax.yaxis.grid(False)
        ax.set_xlabel("")
    else:
        ax.set_xticks(range(n)); ax.set_xticklabels(categories)
        ax.yaxis.grid(True); ax.xaxis.grid(False)
    if title:
        ax.set_title(title, pad=6)
    _legend(ax)
    return _save(fig, name)


def bar_line_combo(name, categories, bar_vals, line_vals, bar_label="", line_label="",
                   title="", bar_pct=False, line_pct=True, w=3.6, h=2.4):
    """The workhorse: Revenue bars + Growth% line on a secondary axis.
    Also used for EBITDA & Margin, Capex & Capex%Sales, Inventory & Days."""
    fig, ax = _new(w, h)
    b = ax.bar(range(len(categories)), bar_vals, width=0.62, color=BRAND2, label=bar_label)
    ax.bar_label(b, labels=[_fmt(v, bar_pct) for v in bar_vals], fontsize=5.6, padding=1.5, color=INK)
    ax.set_xticks(range(len(categories))); ax.set_xticklabels(categories)
    ax.yaxis.grid(True); ax.xaxis.grid(False)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: _fmt(x, False, 0)))

    ax2 = ax.twinx()
    ax2.plot(range(len(categories)), line_vals, color=ACCENT, marker="o", ms=2.6, lw=1.3,
             label=line_label)
    for x, v in enumerate(line_vals):
        if v is not None:
            ax2.annotate(_fmt(v, line_pct), (x, v), textcoords="offset points",
                         xytext=(0, 5), ha="center", fontsize=5.6, color=ACCENT, fontweight="bold")
    ax2.grid(False)
    for s in ("top", "right", "left"):
        ax2.spines[s].set_visible(False)
    ax2.tick_params(axis="y", labelsize=6.2, colors=ACCENT)
    ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:.0f}%" if line_pct else f"{x:,.0f}"))
    lo, hi = ax2.get_ylim(); ax2.set_ylim(lo, hi + (hi - lo) * 0.18)

    if title:
        ax.set_title(title, pad=6)
    handles = [plt.Rectangle((0, 0), 1, 1, color=BRAND2), Line2D([0], [0], color=ACCENT, marker="o", ms=3)]
    ax.legend(handles, [bar_label, line_label], loc="upper center", bbox_to_anchor=(0.5, -0.14),
              ncol=2, handlelength=1.2)
    return _save(fig, name)


def line_multi(name, x, series: dict, title="", pct=True, w=3.6, h=2.4,
               annotate_last=True, dashed=()):
    """Peer trend lines — margins, ROCE, cash conversion days, capex % of sales."""
    fig, ax = _new(w, h)
    for i, (lab, vals) in enumerate(series.items()):
        c = PALETTE[i % len(PALETTE)]
        ax.plot(x, vals, color=c, lw=1.6 if i == 0 else 1.0, marker="o", ms=2.2,
                label=lab, ls="--" if lab in dashed else "-",
                zorder=3 if i == 0 else 2, alpha=1.0 if i == 0 else 0.85)
        if annotate_last and vals and vals[-1] is not None:
            ax.annotate(_fmt(vals[-1], pct), (len(x) - 1, vals[-1]), textcoords="offset points",
                        xytext=(4, 0), fontsize=5.8, color=c, fontweight="bold", va="center")
    ax.set_xticks(range(len(x))); ax.set_xticklabels(x)
    if pct:
        ax.yaxis.set_major_formatter(mticker.PercentFormatter(decimals=0))
    if title:
        ax.set_title(title, pad=6)
    _legend(ax)
    return _save(fig, name)


def stacked_bar(name, categories, series: dict, title="", pct=False, w=3.6, h=2.4,
                labels=True, pct_of_total=False):
    """Revenue by segment, shareholding over 10 years, cost structure."""
    fig, ax = _new(w, h)
    bottom = [0.0] * len(categories)
    if pct_of_total:
        tot = [sum(series[k][i] for k in series) or 1 for i in range(len(categories))]
        series = {k: [v / tot[i] * 100 for i, v in enumerate(vs)] for k, vs in series.items()}
        pct = True
    for i, (lab, vals) in enumerate(series.items()):
        c = PALETTE[i % len(PALETTE)]
        b = ax.bar(range(len(categories)), vals, bottom=bottom, width=0.66, label=lab, color=c)
        if labels:
            ax.bar_label(b, labels=[_fmt(v, pct, 0) if v and abs(v) > (3 if pct else 0) else ""
                                    for v in vals], label_type="center", fontsize=5.4, color="#fff")
        bottom = [bottom[j] + vals[j] for j in range(len(categories))]
    ax.set_xticks(range(len(categories))); ax.set_xticklabels(categories)
    ax.yaxis.grid(True); ax.xaxis.grid(False)
    if pct:
        ax.yaxis.set_major_formatter(mticker.PercentFormatter(decimals=0))
    if title:
        ax.set_title(title, pad=6)
    _legend(ax)
    return _save(fig, name)


def indexed_performance(name, dates, series: dict, title="",
                        w=7.0, h=2.8, base=100):
    """Full-width relative stock performance vs Nifty / peers, rebased to 100."""
    fig, ax = _new(w, h)
    for i, (lab, vals) in enumerate(series.items()):
        c = PALETTE[i % len(PALETTE)]
        ax.plot(dates, vals, color=c, lw=1.5 if i == 0 else 1.0, label=lab,
                zorder=3 if i == 0 else 2)
        if vals and vals[-1] is not None:
            ax.annotate(f"{vals[-1]:,.0f}", (len(dates) - 1, vals[-1]),
                        textcoords="offset points", xytext=(4, 0), fontsize=6.4,
                        color=c, fontweight="bold", va="center")
    ax.axhline(base, color=RULE, lw=0.7, ls="--", zorder=1)
    step = max(1, len(dates) // 12)
    ax.set_xticks(range(0, len(dates), step))
    ax.set_xticklabels([dates[i] for i in range(0, len(dates), step)], rotation=0)
    if title:
        ax.set_title(title, pad=6)
    _legend(ax, ncol=min(len(series), 5))
    return _save(fig, name)


def waterfall(name, labels, deltas, title="", start=0.0, w=3.8, h=2.4):
    """FCF bridge, EBITDA bridge, DCF equity-value build-up."""
    fig, ax = _new(w, h)
    run = start
    for i, (lab, d) in enumerate(zip(labels, deltas)):
        if d is None:                      # None => a total/subtotal column
            ax.bar(i, run, width=0.6, color=BRAND)
            ax.annotate(_fmt(run), (i, run), textcoords="offset points", xytext=(0, 3),
                        ha="center", fontsize=5.8, fontweight="bold", color=INK)
            continue
        c = POS if d >= 0 else NEG
        ax.bar(i, d, bottom=run, width=0.6, color=c)
        ax.annotate(_fmt(d), (i, run + d), textcoords="offset points",
                    xytext=(0, 3 if d >= 0 else -8), ha="center", fontsize=5.8, color=INK)
        run += d
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=25, ha="right", fontsize=6.0)
    ax.yaxis.grid(True); ax.xaxis.grid(False)
    if title:
        ax.set_title(title, pad=6)
    return _save(fig, name)


def donut(name, labels, values, title="", w=2.6, h=2.4, center=""):
    """Shareholding pattern, revenue mix, geographic mix."""
    fig, ax = _new(w, h)
    ax.grid(False)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_xticks([]); ax.set_yticks([])
    wedges, _, autot = ax.pie(
        values, colors=PALETTE[:len(values)], startangle=90, counterclock=False,
        wedgeprops=dict(width=0.42, edgecolor="#fff", linewidth=0.8),
        autopct=lambda p: f"{p:.1f}%" if p >= 4 else "", pctdistance=0.79,
        textprops=dict(fontsize=6.0, color="#fff", fontweight="bold"))
    if center:
        ax.text(0, 0, center, ha="center", va="center", fontsize=8, fontweight="bold", color=BRAND)
    ax.legend(wedges, labels, loc="center left", bbox_to_anchor=(0.98, 0.5), handlelength=1.0)
    if title:
        ax.set_title(title, pad=6)
    return _save(fig, name)


def scatter_peers(name, points, xlab, ylab, title="", w=3.4, h=2.6, highlight=None):
    """Valuation scatter — e.g. ROE vs P/B, growth vs EV/EBITDA.
    Accepts either shape:
        {"Maruti": (13.7, 3.6), ...}                       mapping
        [{"label": "Maruti", "x": 13.7, "y": 3.6}, ...]    list of records
    The list form is what reference/components.md documents, so both are honoured
    rather than raising AttributeError on .items()."""
    fig, ax = _new(w, h)
    if isinstance(points, dict):
        items = list(points.items())
    else:
        items = [((p.get("label") or p.get("name") or ""),
                  (p.get("x"), p.get("y"))) if isinstance(p, dict) else (p[0], (p[1], p[2]))
                 for p in points]
    for i, (lab, (x, y)) in enumerate(items):
        hl = (lab == highlight)
        ax.scatter([x], [y], s=48 if hl else 26, color=ACCENT if hl else BRAND2,
                   zorder=3, edgecolor="#fff", linewidth=0.6)
        ax.annotate(lab, (x, y), textcoords="offset points", xytext=(5, 3),
                    fontsize=5.9, color=INK if hl else INK_SOFT,
                    fontweight="bold" if hl else "normal")
    ax.set_xlabel(xlab, fontsize=6.6); ax.set_ylabel(ylab, fontsize=6.6)
    if title:
        ax.set_title(title, pad=6)
    return _save(fig, name)


def sensitivity_heat(name, row_vals, col_vals, grid, row_lab, col_lab, title="", w=3.6, h=2.4):
    """DCF sensitivity: WACC x terminal growth -> intrinsic value per share."""
    fig, ax = _new(w, h)
    ax.grid(False)
    im = ax.imshow(grid, cmap="RdYlGn", aspect="auto")
    ax.set_xticks(range(len(col_vals))); ax.set_xticklabels(col_vals, fontsize=6.2)
    ax.set_yticks(range(len(row_vals))); ax.set_yticklabels(row_vals, fontsize=6.2)
    ax.set_xlabel(col_lab, fontsize=6.6); ax.set_ylabel(row_lab, fontsize=6.6)
    for i in range(len(row_vals)):
        for j in range(len(col_vals)):
            ax.text(j, i, f"{grid[i][j]:,.0f}", ha="center", va="center",
                    fontsize=5.8, color=INK)
    if title:
        ax.set_title(title, pad=6)
    fig.colorbar(im, ax=ax, fraction=0.035, pad=0.02).ax.tick_params(labelsize=5.6)
    return _save(fig, name)


def area_stack(name, x, series: dict, title="", w=3.6, h=2.4, pct=False):
    """Segment revenue evolution, cash-flow composition."""
    fig, ax = _new(w, h)
    ax.stackplot(range(len(x)), *series.values(), labels=list(series),
                 colors=PALETTE[:len(series)], alpha=0.9, edgecolor="#fff", linewidth=0.5)
    ax.set_xticks(range(len(x))); ax.set_xticklabels(x)
    if pct:
        ax.yaxis.set_major_formatter(mticker.PercentFormatter(decimals=0))
    if title:
        ax.set_title(title, pad=6)
    _legend(ax)
    return _save(fig, name)


def football_field(name, methods: list, current_price=None, target=None,
                   w=7.0, h=2.8, currency="INR"):
    """Valuation range by method — the standard sell-side valuation summary.

    methods = [{"label": "DCF (base)", "low": 2900, "high": 4100, "mid": 3350}, ...]
    `mid` is optional; when present it is marked with a tick inside the bar.

    Draws the current price as a vertical rule so the reader sees at a glance which
    methods bracket the market and which do not — the single most useful valuation
    exhibit, and the one this pack was missing.
    """
    fig, ax = _new(w, h)
    labels = [m["label"] for m in methods]
    y = list(range(len(methods)))[::-1]      # first method at the top

    for yi, m in zip(y, methods):
        lo, hi = float(m["low"]), float(m["high"])
        if hi < lo:
            lo, hi = hi, lo
        ax.barh(yi, hi - lo, left=lo, height=0.52, color=BRAND2, alpha=0.85,
                edgecolor="#fff", linewidth=0.6, zorder=3)
        ax.text(lo, yi, f" {_fmt(lo)}", va="center", ha="right", fontsize=5.8,
                color=INK_SOFT, zorder=4)
        ax.text(hi, yi, f" {_fmt(hi)}", va="center", ha="left", fontsize=5.8,
                color=INK_SOFT, zorder=4)
        if m.get("mid") is not None:
            ax.plot([float(m["mid"])] * 2, [yi - 0.26, yi + 0.26], color="#fff",
                    lw=1.4, zorder=5)

    if current_price is not None:
        ax.axvline(float(current_price), color=INK, lw=1.1, ls="--", zorder=6)
        ax.annotate(f"CMP {_fmt(float(current_price))}", (float(current_price), max(y) + 0.62),
                    ha="left", va="bottom", fontsize=6.0, color=INK, fontweight="bold",
                    textcoords="offset points", xytext=(3, 0))
    if target is not None:
        ax.axvline(float(target), color=ACCENT, lw=1.1, zorder=6)
        ax.annotate(f"TP {_fmt(float(target))}", (float(target), min(y) - 0.62),
                    ha="right", va="top", fontsize=6.0, color=ACCENT, fontweight="bold",
                    textcoords="offset points", xytext=(-3, 0))

    # The lo/hi values are drawn OUTSIDE each bar, so the axis needs head-room or
    # the leftmost label lands on top of the y-tick text.
    vals = [v for m in methods for v in (float(m["low"]), float(m["high"]))]
    for extra in (current_price, target):
        if extra is not None:
            vals.append(float(extra))
    lo_v, hi_v = min(vals), max(vals)
    pad = (hi_v - lo_v) * 0.14 or (hi_v * 0.1 or 1)
    ax.set_xlim(lo_v - pad, hi_v + pad)

    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=6.6)
    ax.set_xlabel(f"Value per share ({currency})", fontsize=6.4)
    ax.grid(axis="x", lw=0.5)
    ax.grid(axis="y", visible=False)
    ax.set_ylim(min(y) - 1.0, max(y) + 1.0)
    return _save(fig, name)


def tornado(name, drivers: list, base_value, w=3.8, h=2.4, currency="INR"):
    """Driver sensitivity, ranked by swing — what actually moves the valuation.

    drivers = [{"label": "EBIT margin ±100bp", "low": 3050, "high": 3660}, ...]

    Sorted by absolute swing so the widest bar sits at the top, which is the whole
    point of the exhibit: it ranks the assumptions worth arguing about.
    """
    base = float(base_value)
    items = []
    for d in drivers:
        lo, hi = float(d["low"]), float(d["high"])
        items.append({"label": d["label"], "lo": min(lo, hi), "hi": max(lo, hi),
                      "swing": abs(hi - lo)})
    items.sort(key=lambda d: d["swing"])      # largest ends up at the top

    fig, ax = _new(w, h)
    for i, d in enumerate(items):
        ax.barh(i, d["lo"] - base, left=base, height=0.6, color=NEG, alpha=0.85,
                edgecolor="#fff", linewidth=0.5, zorder=3)
        ax.barh(i, d["hi"] - base, left=base, height=0.6, color=POS, alpha=0.85,
                edgecolor="#fff", linewidth=0.5, zorder=3)
        ax.text(d["lo"], i, f"{_fmt(d['lo'])} ", va="center", ha="right",
                fontsize=5.6, color=INK_SOFT, zorder=4)
        ax.text(d["hi"], i, f" {_fmt(d['hi'])}", va="center", ha="left",
                fontsize=5.6, color=INK_SOFT, zorder=4)

    ax.axvline(base, color=INK, lw=1.1, zorder=5)
    ax.set_yticks(range(len(items)))
    ax.set_yticklabels([d["label"] for d in items], fontsize=6.2)
    ax.set_xlabel(f"Value per share ({currency}) — base {_fmt(base)}", fontsize=6.2)
    ax.grid(axis="x", lw=0.5)
    ax.grid(axis="y", visible=False)
    return _save(fig, name)


# --------------------------------------------------------------------- CLI
_FNS = {k: v for k, v in list(globals().items()) if callable(v) and not k.startswith("_")
        and k not in ("set_outdir", "set_brand")}


def main():
    spec = json.load(open(sys.argv[1])) if len(sys.argv) > 1 else json.load(sys.stdin)
    set_outdir(spec.get("outdir", "charts"))

    # Company palette: spec wins, then EQR_BRAND, then a brand.json sitting one
    # level above the chart outdir (the usual reports/<TICKER>/ layout).
    brand = spec.get("brand") or os.environ.get("EQR_BRAND")
    if not brand:
        guess = os.path.join(os.path.dirname(_OUTDIR.rstrip("/\\")), "brand.json")
        if os.path.exists(guess):
            brand = guess
    if brand and os.path.exists(brand):
        set_brand(brand)
        print(f"palette: {brand}")

    for c in spec["charts"]:
        fn = _FNS[c["fn"]]
        fn(**c["args"])
    print(f"\n{len(spec['charts'])} charts written to {_OUTDIR}")


if __name__ == "__main__":
    main()
