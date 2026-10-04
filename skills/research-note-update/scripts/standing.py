#!/usr/bin/env python3
"""
standing.py — open an update note by pulling the standing position into one file.

    python3 standing.py --ticker EICHERMOT --root reports

Reads the call ledger (reports/_knowledge/calls.json), the standing decisions.json,
and whichever models exist, then writes

    reports/<TICKER>/updates/<YYYY-MM-DD>/standing.json

and prints a brief. Nothing downstream in this skill runs without that file: the
whole point of an update note is that it is scored against a position that was
recorded BEFORE the quarter, not reconstructed after it.

Exit codes
  0  standing position found
  2  no open call on this ticker (there is nothing to update — initiate first)
  3  a required input file is missing
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date

# Lines the note tracks. Order is the order they print in the variance table.
TRACKED = ["revenue", "ebitda", "ebit", "pat", "eps"]


def _load(path, default=None):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError):
        return default


def _days_between(a: str, b: str):
    """b - a, in days, from two ISO dates. None if either is unparseable."""
    try:
        ay, am, ad = (int(x) for x in a.split("-"))
        by, bm, bd = (int(x) for x in b.split("-"))
        return (date(by, bm, bd) - date(ay, am, ad)).days
    except (ValueError, AttributeError):
        return None


def find_call(root: str, ticker: str) -> tuple[dict | None, list]:
    """The standing call = the most recent OPEN call on this ticker."""
    calls = _load(os.path.join(root, "_knowledge", "calls.json"), []) or []
    mine = [c for c in calls if str(c.get("ticker", "")).upper() == ticker.upper()]
    open_calls = [c for c in mine if c.get("outcome") is None]
    return (open_calls[-1] if open_calls else None), mine


def dcf_forecast(model: dict) -> dict:
    """Pull the FY forecast rows out of equity-research-report's model.json.

    The DCF carries Sales / EBIT / margin only — no EBITDA or PAT — so a note
    that wants those needs the three-statement model as well. Say so rather
    than silently reporting a two-line variance table.
    """
    d = (model or {}).get("dcf") or {}
    rows = d.get("forecast") or []
    out = {"source": "dcf", "years": [], "lines": {k: [] for k in TRACKED}}
    for r in rows:
        out["years"].append(f"Y{r.get('year')}")
        out["lines"]["revenue"].append(r.get("Sales"))
        out["lines"]["ebit"].append(r.get("EBIT"))
    out["lines"]["ebitda"] = []
    out["lines"]["pat"] = []
    out["lines"]["eps"] = []
    out["margins"] = {"ebit_pct": [r.get("EBIT %") for r in rows],
                      "growth_pct": [r.get("Growth %") for r in rows]}
    out["bridge"] = d.get("bridge") or {}
    out["wacc"] = (d.get("wacc_build") or {}).get("WACC")
    return out


def ts_forecast(model: dict) -> dict:
    """Pull the FY forecast out of financial-model's three-statement model.json.

    This is the better forecast to score against: it has EBITDA, PAT and EPS,
    and its periods are real fiscal-year labels rather than Y1..Yn.
    """
    per = (model or {}).get("periods") or {}
    rows = (model or {}).get("rows") or {}
    fcst = per.get("fcst") or []
    nh = int(per.get("n_hist") or 0)
    key_for = {"revenue": "revenue", "ebitda": "ebitda", "ebit": "ebit",
               "pat": "pat", "eps": "eps"}
    out = {"source": "three_statement", "years": list(fcst),
           "lines": {}, "hist": {}, "margins": {}}
    for name, key in key_for.items():
        vals = ((rows.get(key) or {}).get("values")) or []
        out["lines"][name] = [round(v, 2) for v in vals[nh:]] if vals else []
        out["hist"][name] = [round(v, 2) for v in vals[:nh]] if vals else []
    out["hist_years"] = list(per.get("hist") or [])
    rev, eb = out["lines"]["revenue"], out["lines"]["ebitda"]
    if rev and eb and len(rev) == len(eb):
        out["margins"]["ebitda_pct"] = [
            None if not r else round(e / r * 100, 2) for e, r in zip(eb, rev)]
    return out


def driver_bands(dec: dict) -> dict:
    """The standing driver values a quarter can breach. Year 1 of each series."""
    A = (dec or {}).get("assumptions") or {}
    out = {}
    for key in ("revenue_growth", "ebitda_margin", "ebit_margin", "gross_margin",
                "capex_pct_sales", "dso", "dio", "dpo", "effective_tax_rate"):
        entry = A.get(key)
        if not isinstance(entry, dict):
            continue
        v = entry.get("value")
        if isinstance(v, list):
            v = v[0] if v else None
        if v is None:
            continue
        out[key] = {"y1": v, "confidence": entry.get("confidence"),
                    "n_evidence": len(entry.get("evidence") or [])}
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--ticker", required=True)
    ap.add_argument("--root", default="reports", help="reports directory")
    ap.add_argument("--report-dir", help="default: <root>/<TICKER>")
    ap.add_argument("--asof", default=date.today().isoformat(),
                    help="note date, also the updates/ folder name")
    ap.add_argument("--trigger", default="quarterly_results",
                    choices=["quarterly_results", "annual_results", "management_change",
                             "capex_or_ma", "regulatory", "guidance_change",
                             "falsifier", "review_due", "other"])
    ap.add_argument("--trigger-note", default="", help="one line: what happened")
    args = ap.parse_args()

    tick = args.ticker.upper()
    rdir = args.report_dir or os.path.join(args.root, tick)
    call, history = find_call(args.root, tick)

    if call is None:
        closed = [c for c in history if c.get("outcome")]
        print(f"No OPEN call on {tick} in {args.root}/_knowledge/calls.json.")
        if closed:
            print(f"  {len(closed)} closed call(s) on file — the last one was "
                  f"{closed[-1].get('rating')} on {closed[-1].get('date')}.")
            print("  An update note revises a live call. Re-initiate with "
                  "equity-research-report, or log the standing call with "
                  f"`kb.py call --ticker {tick} ...` if it was published outside the ledger.")
        else:
            print("  This name has never been covered. Run equity-research-report "
                  "first — an update note computes a delta, it cannot create a thesis.")
        return 2

    dec_path = os.path.join(rdir, "decisions.json")
    dec = _load(dec_path)
    if dec is None:
        print(f"missing {dec_path} — the standing assumption set. Cannot open a note.")
        return 3

    dcf_m = _load(os.path.join(rdir, "data", "model.json"))
    ts_m = _load(os.path.join(rdir, "data", "three_statement", "model.json"))

    forecast = {}
    if ts_m:
        forecast = ts_forecast(ts_m)
    if dcf_m:
        d = dcf_forecast(dcf_m)
        if forecast:
            forecast["valuation"] = {"bridge": d["bridge"], "wacc": d["wacc"]}
        else:
            forecast = d

    prior = []
    updir = os.path.join(rdir, "updates")
    if os.path.isdir(updir):
        prior = sorted(x for x in os.listdir(updir)
                       if os.path.isdir(os.path.join(updir, x)))

    days = _days_between(args.asof, call.get("review_on") or "")
    standing = {
        "ticker": tick,
        "company": dec.get("company") or tick,
        "sector": dec.get("sector"),
        "note_date": args.asof,
        "note_id": f"{tick}-{args.asof}",
        "trigger": args.trigger,
        "trigger_note": args.trigger_note,
        "report_dir": rdir,
        "call": {
            "opened": call.get("date"),
            "rating": call.get("rating"),
            "target": call.get("target"),
            "cmp_at_call": call.get("cmp_at_call"),
            "thesis": call.get("thesis"),
            "review_on": call.get("review_on"),
            "days_to_review": days,
            "review_due": (days is not None and days <= 0),
        },
        "falsifiers": [{"text": f, "status": "unassessed", "evidence": None}
                       for f in (call.get("falsifiers") or [])],
        "forecast": forecast,
        "drivers": driver_bands(dec),
        "rating_bands": dec.get("rating_bands"),
        "tolerances": dec.get("tolerances"),
        "prior_updates": prior,
        "closed_call_history": [
            {"date": c.get("date"), "rating": c.get("rating"), "target": c.get("target"),
             "error_pct": (c.get("outcome") or {}).get("target_error_%")}
            for c in history if c.get("outcome")],
    }

    outdir = os.path.join(rdir, "updates", args.asof)
    os.makedirs(outdir, exist_ok=True)
    outp = os.path.join(outdir, "standing.json")
    with open(outp, "w", encoding="utf-8") as fh:
        json.dump(standing, fh, indent=1, default=str)

    # ---- brief ----------------------------------------------------------
    c = standing["call"]
    print("=" * 68)
    print(f"STANDING POSITION — {standing['company']} ({tick})   note {args.asof}")
    print("=" * 68)
    print(f"  {c['rating']}  TP {c['target']}  (CMP at call {c['cmp_at_call']}, "
          f"set {c['opened']})")
    if c["thesis"]:
        print(f"  thesis: {c['thesis']}")
    if c["days_to_review"] is None:
        print(f"  review_on {c['review_on']} — unparseable date")
    elif c["review_due"]:
        print(f"  ** REVIEW DUE — was {c['review_on']}, {-c['days_to_review']} days ago. "
              "This note must close the call. **")
    else:
        print(f"  review due {c['review_on']} ({c['days_to_review']} days away)")

    print(f"\nFALSIFIERS ({len(standing['falsifiers'])}) — adjudicate every one in Phase 3:")
    for i, f in enumerate(standing["falsifiers"], 1):
        print(f"  [{i}] {f['text']}")
    if not standing["falsifiers"]:
        print("  none logged. The standing call is unfalsifiable — say so in the note "
              "and log falsifiers when you re-open the call.")

    fc = standing["forecast"]
    if not fc:
        print("\nFORECAST: no model.json found under data/ or data/three_statement/. "
              "A variance table needs one — run the model before writing.")
    else:
        print(f"\nFORECAST ({fc.get('source')}): years "
              f"{', '.join(str(y) for y in fc.get('years') or []) or '(none)'}")
        for k in TRACKED:
            v = (fc.get("lines") or {}).get(k) or []
            if v:
                print(f"  {k:<9} {'  '.join(str(x) for x in v[:5])}")
        missing = [k for k in TRACKED if not (fc.get("lines") or {}).get(k)]
        if missing:
            print(f"  not in this model: {', '.join(missing)} — either build the "
                  "three-statement model or drop those rows from the variance table.")

    if standing["closed_call_history"]:
        errs = [h["error_pct"] for h in standing["closed_call_history"]
                if h["error_pct"] is not None]
        if errs:
            mean = sum(errs) / len(errs)
            print(f"\nCALIBRATION on {tick}: {len(errs)} closed call(s), "
                  f"mean target error {mean:+.1f}%")
            print("  Carry that bias into the new target explicitly — do not repeat it.")

    if prior:
        print(f"\nPRIOR UPDATE NOTES: {', '.join(prior)}")
    print(f"\nwrote {outp}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
