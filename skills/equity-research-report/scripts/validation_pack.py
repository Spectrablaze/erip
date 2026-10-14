"""validation_pack.py - one page a reviewer can audit the model from, built only from the data files.

It gathers what the pipeline already checks and shows the working, not just the verdict:

  1 integrity    every three-statement check, its tolerance and its worst residual, per scenario,
                 with the reason for any failure taken from data/exceptions.json
  2 history      annual-report figures against the Screener spine, and reconstructed against
                 reported operating cash flow, year by year
  3 python/excel every line of the DCF (revenue, EBITDA, EBIT, FCFF, PV) and every step of the
                 equity bridge, Python against the LibreOffice-recalculated workbook, per scenario
  4 valuation    the enterprise-to-equity bridge, the WACC by terminal-growth grid, the tornado
  5 assumptions  each driver: model value, the disclosed figure it rests on, the model's reading
                 of it, citation grade, evidence type, accounting scope, value moved
  6 stress       the balance-sheet stress summary
  7 limitations  data/limitations.json, written by the analyst

    python validation_pack.py --root reports/JSWINFRA

Writes <root>/validation/validation_pack.html and validation_pack.json. Nothing is typed by hand
except the limitations; if a data file is missing, its section says so.
"""
from __future__ import annotations

import argparse
import html
import json
import os
from datetime import datetime

CASES = ("base", "bull", "bear")
TOL_LINE = 0.01            # INR Cr or INR per share: the most Python and Excel may differ by


def _j(root, *p):
    path = os.path.join(root, *p)
    return json.load(open(path, encoding="utf-8")) if os.path.exists(path) else None


def e(x):
    return html.escape(str(x))


def n(x, d=1):
    if x is None:
        return "-"
    if isinstance(x, str):
        return e(x)
    return f"{x:,.{d}f}"


def tag(ok, yes="PASS", no="FAIL", warn=False):
    cls = "ok" if ok else ("warn" if warn else "bad")
    return f'<span class="tag {cls}">{yes if ok else no}</span>'


# ---------------------------------------------------------------- 1 integrity
def tolerance_text(item, tol):
    c = item["check"]
    if c.endswith("_hist") and c != "hist_balance":
        return "&le; 0.2% of total assets"
    if c == "cfo_reconstruction":
        return "&le; 25% of the largest reported CFO"
    if c.startswith("band_"):
        return e(item["detail"])
    if item["detail"].startswith("a negative"):
        return f"&ge; -{tol:,.2f}"
    return f"&le; {tol:,.2f}"


def integrity(root):
    models = {}
    for c in CASES:
        m = _j(root, "data", "three_statement", "scenarios", c, "model.json") or (
            _j(root, "data", "three_statement", "model.json") if c == "base" else None)
        if m:
            models[c] = m
    if not models:
        return None, "<p>No three-statement model found.</p>"
    exc = {x["check"]: x for x in (_j(root, "data", "exceptions.json") or {}).get("exceptions", [])}
    base = models.get("base") or next(iter(models.values()))
    ta = base["rows"]["total_assets"]["values"]
    tol = max(0.01, max(abs(v) for v in ta if v is not None) * 1e-6)
    rows, n_block, n_block_ok = [], 0, 0
    for item in base["checks"]["items"]:
        cells = []
        for c in CASES:
            it = next((x for x in models[c]["checks"]["items"] if x["check"] == item["check"]), None) if c in models else None
            if it is None:
                cells.append("<td>-</td>")
                continue
            if it["severity"] == "blocking":
                n_block += 1
                n_block_ok += it["ok"]
            cells.append(f'<td class="num">{n(it["worst"], 2)}<br><small>{e(it["period"])}</small> '
                         f'{tag(it["ok"], no="FAIL" if it["severity"] == "blocking" else "FLAG", warn=it["severity"] != "blocking")}</td>')
        x = exc.get(item["label"])
        why = (f'<b>{e(x["status"])}</b>: {e(x["reason"])} <small>Moves the valuation: '
               f'{"yes" if x.get("moves_valuation") else "no"}. Source: {e(x["source"])}</small>') if x else e(item["detail"])
        rows.append(f'<tr><td><b>{e(item["label"])}</b><br><small>{e(item["severity"])}</small></td>'
                    f'<td>{tolerance_text(item, tol)}</td>{"".join(cells)}<td class="why">{why}</td></tr>')
    head = "".join(f"<th>{c.title()}</th>" for c in CASES)
    body = (f"<p>Tolerance for identities is the larger of INR 0.01 Cr and one millionth of total assets "
            f"(INR {tol:,.2f} Cr here). Blocking checks stop the model; advisory checks are statements about the "
            f"source data and must be explained. Worst residual in INR Cr, with the period it occurs in.</p>"
            f'<div class="scroll"><table><tr><th>Check</th><th>Tolerance</th>{head}<th>What it means</th></tr>'
            + "".join(rows) + "</table></div>")
    return {"blocking_checks": n_block, "blocking_pass": n_block_ok, "tolerance_cr": tol}, body


# ---------------------------------------------------------------- 2 history
def history(root):
    m = _j(root, "data", "three_statement", "model.json")
    ov = _j(root, "data", "three_statement", "overrides.json") or {}
    if not m:
        return None, "<p>No model.</p>"
    out = []
    rec = m.get("reconciliation") or []
    cits = ov.get("citations") or {}
    if rec:
        out.append("<h3>Annual report against the Screener spine</h3><p>Where an annual-report figure replaces a "
                   "Screener figure and the two differ by more than 2%.</p><table><tr><th>Line</th><th>Period</th>"
                   "<th>Screener</th><th>Annual report (used)</th><th>Difference</th><th>Source</th></tr>")
        for r in rec:
            c = cits.get(r["row"], {})
            out.append(f'<tr><td>{e(r["row"])}</td><td>{e(r["period"])}</td><td class="num">{n(r["screener"], 2)}</td>'
                       f'<td class="num">{n(r["annual_report"], 2)}</td><td class="num">{n(r["diff_pct"], 1)}%</td>'
                       f'<td class="why">{e(c.get("source", ""))}: {e(c.get("quote", ""))}</td></tr>')
        out.append("</table>")
    R, P = m["rows"], m["periods"]
    hist = P["hist"]
    rep, cfo, gap = (R[k]["values"] for k in ("rep_cfo", "cfo", "cfo_gap"))
    bal = R["chk_balance"]["values"]
    out.append("<h3>Operating cash flow: model reconstruction against reported</h3><p>The model rebuilds CFO from "
               "profit, depreciation and balance-sheet working-capital movements. A gap means profit is not "
               "converting to cash the way the driver model assumes. The balance check is total assets less "
               "liabilities and equity on the reported balance sheet.</p><div class=\"scroll\"><table><tr><th>INR Cr</th>"
               + "".join(f"<th>{e(p)}</th>" for p in hist) + "</tr>")
    for lab, vals in (("Reported CFO", rep), ("Reconstructed CFO", cfo), ("Gap", gap), ("Balance check", bal)):
        out.append(f"<tr><td>{lab}</td>" + "".join(f'<td class="num">{n(vals[j], 0)}</td>' for j in range(len(hist))) + "</tr>")
    out.append("</table></div>")
    ratio = [abs(gap[j]) / abs(rep[j]) for j in range(1, len(hist)) if rep[j]]
    return {"screener_vs_ar_differences": len(rec), "worst_cfo_gap_pct": round(max(ratio) * 100, 1) if ratio else None}, "".join(out)


# ---------------------------------------------------------------- 3 python vs excel
def python_lines(root, case):
    sc = (_j(root, "data", "scenarios_3s.json") or {}).get("cases", {}).get(case)
    if not sc:
        return None
    t = sc["timing"]
    m = _j(root, *sc["three_statement"].replace("\\", "/").split("/"))
    br = m["bridge"]
    f = sc["fcff_exact"]
    w, g, ro = t["wacc"], t["terminal_growth"], t.get("terminal_ronic")
    share = [t["first_year_share"]] + [1.0] * (len(f) - 1)
    pv = [f[i] * share[i] / (1 + w) ** t["periods"][i] for i in range(len(f))]
    tv = t["terminal_nopat"] * (1 + g) * (1 - (g / ro if ro else 0)) / (w - g)
    pv_tv = tv / (1 + w) ** t["terminal_period"]
    ev = sum(pv) + pv_tv
    eq_bal = ev - t["net_debt"] - (t.get("lease_liabilities") or 0) - (t.get("minority_interest") or 0) + (t.get("non_operating_assets") or 0)
    eq_val = eq_bal * t["roll_forward"]
    return {"lines": {"revenue": br["revenue"], "ebitda": br["ebitda"], "ebit": br["ebit"], "fcff": f, "pv_fcff": pv},
            "scalars": {"pv_explicit": sum(pv), "terminal_value": tv, "pv_terminal": pv_tv, "ev": ev,
                        "net_debt": t["net_debt"], "lease_liabilities": t.get("lease_liabilities") or 0,
                        "minority_interest": t.get("minority_interest") or 0,
                        "non_operating_assets": t.get("non_operating_assets") or 0,
                        "equity_balance_date": eq_bal, "equity_valuation_date": eq_val, "shares": t["shares"],
                        "wacc": w, "cost_of_equity": t["cost_of_equity"]},
            "value": eq_val / t["shares"], "periods": br["periods"]}


LINE_NAMES = {"revenue": "Revenue", "ebitda": "EBITDA", "ebit": "EBIT", "fcff": "Free cash flow to the firm",
              "pv_fcff": "PV of FCFF"}
SCALAR_NAMES = {"pv_explicit": "Sum of PV of FCFF", "terminal_value": "Terminal value", "pv_terminal": "PV of terminal value",
                "ev": "Enterprise value", "net_debt": "Net debt (negative = net cash)", "lease_liabilities": "Lease liabilities",
                "minority_interest": "Minority interest", "non_operating_assets": "Non-operating assets",
                "equity_balance_date": "Equity value, balance-sheet date", "equity_valuation_date": "Equity value, valuation date",
                "shares": "Shares (Cr)", "wacc": "WACC", "cost_of_equity": "Cost of equity"}


def python_vs_excel(root):
    wb = _j(root, "data", "workbook_check.json")
    if not wb or not any("lines" in c for c in wb["cases"].values()):
        return None, "<p>The workbook check has no line reads. Rerun live_valuation.py --recalc.</p>"
    worst, out, compared = 0.0, [], 0
    summary = []
    for case in CASES:
        py, xl = python_lines(root, case), wb["cases"].get(case)
        if not py or not xl:
            continue
        diffs = {}
        for k, vals in py["lines"].items():
            xv = xl["lines"].get(k)
            if xv:
                d = max(abs(a - b) for a, b in zip(vals, xv))
                diffs[k] = d
                compared += len(vals)
        for k, v in py["scalars"].items():
            if k in xl["scalars"]:
                diffs[k] = abs(v - xl["scalars"][k])
                compared += 1
        dv = abs(py["value"] - xl["value"])
        diffs["value"] = dv if dv > 0.005 else 0.0      # the workbook value is stored to the paisa
        worst = max(worst, max(diffs.values()))
        summary.append((case, py, xl, diffs))
    # base case in full, year by year
    case, py, xl, diffs = summary[0]
    out.append(f"<h3>Base case, every year</h3><div class=\"scroll\"><table><tr><th>INR Cr</th><th></th>"
               + "".join(f"<th>{e(p)}</th>" for p in py["periods"]) + "</tr>")
    for k, name in LINE_NAMES.items():
        if k not in xl["lines"]:
            continue
        a, b = py["lines"][k], xl["lines"][k]
        out.append(f'<tr><td rowspan="3"><b>{name}</b></td><td>Python</td>' + "".join(f'<td class="num">{n(v, 1)}</td>' for v in a) + "</tr>")
        out.append("<tr><td>Excel</td>" + "".join(f'<td class="num">{n(v, 1)}</td>' for v in b) + "</tr>")
        out.append('<tr class="diff"><td>Difference</td>' + "".join(f'<td class="num">{abs(x - y):.4f}</td>' for x, y in zip(a, b)) + "</tr>")
    out.append("</table></div>")
    # bridge, every case
    out.append("<h3>Valuation steps, every scenario</h3><div class=\"scroll\"><table><tr><th>Step</th>"
               + "".join(f"<th>{c.title()} Python</th><th>{c.title()} Excel</th>" for c, *_ in summary) + "<th>Largest difference</th></tr>")
    for k, name in SCALAR_NAMES.items():
        pct = k in ("wacc", "cost_of_equity")
        fmt = (lambda v: f"{v * 100:.4f}%") if pct else (lambda v: n(v, 2))
        cells = "".join(f'<td class="num">{fmt(p["scalars"][k])}</td><td class="num">{fmt(x["scalars"].get(k, 0))}</td>'
                        for c, p, x, d in summary)
        out.append(f"<tr><td>{name}</td>{cells}<td class=\"num\">{max(d.get(k, 0) for *_, d in summary):.6f}</td></tr>")
    cells = "".join(f'<td class="num">{p["value"]:.4f}</td><td class="num">{x["value"]:.2f}</td>' for c, p, x, d in summary)
    out.append(f"<tr><td><b>Value per share (INR)</b></td>{cells}<td class=\"num\">{max(d['value'] for *_, d in summary):.4f}</td></tr></table></div>")
    ok = worst <= TOL_LINE
    head = (f"<p>{compared} numbers compared across {len(summary)} scenarios. Excel values come from the workbook after "
            f"LibreOffice recalculates it with the scenario switch set to each case (run {e(wb['run_at'])}); Python values "
            f"from the three-statement model and model.py. Largest difference: {worst:.1e} (tolerance {TOL_LINE}). "
            f"{tag(ok)}</p>")
    return {"numbers_compared": compared, "largest_difference": worst, "pass": ok, "run_at": wb["run_at"]}, head + "".join(out)


# ---------------------------------------------------------------- 4 valuation
def valuation(root):
    m = _j(root, "data", "model.json")
    if not m:
        return None, ""
    d = m["dcf"]
    out = ['<h3>Enterprise value to equity value, base case</h3><table class="bridge">']
    for k, v in d["bridge"].items():
        if k == "Less: net debt" and isinstance(v, (int, float)) and v > 0:
            k = "Add: net cash"                  # net debt is negative: the bridge adds cash
        if not isinstance(v, (int, float)):
            cell = e(v)
        elif "%" in k:
            cell = f"{v:,.1f}%"
        elif "Shares" in k:
            cell = n(v, 2)
        else:
            cell = n(v, 0)
        out.append(f'<tr><td>{e(k)}</td><td class="num">{cell}</td></tr>')
    out.append("</table>")
    s = d.get("sensitivity")
    if s:
        t = d["timing"]
        out.append("<h3>WACC against terminal growth, value per share (INR)</h3><table><tr><th>WACC \\ g</th>"
                   + "".join(f"<th>{e(g)}</th>" for g in s["terminal_growth"]) + "</tr>")
        bw, bg = f"{t['wacc'] * 100:.1f}%", f"{t['terminal_growth'] * 100:.1f}%"
        for w, row in zip(s["wacc"], s["grid"]):
            out.append(f"<tr><th>{e(w)}</th>" + "".join(
                f'<td class="num{" hl" if (w == bw and g == bg) else ""}">{n(v, 0)}</td>' for g, v in zip(s["terminal_growth"], row)) + "</tr>")
        out.append("</table>")
        if t.get("terminal_ronic"):
            out.append(f"<p>The terminal value is funded at a {t['terminal_ronic'] * 100:.1f}% return on new capital. "
                       f"Growth creates value only when that return exceeds the WACC, so where the two are close, as here, "
                       f"terminal growth moves the value very little and the discount rate dominates.</p>")
    tor = _j(root, "data", "tornado.json")
    if tor:
        out.append(f"<h3>One driver at a time (each re-runs the three-statement model)</h3><table><tr><th>Driver</th>"
                   f"<th>Low</th><th>High</th><th>Range</th></tr>")
        for r in tor["drivers"]:
            out.append(f'<tr><td>{e(r["label"])}</td><td class="num">{r["low"]}</td><td class="num">{r["high"]}</td>'
                       f'<td class="num">{abs(r["high"] - r["low"])}</td></tr>')
        out.append(f'</table><p>Base case INR {tor["base_value"]}.</p>')
    return {"value_per_share": d["bridge"].get("Intrinsic value per share (INR)")}, "".join(out)


# ---------------------------------------------------------------- 5 assumptions
TORNADO_KEYS = {"revenue_growth": "Revenue growth", "ebitda_margin": "EBITDA margin", "beta": "Beta",
                "capex_pct_sales": "Capex", "risk_free_rate": "Risk-free", "effective_tax_rate": "Tax",
                "terminal_growth": "Terminal growth"}


def _val(a):
    v, u = a.get("value"), a.get("unit") or ""
    if isinstance(v, list):
        return f"{v[0]:g} to {v[-1]:g} {e(u)}<br><small>{', '.join(f'{x:g}' for x in v)}</small>"
    return f"{v:g} {e(u)}" if isinstance(v, (int, float)) else e(v)


def assumptions(root):
    D = _j(root, "decisions.json")
    cc = _j(root, "data", "citation_check.json") or {"rows": []}
    tor = {r["label"]: r for r in (_j(root, "data", "tornado.json") or {}).get("drivers", [])}
    if not D:
        return None, ""
    out = ['<div class="scroll"><table><tr><th>Assumption</th><th>Model value</th><th>Confidence</th>'
           '<th>What the source says, and its check</th><th>How the model reads it</th><th>Value moved (INR/share)</th></tr>']
    unsupported = []
    for k, a in D["assumptions"].items():
        rows = [r for r in cc["rows"] if r["assumption"] == k]
        if not rows:
            unsupported.append(k)
        ev = "".join(
            f'<div class="ev"><span class="tag t">{e(r["type"])}</span> <span class="tag g">{e(r["grade"])}</span>'
            f' <span class="tag s">{e(r.get("scope", ""))}</span><br>{e(str(r.get("quote") or "")[:220])}'
            f'<br><small>{e(r.get("source") or "")}{(" p." + str(r["page"])) if r.get("page") else ""}</small></div>'
            for r in rows) or '<span class="tag warn">NO CITATION</span>'
        why = a.get("why")
        why = (why[0] if isinstance(why, list) else why) or ""
        lab = TORNADO_KEYS.get(k)
        hit = next((r for l, r in tor.items() if lab and l.startswith(lab)), None)
        moved = f'{hit["low"]} to {hit["high"]}<br><small>{e(hit["label"])}</small>' if hit else "-"
        out.append(f'<tr><td><b>{e(k)}</b></td><td>{_val(a)}</td><td>{e(a.get("confidence") or "")}</td>'
                   f'<td class="why">{ev}</td><td class="why">{e(why[:320])}{"..." if len(why) > 320 else ""}</td>'
                   f'<td class="num">{moved}</td></tr>')
    out.append("</table></div>")
    head = ("<p>Each driver with the evidence behind it. <b>Type</b> says what kind of statement the source is "
            "(a reported fact, management guidance, a long-range aspiration, a third-party forecast, a market price, an "
            "analyst convention, or a derived figure). <b>Grade</b> says whether the quote was found on the cited page. "
            "<b>Scope</b> says whether the page is from the consolidated or standalone accounts. "
            f"{len(unsupported)} assumption(s) carry no citation: {e(', '.join(unsupported)) or 'none'}.</p>")
    if cc.get("forward_view_on_aspiration"):
        head += f"<p><b>Flag:</b> the forward view of {e(', '.join(cc['forward_view_on_aspiration']))} rests only on a long-range aspiration.</p>"
    return {"assumptions": len(D["assumptions"]), "without_citation": unsupported,
            "accounting_scope": cc.get("accounting_scope"), "evidence_types": cc.get("evidence_types")}, head + "".join(out)


# ---------------------------------------------------------------- 6 stress
def stress(root):
    st = _j(root, "data", "stress.json")
    if not st:
        return None, "<p>No stress run.</p>"
    th = st["thresholds"]
    out = [f'<p>Reference levels: {th["net_debt_ebitda_max"]["value"]}x net debt/EBITDA ({e(th["net_debt_ebitda_max"]["kind"])}), '
           f'{th["interest_cover_min"]["value"]}x interest cover ({e(th["interest_cover_min"]["kind"])}). Invariant violations: '
           f'{len(st.get("invariant_violations") or [])}.</p><table><tr><th>Case</th><th>Value/share</th><th>Peak ND/EBITDA</th>'
           f'<th>Min interest cover</th><th>Revolver peak (Cr)</th></tr>']
    for name, c in [("Base case", st["base"])] + [(c["name"], c) for c in st["cases"]]:
        bad = c["peak_nd_ebitda"] > th["net_debt_ebitda_max"]["value"] or c["min_interest_cover"] < th["interest_cover_min"]["value"]
        out.append(f'<tr class="{"badrow" if bad else ""}"><td>{e(name)}</td><td class="num">{c["value_per_share"]}</td>'
                   f'<td class="num">{c["peak_nd_ebitda"]:.2f}x {e(c["peak_nd_ebitda_year"])}</td>'
                   f'<td class="num">{c["min_interest_cover"]:.1f}x</td><td class="num">{n(c.get("peak_revolver"), 0)} '
                   f'{e(c.get("peak_revolver_year") or "")}</td></tr>')
    out.append("</table>")
    return {"cases": len(st["cases"]), "invariant_violations": len(st.get("invariant_violations") or [])}, "".join(out)


# ---------------------------------------------------------------- 7 limitations
def limitations(root):
    L = (_j(root, "data", "limitations.json") or {}).get("limitations", [])
    if not L:
        return [], '<p class="warn">No limitations recorded in data/limitations.json.</p>'
    out = ["<table><tr><th>Area</th><th>Limitation</th><th>Moves the value</th><th>What would fix it</th></tr>"]
    for x in L:
        out.append(f'<tr><td><b>{e(x["area"])}</b></td><td class="why">{e(x["issue"])}</td>'
                   f'<td>{"yes" if x.get("moves_valuation") else "no"}</td><td class="why">{e(x["fix"])}</td></tr>')
    out.append("</table>")
    return [x["area"] for x in L], "".join(out)


CSS = """
:root{--bg:#fbfaf7;--fg:#1d2430;--mut:#5d6675;--line:#dcd8cf;--card:#fff;--ok:#1d7a46;--bad:#b3261e;--warn:#9a6700;--hl:#fff1c2;--acc:#1f4e79}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#14171c;--fg:#e6e8eb;--mut:#9aa3ae;--line:#2c323b;--card:#1b1f26;--ok:#57c48a;--bad:#ff8a80;--warn:#e3b341;--hl:#4a3d12;--acc:#8ab4e0}}
:root[data-theme="dark"]{--bg:#14171c;--fg:#e6e8eb;--mut:#9aa3ae;--line:#2c323b;--card:#1b1f26;--ok:#57c48a;--bad:#ff8a80;--warn:#e3b341;--hl:#4a3d12;--acc:#8ab4e0}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:14px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
main{max-width:1180px;margin:0 auto;padding:24px 16px 64px}h1{font-size:24px;margin:0 0 4px}h2{font-size:18px;margin:36px 0 8px;padding-top:12px;border-top:2px solid var(--fg)}
h3{font-size:15px;margin:22px 0 6px}p{max-width:900px}small{color:var(--mut)}.sub{color:var(--mut)}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:10px;margin:16px 0}
.tile{background:var(--card);border:1px solid var(--line);border-radius:6px;padding:10px 12px}.tile b{display:block;font-size:20px}
.scroll{overflow-x:auto}table{border-collapse:collapse;width:100%;margin:6px 0 10px;background:var(--card)}
th,td{border:1px solid var(--line);padding:4px 6px;vertical-align:top;text-align:left}th{background:var(--bg);font-weight:600}
td.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}td.hl{background:var(--hl);font-weight:700}
td.why{min-width:260px;font-size:13px}tr.diff td{color:var(--mut);font-size:12px}tr.badrow td{color:var(--bad)}
table.bridge{width:auto}.tag{display:inline-block;font-size:11px;font-weight:700;padding:0 5px;border-radius:3px;border:1px solid}
.tag.ok{color:var(--ok)}.tag.bad{color:var(--bad)}.tag.warn{color:var(--warn)}.tag.t{color:var(--acc)}.tag.g,.tag.s{color:var(--mut)}
.ev{margin-bottom:6px}nav a{margin-right:12px;color:var(--acc)}code{font-size:12px}pre{overflow-x:auto;background:var(--card);border:1px solid var(--line);padding:8px}
"""


def build(root):
    D = _j(root, "decisions.json") or {}
    V = _j(root, "data", "validation.json") or {}
    SR = _j(root, "data", "source_register.json") or {}
    secs = [("integrity", "1. Model integrity checks", integrity),
            ("history", "2. History reconciled to the source", history),
            ("excel", "3. Python against Excel, line by line", python_vs_excel),
            ("valuation", "4. Valuation bridge and sensitivity", valuation),
            ("assumptions", "5. From source to assumption to value", assumptions),
            ("stress", "6. Balance-sheet stress", stress),
            ("limitations", "7. Known limitations", limitations)]
    summary, parts = {}, []
    for key, title, fn in secs:
        s, body = fn(root)
        summary[key] = s
        parts.append(f'<h2 id="{key}">{title}</h2>{body}')
    ig, px = summary.get("integrity") or {}, summary.get("excel") or {}
    dates, call = V.get("dates", {}), V.get("call", {})
    tiles = [
        ("Blocking checks", f'{ig.get("blocking_pass", 0)} of {ig.get("blocking_checks", 0)} pass', "across base, bull and bear"),
        ("Python vs Excel", (lambda x: f"{x:.1e}" if 0 < x < 1e-4 else f"{x:.4f}")(px.get("largest_difference", 0) or 0), f'largest difference over {px.get("numbers_compared", 0)} numbers'),
        ("Report validation", e(V.get("status", "-")), f'run {e(V.get("validated_at", "-"))}'),
        ("Known limitations", str(len(summary.get("limitations") or [])), "stated in section 7"),
    ]
    docs = "".join(f'<tr><td>{e(d["id"])}</td><td>{e(d["kind"])}</td><td>{e(d["path"])}</td><td>{d.get("pages") or "-"}</td>'
                   f'<td><code>{e(d["sha256"][:16])}</code></td></tr>' for d in SR.get("documents", []))
    title = f'{D.get("company", "")} validation pack'
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(D.get("ticker", ""))} validation pack</title><style>{CSS}</style></head><body><main>
<h1>{e(title)}</h1>
<p class="sub">{e(D.get("ticker", ""))} &middot; call v{call.get("version", "-")} {e(call.get("rating", ""))} INR {n(call.get("target"), 0)} &middot;
cover {e(dates.get("cover_date", "-"))} &middot; net debt at {e(dates.get("balance_sheet_date", "-"))} &middot; actuals to {e(dates.get("last_actual_period", "-"))}
&middot; forecast {e(dates.get("forecast", "-"))} &middot; built {datetime.now().strftime("%Y-%m-%d %H:%M")}</p>
<p>This pack shows the working behind the published valuation so it can be checked without trusting it. Every number below is read
from the pipeline's data files; only section 7 is written by hand. A model that ties is not thereby right: sections 2, 5 and 7 are
where judgement enters, and they are shown as such.</p>
<nav>{"".join(f'<a href="#{k}">{t.split(". ", 1)[1]}</a>' for k, t, _ in secs)}</nav>
<div class="tiles">{"".join(f'<div class="tile"><small>{a}</small><b>{b}</b><small>{c}</small></div>' for a, b, c in tiles)}</div>
{"".join(parts)}
<h2 id="sources">Inputs (hashed)</h2><table><tr><th>ID</th><th>Kind</th><th>File</th><th>Pages</th><th>SHA-256 (first 16)</th></tr>{docs}</table>
<h2 id="reproduce">Reproduce</h2><p>From the repository root, with the inputs in place:</p>
<pre><code>python skills/equity-research-report/scripts/scenario_runs.py --root reports/{e(D.get("ticker", "T"))} --sector {e(D.get("sector", ""))}
python skills/equity-research-report/scripts/workbook/live_valuation.py --root reports/{e(D.get("ticker", "T"))} --out model.xlsx --recalc
python skills/equity-research-report/scripts/validation_pack.py --root reports/{e(D.get("ticker", "T"))}
python skills/equity-research-report/tests/run_tests.py</code></pre>
</main></body></html>"""
    # every table scrolls sideways on a phone instead of widening the page
    page = page.replace('<div class="scroll">', "").replace("</table></div>", "</table>")
    page = page.replace("<table", '<div class="scroll"><table').replace("</table>", "</table></div>")
    os.makedirs(os.path.join(root, "validation"), exist_ok=True)
    open(os.path.join(root, "validation", "validation_pack.html"), "w", encoding="utf-8").write(page)
    summary["built_at"] = datetime.now().isoformat(timespec="seconds")
    json.dump(summary, open(os.path.join(root, "validation", "validation_pack.json"), "w", encoding="utf-8"), indent=1, default=str)
    return summary


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--root", required=True)
    a = ap.parse_args()
    s = build(os.path.abspath(a.root))
    ig, px = s.get("integrity") or {}, s.get("excel") or {}
    print(f"blocking checks {ig.get('blocking_pass')}/{ig.get('blocking_checks')}; python vs excel largest difference "
          f"{px.get('largest_difference')} over {px.get('numbers_compared')} numbers; limitations {len(s.get('limitations') or [])}")
    print("->", os.path.join(a.root, "validation", "validation_pack.html"))


if __name__ == "__main__":
    main()
