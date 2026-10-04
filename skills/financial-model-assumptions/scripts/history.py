#!/usr/bin/env python3
"""Historical anchors for financial model assumptions.

Turns a financial statement series into the ratios every assumption has to be
argued against: growth, margins, expense ratios, working-capital days, capex
intensity, effective tax rate and borrowing cost - each with a last value, a
3-year and 5-year average, a range and a trend direction.

No third-party dependencies.

Input (--in) is JSON in either shape:

  flat      {"periods": ["FY21",...], "sales": [...], "ebitda": [...], ...}
  nested    {"annual": {"periods": [...], "sales": [...]},
             "balance": {"receivables": [...]}, "cashflow": {"capex": [...]}}

Line-item names are matched through an alias table, so `revenue`,
`total_income`, `net_sales` and `sales` are all read as sales. Series are
oldest-first and may contain nulls.

Usage
    python history.py --in financials.json                  # markdown to stdout
    python history.py --in financials.json --out history.json
    python history.py --in financials.json --units cr       # label only
"""
from __future__ import annotations

import argparse
import json
import os
import sys

# --------------------------------------------------------------------------
# line-item aliases: canonical -> accepted keys (lowercased, non-alnum stripped)
# --------------------------------------------------------------------------
ALIASES = {
    "sales":       ["sales", "revenue", "revenues", "netsales", "totalincome",
                    "revenuefromoperations", "turnover", "totalrevenue"],
    "cogs":        ["cogs", "costofgoodssold", "costofmaterialsconsumed",
                    "costofsales", "materialcost", "rawmaterialcost"],
    "grossprofit": ["grossprofit", "gp"],
    "ebitda":      ["ebitda", "operatingprofit", "opm", "operatingprofitebitda"],
    "ebit":        ["ebit", "operatingincome", "profitbeforeinterestandtax", "pbit"],
    "dep":         ["dep", "depreciation", "depreciationandamortisation",
                    "depreciationamortization", "da", "depreciationamortisation"],
    "amort":       ["amort", "amortisation", "amortization"],
    "interest":    ["interest", "financecost", "financecosts", "interestexpense"],
    "pbt":         ["pbt", "profitbeforetax", "ebt"],
    "tax":         ["tax", "taxexpense", "taxes", "currenttax", "totaltax"],
    "pat":         ["pat", "netprofit", "profitaftertax", "netincome",
                    "profitfortheyear"],
    "sga":         ["sga", "sgna", "sellinggeneralandadministrative",
                    "otherexpenses", "sellingandadmin", "adminexpenses"],
    "rnd":         ["rnd", "rd", "researchanddevelopment", "randd", "rdexpense"],
    "marketing":   ["marketing", "salesandmarketing", "advertising",
                    "advertisingandpromotion", "adspend", "sellingexpenses"],
    "employee":    ["employee", "employeecost", "employeebenefitexpense",
                    "staffcost", "personnelcost", "employeeexpenses"],
    "receivables": ["receivables", "debtors", "tradereceivables",
                    "accountsreceivable", "sundrydebtors"],
    "inventory":   ["inventory", "inventories", "stock", "closingstock"],
    "payables":    ["payables", "creditors", "tradepayables", "accountspayable",
                    "sundrycreditors"],
    "capex":       ["capex", "capitalexpenditure", "purchaseoffixedassets",
                    "additionstoppe", "fixedassetspurchased"],
    "debt":        ["debt", "borrowings", "totaldebt", "totalborrowings",
                    "loans"],
    "equity":      ["equity", "networth", "shareholdersfunds", "totalequity",
                    "shareholdersequity", "bookvalue"],
    "reserves":    ["reserves", "reservesandsurplus", "retainedearnings"],
    "sharecapital": ["equitysharecapital", "sharecapital", "paidupcapital"],
    "cash":        ["cash", "cashandequivalents", "cashandcashequivalents",
                    "cashbank"],
    "gross_block": ["grossblock", "ppegross", "grossfixedassets"],
    "net_block":   ["netblock", "ppe", "netfixedassets", "propertyplantequipment"],
}

DAYS = 365.0


def _norm(k: str) -> str:
    return "".join(c for c in str(k).lower() if c.isalnum())


# Blocks whose series are NOT annual. A quarterly Operating Profit silently winning
# the "ebitda" key and being divided by annual sales reports a 16% EBITDA margin for a
# business running at 59% — plausible enough to reach a report unchallenged.
_NON_ANNUAL = ("quarter", "quarterly", "qtr", "monthly", "half")


def _is_annualish(name: str) -> bool:
    n = _norm(name)
    return not any(tok in n for tok in _NON_ANNUAL)


def _flatten(doc: dict) -> tuple[list, dict, list]:
    """Collapse nested {annual|balance|cashflow|profitloss|...} into one dict.

    Annual blocks are consumed FIRST so that "first wins" means "annual wins".
    Periods are taken from an annual block, never from whichever block happens to
    be longest — a quarterly block usually is.
    """
    flat: dict = {}
    periods: list = []
    notes: list = []
    annual_blocks, other_blocks = [(None, doc)], []
    for name, v in doc.items():
        if isinstance(v, dict):
            (annual_blocks if _is_annualish(name) else other_blocks).append((name, v))

    for bname, b in annual_blocks + other_blocks:
        annualish = _is_annualish(bname or "")
        for k, v in b.items():
            if _norm(k) in ("periods", "period", "years", "fy", "columns"):
                if isinstance(v, list) and annualish and len(v) > len(periods):
                    periods = list(v)
            elif isinstance(v, list):
                key = _norm(k)
                if key in flat:
                    continue
                flat[key] = v
                if not annualish:
                    notes.append(
                        f"'{k}' was taken from the '{bname}' block — no annual series "
                        "exists for it. Ratios against annual figures will be wrong; "
                        "derive it into the annual block before trusting them.")
    return periods, flat, notes


def _pick(flat: dict, canonical: str) -> list | None:
    for alias in ALIASES[canonical]:
        if alias in flat:
            return flat[alias]
    return None


def _f(x):
    """Coerce to float, tolerating None, '', '1,234', '12%', '(45)'."""
    if x is None or isinstance(x, bool):
        return None
    if isinstance(x, (int, float)):
        return float(x)
    s = str(x).strip().replace(",", "").replace("%", "")
    if not s or s in ("-", "--", "NA", "na", "N/A", "nan"):
        return None
    neg = s.startswith("(") and s.endswith(")")
    if neg:
        s = s[1:-1]
    try:
        v = float(s)
    except ValueError:
        return None
    return -v if neg else v


def _series(flat: dict, canonical: str, n: int) -> list:
    raw = _pick(flat, canonical)
    if raw is None:
        return [None] * n
    out = [_f(x) for x in raw][:n]
    return out + [None] * (n - len(out))


def _div(a, b):
    if a is None or b in (None, 0):
        return None
    return a / b


def _ratio(num: list, den: list, mult: float = 100.0) -> list:
    return [None if _div(a, b) is None else _div(a, b) * mult
            for a, b in zip(num, den)]


def _avg_of(series: list, k: int | None = None):
    v = [x for x in (series[-k:] if k else series) if x is not None]
    return sum(v) / len(v) if v else None


def _growth(series: list) -> list:
    """YoY % growth; first element None."""
    out = [None]
    for prev, cur in zip(series, series[1:]):
        if prev in (None, 0) or cur is None:
            out.append(None)
        elif prev < 0:
            out.append(None)          # growth off a negative base is meaningless
        else:
            out.append((cur / prev - 1) * 100)
    return out


def _cagr(series: list, years: int):
    """CAGR % over the last `years` intervals; needs both endpoints positive."""
    v = [(i, x) for i, x in enumerate(series) if x is not None]
    if len(v) < 2:
        return None
    end_i, end = v[-1]
    start = None
    for i, x in v:
        if end_i - i == years:
            start = x
            break
    if start is None or start <= 0 or end <= 0:
        return None
    return ((end / start) ** (1.0 / years) - 1) * 100


def _trend(series: list) -> str:
    """Direction of the last 5 observations by comparing halves."""
    v = [x for x in series[-5:] if x is not None]
    if len(v) < 3:
        return "n/a"
    h = len(v) // 2
    first, second = _avg_of(v[:h]), _avg_of(v[-h:])
    if first is None or second is None or first == 0:
        return "n/a"
    delta = (second - first) / abs(first) * 100
    if delta > 7:
        return "rising"
    if delta < -7:
        return "falling"
    return "flat"


def _stat(name: str, series: list, unit: str) -> dict:
    vals = [x for x in series if x is not None]
    return {
        "metric": name,
        "unit": unit,
        "series": [None if x is None else round(x, 2) for x in series],
        "last": round(vals[-1], 2) if vals else None,
        "avg_3y": round(_avg_of(series, 3), 2) if _avg_of(series, 3) is not None else None,
        "avg_5y": round(_avg_of(series, 5), 2) if _avg_of(series, 5) is not None else None,
        "min": round(min(vals), 2) if vals else None,
        "max": round(max(vals), 2) if vals else None,
        "trend": _trend(series),
        "n_obs": len(vals),
    }


# --------------------------------------------------------------------------

def compute(doc: dict) -> dict:
    periods, flat, flat_notes = _flatten(doc)
    for _n in flat_notes:
        print(f"  ! {_n}")
    n = len(periods) if periods else max(
        (len(v) for v in flat.values() if isinstance(v, list)), default=0)
    if not periods:
        periods = [f"P{i+1}" for i in range(n)]

    S = {c: _series(flat, c, n) for c in ALIASES}

    # derived line items where the direct one is absent
    if all(x is None for x in S["ebit"]):
        S["ebit"] = [None if (e is None or d is None) else e - d
                     for e, d in zip(S["ebitda"], S["dep"])]
    if all(x is None for x in S["ebitda"]):
        S["ebitda"] = [None if (e is None or d is None) else e + d
                       for e, d in zip(S["ebit"], S["dep"])]
    if all(x is None for x in S["grossprofit"]) and any(x is not None for x in S["cogs"]):
        S["grossprofit"] = [None if (s is None or c is None) else s - c
                            for s, c in zip(S["sales"], S["cogs"])]
    # Cash-flow exports carry capex as an outflow (negative); depreciation and
    # amortisation are occasionally signed the same way. These are magnitudes.
    for c in ("capex", "dep", "amort"):
        S[c] = [None if x is None else abs(x) for x in S[c]]

    # Screener-style exports carry reserves and share capital, not net worth
    if all(x is None for x in S["equity"]):
        S["equity"] = [None if (r is None and c is None) else (r or 0) + (c or 0)
                       for r, c in zip(S["reserves"], S["sharecapital"])]
    if all(x is None for x in S["cogs"]) and any(x is not None for x in S["grossprofit"]):
        S["cogs"] = [None if (s is None or g is None) else s - g
                     for s, g in zip(S["sales"], S["grossprofit"])]

    sales = S["sales"]
    cogs_or_sales = [c if c is not None else s for c, s in zip(S["cogs"], sales)]

    m: dict = {}
    m["revenue_growth"] = _stat("Revenue growth", _growth(sales), "%")
    m["gross_margin"] = _stat("Gross margin", _ratio(S["grossprofit"], sales), "%")
    m["ebitda_margin"] = _stat("EBITDA margin", _ratio(S["ebitda"], sales), "%")
    m["ebit_margin"] = _stat("EBIT margin", _ratio(S["ebit"], sales), "%")
    m["pat_margin"] = _stat("PAT margin", _ratio(S["pat"], sales), "%")
    m["sga_pct_sales"] = _stat("SG&A % sales", _ratio(S["sga"], sales), "%")
    m["rnd_pct_sales"] = _stat("R&D % sales", _ratio(S["rnd"], sales), "%")
    m["marketing_pct_sales"] = _stat("S&M % sales", _ratio(S["marketing"], sales), "%")
    m["employee_pct_sales"] = _stat("Employee cost % sales", _ratio(S["employee"], sales), "%")
    m["capex_pct_sales"] = _stat("Capex % sales", _ratio(S["capex"], sales), "%")
    m["dep_pct_sales"] = _stat("Depreciation % sales", _ratio(S["dep"], sales), "%")
    m["amort_pct_sales"] = _stat("Amortisation % sales", _ratio(S["amort"], sales), "%")
    m["dep_pct_gross_block"] = _stat("Depreciation % gross block",
                                     _ratio(S["dep"], S["gross_block"]), "%")
    m["dso"] = _stat("DSO", _ratio(S["receivables"], sales, DAYS), "days")
    m["dio"] = _stat("DIO", _ratio(S["inventory"], cogs_or_sales, DAYS), "days")
    m["dpo"] = _stat("DPO", _ratio(S["payables"], cogs_or_sales, DAYS), "days")
    ccc = [None if (a is None or b is None or c is None) else a + b - c
           for a, b, c in zip(m["dso"]["series"], m["dio"]["series"], m["dpo"]["series"])]
    m["ccc"] = _stat("Cash conversion cycle", ccc, "days")
    nwc = [None if (r is None and i is None and p is None) else
           (r or 0) + (i or 0) - (p or 0)
           for r, i, p in zip(S["receivables"], S["inventory"], S["payables"])]
    m["nwc_pct_sales"] = _stat("NWC % sales", _ratio(nwc, sales), "%")
    m["effective_tax_rate"] = _stat("Effective tax rate", _ratio(S["tax"], S["pbt"]), "%")

    # borrowing cost on average debt
    avg_debt = [None]
    for prev, cur in zip(S["debt"], S["debt"][1:]):
        avg_debt.append(None if (prev is None or cur is None) else (prev + cur) / 2)
    m["interest_rate"] = _stat("Interest rate on avg debt",
                               _ratio(S["interest"], avg_debt), "%")
    m["debt_growth"] = _stat("Debt growth", _growth(S["debt"]), "%")
    m["net_debt_ebitda"] = _stat(
        "Net debt / EBITDA",
        [None if (d is None or e in (None, 0)) else (d - (c or 0)) / e
         for d, c, e in zip(S["debt"], S["cash"], S["ebitda"])], "x")
    m["roe"] = _stat("ROE", _ratio(S["pat"], S["equity"]), "%")
    capital = [None if (d is None and e is None) else (d or 0) + (e or 0)
               for d, e in zip(S["debt"], S["equity"])]
    m["roce"] = _stat("ROCE (EBIT / capital employed)", _ratio(S["ebit"], capital), "%")
    m["asset_turnover"] = _stat("Sales / net block", _ratio(sales, S["net_block"]), "x")

    cagr = {f"cagr_{k}y": (round(_cagr(sales, k), 2) if _cagr(sales, k) is not None else None)
            for k in (3, 5, 10)}

    missing = sorted(c for c in ("sales", "ebitda", "ebit", "dep", "capex", "tax",
                                 "pbt", "receivables", "inventory", "payables",
                                 "debt", "equity")
                     if all(x is None for x in S[c]))

    return {
        "periods": periods,
        "n_periods": n,
        "revenue_cagr": cagr,
        "metrics": m,
        "missing_line_items": missing,
        "note": "Averages ignore nulls. Growth off a negative base is reported null. "
                "DIO/DPO use COGS where available, else sales - state which in the "
                "evidence note.",
    }


def to_markdown(h: dict) -> str:
    L = [f"# Historical anchors  ({h['n_periods']} periods: "
         f"{h['periods'][0]} - {h['periods'][-1]})", ""]
    c = h["revenue_cagr"]
    L.append("**Revenue CAGR** - " + "  |  ".join(
        f"{k}y: {'n/a' if c[f'cagr_{k}y'] is None else str(c[f'cagr_{k}y']) + '%'}"
        for k in (3, 5, 10)))
    L += ["", "| Metric | Unit | Last | 3y avg | 5y avg | Min | Max | Trend | n |",
          "|---|---|---|---|---|---|---|---|---|"]
    for v in h["metrics"].values():
        if v["n_obs"] == 0:
            continue
        L.append(f"| {v['metric']} | {v['unit']} | {v['last']} | {v['avg_3y']} | "
                 f"{v['avg_5y']} | {v['min']} | {v['max']} | {v['trend']} | {v['n_obs']} |")
    if h["missing_line_items"]:
        L += ["", "**Not present in the input** (no anchor available; the assumption "
              "for these must come from narrative evidence or be declared "
              "insufficient): " + ", ".join(h["missing_line_items"])]
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--in", dest="inp", required=True, help="financials JSON")
    ap.add_argument("--out", help="write history.json here")
    ap.add_argument("--json", action="store_true", help="print JSON not markdown")
    a = ap.parse_args()

    if not os.path.exists(a.inp):
        print(f"error: no such file: {a.inp}", file=sys.stderr)
        return 2
    try:
        doc = json.load(open(a.inp, encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"error: {a.inp} is not valid JSON ({e})", file=sys.stderr)
        return 2
    if not isinstance(doc, dict):
        print("error: expected a JSON object at the top level", file=sys.stderr)
        return 2

    h = compute(doc)
    if h["n_periods"] == 0:
        print("error: no numeric series found. Check the key names against the "
              "alias table in this script.", file=sys.stderr)
        return 1

    if a.out:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        json.dump(h, open(a.out, "w", encoding="utf-8"), indent=2)
        print(f"wrote {a.out}")
    if a.json:
        print(json.dumps(h, indent=2))
    else:
        print(to_markdown(h))
    return 0


if __name__ == "__main__":
    sys.exit(main())
