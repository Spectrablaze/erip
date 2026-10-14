"""stress_test.py - what breaks the balance sheet, and what breaks the thesis.

Every case rebuilds the linked three-statement model from a flexed copy of assumptions.json, so
leverage, interest, the revolver and cash respond to the shock rather than being estimated beside
it. Driven by data/stress_spec.json:

  thresholds  reference levels with their source: net_debt_ebitda_max, interest_cover_min
              (EBITDA / interest). Disclosed covenants where they exist; otherwise a rating agency's
              forecast or management's stated ceiling, labelled as such.
  cases       named stresses, each a list of flexes (below), one at a time or combined
  grid        two drivers moved together (e.g. revenue growth x EBITDA margin)
  reverse     the uniform shock to one driver at which a threshold is first breached

Flexes (assumptions.json units, percent where the input is in percent):
  {"op": "shift", "key": "revenue_growth", "by": -3, "years": [1, 2]}   add, optionally only some years
  {"op": "scale", "key": "capex_pct_sales", "by": 1.2}                    multiply
  {"op": "set",   "key": "tax_rate", "value": 25.17}                      replace
  {"op": "delay", "key": "revenue_growth", "fill": 6.0}                   push the path back a year
  {"op": "margin", "by": -3}       EBITDA margin; moves ebit_margin and _analyst.ebitda_margin together

Committed capex. Capex is a % of sales in the model, so a revenue shock would shrink it. That is right
for maintenance capex and wrong for a contracted build-out: a delayed or weaker project still costs
what it costs. spec["committed_capex_years"] (0-based forecast years) holds those years' capex in
rupees under any revenue shock; an explicit capex flex still scales them.

Invariants. Every run is checked against what must be true whatever the numbers: value rises with
revenue growth and with margin across the grid, and a delay, a cut or a cost shock never raises
value. A violation is reported, because it means the model, not the company, is driving the answer.

    python stress_test.py --root reports/<T> --sector realestate [--skip-grid]

Writes data/stress.json.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from scenario_runs import value_case  # noqa: E402


def _revenue_path(a, base_sales):
    g = a["revenue_growth"]
    out, r = [], base_sales
    for x in g:
        r = r * (1 + (x / 100 if abs(x) > 1 else x))
        out.append(r)
    return out


def apply(a, flex, committed=None, base_sales=None):
    a0 = a
    a = copy.deepcopy(a)
    capex_scale = [1.0] * len(a.get("capex_pct_sales") or [])
    for f in flex:
        if f.get("key") == "capex_pct_sales" and f["op"] == "scale":
            yrs = f.get("years")
            capex_scale = [s_ * (f["by"] if (yrs is None or i in yrs) else 1.0) for i, s_ in enumerate(capex_scale)]
        op = f["op"]
        if op == "margin":
            a["ebit_margin"] = [x + f["by"] for x in a["ebit_margin"]]
            an = a.get("_analyst") or {}
            if an.get("ebitda_margin"):
                an["ebitda_margin"] = [x + f["by"] for x in an["ebitda_margin"]]
            if isinstance(a.get("ebitda_margin"), list):
                a["ebitda_margin"] = [x + f["by"] for x in a["ebitda_margin"]]
            continue
        k, v = f["key"], a.get(f["key"])
        yrs = f.get("years")
        if op == "set":
            a[k] = f["value"]
        elif op in ("shift", "scale"):
            fn = (lambda x: x + f["by"]) if op == "shift" else (lambda x: x * f["by"])
            if isinstance(v, list):
                a[k] = [fn(x) if (yrs is None or i in yrs) else x for i, x in enumerate(v)]
            else:
                a[k] = fn(float(v))
        elif op == "delay":
            a[k] = [f.get("fill", v[0])] + list(v[:-1])
        else:
            raise SystemExit(f"unknown flex op {op}")
    if committed and base_sales and a.get("revenue_growth") != a0.get("revenue_growth"):
        r0, r1 = _revenue_path(a0, base_sales), _revenue_path(a, base_sales)
        p0 = a0["capex_pct_sales"]
        for i in committed:
            if i < len(p0):
                a["capex_pct_sales"][i] = p0[i] * r0[i] / r1[i] * capex_scale[i]   # same rupees, then any overrun
    return a


def metrics(m, ts, th):
    n = len(ts["bridge"]["periods"])
    per = ts["bridge"]["periods"]
    r = ts["rows"]
    v = lambda k: (r[k]["values"] if isinstance(r[k], dict) else r[k])[-n:]
    ebitda, intr = v("ebitda"), v("interest_expense")
    nd_e = v("s_nd_ebitda")
    cover = [(e / i) if i and i > 1e-6 else None for e, i in zip(ebitda, intr)]
    cash_head = [c - mc for c, mc in zip(v("cash"), v("min_cash"))]
    rev = v("revolver")
    k_nd = max(range(n), key=lambda i: nd_e[i])
    covs = [(c, i) for i, c in enumerate(cover) if c is not None]
    k_cov = min(covs)[1] if covs else None
    tg = (m["dcf"].get("target") or {})
    out = {"value_per_share": m["dcf"]["bridge"]["Intrinsic value per share (INR)"], "target": tg.get("target"),
           "rating": tg.get("rating"),
           "peak_nd_ebitda": round(nd_e[k_nd], 2), "peak_nd_ebitda_year": per[k_nd],
           "min_interest_cover": None if k_cov is None else round(cover[k_cov], 2),
           "min_interest_cover_year": None if k_cov is None else per[k_cov],
           "peak_revolver": round(max(rev)), "peak_revolver_year": per[max(range(n), key=lambda i: rev[i])],
           "min_cash_headroom": round(min(cash_head)),
           "nd_ebitda_path": [round(x, 2) for x in nd_e]}
    br = []
    if th.get("net_debt_ebitda_max") and out["peak_nd_ebitda"] > th["net_debt_ebitda_max"]["value"]:
        yrs = [per[i] for i in range(n) if nd_e[i] > th["net_debt_ebitda_max"]["value"]]
        br.append(f"net debt/EBITDA above {th['net_debt_ebitda_max']['value']}x in {', '.join(yrs)}")
    if th.get("interest_cover_min") and out["min_interest_cover"] is not None \
            and out["min_interest_cover"] < th["interest_cover_min"]["value"]:
        br.append(f"interest cover below {th['interest_cover_min']['value']}x in {out['min_interest_cover_year']}")
    if out["peak_revolver"] > 0:
        br.append(f"revolver drawn, peak INR {out['peak_revolver']:,} Cr")
    out["breaches"] = br
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--root", required=True)
    ap.add_argument("--sector", required=True)
    ap.add_argument("--skip-grid", action="store_true")
    a = ap.parse_args()
    root = os.path.abspath(a.root)
    spec = json.load(open(os.path.join(root, "data", "stress_spec.json"), encoding="utf-8"))
    A = json.load(open(os.path.join(root, "data", "assumptions.json"), encoding="utf-8"))
    strat = os.path.join(root, "data", "model_strategy.json")
    strat = strat if os.path.exists(strat) else None
    th = spec.get("thresholds", {})
    committed = spec.get("committed_capex_years")
    F = json.load(open(os.path.join(root, "data", "financials.json"), encoding="utf-8"))
    base_sales = [x for x in F["annual"]["Sales"] if x is not None][-1]

    def run(flex):
        m, ts = value_case(root, apply(A, flex, committed, base_sales), "stress", a.sector, strat, with_statements=True)
        return metrics(m, ts, th)

    base = run([])
    print(f"  base: INR {base['value_per_share']}  peak ND/EBITDA {base['peak_nd_ebitda']}x ({base['peak_nd_ebitda_year']})  "
          f"min cover {base['min_interest_cover']}x  revolver {base['peak_revolver']:,}")
    cases = []
    for c in spec.get("cases", []):
        r = run(c["flex"])
        r.update(name=c["name"], why=c.get("why"), watch=c.get("watch"))
        cases.append(r)
        print(f"  {c['name'][:44]:44} INR {r['value_per_share']:>6}  ND/EBITDA {r['peak_nd_ebitda']:>5}x  "
              f"cover {r['min_interest_cover']}x  {'; '.join(r['breaches']) or 'no breach'}")
    grid = None
    if spec.get("grid") and not a.skip_grid:
        gx, gy = spec["grid"]["x"], spec["grid"]["y"]
        cells = []
        for y in gy["steps"]:
            row = []
            for x in gx["steps"]:
                fl = [dict(gx["flex"], by=x), dict(gy["flex"], by=y)]
                r = run(fl)
                row.append({"value": r["value_per_share"], "peak_nd_ebitda": r["peak_nd_ebitda"]})
            cells.append(row)
            print(f"  grid row {gy['label']} {y:+}: " + "  ".join(f"{c['value']}/{c['peak_nd_ebitda']}x" for c in row))
        grid = {"x": {k: gx[k] for k in ("label", "steps")}, "y": {k: gy[k] for k in ("label", "steps")}, "cells": cells}
    reverse = []
    for rv in spec.get("reverse", []):
        thr = th[rv["threshold"]]["value"]
        key = "peak_nd_ebitda" if rv["threshold"] == "net_debt_ebitda_max" else "min_interest_cover"
        bad = (lambda r: r[key] > thr) if key == "peak_nd_ebitda" else (lambda r: (r[key] or 99) < thr)
        # search between no shock and max_shock (no shock is 0 for a shift, 1 for a scale)
        lo, hi = float(rv.get("neutral", 1.0 if rv["flex"]["op"] == "scale" else 0.0)), float(rv["max_shock"])
        r_hi = run([dict(rv["flex"], by=hi)])
        if not bad(r_hi):
            reverse.append({**{k: rv[k] for k in ("label", "threshold")}, "result": f"no breach within {hi:+g}",
                            "shock": None, "at_shock": r_hi})
            print(f"  reverse {rv['label']}: no breach within {hi:+g}")
            continue
        if bad(base):
            reverse.append({**{k: rv[k] for k in ("label", "threshold")}, "result": "breached in the base case",
                            "shock": 0.0, "at_shock": base})
            continue
        for _ in range(int(rv.get("iterations", 7))):
            mid = (lo + hi) / 2
            r = run([dict(rv["flex"], by=mid)])
            lo, hi, r_hi = (mid, hi, r_hi) if not bad(r) else (lo, mid, r)
        reverse.append({**{k: rv[k] for k in ("label", "threshold")}, "shock": round(hi, 2),
                        "result": f"breaches at {hi:+.1f}", "at_shock": r_hi})
        print(f"  reverse {rv['label']}: breaches at {hi:+.2f} (peak ND/EBITDA {r_hi['peak_nd_ebitda']}x, value INR {r_hi['value_per_share']})")
    # invariants: value must rise with revenue growth and with margin, and no adverse case may raise it
    viol = []
    if grid:
        c = grid["cells"]
        for yi, row in enumerate(c):
            for xi in range(1, len(row)):
                if row[xi]["value"] < row[xi - 1]["value"]:
                    viol.append(f"grid: value falls as {grid['x']['label']} rises ({gy['steps'][yi]:+}, {gx['steps'][xi - 1]:+} to {gx['steps'][xi]:+})")
        for xi in range(len(c[0])):
            for yi in range(1, len(c)):
                if c[yi][xi]["value"] < c[yi - 1][xi]["value"]:
                    viol.append(f"grid: value falls as {grid['y']['label']} rises")
    for cs in cases:
        if cs["value_per_share"] > base["value_per_share"]:
            viol.append(f"case '{cs['name']}' raises value above the base ({cs['value_per_share']} vs {base['value_per_share']})")
    for v_ in viol:
        print("  INVARIANT VIOLATION:", v_)
    out = {"run_at": datetime.now().isoformat(timespec="seconds"), "thresholds": th, "base": base,
           "committed_capex_years": committed, "invariant_violations": viol,
           "cases": cases, "grid": grid, "reverse": reverse,
           "_note": "Each run rebuilds the three-statement model; thresholds are reference levels with sources, "
                    "not disclosed covenants unless stated."}
    json.dump(out, open(os.path.join(root, "data", "stress.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("-> data/stress.json")


if __name__ == "__main__":
    main()
