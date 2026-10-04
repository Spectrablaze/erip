#!/usr/bin/env python3
"""
market_data.py — Yahoo Finance prices and a cross-check feed for the comp set

    python3 market_data.py peers_manifest.json -o data/market.json --as-of 2026-08-01

Fetches, per company in the manifest, from Yahoo:

  * the close on the cover date              -> so all peers are priced on one day
  * daily price history                      -> a far better beta than Screener's monthly
  * market cap and shares outstanding        -> cross-check against the export
  * revenue, total debt, cash, equity        -> cross-check against the export
  * the index series (default ^NSEI)         -> removes the manual NSE CSV download

WHAT THIS IS AND IS NOT FOR

This is a SECOND SOURCE, not a replacement for the Screener exports. The exports remain
the record. Yahoo is used for two things it is genuinely good at — prices, which are
mechanical and unambiguous — and for disagreeing with the exports, which is the whole
point of a second source.

It is deliberately NOT used for the comps themselves, because:

  * Yahoo does not state whether its figures are consolidated or standalone. That is the
    single check this skill treats as a hard error, and Yahoo cannot answer it.
  * Yahoo's "EBITDA" is not the Screener/Indian-reporting operating profit. For Eicher
    Motors it reads ~35% of revenue against a reported ~26%, because it sweeps in other
    income. It is fetched for reference and NEVER cross-checked, because a definitional
    difference reported as a variance is just noise that trains you to ignore flags.

So: revenue and market cap are cross-checked (a large gap means the wrong ticker, the
wrong company, or the wrong basis — all worth catching). EBITDA is not.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys

CRORE = 1e7          # Yahoo reports absolute INR; Screener reports crore

# Cross-check tolerances. Deliberately loose on fundamentals: the two sources have
# genuinely different definitions and different as-of dates, so a tight threshold
# would cry wolf. These are set to catch "wrong company / wrong basis", not "rounded
# differently".
TOL = {"market_cap": 0.03, "revenue": 0.10, "net_debt": 0.25}


def load_yf():
    try:
        import yfinance as yf
    except ImportError:
        raise SystemExit(
            "yfinance is not installed. Either:\n"
            "  pip install yfinance\n"
            "or skip this step entirely — it is optional. The skill works from the "
            "Screener exports alone; this script only adds prices and a second opinion.")
    return yf


def yahoo_ticker(entry: dict) -> str:
    """Manifest `yahoo` wins; otherwise assume an NSE listing."""
    if entry.get("yahoo"):
        return entry["yahoo"]
    t = (entry.get("ticker") or "").strip().upper()
    if not t:
        raise SystemExit(f"{entry.get('name')}: no ticker and no `yahoo` in the manifest")
    return t if "." in t else f"{t}.NS"


def close_asof(hist, as_of: str):
    """Last close on or before the cover date."""
    if hist is None or len(hist) == 0:
        return None, None
    try:
        want = dt.date.fromisoformat(as_of)
    except (ValueError, TypeError):
        row = hist.iloc[-1]
        return float(row["Close"]), str(hist.index[-1].date())
    for i in range(len(hist) - 1, -1, -1):
        d = hist.index[i].date()
        if d <= want:
            return float(hist["Close"].iloc[i]), str(d)
    return None, None


def series_of(hist) -> list:
    """[(YYYY-MM-DD, close)] oldest first."""
    if hist is None or len(hist) == 0:
        return []
    return [(str(hist.index[i].date()), float(hist["Close"].iloc[i]))
            for i in range(len(hist))
            if hist["Close"].iloc[i] == hist["Close"].iloc[i]]  # drop NaN


def _row(frame, *names):
    """First matching row of a yfinance dataframe, latest column, in crore."""
    if frame is None or getattr(frame, "empty", True):
        return None, None
    for n in names:
        if n in frame.index:
            try:
                v = frame.loc[n].iloc[0]
            except (IndexError, KeyError):
                continue
            if v is None or v != v:
                continue
            col = frame.columns[0]
            return float(v) / CRORE, str(col.date() if hasattr(col, "date") else col)
    return None, None


def fetch_one(yf, entry: dict, as_of: str, years: int) -> dict:
    tick = yahoo_ticker(entry)
    rec = {"name": entry.get("name"), "ticker": entry.get("ticker"), "yahoo": tick,
           "warnings": []}
    t = yf.Ticker(tick)

    try:
        hist = t.history(period=f"{years}y", auto_adjust=False)
    except Exception as exc:                                   # network / bad ticker
        rec["warnings"].append(f"history failed for {tick}: {exc}")
        hist = None

    if hist is None or len(hist) == 0:
        rec["warnings"].append(
            f"no price history for {tick} — check the ticker. NSE symbols take .NS, "
            "BSE takes .BO; set `yahoo` in the manifest to override.")
        rec["price"], rec["price_date"], rec["series"] = None, None, []
    else:
        rec["price"], rec["price_date"] = close_asof(hist, as_of)
        rec["series"] = series_of(hist)
        if rec["price_date"] and as_of and rec["price_date"] != as_of:
            rec["warnings"].append(
                f"no trade on {as_of}; used the {rec['price_date']} close "
                "(holiday or weekend)")

    try:
        fi = t.fast_info
        cur = fi["currency"]
        if cur and cur != "INR":
            rec["warnings"].append(
                f"{tick} is quoted in {cur}, not INR — the export is in rupee crore, so "
                "this cross-check is meaningless and is skipped")
            rec["currency"] = cur
            return rec
        rec["currency"] = cur
        rec["market_cap"] = float(fi["marketCap"]) / CRORE if fi["marketCap"] else None
        rec["shares_cr"] = float(fi["shares"]) / 1e7 if fi["shares"] else None
    except Exception as exc:
        rec["warnings"].append(f"fast_info failed for {tick}: {exc}")

    try:
        bs = t.balance_sheet
        rec["total_debt"], rec["bs_date"] = _row(bs, "Total Debt")
        cash, _ = _row(bs, "Cash And Cash Equivalents")
        cash_sti, _ = _row(bs, "Cash Cash Equivalents And Short Term Investments")
        rec["cash"], rec["cash_and_sti"] = cash, cash_sti
        rec["equity"], _ = _row(bs, "Stockholders Equity")
        mi, _ = _row(bs, "Minority Interest")
        rec["minority_interest"] = mi
        if rec["total_debt"] is not None and cash is not None:
            rec["net_debt"] = rec["total_debt"] - cash
    except Exception as exc:
        rec["warnings"].append(f"balance sheet failed for {tick}: {exc}")

    try:
        fin = t.financials
        rec["revenue"], rec["is_date"] = _row(fin, "Total Revenue")
        rec["net_income"], _ = _row(fin, "Net Income")
        # Fetched for eyeballing only — never cross-checked. See the module docstring.
        rec["ebitda_yahoo_reference_only"], _ = _row(fin, "EBITDA")
    except Exception as exc:
        rec["warnings"].append(f"income statement failed for {tick}: {exc}")

    rec["basis"] = None
    rec["basis_note"] = ("Yahoo does not state consolidated vs standalone. The export "
                         "header does, and that is what the skill enforces.")
    return rec


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("manifest")
    ap.add_argument("-o", "--out", default="data/market.json")
    ap.add_argument("--as-of", help="cover date YYYY-MM-DD (default: manifest as_of)")
    ap.add_argument("--years", type=int, default=5, help="history to pull (default 5)")
    ap.add_argument("--index", default="^NSEI",
                    help="Yahoo symbol for the market index (default ^NSEI, NIFTY 50). "
                         "Pass 'none' to skip.")
    args = ap.parse_args()

    yf = load_yf()
    with open(args.manifest, encoding="utf-8") as f:
        man = json.load(f)

    as_of = args.as_of or man.get("as_of")
    if not as_of or not str(as_of)[:4].isdigit():
        print(f"! cover date {as_of!r} is not YYYY-MM-DD; using the latest close instead",
              file=sys.stderr)

    out = {"as_of": as_of, "source": "Yahoo Finance via yfinance",
           "fetched_at": dt.datetime.now().isoformat(timespec="seconds"),
           "companies": [], "index": None, "warnings": []}

    for e in man.get("companies", []):
        print(f"  fetching {yahoo_ticker(e)} ...", file=sys.stderr)
        out["companies"].append(fetch_one(yf, e, as_of, args.years))

    if args.index and args.index.lower() != "none":
        print(f"  fetching index {args.index} ...", file=sys.stderr)
        try:
            ih = yf.Ticker(args.index).history(period=f"{args.years}y", auto_adjust=False)
            out["index"] = {"symbol": args.index, "series": series_of(ih)}
            if not out["index"]["series"]:
                out["warnings"].append(f"index {args.index} returned no data")
        except Exception as exc:
            out["warnings"].append(f"index {args.index} failed: {exc}")

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)

    print(f"\nwrote {args.out}   (source: Yahoo, as of {as_of})")
    def num(v, dp=0):
        return f"{v:,.{dp}f}" if isinstance(v, (int, float)) else "-"

    print(f"{'company':<26}{'close':>10}{'on':>13}{'mcap Cr':>12}"
          f"{'revenue Cr':>12}{'days':>7}")
    for c in out["companies"]:
        print(f"{(c['name'] or c['yahoo'])[:25]:<26}"
              f"{num(c.get('price'), 1):>10}"
              f"{str(c.get('price_date') or '-'):>13}"
              f"{num(c.get('market_cap')):>12}"
              f"{num(c.get('revenue')):>12}"
              f"{len(c.get('series') or []):>7}")
    if out["index"]:
        print(f"index {out['index']['symbol']}: {len(out['index']['series'])} daily closes")
    for c in out["companies"]:
        for w in c["warnings"]:
            print(f"  ! {c['name'] or c['yahoo']}: {w}")
    for w in out["warnings"]:
        print(f"  ! {w}")
    print("\nnext: peer_ingest.py --market {0}   (prices)\n"
          "      peer_beta.py   --market {0}   (daily beta, no CSV needed)\n"
          "      build_comps.py --crosscheck {0}".format(args.out))


if __name__ == "__main__":
    main()
