"""erip_components.py — HTML/CSS components for visuals that should not be charts.

Three archetypes leave the chart engine:
  kpi_strip      unrelated indicators that must not share an axis
  heat_table     a 2-D sensitivity grid; a table of numbers with shading
  dupont_tree    DuPont decomposition, replacing the dedicated chart archetype

All emit markup using classes report.css already defines, plus a small scoped
block for heat_table. Text stays selectable and alignment is exact.
"""
from __future__ import annotations

HOUSE = {
    "ink": "#16202c", "inkSoft": "#5b6875", "navy": "#0b3d62",
    "blue": "#1173a8", "rule": "#dbe3ea", "panel": "#f4f7fa",
}


def _fmt(v, unit=""):
    if v is None:
        return "n/a"
    if unit == "%":
        return f"{v:,.2f}%".rstrip("0").rstrip(".")
    if unit == "x":
        return f"{v:,.2f}x"
    return f"{v:,.0f}" if abs(v) >= 100 else f"{v:,.2f}".rstrip("0").rstrip(".")


def kpi_strip(items):
    """Unrelated indicators. Each carries its own unit and period, so no shared axis
    can imply comparability that does not exist.
    items = [{"label","value","sub"}, ...]
    """
    cells = "".join(
        f'<div class="kpi"><div class="lab">{i["label"]}</div>'
        f'<div class="val">{i["value"]}</div>'
        f'<div class="sub">{i.get("sub","")}</div></div>'
        for i in items)
    return f'<div class="kpis">{cells}</div>'


def heat_table(row_vals, col_vals, grid, row_lab, col_lab, unit="", highlight=None):
    """2-D sensitivity grid. Shading is a linear ramp on the house blue; the text
    flips to white only where the fill is dark enough to need it."""
    flat = [v for r in grid for v in r if v is not None]
    lo, hi = min(flat), max(flat)
    rng = (hi - lo) or 1

    def cell(v):
        if v is None:
            return '<td class="ht-na">n/a</td>'
        t = (v - lo) / rng                      # 0..1
        # house blue at increasing opacity; keep the light end legible
        bg = f"rgba(17,115,168,{0.06 + 0.62 * t:.3f})"
        fg = "#fff" if t > 0.62 else HOUSE["ink"]
        mark = " ht-hi" if (highlight is not None and abs(v - highlight) < 1e-9) else ""
        return f'<td class="ht-c{mark}" style="background:{bg};color:{fg}">{_fmt(v, unit)}</td>'

    head = "".join(f"<th>{c}</th>" for c in col_vals)
    body = "".join(
        f"<tr><th class='ht-rh'>{row_vals[i]}</th>" + "".join(cell(v) for v in row) + "</tr>"
        for i, row in enumerate(grid))
    return f"""<div class="heat">
<table class="ht">
<thead><tr><th class="ht-corner"><span>{row_lab}</span><i>{col_lab}</i></th>{head}</tr></thead>
<tbody>{body}</tbody></table></div>"""


HEAT_CSS = """
.heat { margin: 1mm 0 2mm; }
table.ht { border-collapse: collapse; width: 100%; font-size: 7.6pt;
           font-variant-numeric: tabular-nums; }
table.ht th, table.ht td { border: 1px solid #fff; padding: 1.1mm .8mm; text-align: center; }
table.ht thead th { background: #0b3d62; color: #fff; font-weight: 700; }
table.ht th.ht-rh { background: #f4f7fa; color: #0b3d62; font-weight: 700; }
table.ht th.ht-corner { background: #0b3d62; color: #fff; font-size: 6.6pt; line-height: 1.15; }
table.ht th.ht-corner i { display: block; font-style: normal; opacity: .8; }
table.ht td.ht-c { font-weight: 500; }
table.ht td.ht-hi { outline: 1.4px solid #c8801f; font-weight: 700; }
table.ht td.ht-na { color: #8a97a4; }
"""


def dupont_tree(steps, result):
    """DuPont decomposition as an HTML scorecard, replacing the dupont3 chart.
    steps  = [{"label","value","note"}, ...]   multiplicands
    result = {"label","value"}                 the product
    """
    nodes = []
    for i, s in enumerate(steps):
        if i:
            nodes.append('<div class="dp-op">&times;</div>')
        nodes.append(
            f'<div class="node"><div class="lab">{s["label"]}</div>'
            f'<div class="val">{s["value"]}</div>'
            + (f'<div class="dp-note">{s["note"]}</div>' if s.get("note") else "")
            + "</div>")
    nodes.append('<div class="dp-op">=</div>')
    nodes.append(
        f'<div class="node dp-res"><div class="lab">{result["label"]}</div>'
        f'<div class="val">{result["value"]}</div></div>')
    return f'<div class="tree dp">{"".join(nodes)}</div>'


DUPONT_CSS = """
.tree.dp { display: flex; align-items: stretch; gap: 2mm; flex-wrap: nowrap; }
.tree.dp .node { flex: 1; }
.tree.dp .dp-op { align-self: center; color: #8a97a4; font-size: 11pt; font-weight: 700; }
.tree.dp .dp-note { font-size: 6.6pt; color: #5b6875; margin-top: .6mm; line-height: 1.15; }
.tree.dp .node.dp-res { border-color: #0b3d62; background: #f4f7fa; }
"""

ALL_CSS = HEAT_CSS + DUPONT_CSS
