#!/usr/bin/env python3
"""
peer_ingest.py — Screener exports (subject + peers) -> peers_raw.json

    python3 peer_ingest.py peers_manifest.json -o data/peers_raw.json

Reads one Screener "Export to Excel" file per company through the equity-research-report
skill's `parse_screener.py`, so learned aliases apply here too and there is exactly one
Screener parser in the toolchain. This script deliberately does NOT carry its own copy —
a second copy would drift silently, and a drifted parser is invisible until a multiple is
quietly wrong.

What it extracts per company, and nothing more:
  * the comparability facts   — reporting basis, currency unit, fiscal year end, the
                                trailing window actually used
  * the P&L numerator inputs  — sales, EBITDA, PAT (TTM where four quarters exist,
                                else the latest full year)
  * the balance-sheet inputs  — borrowings, cash, investments, net worth, share count
  * the price series          — for beta, and to price the comps as of the cover date

Every number is stamped with the period it came from. `build_comps.py` does the
arithmetic; this file only reads and labels.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

MONTHS = {m: i + 1 for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun",
     "jul", "aug", "sep", "oct", "nov", "dec"])}

# Screener states the basis and the unit in the first few rows of the Data Sheet,
# e.g. "Consolidated Figures in Rs. Crores / View Source".
BASIS_RE = re.compile(r"\b(consolidated|standalone)\b", re.I)
UNIT_RE = re.compile(r"figures?\s+in\s+(rs\.?\s*)?(crores?|millions?|lakhs?|billions?)", re.I)


# --------------------------------------------------------------- parser locator
def load_parser(explicit: str | None):
    """Import parse_screener.py from the equity-research-report skill.

    Searched in order so that an explicit path always wins and a Cowork install
    (where the skills sit side by side) resolves without configuration.
    """
    here = os.path.dirname(os.path.abspath(__file__))
    cands = []
    if explicit:
        cands.append(explicit)
    if os.environ.get("EQR_SKILL"):
        cands.append(os.path.join(os.environ["EQR_SKILL"], "scripts", "parse_screener.py"))
    cands += [
        os.path.join(here, "..", "..", "equity-research-report", "scripts", "parse_screener.py"),
        os.path.expanduser("~/.claude/skills/equity-research-report/scripts/parse_screener.py"),
        os.path.join(os.getcwd(), ".claude", "skills", "equity-research-report",
                     "scripts", "parse_screener.py"),
    ]
    for c in cands:
        c = os.path.abspath(c)
        if os.path.exists(c):
            sys.path.insert(0, os.path.dirname(c))
            import parse_screener  # noqa: E402
            return parse_screener, c
    raise SystemExit(
        "could not find parse_screener.py from the equity-research-report skill.\n"
        "Tried:\n  " + "\n  ".join(os.path.abspath(c) for c in cands) +
        "\nPass --parser <path to parse_screener.py>, or set EQR_SKILL to the "
        "equity-research-report skill directory.\n"
        "Do not copy the parser into this skill — it must stay a single file so "
        "learned Screener aliases keep applying.")


# --------------------------------------------------------------- small helpers
def period_month(label: str):
    """'Mar-24' -> (3, 2024). Returns None when the label is not a period."""
    if not isinstance(label, str):
        return None
    m = re.match(r"^([A-Za-z]{3})[-\s]?(\d{2,4})$", label.strip())
    if not m:
        return None
    mon = MONTHS.get(m[1].lower())
    if not mon:
        return None
    yr = int(m[2])
    return (mon, yr + 2000 if yr < 100 else yr)


def last_valid(seq, n=1):
    """Last n non-None values of a series, oldest first. Fewer if unavailable."""
    vals = [(i, v) for i, v in enumerate(seq or []) if v is not None]
    return vals[-n:]


def get(block: dict, *names):
    """First present key among `names` (case-insensitive), as a list."""
    if not block:
        return None
    lower = {k.lower(): k for k in block if k != "periods"}
    for n in names:
        if n.lower() in lower:
            return block[lower[n.lower()]]
    return None


def tail(block: dict, *names):
    """Latest non-None value of a line item plus the period it belongs to."""
    ser = get(block, *names)
    if not ser:
        return None, None
    per = block.get("periods") or []
    hit = last_valid(ser, 1)
    if not hit:
        return None, None
    i, v = hit[0]
    return v, (per[i] if i < len(per) else None)


def prior(block: dict, *names):
    """Second-latest non-None value — used for average net worth in ROE."""
    ser = get(block, *names)
    if not ser:
        return None
    hits = last_valid(ser, 2)
    return hits[0][1] if len(hits) == 2 else None


# --------------------------------------------------------------- scanning the raw file
def scan_header(path: str) -> dict:
    """Read the basis and currency unit Screener prints above the Data Sheet."""
    import openpyxl
    out = {"basis_detected": None, "unit_detected": None}
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    try:
        for ws in wb.worksheets:
            for row in ws.iter_rows(min_row=1, max_row=12, values_only=True):
                for cell in row or []:
                    if not isinstance(cell, str):
                        continue
                    if out["basis_detected"] is None:
                        m = BASIS_RE.search(cell)
                        if m:
                            out["basis_detected"] = m[1].lower()
                    if out["unit_detected"] is None:
                        m = UNIT_RE.search(cell)
                        if m:
                            out["unit_detected"] = m[2].lower().rstrip("s")
            if out["basis_detected"] and out["unit_detected"]:
                break
    finally:
        wb.close()
    return out


def ttm(quarterly: dict, *names):
    """Sum of the last four reported quarters, with the window it covers.

    Returns (value, window_end_label, quarters_used). A TTM built from three
    quarters is not a TTM, so anything short returns None and the caller falls
    back to the last full year.
    """
    ser = get(quarterly, *names)
    if not ser:
        return None, None, 0
    per = quarterly.get("periods") or []
    hits = last_valid(ser, 4)
    if len(hits) < 4:
        return None, None, len(hits)
    idx = [i for i, _ in hits]
    # The four must be consecutive columns, or they are not a continuous year.
    if idx != list(range(idx[0], idx[0] + 4)):
        return None, None, len(hits)
    end = per[idx[-1]] if idx[-1] < len(per) else None
    return sum(v for _, v in hits), end, 4


def price_series(fin: dict) -> list:
    """[(period_label, close)] for the share price, oldest first.

    Comes straight from `parse_screener.parse`, like every other number here.
    This used to re-read the workbook itself, because the parser's block reader
    stopped at any row matching its own block markers and "Price" is one of them,
    so the price block always came back empty. That is fixed in the parser, which
    also handles both of Screener's price layouts (dates across a header row, and
    a Date/Price column pair running down), so the second implementation is gone.
    Do not reintroduce it: two Screener layout readers drift, and a drifted one is
    invisible until a beta is quietly wrong.
    """
    blk = fin.get("price") or {}
    per = blk.get("periods") or []
    for k, v in blk.items():
        if k != "periods" and re.search(r"price|close|adj", k, re.I) and isinstance(v, list):
            got = [(p, x) for p, x in zip(per, v) if x is not None]
            if len(got) >= 3:
                return got
    return []


def price_asof(series: list, as_of: str):
    """Close nearest to (and not after) the cover date, else the earliest close."""
    if not series:
        return None, None
    want = period_month(as_of) or None
    if want is None:
        m = re.match(r"^(\d{4})-(\d{2})", as_of or "")
        want = (int(m[2]), int(m[1])) if m else None
    if want is None:
        return series[-1][1], series[-1][0]
    key = want[1] * 12 + want[0]
    best, best_lab, best_gap = None, None, None
    for lab, v in series:
        pm = period_month(lab)
        if not pm:
            continue
        gap = key - (pm[1] * 12 + pm[0])
        if gap < 0:
            continue
        if best_gap is None or gap < best_gap:
            best, best_lab, best_gap = v, lab, gap
    if best is None:
        return series[0][1], series[0][0]
    return best, best_lab


# --------------------------------------------------------------- per-company ingest
def market_lookup(market: dict | None, entry: dict) -> dict:
    """The market_data.py record for this company, matched on ticker then name."""
    if not market:
        return {}
    for c in market.get("companies", []):
        if entry.get("ticker") and c.get("ticker") == entry["ticker"]:
            return c
    for c in market.get("companies", []):
        if entry.get("name") and c.get("name") == entry["name"]:
            return c
    return {}


def ingest_one(entry: dict, manifest: dict, parse_screener, root: str | None,
               market: dict | None = None) -> dict:
    path = entry["export"]
    if not os.path.exists(path):
        raise SystemExit(f"{entry.get('ticker') or entry.get('name')}: export not found: {path}")

    fin = parse_screener.parse(path, root)
    hdr = scan_header(path)

    name = entry.get("name") or fin.get("company") or entry.get("ticker")
    rec = {
        "ticker": entry.get("ticker"),
        "name": name,
        "export": path,
        "company_in_file": fin.get("company"),
        "warnings": [],
        "flags": [],
    }

    # ---- comparability gates ------------------------------------------------
    declared = (entry.get("basis") or manifest.get("basis") or "").lower() or None
    detected = hdr["basis_detected"]
    rec["basis"] = detected or declared
    rec["basis_source"] = "file" if detected else ("declared" if declared else None)
    if detected and declared and detected != declared:
        raise SystemExit(
            f"{name}: basis mismatch — manifest declares '{declared}' but the export "
            f"header says '{detected}'. Re-download the {declared} view from Screener, "
            "or fix the manifest. Mixing bases corrupts every multiple, so this is not "
            "a warning.")
    if not detected:
        rec["warnings"].append(
            "reporting basis not stated in the export header; using the declared "
            f"'{declared}' unverified")

    rec["unit"] = hdr["unit_detected"] or "crore"
    if hdr["unit_detected"] is None:
        rec["warnings"].append("currency unit not stated in the export; assuming Rs crore")

    if fin.get("company") and entry.get("name") and \
            fin["company"].strip().lower()[:12] != entry["name"].strip().lower()[:12]:
        rec["warnings"].append(
            f"manifest name {entry['name']!r} does not look like the export's "
            f"{fin['company']!r} — check the file is the right company")

    annual = fin.get("annual") or {}
    balance = fin.get("balance") or {}
    quarterly = fin.get("quarterly") or {}

    # ---- fiscal calendar ----------------------------------------------------
    ap = annual.get("periods") or []
    fy_end = ap[-1] if ap else None
    pm = period_month(fy_end) if fy_end else None
    rec["fy_end_label"] = fy_end
    rec["fy_end_month"] = pm[0] if pm else None

    # ---- trailing P&L: TTM preferred, last full year as fallback ------------
    sales_t, w_end, nq = ttm(quarterly, "Sales", "Revenue", "Net Sales")
    ebitda_t, _, _ = ttm(quarterly, "Operating Profit", "EBITDA")
    pat_t, _, _ = ttm(quarterly, "Net profit", "Net Profit", "Profit after tax", "PAT")

    if sales_t is not None and ebitda_t is not None and pat_t is not None:
        rec["window"] = {"kind": "TTM", "end": w_end, "quarters": nq}
        rec["sales"], rec["ebitda"], rec["pat"] = sales_t, ebitda_t, pat_t
    else:
        s, sp = tail(annual, "Sales", "Revenue", "Net Sales")
        e, _ = tail(annual, "Operating Profit", "EBITDA")
        p, _ = tail(annual, "Net profit", "Net Profit", "Profit after tax", "PAT")
        rec["window"] = {"kind": "FY", "end": sp or fy_end, "quarters": 0}
        rec["sales"], rec["ebitda"], rec["pat"] = s, e, p
        if nq:
            rec["warnings"].append(
                f"only {nq} usable quarter(s) in the export — fell back to the last "
                "full year, which is staler than the peers priced on TTM")

    # ---- balance sheet ------------------------------------------------------
    esc, bs_per = tail(balance, "Equity Share Capital", "Share Capital")
    res, _ = tail(balance, "Reserves")
    rec["bs_period"] = bs_per
    rec["equity_capital"], rec["reserves"] = esc, res
    rec["bv"] = None if esc is None or res is None else esc + res

    prev_esc, prev_res = prior(balance, "Equity Share Capital", "Share Capital"), \
        prior(balance, "Reserves")
    rec["bv_prior"] = None if prev_esc is None or prev_res is None else prev_esc + prev_res

    rec["borrowings"], _ = tail(balance, "Borrowings")
    rec["cash"], _ = tail(balance, "Cash & Bank", "Cash and Bank", "Cash")
    rec["investments"], _ = tail(balance, "Investments")

    # Screener ships two different share-count lines and only one is in crore.
    # Falling through the aliases blindly puts an ABSOLUTE count in a field named
    # shares_cr: market cap then comes out in rupees against a P&L in crore, net
    # debt is 7 orders of magnitude too small, and it silently vanishes from EV.
    sh, _ = tail(balance, "Adjusted Equity Shares in Cr")
    if sh is None:
        sh_abs, _ = tail(balance, "No. of Equity Shares", "Number of Shares")
        if sh_abs is not None:
            sh = sh_abs / 1e7
            rec["warnings"].append(
                f"share count read from an absolute line and converted to crore "
                f"({sh_abs:,.0f} -> {sh:,.2f} Cr)")
    # Magnitude guard. A listed Indian company sits roughly between 0.1 and 10,000
    # crore shares; anything outside that means the basis is still wrong.
    if sh is not None and not (0.01 <= sh <= 100000):
        rec["warnings"].append(
            f"share count {sh:,.2f} is outside the plausible crore range — check the "
            "units before trusting market cap, EV or any multiple")
    rec["shares_cr"] = sh
    if sh is None:
        rec["warnings"].append(
            "share count not found in the balance sheet block — market cap cannot be "
            "struck from the cover-date price for this company")

    # ---- price --------------------------------------------------------------
    series = price_series(fin)
    rec["price_points"] = len(series)
    as_of = manifest.get("as_of") or ""

    # Price precedence: what the analyst typed, then the market feed, then the
    # export's own block. The export is last because it is the only one of the
    # three that cannot be struck on the cover date.
    mkt = market_lookup(market, entry)
    if mkt:
        rec["market"] = {k: mkt.get(k) for k in
                         ("yahoo", "price", "price_date", "market_cap", "shares_cr",
                          "revenue", "net_debt", "total_debt", "cash", "equity",
                          "net_income", "currency")}

    if entry.get("price") is not None:
        rec["price"] = float(entry["price"])
        rec["price_basis"] = entry.get("price_source") or "manifest"
    elif mkt.get("price") is not None:
        rec["price"] = float(mkt["price"])
        rec["price_basis"] = f"Yahoo {mkt.get('yahoo')} close {mkt.get('price_date')}"
    else:
        pv, plab = price_asof(series, as_of)
        rec["price"] = pv
        rec["price_basis"] = f"export price block, {plab}" if pv is not None else None
        if pv is None:
            rec["warnings"].append(
                "no price in the manifest and no usable price block in the export "
                "(if the export does have one, check --parser is not pointing at an "
                "old parse_screener.py whose price block never parsed)")
        elif plab and as_of and not str(plab).lower().startswith(str(as_of).lower()[:3]):
            rec["warnings"].append(
                f"priced off the export at {plab}, not the cover date {as_of}; supply "
                "`price` in the manifest to price every peer on the same day")

    # Carried through for beta. Collapsed to the last observation in each calendar
    # month: a daily export would otherwise put thousands of points in this file,
    # and monthly is the finest frequency the regression uses anyway.
    seen = {}
    for lab, v in series:
        pm = period_month(lab)
        if pm:
            seen[pm] = (lab, v)
    # period_month is (month, year), so sort on (year, month) or the series comes
    # back ordered by calendar month rather than chronologically.
    rec["price_series"] = [seen[k] for k in sorted(seen, key=lambda p: (p[1], p[0]))]

    # ---- analyst overrides and forward estimates ----------------------------
    for k in ("surplus_investments", "minority_interest", "preference_capital"):
        if entry.get(k) is not None:
            rec[k] = float(entry[k])

    fwd = entry.get("forward") or {}
    if any(fwd.get(k) is not None for k in ("eps", "ebitda", "sales", "pat")):
        missing = [k for k in ("source", "as_of") if not fwd.get(k)]
        if missing:
            raise SystemExit(
                f"{name}: forward estimates supplied without {', '.join(missing)}. "
                "A forward multiple with no attribution is not auditable — add "
                f"\"source\" and \"as_of\" to the forward block, or clear the numbers.")
        rec["forward"] = fwd

    rec["screener_warnings"] = fin.get("warnings", [])
    return rec


# --------------------------------------------------------------- CLI
def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("manifest", help="peers_manifest.json (see assets/ for the template)")
    ap.add_argument("-o", "--out", default="data/peers_raw.json")
    ap.add_argument("--parser", help="path to parse_screener.py, if not auto-found")
    ap.add_argument("--market", help="market.json from market_data.py — supplies the "
                                     "cover-date close where the manifest has none, and "
                                     "carries the second source for --crosscheck later")
    ap.add_argument("--root", default=None,
                    help="reports root holding _knowledge/aliases.json "
                         "(default: $EQR_REPORTS_ROOT or ./reports)")
    args = ap.parse_args()

    parse_screener, ppath = load_parser(args.parser)

    with open(args.manifest, encoding="utf-8") as f:
        man = json.load(f)

    comps = man.get("companies") or []
    if len(comps) < 2:
        raise SystemExit("manifest needs the subject plus at least one peer")

    subject = man.get("subject")
    if subject and not any((c.get("ticker") == subject or c.get("name") == subject)
                           for c in comps):
        raise SystemExit(f"manifest 'subject' {subject!r} is not one of the companies")

    root = args.root or os.environ.get("EQR_REPORTS_ROOT")

    market = None
    if args.market:
        with open(args.market, encoding="utf-8") as f:
            market = json.load(f)

    out = {
        "as_of": man.get("as_of"),
        "basis": man.get("basis"),
        "subject": subject or (comps[0].get("ticker") or comps[0].get("name")),
        "parser": ppath,
        "market_source": (market or {}).get("source"),
        "companies": [ingest_one(c, man, parse_screener, root, market) for c in comps],
    }

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, default=str)

    print(f"parser  : {ppath}")
    print(f"as of   : {out['as_of']}   basis: {out['basis']}   subject: {out['subject']}")
    print(f"{'company':<26}{'basis':<19}{'FY end':<9}{'window':<14}{'price':>10}  warn")
    for c in out["companies"]:
        w = c["window"]
        basis = f"{c['basis'] or '?'}/{c['basis_source'] or '?'}"
        price = f"{c['price']:,.1f}" if c["price"] is not None else "-"
        print(f"{(c['name'] or '?')[:25]:<26}{basis:<19}{str(c['fy_end_label']):<9}"
              f"{w['kind'] + ' ' + str(w['end']):<14}{price:>10}"
              f"  {len(c['warnings']) or ''}")
    for c in out["companies"]:
        for w in c["warnings"]:
            print(f"  ! {c['name']}: {w}")

    print(f"\nwrote {args.out}")
    print("next: build_comps.py " + args.out)


if __name__ == "__main__":
    main()
