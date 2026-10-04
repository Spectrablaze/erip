#!/usr/bin/env python3
"""
peer_beta.py — peers_raw.json + an index series -> peer_betas.json

    python3 peer_beta.py data/peers_raw.json --index data/nifty50.csv \
        -o data/peer_betas.json

Regresses each company's monthly return on the index's, and pairs the result with a
market-value debt/equity ratio, producing the `peer_betas` block that `model.py` unlevers
(Hamada), medians, and relevers at the target capital structure.

Why monthly, and why this is honest about its own limits:

  * Screener's price block is collapsed to one observation per calendar month by
    `parse_screener.py` (its period labels are `%b-%y`), so a monthly regression is the
    finest frequency the data actually supports. Claiming a daily beta from this file
    would be false precision.
  * A beta from a short window is noise. Below MIN_OBS observations this script emits
    `beta: null` with a reason rather than a number nobody should use.
  * R-squared is reported per company. A beta with an R-squared near zero says the
    index does not explain the stock, and belongs in the report's caveats.

The index CSV needs a date column and a close column; common NSE / Yahoo layouts are
detected automatically.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import math
import os
import re

# Thresholds per frequency. A monthly and a daily series need very different
# observation counts to say the same thing: 24 monthly points is two years, 24 daily
# points is a month and worthless.
LIMITS = {"monthly": {"min": 24, "thin": 36},
          "daily": {"min": 120, "thin": 250}}

MONTHS = {m: i + 1 for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun",
     "jul", "aug", "sep", "oct", "nov", "dec"])}

DATE_FORMATS = ["%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y",
                "%d-%b-%Y", "%d %b %Y", "%b %d, %Y", "%Y/%m/%d"]


# --------------------------------------------------------------- date handling
def to_ym(label) -> tuple | None:
    """Any supported date or Screener period label -> (year, month)."""
    if isinstance(label, (dt.datetime, dt.date)):
        return (label.year, label.month)
    s = str(label).strip()
    m = re.match(r"^([A-Za-z]{3})[-\s]?(\d{2,4})$", s)
    if m and m[1].lower() in MONTHS:
        y = int(m[2])
        return (y + 2000 if y < 100 else y, MONTHS[m[1].lower()])
    for fmt in DATE_FORMATS:
        try:
            d = dt.datetime.strptime(s[:len(fmt) + 4], fmt)
            return (d.year, d.month)
        except ValueError:
            continue
    m = re.match(r"^(\d{4})-(\d{1,2})", s)
    if m:
        return (int(m[1]), int(m[2]))
    return None


def monthly(points: list) -> dict:
    """[(label, value)] -> {(year, month): last value in that month}.

    Last-in-month wins, which makes a daily and a monthly export produce the same
    series rather than two incomparable ones.
    """
    out = {}
    for lab, val in points:
        ym = to_ym(lab)
        if ym is None or val is None:
            continue
        try:
            out[ym] = float(val)
        except (TypeError, ValueError):
            continue
    return out


def read_index(path: str) -> tuple:
    """Index CSV -> ({(y,m): close}, column name used)."""
    with open(path, encoding="utf-8-sig", newline="") as f:
        sample = f.read(4096)
        f.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
        except csv.Error:
            dialect = csv.excel
        rows = list(csv.DictReader(f, dialect=dialect))
    if not rows:
        raise SystemExit(f"{path}: no rows")

    cols = list(rows[0].keys())

    def pick(pats):
        for p in pats:
            for c in cols:
                if c and re.search(p, c.strip(), re.I):
                    return c
        return None

    dcol = pick([r"^date$", r"date", r"^time"])
    ccol = pick([r"^close$", r"adj.*close", r"close", r"^price$", r"^ltp$", r"^index"])
    if not dcol or not ccol:
        raise SystemExit(
            f"{path}: could not find a date and a close column in {cols}. "
            "Rename the headers to 'Date' and 'Close'.")

    pts = []
    for r in rows:
        v = (r.get(ccol) or "").replace(",", "").strip()
        if not v:
            continue
        try:
            pts.append((r[dcol], float(v)))
        except ValueError:
            continue
    series = monthly(pts)
    need = LIMITS["monthly"]["min"]
    if len(series) < need + 1:
        raise SystemExit(
            f"{path}: only {len(series)} monthly index observations; need at least "
            f"{need + 1} to compute a {need}-observation regression.")
    return series, ccol


# --------------------------------------------------------------- regression
def log_returns(series: dict, keys: list, freq: str = "monthly") -> list:
    """Log returns over `keys` (sorted).

    Monthly keys are (year, month) and must be calendar-adjacent, or the "return"
    spans a gap in the data. Daily keys are ISO date strings and are simply
    consecutive entries in the common set — both securities traded on both days,
    which is what alignment on the intersection already guarantees.
    """
    out = []
    for a, b in zip(keys, keys[1:]):
        if freq == "monthly" and (b[0] * 12 + b[1]) - (a[0] * 12 + a[1]) != 1:
            out.append(None)
            continue
        pa, pb = series.get(a), series.get(b)
        if not pa or not pb or pa <= 0 or pb <= 0:
            out.append(None)
            continue
        out.append(math.log(pb / pa))
    return out


def ols(y: list, x: list) -> dict:
    """Slope, intercept and R-squared of y on x. Pairs with a None are dropped."""
    pairs = [(a, b) for a, b in zip(y, x) if a is not None and b is not None]
    n = len(pairs)
    if n < 2:
        return {"n": n, "beta": None, "alpha": None, "r2": None}
    my = sum(p[0] for p in pairs) / n
    mx = sum(p[1] for p in pairs) / n
    sxx = sum((p[1] - mx) ** 2 for p in pairs)
    sxy = sum((p[0] - my) * (p[1] - mx) for p in pairs)
    if sxx == 0:
        return {"n": n, "beta": None, "alpha": None, "r2": None}
    beta = sxy / sxx
    alpha = my - beta * mx
    syy = sum((p[0] - my) ** 2 for p in pairs)
    r2 = 0.0 if syy == 0 else (sxy ** 2) / (sxx * syy)
    return {"n": n, "beta": beta, "alpha": alpha, "r2": r2}


# --------------------------------------------------------------- per company
def debt_equity(c: dict, basis: str) -> tuple:
    """Market-value D/E, plus notes. E is market cap, D is gross or net debt."""
    notes = []
    price, sh = c.get("price"), c.get("shares_cr")
    if price is None or not sh:
        return None, ["no price or share count, so market D/E cannot be struck"]
    mcap = float(price) * float(sh)
    gross = c.get("borrowings") or 0.0
    net = gross - (c.get("cash") or 0.0) - (c.get("surplus_investments") or 0.0)
    debt = gross if basis == "gross" else net
    if basis == "net" and debt < 0:
        notes.append(f"net cash of {-debt:,.0f} cr — D/E floored at 0, so the unlevered "
                     "beta equals the levered beta rather than exceeding it")
        debt = 0.0
    if mcap <= 0:
        return None, ["market cap is not positive"]
    return debt / mcap, notes


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("raw", help="peers_raw.json from peer_ingest.py")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--index",
                     help="CSV of the market index with Date and Close columns "
                          "(NIFTY 50 for an Indian comp set). Monthly regression, "
                          "because the Screener price block is monthly.")
    src.add_argument("--market",
                     help="market.json from market_data.py. Daily regression against "
                          "the index it already fetched — better, and no CSV to "
                          "download.")
    ap.add_argument("-o", "--out", default="data/peer_betas.json")
    ap.add_argument("--debt", choices=["net", "gross"], default="net",
                    help="debt used in the market D/E (default: net, matching the EV "
                         "bridge in build_comps.py)")
    ap.add_argument("--exclude-subject", action="store_true",
                    help="leave the subject out, so model.py medians peers only")
    ap.add_argument("--months", type=int, default=60,
                    help="most recent N months to regress over (default 60)")
    args = ap.parse_args()

    with open(args.raw, encoding="utf-8") as f:
        raw = json.load(f)

    market, daily_stock = None, {}
    if args.market:
        with open(args.market, encoding="utf-8") as f:
            market = json.load(f)
        if not (market.get("index") or {}).get("series"):
            raise SystemExit(
                f"{args.market} has no index series. Re-run market_data.py without "
                "--index none, or fall back to --index <csv>.")
        freq = "daily"
        idx = {d: v for d, v in market["index"]["series"]}
        idx_col = market["index"]["symbol"]
        for c in market.get("companies", []):
            key = c.get("ticker") or c.get("name")
            daily_stock[key] = {d: v for d, v in (c.get("series") or [])}
    else:
        freq = "monthly"
        idx, idx_col = read_index(args.index)

    lim = LIMITS[freq]
    subject = raw.get("subject")

    rows, warnings = [], []
    for c in raw["companies"]:
        is_subject = (c.get("ticker") == subject or c.get("name") == subject)
        if is_subject and args.exclude_subject:
            continue

        rec = {"name": c["name"], "ticker": c.get("ticker"), "is_subject": is_subject,
               "beta": None, "debt_equity": None, "n": 0, "r2": None, "freq": freq,
               "window": None, "debt_basis": args.debt, "notes": []}

        if freq == "daily":
            stock = daily_stock.get(c.get("ticker")) or daily_stock.get(c.get("name")) or {}
            if not stock:
                rec["notes"].append(
                    "no daily series in market.json for this company — it is in the "
                    "Screener set but not the market feed. Check the ticker mapping.")
                rows.append(rec)
                continue
        else:
            stock = monthly(c.get("price_series") or [])

        common = sorted(set(stock) & set(idx))
        if freq == "monthly" and args.months and len(common) > args.months + 1:
            common = common[-(args.months + 1):]

        if len(common) < lim["min"] + 1:
            rec["notes"].append(
                f"only {max(len(common) - 1, 0)} overlapping {freq} returns against the "
                f"index (need {lim['min']}); no beta emitted.")
            rows.append(rec)
            continue

        reg = ols(log_returns(stock, common, freq), log_returns(idx, common, freq))
        rec["n"] = reg["n"]
        if freq == "daily":
            rec["window"] = f"{common[0]} to {common[-1]}"
        else:
            rec["window"] = (f"{common[0][0]}-{common[0][1]:02d} to "
                             f"{common[-1][0]}-{common[-1][1]:02d}")

        if reg["beta"] is None or reg["n"] < lim["min"]:
            rec["notes"].append(f"regression produced only {reg['n']} usable returns; "
                                "no beta emitted")
        else:
            rec["beta"] = round(reg["beta"], 3)
            rec["r2"] = round(reg["r2"], 3)
            if reg["n"] < lim["thin"]:
                rec["notes"].append(f"thin window: {reg['n']} {freq} returns. Treat the "
                                    "beta as indicative and say so in the report.")
            if reg["r2"] < 0.10:
                rec["notes"].append(
                    f"R-squared {reg['r2']:.2f} — the index explains almost none of this "
                    "stock's movement, so the beta is not a reliable risk measure.")

        de, notes = debt_equity(c, args.debt)
        rec["debt_equity"] = None if de is None else round(de, 3)
        rec["notes"] += notes
        rows.append(rec)

    usable = [r for r in rows if r["beta"] is not None and r["debt_equity"] is not None]
    if not usable:
        warnings.append(
            "no company produced both a beta and a D/E, so model.py will fall back to "
            "the input beta. Check that the index series covers the same dates as the "
            "price series.")
    elif len(usable) < 3:
        warnings.append(
            f"only {len(usable)} usable peer beta(s). A median of fewer than three is "
            "barely more robust than the single regression beta it replaces.")

    doc = {"index": os.path.basename(args.index) if args.index else idx_col,
           "index_column": idx_col, "frequency": freq, "min_obs": lim["min"],
           "debt_basis": args.debt, "peer_betas": rows, "warnings": warnings}

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=1)
    print(f"wrote {args.out}")

    print(f"\nindex {doc['index']} ({idx_col!r}), {freq} log returns, "
          f"D/E on {args.debt} debt")
    print(f"{'company':<26}{'beta':>8}{'D/E':>8}{'obs':>6}{'R2':>7}  window")
    for r in rows:
        print(f"{r['name'][:25]:<26}{str(r['beta'] or '-'):>8}"
              f"{str(r['debt_equity'] if r['debt_equity'] is not None else '-'):>8}"
              f"{r['n']:>6}{str(r['r2'] or '-'):>7}  {r['window'] or '-'}")
    for r in rows:
        for n in r["notes"]:
            print(f"  ! {r['name']}: {n}")
    for w in warnings:
        print(f"  ! {w}")
    if usable:
        print(f"\n{len(usable)} usable for the Hamada relever. Pass with "
              f"build_comps.py --betas {args.out}")


if __name__ == "__main__":
    main()
