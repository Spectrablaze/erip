"""stress_section.py - the report page for data/stress.json, built from the report's own helpers.

    from stress_section import stress_page
    stress_page(ST, CMP, helpers)   # helpers: dict with w, table, row, split, n, pc, heat_table

Every number comes from stress.json (written by stress_test.py), so the page follows the model.
"""
from __future__ import annotations


def stress_page(ST, CMP, h, title="Stress tests: what breaks the balance sheet, and what breaks the thesis"):
    w, table, row, split, n, pc, heat = (h[k] for k in ("w", "table", "row", "split", "n", "pc", "heat_table"))
    th, base, cases = ST["thresholds"], ST["base"], ST["cases"]
    nd_t = th.get("net_debt_ebitda_max", {})
    ic_t = th.get("interest_cover_min", {})
    worst = min(cases, key=lambda c: c["value_per_share"]) if cases else None
    breaching = [c for c in cases if any("net debt/EBITDA" in b or "interest cover" in b for b in c["breaches"])]

    rows = [row("Base case", [n(base["value_per_share"]), "", f"{base['peak_nd_ebitda']:.2f}x ({base['peak_nd_ebitda_year']})",
                              f"{base['min_interest_cover']:.1f}x", n(base["peak_revolver"])], cls="sub")]
    for c in cases:
        hit = [b for b in c["breaches"] if "revolver" not in b]
        rows.append(row(c["name"], [n(c["value_per_share"]), pc((c["value_per_share"] / base["value_per_share"] - 1) * 100, 0, True),
                                    f"{c['peak_nd_ebitda']:.2f}x ({c['peak_nd_ebitda_year']})" + (" !" if hit else ""),
                                    f"{c['min_interest_cover']:.1f}x", n(c["peak_revolver"])],
                        cls="total" if hit else ""))
    if base["peak_revolver"] > 0:
        fund = (f"<p><b>The base case is not fully funded.</b> On our capex and dividend path the model draws "
                f"INR {base['peak_revolver']:,} Cr on its revolver, peaking in {base.get('peak_revolver_year', 'the build-out')}: "
                "borrowing beyond the term debt we model. The company has not disclosed how it will fund this, so the "
                "valuation assumes it can be raised at our cost of debt.</p>")
    else:
        fund = ("<p><b>The base case is fully funded</b> from operating cash flow, cash on hand and the term debt we model: "
                "the revolver is never drawn.</p>")
    left = (
        "<h3>How the tests work</h3>"
        "<p>Each stress rebuilds the linked three-statement model, so working capital, the revolver and interest respond to the "
        "shock instead of being estimated beside it. Leverage is measured against "
        f"<b>{nd_t.get('value', 'n/a')}x net debt/EBITDA</b> ({nd_t.get('kind', '')}) and interest cover against "
        f"<b>{ic_t.get('value', 'n/a')}x EBITDA/interest</b> ({ic_t.get('kind', '')}). Neither is a disclosed loan covenant: "
        "the annual report states only that covenants are met.</p>" + fund
        + table("Named stresses (value per share in INR; leverage peak and year)",
                ["Stress", "INR/share", "vs base", "Peak ND/EBITDA", "Min cover", "Revolver peak (Cr)"], rows, cls="xs",
                src=f"stress.json; ! marks a breached reference level. Leverage reference: {nd_t.get('source', '')}")
    )
    g = ST.get("grid")
    right = ""
    if g:
        rl = [f"{y:+}pp" for y in g["y"]["steps"]]
        cl = [f"{x:+}pp" for x in g["x"]["steps"]]
        vals = [[c["value"] for c in r] for r in g["cells"]]
        levs = [c["peak_nd_ebitda"] for r in g["cells"] for c in r]
        right += ("<h3>Two drivers at once (INR per share)</h3>"
                  + heat(rl, cl, vals, g["y"]["label"], g["x"]["label"], highlight=base["value_per_share"])
                  + f"<p class=\"source\">Rows: {g['y']['label']}; columns: {g['x']['label']}, both relative to the base case. "
                    f"Peak net debt/EBITDA across the grid ranges {min(levs):.2f}x to {max(levs):.2f}x. "
                    f"Even the best corner is INR {max(max(r) for r in vals):,} against a price of INR {CMP:,.0f}.</p>")
    rev = ST.get("reverse") or []
    if rev:
        items = []
        for r in rev:
            if r.get("shock") is None:
                a = r.get("at_shock") or {}
                items.append(f"<li><b>{r['label']}:</b> {r['result']}. Leverage stays inside the reference level, but "
                             f"value falls to INR {a.get('value_per_share', 0):,}: this shock destroys value, not solvency.</li>")
            else:
                a = r["at_shock"]
                items.append(f"<li><b>{r['label']}:</b> breaches at {r['shock']:+g} (peak {a['peak_nd_ebitda']:.2f}x in "
                             f"{a['peak_nd_ebitda_year']}, value INR {a['value_per_share']:,}).</li>")
        right += "<h3>Reverse stress: how far before leverage breaks</h3><ul class=\"bullet-sq tight\">" + "".join(items) + "</ul>"
    watch = [c for c in cases if c.get("watch")]
    if watch:
        right += ("<h3>What would show it early</h3><ul class=\"bullet-sq tight\">"
                  + "".join(f"<li><b>{c['name']}:</b> {c['watch']}</li>" for c in watch[:4]) + "</ul>")
    viol = ST.get("invariant_violations") or []
    right += ("<p class=\"source\">Invariant checks (value rises with growth and margin; no adverse case raises value): "
              + ("all hold." if not viol else f"{len(viol)} violation(s): {viol[0]}") + "</p>")

    rt = (f"The worst single stress is <b>{worst['name'].lower()}</b> at INR {worst['value_per_share']:,} a share. "
          if worst else "")
    rt += (f"{len(breaching)} of {len(cases)} stresses breach a leverage or cover reference level"
           + (f" ({', '.join(c['name'].lower() for c in breaching)})" if breaching else "") + ". ")
    rt += "None of them changes the rating: every case values the stock below the price."
    if any(c["value_per_share"] >= CMP for c in cases):
        rt = rt.replace("None of them changes the rating: every case values the stock below the price.",
                        "At least one case reaches the price; the rating depends on it not happening.")
    # Smaller pieces in sequence rather than one tall split, so the page can start part-way down a
    # page that is already in use; a single atomic block strands whatever precedes it.
    w(f'<section class="page flow"><h2>{title}</h2>')
    w(left)
    rv_watch = right[right.index("<h3>Reverse"):] if "<h3>Reverse" in right else right
    grid_part = right[:right.index("<h3>Reverse")] if "<h3>Reverse" in right else ""
    w(split(grid_part, rv_watch) if grid_part else rv_watch)
    w(f'<div class="note"><b>Read-through:</b> {rt}</div>')
    w("</section>")
