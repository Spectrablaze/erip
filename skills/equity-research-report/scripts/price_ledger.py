"""price_ledger.py - what happened to the price after each call, against the market.

The call ledger (calls.json) records what ERIP believed and when. This records what happened, in
reports/_knowledge/price_ledger.json, so calls can be scored without hindsight:

  * one entry per call version, with the price and the benchmark level on the call date
  * observations are appended, never edited: date, close, benchmark close, dividends since the call,
    and the source of each number
  * a call is only SCORED at or after its horizon (12 months); earlier observations are marked
    INTERIM and say so, because a SELL that is right in a year can be wrong in a fortnight

    python price_ledger.py open    --ticker T --version N --date YYYY-MM-DD --price P --benchmark B \
                                   --benchmark-name "NIFTY 50" --source "..."
    python price_ledger.py observe --ticker T --date YYYY-MM-DD --price P --benchmark B [--dividends D] --source "..."
    python price_ledger.py report
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime

HORIZON_DAYS = 365


def _path(root):
    return os.path.join(root, "_knowledge", "price_ledger.json")


def _load(root):
    p = _path(root)
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {"_about": __doc__.split("\n\n")[1], "calls": []}


def _save(root, L):
    json.dump(L, open(_path(root), "w", encoding="utf-8"), indent=2, ensure_ascii=False)


def _standing(L, ticker):
    open_ = [c for c in L["calls"] if c["ticker"] == ticker and not c.get("superseded_on")]
    return open_[-1] if open_ else None


def score(c, o):
    """Return of the stock (with dividends) and of the benchmark since the call, and the verdict so far."""
    stock = (o["price"] + (o.get("dividends") or 0)) / c["price_at_call"] - 1
    bench = o["benchmark"] / c["benchmark_at_call"] - 1
    rel = stock - bench
    days = (date.fromisoformat(o["date"]) - date.fromisoformat(c["date"])).days
    want = {"SELL": -1, "REDUCE": -1, "UNDERPERFORM": -1, "BUY": 1, "ADD": 1, "OUTPERFORM": 1}.get(c["rating"], 0)
    right = None if want == 0 else (rel * want > 0)
    tgt_move = c["target"] - c["price_at_call"]
    progress = (o["price"] - c["price_at_call"]) / tgt_move if tgt_move else None
    return {"days": days, "stock_return": round(stock * 100, 2), "benchmark_return": round(bench * 100, 2),
            "relative": round(rel * 100, 2), "direction_right": right,
            "progress_to_target": None if progress is None else round(progress * 100, 1),
            "status": "SCORED" if days >= HORIZON_DAYS else "INTERIM"}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--root", default="reports")
    sub = ap.add_subparsers(dest="cmd", required=True)
    o = sub.add_parser("open")
    for a in ("--ticker", "--date", "--source", "--benchmark-name"):
        o.add_argument(a, required=True)
    for a in ("--version", "--price", "--benchmark"):
        o.add_argument(a, type=float, required=True)
    ob = sub.add_parser("observe")
    for a in ("--ticker", "--date", "--source"):
        ob.add_argument(a, required=True)
    for a in ("--price", "--benchmark"):
        ob.add_argument(a, type=float, required=True)
    ob.add_argument("--dividends", type=float, default=0.0)
    sub.add_parser("report")
    a = ap.parse_args()
    L = _load(a.root)
    calls = json.load(open(os.path.join(a.root, "_knowledge", "calls.json"), encoding="utf-8"))

    if a.cmd == "open":
        call = next((c for c in calls if c["ticker"] == a.ticker and int(c.get("version", 1)) == int(a.version)), None)
        if not call:
            sys.exit(f"no call v{int(a.version)} on {a.ticker} in calls.json")
        prior = _standing(L, a.ticker)
        if prior:
            prior["superseded_on"] = a.date            # stamps only; its observations stay as they were
        L["calls"].append({"ticker": a.ticker, "version": int(a.version), "rating": call["rating"],
                           "target": call["target"], "date": a.date, "price_at_call": a.price,
                           "benchmark_name": a.benchmark_name, "benchmark_at_call": a.benchmark,
                           "horizon_days": HORIZON_DAYS, "source": a.source, "observations": []})
        _save(a.root, L)
        print(f"opened {a.ticker} v{int(a.version)} {call['rating']} {call['target']:g} at {a.price} ({a.benchmark_name} {a.benchmark})")
    elif a.cmd == "observe":
        c = _standing(L, a.ticker)
        if not c:
            sys.exit(f"no open ledger entry for {a.ticker}")
        if a.date <= c["date"] or a.date > date.today().isoformat():
            sys.exit("an observation must fall after the call date and not in the future")
        if any(x["date"] >= a.date for x in c["observations"]):
            sys.exit("observations are append-only and in date order")
        obs = {"date": a.date, "price": a.price, "benchmark": a.benchmark, "dividends": a.dividends,
               "source": a.source, "recorded_at": datetime.now().isoformat(timespec="seconds")}
        obs["score"] = score(c, obs)
        c["observations"].append(obs)
        _save(a.root, L)
        s = obs["score"]
        print(f"{a.ticker} {a.date}: stock {s['stock_return']:+.1f}%, {c['benchmark_name']} {s['benchmark_return']:+.1f}%, "
              f"relative {s['relative']:+.1f}pp ({s['status']}, day {s['days']} of {c['horizon_days']})")
    else:
        for c in L["calls"]:
            last = c["observations"][-1] if c["observations"] else None
            tag = " (superseded)" if c.get("superseded_on") else ""
            print(f"{c['ticker']} v{c['version']} {c['rating']} {c['target']:g} from {c['price_at_call']} on {c['date']}{tag}")
            if last:
                s = score(c, last)                     # derived: always recomputed from the raw observation
                print(f"   {last['date']}: stock {s['stock_return']:+.1f}% vs {c['benchmark_name']} {s['benchmark_return']:+.1f}% "
                      f"= {s['relative']:+.1f}pp; {s['status']}; direction "
                      + ("n/a (HOLD)" if s['direction_right'] is None else ('right' if s['direction_right'] else 'wrong')) + " so far")


if __name__ == "__main__":
    main()
