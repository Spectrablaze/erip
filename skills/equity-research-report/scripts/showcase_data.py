"""showcase_data.py - export what the showcase web page needs, from the report data files.

The page recomputes each DCF in the browser when a reader moves a slider, so it needs each
scenario's unrounded cash flows and timing (scenario_runs.py stores them), plus the call, the
peer bands and the tornado. Nothing on the page is typed by hand.

    python showcase_data.py --report reports/JSWINFRA --report reports/ADANIPORTS \
        --links links.json -o erip/docs/data.js

links.json maps ticker -> {"pdf": url, "xlsx": url, "audit": url, "cover_date": "1 Oct 2026"}.
"""
from __future__ import annotations

import argparse
import json
import os


def _track(root, ticker):
    """Every ledgered call on this ticker with its latest observation, scored from the raw numbers."""
    p = os.path.join(os.path.dirname(root), "_knowledge", "price_ledger.json")
    if not os.path.exists(p):
        return []
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from price_ledger import score
    out = []
    for c in json.load(open(p, encoding="utf-8"))["calls"]:
        if c["ticker"] != ticker:
            continue
        last = c["observations"][-1] if c["observations"] else None
        out.append({k: c[k] for k in ("version", "rating", "target", "date", "price_at_call", "benchmark_name",
                                      "benchmark_at_call", "horizon_days")}
                   | {"superseded_on": c.get("superseded_on"), "last": None if not last else
                      {"date": last["date"], "price": last["price"], "benchmark": last["benchmark"], **score(c, last)}})
    return out


def company(root, links):
    J = lambda p: json.load(open(os.path.join(root, p), encoding="utf-8"))
    M, S3, A = J("data/model.json"), J("data/scenarios_3s.json"), J("data/assumptions.json")
    P = J("data/peers.json")
    T = J("data/tornado.json") if os.path.exists(os.path.join(root, "data", "tornado.json")) else {"drivers": []}
    BR = M["dcf"]["bridge"]
    fin = J("data/financials.json")
    name = (A.get("company") or fin.get("company") or os.path.basename(root)).strip()
    ticker = os.path.basename(os.path.normpath(root))
    cases = {}
    for k, c in S3["cases"].items():
        t = c["timing"]
        cases[k] = {"value": c["intrinsic_value_per_share"],
                    "fcff": c["fcff_exact"], "first_year_share": t["first_year_share"], "periods": t["periods"],
                    "terminal_period": t["terminal_period"], "roll": t["roll_forward"], "ronic": t["terminal_ronic"],
                    "nopat_T": t["terminal_nopat"], "ebitda_T": t["terminal_ebitda"], "net_debt": t["net_debt"],
                    "nonop": t["non_operating_assets"], "shares": t["shares"], "wacc": t["wacc"],
                    "claims": t.get("lease_liabilities", 0) + t.get("minority_interest", 0),
                    "g": t["terminal_growth"], "revenue": c.get("revenue")}
    ff = [m for m in P.get("football_field", []) if "52" not in m.get("label", "")]
    ts = J(S3["cases"]["base"]["three_statement"])
    return {
        "ticker": ticker, "name": name, "cmp": BR["Current market price (INR)"],
        "house_multiple": M["dcf"]["target"].get("exit_multiple") or 10, "round": M["dcf"]["target"]["round"],
        "buy_above": M["dcf"]["target"]["buy_above"] * 100, "sell_below": -M["dcf"]["target"]["sell_below"] * 100,
        "alt_multiple": M["dcf"]["terminal_cross_check"].get("Exit multiple supplied (x)"),
        "peer_ev_ebitda": (P.get("comps") or {}).get("median", {}).get("EV/EBITDA (x)"),
        "range": S3.get("range"),
        "stress": J("data/stress.json") if os.path.exists(os.path.join(root, "data", "stress.json")) else None,
        "years": [p.replace("Mar-", "FY") for p in ts["bridge"]["periods"]],
        "football": [{"label": m["label"], "low": m["low"], "high": m["high"], "mid": m.get("mid")} for m in ff],
        "tornado": T["drivers"], "tornado_base": T.get("base_value"),
        "cases": cases, "target": M["dcf"]["target"],
        "validation": J("data/validation.json") if os.path.exists(os.path.join(root, "data", "validation.json")) else None,
        # Python value vs the LibreOffice-recalculated workbook, per case; the page adds its own value
        "reconciliation": {k: {"python": c["intrinsic_value_per_share"],
                               "python_exact": None, "excel": ((J("data/workbook_check.json")["cases"].get(k) or {}).get("value")
                                                              if os.path.exists(os.path.join(root, "data", "workbook_check.json")) else None),
                               "excel_run": (J("data/workbook_check.json")["run_at"]
                                             if os.path.exists(os.path.join(root, "data", "workbook_check.json")) else None)}
                           for k, c in S3["cases"].items()},
        "claims": {"lease_liabilities": M["dcf"]["timing"].get("lease_liabilities", 0),
                   "minority_interest": M["dcf"]["timing"].get("minority_interest", 0)},
        "track_record": _track(root, ticker),
        **links.get(ticker, {}),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--report", action="append", required=True)
    ap.add_argument("--links", required=True)
    ap.add_argument("-o", "--out", required=True)
    a = ap.parse_args()
    links = json.load(open(a.links, encoding="utf-8"))
    data = [company(os.path.abspath(r), links) for r in a.report]
    with open(a.out, "w", encoding="utf-8") as f:
        f.write("// generated by showcase_data.py from the report data files; do not edit\n")
        f.write("window.ERIP = " + json.dumps(data, separators=(",", ":")) + ";\n")
    for d in data:
        print(f"  {d['ticker']}: {', '.join(f'{k} {v['value']}' for k, v in d['cases'].items())}; CMP {d['cmp']}")
    print("->", a.out)


if __name__ == "__main__":
    main()
