#!/usr/bin/env python3
"""Validate confirmed assumptions and emit the model-ready files.

Input is `decisions.json` - the working record of every assumption, its value,
its reasoning, its evidence and its confidence (schema in
references/integration.md). Output is two files:

  assumptions.json          consumed directly by the equity-research-report
                            skill's `model.py`
  assumptions_evidence.md   the audit trail: value, why, quoted evidence with
                            page citations, confidence, and who set it

What this script catches that a hand-written JSON does not:

  * `terminal_growth >= WACC`, which makes model.py exit rather than warn
  * working-capital days given but `nwc_pct_sales` missing - it derives the
    conversion, adjusting for whether DIO/DPO were struck on COGS or on sales
  * per-year lists shorter than `forecast_years`
  * values outside a plausible band (flagged, never silently changed)
  * assumptions carrying no evidence and not marked `insufficient`

Usage
    python build_assumptions.py --in decisions.json --outdir data/
    python build_assumptions.py --in decisions.json --outdir data/ --strict

    # with an approved modeling strategy (optional; without it nothing changes)
    python build_assumptions.py --in decisions.json --outdir data/ \
           --strategy data/model_strategy.json \
           --segment-build data/segment_build.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date


def _load_gate():
    """Import check_strategy.py from the `modeling-strategy` skill.

    Same discovery convention as peer_ingest.py's parse_screener loader:
    env var, sibling skill directory, user skills, project skills.
    """
    here = os.path.dirname(os.path.abspath(__file__))
    cands = []
    if os.environ.get("MS_SKILL"):
        cands.append(os.path.join(os.environ["MS_SKILL"], "scripts"))
    cands += [
        os.path.join(here, "..", "..", "modeling-strategy", "scripts"),
        os.path.expanduser("~/.claude/skills/modeling-strategy/scripts"),
        os.path.join(os.getcwd(), ".claude", "skills", "modeling-strategy", "scripts"),
    ]
    for c in cands:
        if os.path.isfile(os.path.join(c, "check_strategy.py")):
            sys.path.insert(0, os.path.abspath(c))
            import check_strategy
            return check_strategy
    raise SystemExit(
        "--strategy was given but the modeling-strategy skill could not be found.\n"
        "Install it beside this skill, or set MS_SKILL to its directory.")

# assumption key -> (model.py key, kind)
#   kind: "series" may be a list or a scalar; "rate"/"value" are scalars
MODEL_MAP = {
    "revenue_growth":     ("revenue_growth", "series"),
    "ebit_margin":        ("ebit_margin", "series"),
    "capex_pct_sales":    ("capex_pct_sales", "series"),
    "dep_pct_sales":      ("dep_pct_sales", "series"),
    "nwc_pct_sales":      ("nwc_pct_sales", "series"),
    "effective_tax_rate": ("tax_rate", "rate"),
    "terminal_growth":    ("terminal_growth", "rate"),
    "interest_rate":      ("cost_of_debt", "rate"),
    "risk_free_rate":     ("rf", "rate"),
    "equity_risk_premium": ("erp", "rate"),
    "beta":               ("beta", "value"),
    "target_debt_weight": ("target_debt_weight", "rate"),
    "forecast_years":     ("forecast_years", "value"),
    "net_debt":           ("net_debt", "value"),
    "shares_out":         ("shares_out", "value"),
    "current_price":      ("current_price", "value"),
    "exit_multiple":      ("exit_multiple", "value"),
}

# analyst-facing assumptions model.py does not read directly; kept in the JSON
# under `_analyst` so the forecast sheet and the report narrative can use them
ANALYST_ONLY = ["volume_growth", "pricing_growth", "new_customers",
                "customer_retention", "gross_margin", "ebitda_margin",
                "sga_pct_sales", "rnd_pct_sales", "marketing_pct_sales",
                "employee_pct_sales", "amort_pct_sales", "dso", "dio", "dpo",
                "debt_growth"]

# plausibility bands (percent unless noted). Outside -> warn, never change.
BANDS = {
    "revenue_growth": (-20, 40), "volume_growth": (-25, 40),
    "pricing_growth": (-15, 25), "gross_margin": (5, 90),
    "ebitda_margin": (0, 60), "ebit_margin": (0, 55),
    "sga_pct_sales": (0, 40), "rnd_pct_sales": (0, 25),
    "marketing_pct_sales": (0, 30), "employee_pct_sales": (0, 60),
    "capex_pct_sales": (0, 30), "dep_pct_sales": (0, 20),
    "amort_pct_sales": (0, 15), "effective_tax_rate": (0, 45),
    "terminal_growth": (0, 7), "interest_rate": (0, 20),
    "risk_free_rate": (0, 15), "equity_risk_premium": (2, 12),
    "beta": (0.2, 2.5), "target_debt_weight": (0, 80),
    "dso": (0, 300), "dio": (0, 400), "dpo": (0, 300),
    "customer_retention": (0, 105), "nwc_pct_sales": (-40, 80),
}

CONFIDENCE = {"high", "medium", "low"}


def _val(entry):
    return entry.get("value") if isinstance(entry, dict) else entry


def _as_list(v, n):
    if isinstance(v, list):
        return [float(x) for x in v]
    return [float(v)] * n if v is not None else None


def _mean(v):
    v = [x for x in v if x is not None]
    return sum(v) / len(v) if v else None


def derive_nwc(dso, dio, dpo, gross_margin_pct, cogs_basis=True):
    """NWC as % of sales from receivable/inventory/payable days.

    Inventory and payables are usually struck on COGS, receivables on sales.
    Mixing the two bases without rescaling is the standard error here:

        NWC/Sales = DSO/365 + (DIO - DPO)/365 * (COGS/Sales)

    With `cogs_basis=False` all three are treated as sales-based.
    Returns (percent_of_sales, explanation).
    """
    if dso is None and dio is None and dpo is None:
        return None, None
    dso, dio, dpo = (dso or 0.0), (dio or 0.0), (dpo or 0.0)
    if cogs_basis:
        gm = 40.0 if gross_margin_pct is None else float(gross_margin_pct)
        cogs_ratio = max(0.05, 1 - gm / 100)
        pct = (dso / 365.0 + (dio - dpo) / 365.0 * cogs_ratio) * 100
        how = (f"DSO {dso:g}d on sales; DIO {dio:g}d and DPO {dpo:g}d on COGS "
               f"rescaled at COGS/Sales = {cogs_ratio:.2f} "
               f"(gross margin {gm:g}%)")
    else:
        pct = (dso + dio - dpo) / 365.0 * 100
        how = f"DSO {dso:g}d + DIO {dio:g}d - DPO {dpo:g}d, all on sales"
    return round(pct, 2), how


def wacc_of(A) -> tuple[float | None, str]:
    """Replicate model.py's WACC so terminal growth can be checked here."""
    try:
        rf, erp, beta = float(A["rf"]), float(A["erp"]), float(A["beta"])
    except (KeyError, TypeError, ValueError):
        return None, "rf, erp or beta absent - WACC not checked"
    kd = float(A.get("cost_of_debt", rf + (1.5 if rf > 1 else 0.015)))
    wd = float(A.get("target_debt_weight", 0.0))
    tax = float(A.get("tax_rate", 25.0))
    rf, erp, kd, wd, tax = (x / 100 if x > 1 else x for x in (rf, erp, kd, wd, tax))
    ke = rf + beta * erp
    w = ke * (1 - wd) + kd * (1 - tax) * wd
    return w, (f"ke = {rf:.2%} + {beta:.2f} x {erp:.2%} = {ke:.2%}; "
               f"WACC = {w:.2%} at {wd:.0%} debt")


def strategy_coverage(dec: dict, strategy: dict, segbuild: dict | None) -> list[str]:
    """Every required driver in the approved strategy must be accounted for.

    A driver counts as covered when it appears as an assumption key, in a
    top-level `segment_drivers` block, or in the segment build (which is proof a
    value existed and was used). Anything else is a gap that must be declared,
    not discovered later as a historical-average default.
    """
    covered = set((dec.get("assumptions") or {}).keys())
    for seg, ds in (dec.get("segment_drivers") or {}).items():
        covered |= {f"{seg}::{k}" for k in ds} | set(ds)
    if segbuild:
        for s in segbuild.get("segments") or []:
            covered |= {f"{s['name']}::{k}" for k in (s.get("evidence") or {})}
            covered |= set((s.get("evidence") or {}).keys())
            covered |= set((s.get("rows") or {}).keys())
    missing = []
    for d in strategy.get("required_drivers") or []:
        if d.get("optional"):
            continue
        did, seg = d["driver_id"], d.get("segment")
        if did in covered or f"{seg}::{did}" in covered:
            continue
        # the common margin/capital/WC drivers map onto ordinary assumption keys
        alias = {"segment_margin": ("ebit_margin", "ebitda_margin"),
                 "segment_capex_intensity": ("capex_pct_sales",),
                 "segment_wc_days": ("dso", "dio", "dpo", "nwc_pct_sales")}.get(did, ())
        if any(a in covered for a in alias):
            continue
        missing.append(f"{seg} / {did} ({d.get('label')})")
    return missing


def _scalarise(v, key, warn):
    """Collapse a per-year path onto the single value model.py expects.

    terminal_growth, tax_rate and cost_of_debt are scalars downstream. Handing one a
    list used to raise an unhandled TypeError out of float(); a loud collapse is more
    useful than a traceback, and silently dropping the path would be worse than both.
    """
    if not isinstance(v, list):
        return v
    vals = [x for x in v if x is not None]
    if not vals:
        return None
    uniq = sorted(set(float(x) for x in vals))
    if len(uniq) == 1:
        return uniq[0]
    warn.append(f"{key}: model.py takes a single value here, but a {len(vals)}-year "
                f"path was supplied ({vals[0]} .. {vals[-1]}); using the final-year "
                f"{vals[-1]}. Put the path in _analyst if the trajectory matters.")
    return vals[-1]


def build(dec: dict, strict: bool, strategy: dict | None = None,
          segbuild: dict | None = None):
    A_in = dec.get("assumptions") or {}
    n = int(_val(A_in.get("forecast_years")) or dec.get("forecast_years") or 5)
    warn: list[str] = []
    A: dict = {"_comment": "Generated by financial-model-assumptions. Rates may be "
                           "percent (12.0) or decimal (0.12); per-year lists override "
                           "a scalar. Every value is sourced in "
                           "assumptions_evidence.md.",
               "_generated": date.today().isoformat(),
               "forecast_years": n}
    if dec.get("sector"):
        A["sector"] = dec["sector"]

    # ---- band + evidence checks ------------------------------------------
    for key, entry in A_in.items():
        v = _val(entry)
        if v is None or key == "forecast_years":
            continue
        status = (entry.get("status") if isinstance(entry, dict) else "") or "recommended"
        if isinstance(entry, dict):
            conf = str(entry.get("confidence", "")).lower()
            if conf and conf not in CONFIDENCE:
                warn.append(f"{key}: confidence '{conf}' is not High/Medium/Low")
            if status != "insufficient" and not entry.get("evidence"):
                warn.append(f"{key}: no evidence recorded - either cite the knowledge "
                            f"base or set status 'insufficient'")
        if key in BANDS and not isinstance(v, str):
            lo, hi = BANDS[key]
            for x in (v if isinstance(v, list) else [v]):
                try:
                    x = float(x)
                except (TypeError, ValueError):
                    continue
                if x < lo or x > hi:
                    warn.append(f"{key}: {x} is outside the plausible band "
                                f"{lo}-{hi} - keep it only if the evidence is explicit")

    # ---- map into model.py keys ------------------------------------------
    for key, (mkey, kind) in MODEL_MAP.items():
        if key not in A_in:
            continue
        v = _val(A_in[key])
        if v is None or (isinstance(v, str)):
            continue
        if kind == "series":
            lst = _as_list(v, n)
            if lst is None:
                continue
            if len(lst) < n:
                warn.append(f"{key}: {len(lst)} values for a {n}-year forecast - "
                            f"held flat at {lst[-1]} for the remainder")
                lst += [lst[-1]] * (n - len(lst))
            A[mkey] = lst[:n]
        else:
            v = _scalarise(v, key, warn)
            if v is None:
                continue
            A[mkey] = float(v) if kind != "value" or isinstance(v, (int, float)) else v

    # ---- working capital -------------------------------------------------
    if "nwc_pct_sales" not in A:
        pct, how = derive_nwc(_scalarise(_val(A_in.get("dso")), "dso", warn),
                              _scalarise(_val(A_in.get("dio")), "dio", warn),
                              _scalarise(_val(A_in.get("dpo")), "dpo", warn),
                              _mean(_as_list(_val(A_in.get("gross_margin")), n) or []),
                              cogs_basis=bool(dec.get("wc_days_on_cogs", True)))
        if pct is not None:
            A["nwc_pct_sales"] = [pct] * n
            warn.append(f"nwc_pct_sales derived as {pct}% of sales - {how}")

    # ---- EBIT margin fallback from EBITDA --------------------------------
    if "ebit_margin" not in A and "ebitda_margin" in A_in:
        eb = _as_list(_val(A_in["ebitda_margin"]), n)
        dp = _as_list(_val(A_in.get("dep_pct_sales")), n)
        if eb and dp:
            A["ebit_margin"] = [round(a - b, 2) for a, b in zip(eb, dp)][:n]
            warn.append("ebit_margin derived as EBITDA margin less depreciation % "
                        "of sales - confirm it against the reported EBIT margin")
        elif eb:
            warn.append("ebitda_margin given without dep_pct_sales, so ebit_margin "
                        "could not be derived; model.py will fall back to the "
                        "historical average")

    # ---- terminal growth vs WACC (model.py exits on this) ----------------
    w, how = wacc_of(A)
    if w is not None and "terminal_growth" in A:
        gt = float(A["terminal_growth"])
        gt = gt / 100 if gt > 1 else gt
        if gt >= w:
            warn.append(f"BLOCKING: terminal growth {gt:.2%} >= WACC {w:.2%} - "
                        f"model.py will refuse to run. {how}")
        elif gt > w - 0.02:
            warn.append(f"terminal growth {gt:.2%} sits within 2pp of WACC "
                        f"{w:.2%}; terminal value will dominate. {how}")
    A["_wacc_check"] = how

    # ---- pass-through blocks ---------------------------------------------
    analyst = {k: A_in[k] for k in ANALYST_ONLY if k in A_in}
    if analyst:
        A["_analyst"] = {k: _val(v) for k, v in analyst.items()}
    for k in ("peers", "peer_betas", "scenarios", "mid_year_convention",
              "blume_adjust", "non_operating_assets"):
        if k in dec:
            A[k] = dec[k]
        elif k in A_in:
            A[k] = _val(A_in[k])

    # ---- approved modeling strategy (optional) ----------------------------
    if strategy is not None:
        ms = strategy.get("modelability") or {}
        A["_strategy"] = {
            "revenue_model": (strategy.get("model_architecture") or {}).get("revenue_model"),
            "modelability": ms.get("status"),
            "analyst_decision": (strategy.get("analyst_decision") or {}).get("status"),
            "primary_methods": [m.get("method") for m in
                                strategy.get("valuation_methods") or []
                                if m.get("role") == "PRIMARY"],
            "required_driver_count": len(strategy.get("required_drivers") or []),
        }
        if strategy.get("sector") and A.get("sector") and \
                strategy["sector"] != A["sector"]:
            warn.append(f"sector disagrees: strategy says '{strategy['sector']}', "
                        f"decisions.json says '{A['sector']}' - reconcile them, the "
                        f"sector flows through to model.py")
        for m in strategy_coverage(dec, strategy, segbuild):
            warn.append(f"BLOCKING: required driver not covered - {m}. The approved "
                        f"architecture needs it; find evidence or mark it "
                        f"'insufficient'. It must not fall back to a historical "
                        f"average silently.")

    if segbuild is not None:
        g = segbuild.get("derived_revenue_growth_pct") or []
        g = [x for x in g if x is not None]
        if not g:
            warn.append("BLOCKING: --segment-build supplied but it carries no derived "
                        "revenue growth path")
        else:
            prior = A.get("revenue_growth")
            if len(g) < n:
                warn.append(f"segment build covers {len(g)} years against a {n}-year "
                            f"forecast - held flat at {g[-1]}% for the remainder")
                g = g + [g[-1]] * (n - len(g))
            A["revenue_growth"] = g[:n]
            A.setdefault("_strategy", {})["revenue_growth_source"] = (
                "segment_build.json - derived from the approved segment economics; "
                "the full build and its citations are in segment_build.md")
            if prior and [round(x, 2) for x in prior[:len(g[:n])]] != \
                    [round(x, 2) for x in g[:n]]:
                warn.append(f"revenue_growth replaced by the segment build "
                            f"({[round(x, 2) for x in g[:n]]}) - decisions.json had "
                            f"{[round(x, 2) for x in prior]}. The derived path wins; "
                            f"change the segment drivers, not this value.")
            for w in segbuild.get("warnings") or []:
                warn.append(f"segment build: {w}")

    missing = [m for m in ("rf", "erp", "beta", "terminal_growth", "shares_out",
                           "current_price", "net_debt") if m not in A or A[m] is None]
    if missing:
        warn.append("model.py inputs still unset (it will substitute historical "
                    "averages or skip the per-share bridge): " + ", ".join(missing))

    if strict and any(x.startswith("BLOCKING") for x in warn):
        raise SystemExit("strict mode: " + next(x for x in warn if x.startswith("BLOCKING")))
    return A, warn


def evidence_md(dec: dict, A: dict, warn: list[str]) -> str:
    company = dec.get("company", "the company")
    L = [f"# Assumption evidence - {company}", ""]
    if dec.get("as_of"):
        L.append(f"As of {dec['as_of']}. ")
    L += [f"Knowledge base: `{dec.get('kb', 'not recorded')}`",
          f"Forecast horizon: {A.get('forecast_years')} years"
          + (f"  |  Sector: {A['sector']}" if A.get("sector") else ""), "",
          "| Assumption | Value | Confidence | Set by | Key reason |",
          "|---|---|---|---|---|"]
    A_in = dec.get("assumptions") or {}
    for k, e in A_in.items():
        if not isinstance(e, dict):
            e = {"value": e}
        v = e.get("value")
        vs = ", ".join(str(x) for x in v) if isinstance(v, list) else str(v)
        why = (e.get("why") or [""])[0] if isinstance(e.get("why"), list) else (e.get("why") or "")
        by = {"user_modified": "user", "insufficient": "-"}.get(e.get("status"), "analyst")
        L.append(f"| {k} | {vs} | {e.get('confidence', '-')} | {by} | "
                 f"{str(why)[:90]} |")

    L += ["", "## Detail", ""]
    for k, e in A_in.items():
        if not isinstance(e, dict):
            e = {"value": e}
        v = e.get("value")
        vs = ", ".join(str(x) for x in v) if isinstance(v, list) else str(v)
        L += [f"### {k}", "", f"**Value:** {vs} {e.get('unit', '')}".rstrip(), ""]
        if e.get("status") == "insufficient":
            L += ["**Not enough evidence in the knowledge base for this assumption.**", ""]
        why = e.get("why") or []
        if why:
            L.append("**Why**")
            L += [f"- {w}" for w in (why if isinstance(why, list) else [why])] + [""]
        ev = e.get("evidence") or []
        if ev:
            L.append("**Evidence**")
            for x in ev:
                if isinstance(x, dict):
                    pg = f" (p. {x['page']})" if x.get("page") else ""
                    src = f" - `{x['source']}`" if x.get("source") else ""
                    L.append(f"- \"{x.get('quote', '')}\"{pg}{src}")
                else:
                    L.append(f"- {x}")
            L.append("")
        L += [f"**Confidence:** {e.get('confidence', 'not stated')}", ""]
        if e.get("status") == "user_modified":
            L += [f"**Changed by the user** from the recommended "
                  f"{e.get('recommended', 'n/a')}." , ""]

    if warn:
        L += ["## Checks raised at build time", ""] + [f"- {w}" for w in warn] + [""]
    L += ["---", "", "Every value above is a starting point, not a forecast. "
          "Change any of them in `decisions.json` and rebuild."]
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--in", dest="inp", required=True, help="decisions.json")
    ap.add_argument("--outdir", default=".", help="where to write both outputs")
    ap.add_argument("--strict", action="store_true",
                    help="exit non-zero on a blocking check")
    ap.add_argument("--strategy", help="model_strategy.json from the "
                                       "modeling-strategy skill. Optional: without "
                                       "it this script behaves exactly as before.")
    ap.add_argument("--segment-build", dest="segbuild",
                    help="segment_build.json - its derived revenue growth path "
                         "replaces revenue_growth, with provenance")
    a = ap.parse_args()

    if not os.path.exists(a.inp):
        print(f"error: no such file: {a.inp}", file=sys.stderr)
        return 2
    try:
        dec = json.load(open(a.inp, encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"error: {a.inp} is not valid JSON ({e})", file=sys.stderr)
        return 2

    strategy = segbuild = None
    if a.strategy:
        strategy = json.load(open(a.strategy, encoding="utf-8"))
        gate = _load_gate()
        ok, why = gate.gate_ok(strategy, require_approved=True)
        if not ok:
            print(f"error: refusing to build assumptions - {why}", file=sys.stderr)
            print("       The modeling strategy decides what is being modelled. "
                  "Resolve it first.", file=sys.stderr)
            return 3
    if a.segbuild:
        segbuild = json.load(open(a.segbuild, encoding="utf-8"))
        if strategy is None:
            print("error: --segment-build requires --strategy; the build is only "
                  "meaningful against the architecture it came from",
                  file=sys.stderr)
            return 2

    A, warn = build(dec, a.strict, strategy, segbuild)
    os.makedirs(a.outdir, exist_ok=True)
    ap_path = os.path.join(a.outdir, "assumptions.json")
    ev_path = os.path.join(a.outdir, "assumptions_evidence.md")
    json.dump(A, open(ap_path, "w", encoding="utf-8"), indent=2)
    open(ev_path, "w", encoding="utf-8").write(evidence_md(dec, A, warn))

    print(f"wrote {ap_path}\nwrote {ev_path}")
    if warn:
        print("\nchecks:")
        for w in warn:
            print(f"  - {w}")
    else:
        print("\nno checks raised.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
