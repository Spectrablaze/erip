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


# Keys model.py itself reads once the DCF discounts the three-statement FCFF (--fcff-from-model).
# Everything operating (growth, margin, capex, tax, depreciation, working capital) must go through
# ingest.py, which reads dso/dio/dpo but NOT nwc_pct_sales: model.py's own nwc_pct_sales path is
# dead under --fcff-from-model. TRENT, 15 Oct 2026: an nwc_pct_sales stress returned the base value.
VALUATION_KEYS = set(VAL_KEYS) | {
    "terminal_ronic", "net_debt", "non_operating_assets", "lease_liabilities", "minority_interest",
    "shares_out", "current_price", "exit_multiple", "peer_betas", "blume_adjust",
    "mid_year_convention", "balance_date", "first_fy_end", "valuation_date", "target_policy"}
KEY_HINTS = {"nwc_pct_sales": "dso / dio / dpo (working-capital days)",
             "ebit_margin": "ebitda_margin (or the 'margin' op, which moves both)",
             "dividend_payout": "payout_ratio"}


class DeadFlexError(SystemExit):
    """A flex changed assumption keys that the three-statement model never reads."""


def _ingest():
    if FM not in sys.path:
        sys.path.insert(0, FM)
    import ingest
    return ingest


def ingested_drivers(root, assumptions):
    """The drivers ingest.py would build from these assumptions, overrides.json included.

    Calls ingest.drivers_from_assumptions directly, so this set cannot drift from what ingest reads."""
    ing = _ingest()
    drv = ing.drivers_from_assumptions(copy.deepcopy(assumptions), [])
    ov = os.path.join(root, "data", "three_statement", "overrides.json")
    if os.path.exists(ov):
        for k, v in (json.load(open(ov, encoding="utf-8")).get("drivers") or {}).items():
            if v is not None and not k.startswith("_"):
                drv[k] = ing._rate(v) if k in ing.RATE_DRIVERS else v
    return drv


def _revert(flexed, base, name):
    a = copy.deepcopy(flexed)
    for d_f, d_b in ((a, base), (a.get("_analyst"), base.get("_analyst"))):
        if isinstance(d_f, dict):
            if isinstance(d_b, dict) and name in d_b:
                d_f[name] = copy.deepcopy(d_b[name])
            else:
                d_f.pop(name, None)
    return a


def dead_flex_keys(root, base, flexed):
    """Assumption keys that differ between base and flexed but reach neither ingest nor model.py."""
    def flat(d):
        d = {k: v for k, v in d.items() if k != "scenarios"}
        an = d.pop("_analyst", None) or {}
        return {**d, **{k: v for k, v in an.items() if k not in d}}
    fb, ff = flat(base), flat(flexed)
    changed = sorted(k for k in set(fb) | set(ff) if fb.get(k) != ff.get(k))
    ref = ingested_drivers(root, flexed)
    dead = []
    for k in changed:
        if k in VALUATION_KEYS or k.startswith("_"):
            continue
        if k == "ebit_margin" and "ebitda_margin" in changed:
            continue                       # the 'margin' op moves both; ebitda_margin is the one read
        if ingested_drivers(root, _revert(flexed, base, k)) == ref:
            dead.append(k)
    return dead


def check_flex_live(root, base, flexed, label=""):
    dead = dead_flex_keys(root, base, flexed)
    if dead:
        lines = [f"  '{k}' is not read by the three-statement model; use "
                 f"{KEY_HINTS.get(k, 'a key ingest.drivers_from_assumptions reads')}" for k in dead]
        raise DeadFlexError(f"DEAD FLEX{' in ' + repr(label) if label else ''}: the flex changes assumption "
                            "keys that never reach the model, so the result would silently equal the base:\n"
                            + "\n".join(lines))


_BASE = {}


def value_case(root, assumptions, tag, sector, strategy=None, keep_dir=None, with_statements=False,
               check_live=True):
    """Build the three-statement model for one assumption set and value its own FCFF.

    Returns the model.py output dict (and, with_statements, the three-statement model.json too).
    keep_dir keeps the three-statement model on disk.

    check_live compares the assumptions with data/assumptions.json and raises DeadFlexError when
    a changed key never reaches the model (see dead_flex_keys), instead of returning the base value."""
    if check_live:
        if root not in _BASE:
            p = os.path.join(root, "data", "assumptions.json")
            _BASE[root] = json.load(open(p, encoding="utf-8")) if os.path.exists(p) else None
        if _BASE[root] is not None:
            check_flex_live(root, _BASE[root], assumptions, tag)
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
        if with_statements:
            return json.load(open(out)), json.load(open(os.path.join(outdir, "model.json"), encoding="utf-8"))
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
    cases = {k: v for k, v in (A.get("scenarios") or {}).items() if not k.startswith("_")} or {"base": {}}
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
            "intrinsic_value_per_share": br["Intrinsic value per share (INR)"],
            "TV_as_%_of_EV": br["TV as % of EV"],
            "upside_%": br.get("Upside / (downside) %"),
            "target": (m["dcf"].get("target") or {}).get("target"),
            "implied_exit_ev_ebitda": tcc.get("Implied exit EV/EBITDA (x)"),
            "revenue_growth_y1_%": round(_rate1(a["revenue_growth"]) * 100, 1),
            "exit_ebit_margin_%": m["dcf"]["forecast"][-1].get("EBIT %"),
            "terminal_growth_%": round(_rate1(a["terminal_growth"]) * 100, 2),
            "terminal_year_ebitda": tcc.get("Terminal-year EBITDA"),
            "fcff": [r["FCFF"] for r in m["dcf"]["forecast"]],
            "revenue": [r["Sales"] for r in m["dcf"]["forecast"]],
            "three_statement": os.path.relpath(os.path.join(keep, "model.json"), root),
            # unrounded inputs to the headline, so a page or a workbook can recompute it exactly
            "fcff_exact": json.load(open(os.path.join(keep, "model.json"), encoding="utf-8"))["bridge"]["fcff"][:len(m["dcf"]["forecast"])],
            "timing": m["dcf"].get("timing"),
        }
        if name == "base":
            base_model = m
        print(f"  {name:5}  INR {br['Intrinsic value per share (INR)']}  "
              f"TV {br['TV as % of EV']}% of EV  FCFF Y1 {res[name]['fcff'][0]:,}")
    # No probability weighting: the weights were never evidenced, so the cases are reported as a
    # range (decision 2026-10-14). A scenario's "probability" key, if present, is ignored.
    vals = {k: v["intrinsic_value_per_share"] for k, v in res.items()}
    rng = {"low": min(vals.values()), "high": max(vals.values()), "base": vals.get("base")}
    out = {"basis": "each case re-runs the linked three-statement model; DCF discounts its FCFF",
           "weighting": "none: cases are a range, not a probability-weighted value", "cases": res, "range": rng}
    json.dump(out, open(os.path.join(root, "data", "scenarios_3s.json"), "w"), indent=1)
    # The report and charts read scenarios off model.json, so the base model carries them.
    base_model["scenarios"] = {"basis": out["basis"], "weighting": out["weighting"], "range": rng,
                               "cases": {k: {kk: v[kk] for kk in ("intrinsic_value_per_share",
                                                                  "TV_as_%_of_EV", "implied_exit_ev_ebitda",
                                                                  "revenue_growth_y1_%", "exit_ebit_margin_%",
                                                                  "terminal_growth_%", "upside_%", "target")}
                                         for k, v in res.items()}}
    json.dump(base_model, open(os.path.join(root, "data", "model.json"), "w"), indent=1)
    print(f"  range INR {rng['low']} to {rng['high']} (base {rng['base']})  -> data/scenarios_3s.json; base -> data/model.json")


if __name__ == "__main__":
    main()
