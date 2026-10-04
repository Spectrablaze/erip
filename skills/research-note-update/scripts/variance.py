#!/usr/bin/env python3
"""
variance.py — the quarter's actuals against the standing forecast.

    python3 variance.py --standing reports/EICHERMOT/updates/2026-08-01/standing.json \
                        --actuals  reports/EICHERMOT/updates/2026-08-01/actuals.json

Writes variance.json + variance.md next to the actuals, and prints the table.
Its second job is to answer one question the note depends on: does this quarter
justify a full re-forecast, or only a re-strike of the standing model?

THE SEASONALITY TRAP
    Annualising one quarter by x4 is wrong for any business with a season, and
    Indian industrials, consumer and auto names all have one. Supply
    `seasonality.q_share_of_fy` (this quarter's historical share of full-year
    revenue) in actuals.json and the run-rate is grossed up on that share
    instead. Without it the script still runs, flags every line `flat_x4`, and
    refuses to declare a tolerance breach on revenue or PAT — a naive x4 is not
    evidence strong enough to move a rating.

ACTUALS FILE
    {
      "period": "Q1FY27", "fy": "FY27", "quarters_elapsed": 1,
      "actual":  {"revenue": 4210, "ebitda": 980, "ebit": 820, "pat": 610, "eps": 22.4},
      "ytd":     {"revenue": 4210, "ebitda": 980, "ebit": 820, "pat": 610},
      "yoy":     {"revenue": 3780, "ebitda": 850, "ebit": 700, "pat": 520},
      "qoq":     {"revenue": 4400, "ebitda": 1010, "ebit": 850, "pat": 640},
      "seasonality": {"q_share_of_fy": 0.226, "basis": "mean Q1 share FY22-FY26"},
      "source": "Q1FY27 results, 24 Jul 2026, p.2"
    }
    Only `period`, `quarters_elapsed` and `actual` are required. Units must match
    the model's currency block (Screener exports are INR cr; so is the model).

Exit codes
  0  variance computed
  3  missing or unusable input
"""
from __future__ import annotations

import argparse
import json
import os
import sys

LINES = ["revenue", "ebitda", "ebit", "pat", "eps"]
LABEL = {"revenue": "Revenue", "ebitda": "EBITDA", "ebit": "EBIT",
         "pat": "PAT", "eps": "EPS"}

# House tolerances. A breach is what escalates a note from variance-only to a
# full re-forecast, and what supplies the thesis reason a rating change needs.
# Override per company with a top-level "tolerances" block in decisions.json.
TOLERANCE = {
    "revenue_pct": 5.0,       # implied FY revenue vs forecast FY revenue
    "pat_pct": 10.0,
    "ebitda_pct": 10.0,
    "ebit_pct": 10.0,
    "eps_pct": 10.0,
    "margin_bps": 150.0,      # EBITDA margin, actual quarter vs forecast FY
}


def _load(path, what):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except OSError:
        sys.exit(f"cannot read {what}: {path}")
    except json.JSONDecodeError as exc:
        sys.exit(f"{what} is not valid JSON ({path}): {exc}")


def _pct(new, base):
    if new is None or base in (None, 0):
        return None
    return round((float(new) / float(base) - 1) * 100, 1)


def _num(d, k):
    v = (d or {}).get(k)
    try:
        return None if v is None else float(v)
    except (TypeError, ValueError):
        return None


def pick_fy(forecast: dict, fy: str | None) -> tuple[int, str]:
    """Which forecast column this quarter rolls up into."""
    years = [str(y) for y in (forecast.get("years") or [])]
    if not years:
        sys.exit("the standing forecast has no year columns — re-run the model")
    if fy:
        for i, y in enumerate(years):
            if fy.upper() in y.upper() or y.upper() in fy.upper():
                return i, years[i]
        sys.exit(f"--fy {fy} matches no forecast column ({', '.join(years)}). "
                 "Pass the label the model uses, or omit --fy for the first year.")
    return 0, years[0]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--standing", required=True)
    ap.add_argument("--actuals", required=True)
    ap.add_argument("--fy", help="forecast column to score against (default: first)")
    ap.add_argument("--out", help="default: variance.json beside the actuals")
    args = ap.parse_args()

    st = _load(args.standing, "standing.json")
    ac = _load(args.actuals, "actuals.json")
    fcst = st.get("forecast") or {}
    tol = dict(TOLERANCE)
    tol.update({k: float(v) for k, v in (st.get("tolerances") or {}).items()
                if k in TOLERANCE})

    idx, fy_label = pick_fy(fcst, args.fy or ac.get("fy"))
    qe = int(ac.get("quarters_elapsed") or 1)
    if not 1 <= qe <= 4:
        sys.exit(f"quarters_elapsed must be 1-4, got {qe}")

    season = (ac.get("seasonality") or {}).get("q_share_of_fy")
    ytd = ac.get("ytd") or ac.get("actual") or {}
    actual = ac.get("actual") or {}
    if not actual:
        sys.exit("actuals.json has no `actual` block")

    # ---- implied full year ------------------------------------------------
    # With a seasonal share, gross up YTD on the cumulative share it represents.
    # Without one, fall back to flat annualisation and mark it as weak evidence.
    if season:
        try:
            share = float(season) * qe if qe > 1 and (ac.get("seasonality") or {}).get(
                "share_is_per_quarter", True) else float(season)
        except (TypeError, ValueError):
            share = None
    else:
        share = None
    if share and 0 < share <= 1.0:
        method = f"seasonal (YTD / {share:.3f})"
        weak = False
        def annualise(v):
            return None if v is None else round(v / share, 1)
    else:
        method = f"flat_x4 (YTD x {4/qe:.2f})"
        weak = True
        def annualise(v):
            return None if v is None else round(v * 4.0 / qe, 1)

    rows, breaches, notes = [], [], []
    fl = fcst.get("lines") or {}
    for key in LINES:
        f_series = fl.get(key) or []
        f_val = f_series[idx] if idx < len(f_series) else None
        a_q = _num(actual, key)
        a_ytd = _num(ytd, key)
        implied = annualise(a_ytd if a_ytd is not None else a_q)
        var = _pct(implied, f_val)
        row = {
            "line": key, "label": LABEL[key],
            "quarter_actual": a_q,
            "ytd": a_ytd,
            "implied_fy": implied,
            "forecast_fy": f_val,
            "variance_pct": var,
            "yoy_pct": _pct(a_q, _num(ac.get("yoy"), key)),
            "qoq_pct": _pct(a_q, _num(ac.get("qoq"), key)),
            "breach": False,
            "suppressed": False,
        }
        limit = tol.get(f"{key}_pct")
        if var is not None and limit is not None and abs(var) > limit:
            # Every line in this table is a LEVEL, so every one of them is
            # distorted by a naive x4. Suppress the whole column, not a subset —
            # the margin below is the only figure a single quarter measures
            # honestly, because it is a ratio struck inside the quarter itself.
            if weak:
                row["suppressed"] = True
                notes.append(
                    f"{LABEL[key]} implies {var:+.1f}% against forecast, past the "
                    f"±{limit:.0f}% tolerance — but the run-rate is a flat x4 with no "
                    "seasonal share supplied, so it is NOT recorded as a breach. "
                    "Supply seasonality.q_share_of_fy to make this count.")
            else:
                row["breach"] = True
                breaches.append(f"{LABEL[key]} {var:+.1f}% vs ±{limit:.0f}% tolerance")
        rows.append(row)

    # ---- margin variance, in bps -----------------------------------------
    margin = None
    a_rev, a_eb = _num(actual, "revenue"), _num(actual, "ebitda")
    f_marg = (fcst.get("margins") or {}).get("ebitda_pct") or []
    f_m = f_marg[idx] if idx < len(f_marg) else None
    if a_rev and a_eb is not None and f_m is not None:
        a_m = round(a_eb / a_rev * 100, 2)
        bps = round((a_m - float(f_m)) * 100, 0)
        breach = abs(bps) > tol["margin_bps"]
        margin = {"actual_quarter_pct": a_m, "forecast_fy_pct": round(float(f_m), 2),
                  "delta_bps": bps, "breach": breach,
                  "tolerance_bps": tol["margin_bps"]}
        if breach:
            breaches.append(f"EBITDA margin {bps:+.0f}bps vs ±{tol['margin_bps']:.0f}bps "
                            "tolerance")
    elif a_rev and a_eb is not None:
        notes.append("no forecast EBITDA margin in the standing model — margin "
                     "variance not computed. Build the three-statement model.")

    period = str(ac.get("period") or "the quarter")
    is_year_end = period.upper().startswith("Q4") or ac.get("period_type") == "annual" \
        or qe == 4

    escalate, why = False, []
    if breaches:
        escalate = True
        why.append(f"{len(breaches)} tolerance breach(es): " + "; ".join(breaches))
    if is_year_end:
        escalate = True
        why.append("full-year / Q4 actuals — the standing forecast's base year is now "
                   "history, so it must be re-struck")
    if st.get("call", {}).get("review_due"):
        escalate = True
        why.append("the standing call is past its review date")

    out = {
        "note_id": st.get("note_id"),
        "ticker": st.get("ticker"),
        "period": period,
        "fy_scored": fy_label,
        "quarters_elapsed": qe,
        "annualisation": {"method": method, "weak_evidence": weak,
                          "share_used": share,
                          "basis": (ac.get("seasonality") or {}).get("basis")},
        "source": ac.get("source"),
        "rows": rows,
        "margin": margin,
        "breaches": breaches,
        "notes": notes,
        "rerun": {"full_rerun_required": escalate, "why": why},
        "tolerances": tol,
    }

    outp = args.out or os.path.join(os.path.dirname(os.path.abspath(args.actuals)),
                                    "variance.json")
    with open(outp, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)

    md = render_md(out, st)
    mdp = os.path.splitext(outp)[0] + ".md"
    with open(mdp, "w", encoding="utf-8") as fh:
        fh.write(md)

    print(md)
    print(f"\nwrote {outp}\nwrote {mdp}")
    return 0


def render_md(v: dict, st: dict) -> str:
    L = [f"### {v['ticker']} — {v['period']} against the {v['fy_scored']} forecast", ""]
    L.append(f"Run-rate method: **{v['annualisation']['method']}**"
             + (f" — {v['annualisation']['basis']}" if v["annualisation"].get("basis") else ""))
    if v["annualisation"]["weak_evidence"]:
        L.append("")
        L.append("> No seasonal share supplied. The implied full year is a flat "
                 "annualisation and is treated as weak evidence: it can inform the "
                 "commentary, it cannot on its own move the rating.")
    L += ["",
          "| Line | " + v["period"] + " | YTD | Implied FY | Forecast FY | Var % | YoY % |",
          "|---|---:|---:|---:|---:|---:|---:|"]

    def n(x):
        """Absolute figures: whole numbers in crore, one decimal for per-share."""
        if x is None:
            return "—"
        return f"{x:,.0f}" if abs(x) >= 100 else f"{x:,.1f}"

    def p(x):
        return "—" if x is None else f"{x:+.1f}%"

    for r in v["rows"]:
        if r["quarter_actual"] is None and r["forecast_fy"] is None:
            continue
        flag = " **!**" if r["breach"] else (" _(weak)_" if r.get("suppressed") else "")
        L.append(f"| {r['label']} | {n(r['quarter_actual'])} | {n(r['ytd'])} | "
                 f"{n(r['implied_fy'])} | {n(r['forecast_fy'])} | "
                 f"{p(r['variance_pct'])}{flag} | {p(r['yoy_pct'])} |")
    if v.get("margin"):
        m = v["margin"]
        flag = " **!**" if m["breach"] else ""
        L += ["",
              f"EBITDA margin: **{m['actual_quarter_pct']:.1f}%** in the quarter against "
              f"**{m['forecast_fy_pct']:.1f}%** forecast for the year — "
              f"**{m['delta_bps']:+.0f}bps**{flag} "
              f"(tolerance ±{m['tolerance_bps']:.0f}bps)."]
    if v["breaches"]:
        L += ["", "**Tolerance breaches**"] + [f"- {b}" for b in v["breaches"]]
    if v["notes"]:
        L += ["", "**Notes**"] + [f"- {n}" for n in v["notes"]]
    r = v["rerun"]
    L += ["", f"**Re-run depth: {'FULL RE-FORECAST' if r['full_rerun_required'] else 'variance only'}**"]
    for w in r["why"]:
        L.append(f"- {w}")
    if not r["full_rerun_required"]:
        L.append("- every tracked line inside tolerance, not a year-end, review not due — "
                 "re-strike the standing model, do not rebuild it")
    if v.get("source"):
        L += ["", f"_Source: {v['source']}_"]
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    sys.exit(main())
