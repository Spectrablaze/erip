#!/usr/bin/env python3
"""
check_model.py - review a built model without rebuilding it.

    python check_model.py --in data/model.json
    python check_model.py --in data/model.json --md data/model_review.md --strict

Prints three things:

  1. the integrity checks, with the blocking ones separated from the advisory
     ones, because "all pass" means nothing if you cannot see which checks were
     structural identities and which were statements about the data;
  2. every driver, its history (last, trailing average, range) against its
     forecast, so a forecast that quietly steps outside the historical range is
     visible on one screen;
  3. what the model actually produces - growth, margins, returns, leverage.

This is the step to run before anyone reads a number out of the model.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rows as R  # noqa: E402


def _fmt(v, unit):
    if v is None:
        return "-"
    if unit == "pct":
        return f"{v * 100:,.1f}%"
    if unit == "days":
        return f"{v:,.0f}d"
    if unit == "x":
        return f"{v:,.2f}x"
    if unit == "sh":
        return f"{v:,.2f}"
    return f"{v:,.1f}"


def driver_table(m):
    nh = m["periods"]["n_hist"]
    avg_years = int(m.get("options", {}).get("avg_years", 3))
    out = []
    for key in R.DRIVER_KEYS:
        row = m["rows"].get(key)
        if not row:
            continue
        vals = row["values"]
        hist = [v for v in vals[1:nh]]
        fcst = vals[nh:]
        trail = hist[-avg_years:] if hist else []
        out.append({
            "key": key, "label": row["label"], "unit": row["unit"],
            "last": hist[-1] if hist else None,
            "avg": (sum(trail) / len(trail)) if trail else None,
            "lo": min(hist) if hist else None,
            "hi": max(hist) if hist else None,
            "fcst": fcst,
            "source": (m.get("drivers", {}).get(key) or {}).get("source", "?"),
            "outside": bool(hist) and any(v < min(hist) or v > max(hist) for v in fcst),
        })
    return out


def output_table(m):
    nh = m["periods"]["n_hist"]
    keys = ["revenue", "s_rev_growth", "ebitda", "s_ebitda_margin", "ebit", "pat",
            "eps", "s_fcff", "s_cash_conv", "cash", "debt_total", "s_net_debt",
            "s_nd_ebitda", "s_int_cover", "s_roce", "s_roe"]
    return [{"label": m["rows"][k]["label"], "unit": m["rows"][k]["unit"],
             "hist": m["rows"][k]["values"][max(0, nh - 3):nh],
             "fcst": m["rows"][k]["values"][nh:]} for k in keys if k in m["rows"]]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--in", dest="inp", default="data/model.json")
    ap.add_argument("--md", help="also write the review as markdown")
    ap.add_argument("--strict", action="store_true",
                    help="exit non-zero if a blocking check fails")
    args = ap.parse_args()

    with open(args.inp, encoding="utf-8") as f:
        m = json.load(f)

    P = m["periods"]
    nh = P["n_hist"]
    lines: list[str] = []

    def out(s=""):
        print(s)
        lines.append(s)

    out(f"# {m['company']} - model review")
    out()
    out(f"- {m['currency']}, sector {m.get('sector') or 'not resolved'}")
    out(f"- history {P['hist'][0]} to {P['hist'][-1]} ({nh}y), "
        f"forecast {P['fcst'][0]} to {P['fcst'][-1]} ({len(P['fcst'])}y)")
    out(f"- circular solve: {m['solve']['iterations']} passes, "
        f"residual {m['solve']['residual']:.3g}")
    out()

    # ---------------------------------------------------------------- checks
    items = m["checks"]["items"]
    blocking = [i for i in items if i["severity"] == "blocking"]
    advisory = [i for i in items if i["severity"] != "blocking"]
    out("## Integrity checks")
    out()
    out("| | check | worst | period | note |")
    out("|---|---|---|---|---|")
    for i in blocking + advisory:
        out(f"| {'ok' if i['ok'] else '**FAIL**'} | {i['label']} | "
            f"{i['worst']:,.4g} | {i['period']} | {i['detail']} |")
    out()
    bad = [i for i in items if not i["ok"]]
    hard = [i for i in bad if i["severity"] == "blocking"]
    if hard:
        out(f"**{len(hard)} blocking check(s) failed. Do not read a number out of "
            "this model until they are fixed - see references/checks.md.**")
    elif bad:
        out(f"{len(bad)} advisory check(s) flagged. These are judgements to defend, "
            "not defects to fix.")
    else:
        out("All checks pass.")
    out()

    # --------------------------------------------------------------- drivers
    out("## Drivers: history against forecast")
    out()
    out("A forecast outside the historical range is not wrong - but it is a claim, "
        "and it needs a reason in the evidence trail.")
    out()
    hdr = "| driver | last | avg | range | " + " | ".join(P["fcst"]) + " | source |"
    out(hdr)
    out("|" + "---|" * (5 + len(P["fcst"])))
    for d in driver_table(m):
        u = d["unit"]
        rng = f"{_fmt(d['lo'], u)} - {_fmt(d['hi'], u)}"
        f = " | ".join(_fmt(v, u) for v in d["fcst"])
        flag = " !" if d["outside"] else ""
        out(f"| {d['label']}{flag} | {_fmt(d['last'], u)} | {_fmt(d['avg'], u)} | "
            f"{rng} | {f} | {d['source']} |")
    out()
    off = [d["label"] for d in driver_table(m) if d["outside"]]
    if off:
        out(f"Marked `!` - forecast steps outside the historical range: "
            f"{', '.join(off)}.")
        out()

    # --------------------------------------------------------------- outputs
    out("## What the model produces")
    out()
    out("| line | " + " | ".join(P["hist"][max(0, nh - 3):nh]) + " | "
        + " | ".join(P["fcst"]) + " |")
    out("|" + "---|" * (1 + min(3, nh) + len(P["fcst"])))
    for r in output_table(m):
        cells = [_fmt(v, r["unit"]) for v in r["hist"] + r["fcst"]]
        out(f"| {r['label']} | " + " | ".join(cells) + " |")
    out()

    if m.get("reconciliation"):
        out("## Screener against the annual report")
        out()
        out("| line | period | screener | annual report | diff |")
        out("|---|---|---|---|---|")
        for d in m["reconciliation"]:
            out(f"| {d['row']} | {d['period']} | {d['screener']:,.1f} | "
                f"{d['annual_report']:,.1f} | {d['diff_pct']}% |")
        out()

    if m.get("citations"):
        out("## Annual-report citations")
        out()
        for k, c in m["citations"].items():
            src = c.get("source", "") if isinstance(c, dict) else str(c)
            pg = c.get("page", "") if isinstance(c, dict) else ""
            q = c.get("quote", "") if isinstance(c, dict) else ""
            out(f"- `{k}` - {src} p.{pg}" + (f' - "{q}"' if q else ""))
        out()

    if m.get("notes"):
        out("## Notes from the build")
        out()
        for n in m["notes"]:
            out(f"- {n}")
        out()

    if args.md:
        os.makedirs(os.path.dirname(args.md) or ".", exist_ok=True)
        with open(args.md, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        print(f"wrote {args.md}", file=sys.stderr)

    return 1 if (args.strict and hard) else 0


if __name__ == "__main__":
    raise SystemExit(main())
