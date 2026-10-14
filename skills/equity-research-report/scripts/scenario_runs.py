"""scenario_runs.py - value each scenario on its own three-statement model.

model.py's built-in scenarios flex its internal driver projection. Once the DCF discounts
the three-statement cash flows (--fcff-from-model), those built-in scenarios no longer move
the cash flows at all, so every case must re-run the three-statement model. This script does
that, and is the single function the tornado and the live workbook check against.

    python scenario_runs.py --root reports/<T> --sector realestate

Reads   data/financials.json, data/assumptions.json, data/three_statement/overrides.json,
        data/model_strategy.json (optional)
Writes  data/three_statement/scenarios/<case>/model.json   (one linked model per case)
        data/scenarios_3s.json                             (values, weights, paths)
        data/model.json                                    (base case, on three-statement FCFF)
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SKILLS = os.path.dirname(os.path.dirname(HERE))
FM = os.path.join(SKILLS, "financial-model", "scripts")
MODEL_PY = os.path.join(HERE, "model.py")
PY = sys.executable

# Keys a scenario may override, and where each lands.
FM_KEYS = ("revenue_growth", "ebitda_margin", "capex_pct_sales", "tax_rate", "dep_pct_sales", "nwc_pct_sales")
VAL_KEYS = ("terminal_growth", "rf", "erp", "beta", "cost_of_debt", "target_debt_weight")


def _rate1(v):
    """First value of a scalar-or-path driver, as a fraction (inputs mix percent and fraction)."""
    v = float(v[0] if isinstance(v, list) else v)
    return v / 100 if abs(v) > 1 else v


def _run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"failed: {' '.join(cmd)}\n{r.stdout[-1500:]}\n{r.stderr[-1500:]}")
    return r.stdout


def value_case(root, assumptions, tag, sector, strategy=None, keep_dir=None):
    """Build the three-statement model for one assumption set and value its own FCFF.

    Returns the model.py output dict. keep_dir keeps the three-statement model on disk."""
    a = copy.deepcopy(assumptions)
    a.pop("scenarios", None)
    with tempfile.TemporaryDirectory() as td:
        ap = os.path.join(td, "assumptions.json")
        json.dump(a, open(ap, "w"))
        outdir = keep_dir or os.path.join(td, "ts")
        os.makedirs(outdir, exist_ok=True)
        mi = os.path.join(outdir, "model_input.json")
        cmd = [PY, os.path.join(FM, "ingest.py"), "--screener", os.path.join(root, "data", "financials.json"),
               "--assumptions", ap, "-o", mi]
        ov = os.path.join(root, "data", "three_statement", "overrides.json")
        if os.path.exists(ov):
            cmd += ["--overrides", ov]
        if strategy:
            cmd += ["--strategy", strategy]
        _run(cmd)
        _run([PY, os.path.join(FM, "build_model.py"), "--in", mi, "--outdir", outdir]
             + ([] if keep_dir else ["--no-xlsx"]))
        out = os.path.join(td, "m.json")
        cmd = [PY, MODEL_PY, os.path.join(root, "data", "financials.json"), ap, "--sector", sector,
               "--fm", os.path.join(outdir, "model.json"), "--fcff-from-model", "-o", out]
        if strategy:
            cmd += ["--strategy", strategy]
        _run(cmd)
        return json.load(open(out))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--root", required=True)
    ap.add_argument("--sector", required=True)
    args = ap.parse_args()
    root = os.path.abspath(args.root)
    strat = os.path.join(root, "data", "model_strategy.json")
    strat = strat if os.path.exists(strat) else None
    A = json.load(open(os.path.join(root, "data", "assumptions.json"), encoding="utf-8"))
    cases = {k: v for k, v in (A.get("scenarios") or {}).items() if not k.startswith("_")} or {"base": {"probability": 1.0}}
    res, base_model = {}, None
    for name, sc in cases.items():
        a = copy.deepcopy(A)
        for k in FM_KEYS + VAL_KEYS:
            if k in sc:
                a[k] = sc[k]
        # decisions.json names the tax driver effective_tax_rate; assumptions.json and ingest read tax_rate
        if "effective_tax_rate" in sc:
            a["tax_rate"] = sc["effective_tax_rate"]
        unknown = [k for k in sc if not k.startswith("_") and k not in FM_KEYS + VAL_KEYS
                   + ("probability", "effective_tax_rate", "ebit_margin")]
        if unknown:
            print(f"  ! {name}: scenario keys not applied to the three-statement run: {unknown}")
        keep = os.path.join(root, "data", "three_statement", "scenarios", name)
        m = value_case(root, a, name, args.sector, strat, keep_dir=keep)
        br, tcc = m["dcf"]["bridge"], m["dcf"]["terminal_cross_check"]
        res[name] = {
            "probability": sc.get("probability"),
            "intrinsic_value_per_share": br["Intrinsic value per share (INR)"],
            "TV_as_%_of_EV": br["TV as % of EV"],
            "upside_%": br.get("Upside / (downside) %"),
            "implied_exit_ev_ebitda": tcc.get("Implied exit EV/EBITDA (x)"),
            "revenue_growth_y1_%": round(_rate1(a["revenue_growth"]) * 100, 1),
            "exit_ebit_margin_%": m["dcf"]["forecast"][-1].get("EBIT %"),
            "terminal_growth_%": round(_rate1(a["terminal_growth"]) * 100, 2),
            "terminal_year_ebitda": tcc.get("Terminal-year EBITDA"),
            "fcff": [r["FCFF"] for r in m["dcf"]["forecast"]],
            "revenue": [r["Sales"] for r in m["dcf"]["forecast"]],
            "three_statement": os.path.relpath(os.path.join(keep, "model.json"), root),
        }
        if name == "base":
            base_model = m
        print(f"  {name:5} p={sc.get('probability')}  INR {br['Intrinsic value per share (INR)']}  "
              f"TV {br['TV as % of EV']}% of EV  FCFF Y1 {res[name]['fcff'][0]:,}")
    w = sum((v["probability"] or 0) * v["intrinsic_value_per_share"] for v in res.values())
    out = {"basis": "each case re-runs the linked three-statement model; DCF discounts its FCFF",
           "cases": res, "probability_weighted": round(w)}
    json.dump(out, open(os.path.join(root, "data", "scenarios_3s.json"), "w"), indent=1)
    # The report and charts read scenarios off model.json, so the base model carries them.
    base_model["scenarios"] = {"basis": out["basis"], "probability_weighted": out["probability_weighted"],
                               "cases": {k: {kk: v[kk] for kk in ("probability", "intrinsic_value_per_share",
                                                                  "TV_as_%_of_EV", "implied_exit_ev_ebitda",
                                                                  "revenue_growth_y1_%", "exit_ebit_margin_%",
                                                                  "terminal_growth_%", "upside_%")}
                                         for k, v in res.items()}}
    json.dump(base_model, open(os.path.join(root, "data", "model.json"), "w"), indent=1)
    print(f"  weighted INR {round(w)}  -> data/scenarios_3s.json; base -> data/model.json")


if __name__ == "__main__":
    main()
