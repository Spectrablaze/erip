#!/usr/bin/env python3
"""
ingest.py - assemble one `model_input.json` from every source the model needs.

    python ingest.py --screener export.xlsx \
                     --assumptions data/assumptions.json \
                     --overrides overrides.json \
                     -o data/model_input.json

Sources, in increasing order of authority:

  1. Screener export (.xlsx) or an already-parsed financials.json - the historical
     spine. Broad, consistent, but it has no trade payables and no expense detail
     for some companies.
  2. `overrides.actuals` - figures read off the annual report, each with a page
     citation. These fill what Screener lacks and win where the two disagree.
  3. `assumptions.json` from the financial-model-assumptions skill - the forecast
     drivers.
  4. `overrides.drivers` - the analyst's last word on any driver.

Every disagreement between (1) and (2) above the tolerance is reported rather
than silently resolved.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rows as R  # noqa: E402

MONTHS = {m: i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
     "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}


# ------------------------------------------------------------ screener loading
def _find_parse_screener():
    """Prefer the equity-research-report parser when it is installed: it carries
    the learned Screener label aliases, so a label that broke once stays fixed."""
    for base in (os.path.expanduser("~/.claude/skills/equity-research-report/scripts"),
                 os.path.join(os.getcwd(), ".claude", "skills",
                              "equity-research-report", "scripts")):
        if os.path.isfile(os.path.join(base, "parse_screener.py")):
            sys.path.insert(0, base)
            try:
                import parse_screener  # noqa: F401
                return parse_screener, base
            except ImportError:
                sys.path.remove(base)
    return None, None


def _num(v):
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace(",", "").replace("%", "").replace("₹", "")
    if s in ("", "-", "--", "NA", "N/A", "nan"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _period(v):
    if isinstance(v, (dt.datetime, dt.date)):
        return v.strftime("%b-%y")
    s = str(v).strip()
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        return dt.date(int(m[1]), int(m[2]), int(m[3])).strftime("%b-%y")
    return s


BLOCKS = {
    "annual": re.compile(r"^\s*profit\s*&?\s*(and)?\s*loss", re.I),
    "quarterly": re.compile(r"^\s*quarter", re.I),
    "balance": re.compile(r"^\s*balance\s*sheet", re.I),
    "cashflow": re.compile(r"^\s*cash\s*flow", re.I),
    "derived": re.compile(r"^\s*derived", re.I),
    "price": re.compile(r"^\s*price", re.I),
}
STOP = re.compile(r"^\s*(profit\s*&|quarter|balance\s*sheet|cash\s*flow|derived|price)", re.I)


def _fallback_parse(path: str) -> dict:
    """A self-contained Screener reader, used when equity-research-report is absent."""
    try:
        import openpyxl
    except ImportError:
        sys.exit("openpyxl is required to read a Screener .xlsx: pip install openpyxl")
    wb = openpyxl.load_workbook(path, data_only=True)
    out = {"company": None, "meta": {}, "warnings": ["parsed without the "
           "equity-research-report alias table"]}
    for ws in wb.worksheets:
        grid = list(ws.iter_rows(values_only=True))
        if not grid:
            continue
        if out["company"] is None:
            for r in grid[:6]:
                for c in r or []:
                    if isinstance(c, str) and len(c.strip()) > 2 and not STOP.match(c):
                        out["company"] = c.strip()
                        break
                if out["company"]:
                    break
        for i, r in enumerate(grid):
            head = r[0] if r else None
            if not isinstance(head, str):
                continue
            for key, pat in BLOCKS.items():
                if pat.match(head.strip()):
                    blk = _read_block(grid, i)
                    if blk and len(blk) > len(out.get(key, {})):
                        out[key] = blk
    return out


def _read_block(grid, start) -> dict:
    periods, header_at = None, None
    for j in range(start, min(start + 6, len(grid))):
        vals = list((grid[j] or [])[1:])
        looks = [v for v in vals if isinstance(v, (dt.datetime, dt.date))
                 or (isinstance(v, str)
                     and re.match(r"^[A-Za-z]{3}[-\s]?\d{2,4}$|^\d{4}-\d{2}", v.strip()))]
        if len(looks) >= 3:
            periods = [_period(v) for v in vals if v not in (None, "")]
            header_at = j
            break
    if periods is None:
        return {}
    block = {"periods": periods}
    for j in range(header_at + 1, len(grid)):
        r = grid[j] or []
        head = r[0]
        if isinstance(head, str) and STOP.match(head.strip()):
            break
        if not isinstance(head, str) or not head.strip():
            if all(v is None for v in r[1:]) and j + 1 < len(grid) \
                    and all(v is None for v in (grid[j + 1] or [])):
                break
            continue
        vals = [_num(v) for v in r[1:1 + len(periods)]]
        if any(v is not None for v in vals):
            block[head.strip().rstrip(":")] = vals
    return block


def load_screener(path: str, notes: list) -> dict:
    if path.lower().endswith(".json"):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    mod, base = _find_parse_screener()
    if mod:
        notes.append(f"screener parsed with {base}/parse_screener.py (alias table applied)")
        return mod.parse(path)
    notes.append("screener parsed with the built-in fallback reader")
    return _fallback_parse(path)


# ----------------------------------------------------------- canonical actuals
def _pick(block: dict, *names):
    if not block:
        return None
    low = {k.lower().strip(): k for k in block}
    for n in names:
        if n.lower() in low:
            return block[low[n.lower()]]
    return None


def _sum_rows(block, names, n):
    got = [_pick(block, nm) for nm in names]
    got = [g for g in got if g]
    if not got:
        return None
    return [sum(v[i] for v in got if i < len(v) and v[i] is not None) or 0.0
            for i in range(n)]


def _al(series, n):
    """Align a series to n columns, padding with None."""
    if series is None:
        return [None] * n
    s = list(series)[:n]
    return s + [None] * (n - len(s))


def canonical(fin: dict, notes: list) -> tuple[list, dict]:
    """Screener blocks -> the model's line items, one list per row key."""
    a, b, c = fin.get("annual", {}), fin.get("balance", {}), fin.get("cashflow", {})
    pa, pb = a.get("periods", []), b.get("periods", [])
    periods = [p for p in pa if p in pb] if pb else list(pa)
    if not periods:
        sys.exit("no overlapping annual and balance-sheet periods in the export")
    ia = [pa.index(p) for p in periods]
    ib = [pb.index(p) for p in periods] if pb else ia
    pc = c.get("periods", [])
    ic = [pc.index(p) if p in pc else None for p in periods]
    n = len(periods)

    def A(*names):
        s = _pick(a, *names)
        return [None if s is None or i >= len(s) else s[i] for i in ia] if s else [None] * n

    def B(*names):
        s = _pick(b, *names)
        return [None if s is None or i >= len(s) else s[i] for i in ib] if s else [None] * n

    def C(*names):
        s = _pick(c, *names)
        if not s:
            return [None] * n
        return [None if i is None or i >= len(s) else s[i] for i in ic]

    v = {}
    v["revenue"] = A("Sales", "Revenue", "Net Sales", "Sales +")
    v["ebitda"] = A("Operating Profit", "EBITDA")
    v["dep_charge"] = A("Depreciation")
    v["other_income"] = A("Other Income")
    v["interest_expense"] = A("Interest")
    v["pbt"] = A("Profit before tax", "PBT")
    v["pat"] = A("Net profit", "Net Profit", "Profit after tax", "PAT")
    v["exceptional"] = A("Exceptional Items", "Extraordinary Items", "Exceptional items")
    v["dividends"] = A("Dividend Amount", "Dividends", "Dividend")

    # Tax struck as PBT - PAT is exact where reported tax is a rate or is missing.
    rep_tax = A("Tax")
    v["tax"] = [None if (p is None or q is None) else p - q
                for p, q in zip(v["pbt"], v["pat"])]
    if any(t is None for t in v["tax"]) and any(t is not None for t in rep_tax):
        v["tax"] = [t if t is not None else r for t, r in zip(v["tax"], rep_tax)]

    # Cost of goods: material and manufacturing lines when the export carries them.
    cogs = _sum_rows({k: [x for x in (_al(vv, len(pa)))] for k, vv in a.items()
                      if k != "periods"},
                     ["Raw Material Cost", "Change in Inventory", "Power and Fuel",
                      "Other Mfr. Exp", "Cost of Materials Consumed",
                      "Purchase of Stock-in-Trade"], len(pa))
    if cogs is not None and any(x for x in cogs):
        v["cogs"] = [cogs[i] if i < len(cogs) else None for i in ia]
    else:
        v["cogs"] = [None if (s is None or e is None) else s - e
                     for s, e in zip(v["revenue"], v["ebitda"])]
        notes.append("no expense detail in the source: COGS set to revenue less EBITDA, "
                     "so gross margin equals EBITDA margin and opex is zero")

    v["share_capital"] = B("Equity Share Capital", "Share Capital")
    v["reserves"] = B("Reserves")
    v["term_debt"] = B("Borrowings")
    v["revolver"] = [0.0] * n
    v["net_block"] = B("Net Block", "Fixed Assets")
    v["cwip"] = B("Capital Work in Progress", "CWIP")
    v["investments"] = B("Investments")
    v["receivables"] = B("Receivables", "Trade Receivables")
    v["inventory"] = B("Inventory", "Inventories")
    v["cash"] = B("Cash & Bank", "Cash and Bank", "Cash")
    v["shares"] = B("Adjusted Equity Shares in Cr", "No. of Equity Shares",
                    "Number of Shares")

    other_assets = B("Other Assets")
    other_liabs = B("Other Liabilities")
    v["payables"] = [0.0] * n            # Screener does not carry trade payables
    v["other_ca"] = [None if oa is None else
                     oa - (r or 0) - (i or 0) - (ch or 0)
                     for oa, r, i, ch in zip(other_assets, v["receivables"],
                                             v["inventory"], v["cash"])]
    v["other_liab"] = list(other_liabs)
    v["rep_cfo"] = C("Cash from Operating Activity", "Cash Flow from Operations", "CFO")
    v["rep_cfi"] = C("Cash from Investing Activity", "CFI")
    v["rep_cff"] = C("Cash from Financing Activity", "CFF")

    # Capex is not disclosed in the export: back it out of the net block roll.
    v["capex"] = [None] + [
        None if (nb1 is None or nb0 is None or d is None) else nb1 - nb0 + d
        for nb0, nb1, d in zip(v["net_block"], v["net_block"][1:], v["dep_charge"][1:])]

    for k in list(v):
        v[k] = _al(v[k], n)
    return periods, v


# ---------------------------------------------------------------- assumptions
# Drivers expressed as a rate. assumptions.json values go through _rate(); anything
# arriving via overrides.drivers must too, or a gross_margin of 98.7 is read as 98.7x
# rather than 98.7%. On a port that drove payables to -327,000 Cr and PAT negative,
# and the model still reported "circular solve converged".
RATE_DRIVERS = {
    "rev_growth", "ebitda_margin", "gross_margin", "capex_pct_sales",
    "dep_pct_sales", "tax_rate", "cost_of_debt", "payout_ratio", "debt_growth",
    "other_income_pct", "dep_pct_nb", "cwip_pct_sales", "other_ca_pct",
    "other_liab_pct", "interest_income_rate", "term_debt_repay",
}


def _rate(x):
    """Accept 12.0 or 0.12 and return a decimal."""
    if x is None:
        return None
    if isinstance(x, list):
        return [_rate(i) for i in x]
    try:
        f = float(x)
    except (TypeError, ValueError):
        return None
    return f / 100.0 if abs(f) > 1.5 else f


def _plain(x):
    if isinstance(x, list):
        return [_plain(i) for i in x]
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def drivers_from_assumptions(asm: dict, notes: list) -> dict:
    """assumptions.json -> forecast driver values. Unmapped drivers stay None and
    are filled from history by build_model.py."""
    if not asm:
        return {}
    an = asm.get("_analyst", {}) or {}

    def get(*keys):
        for k in keys:
            if k in asm and asm[k] is not None:
                return asm[k]
            if k in an and an[k] is not None:
                return an[k]
        return None

    out = {}
    out["rev_growth"] = _rate(get("revenue_growth"))
    def _add_paths(a, b):
        """Add two drivers that may each be a scalar or a per-year path.

        Both being lists is the normal case — `financial-model-assumptions` emits
        per-year paths for margin and depreciation alike. A shorter path is held
        flat at its last value rather than truncating the longer one.
        """
        la, lb = isinstance(a, list), isinstance(b, list)
        if not la and not lb:
            return a + b
        if la and not lb:
            return [x + b for x in a]
        if lb and not la:
            return [a + x for x in b]
        n = max(len(a), len(b))
        return [(a[min(i, len(a) - 1)] + b[min(i, len(b) - 1)]) for i in range(n)]

    out["ebitda_margin"] = _rate(get("ebitda_margin"))
    out["gross_margin"] = _rate(get("gross_margin"))
    out["capex_pct_sales"] = _rate(get("capex_pct_sales"))
    out["dep_pct_sales"] = _rate(get("dep_pct_sales"))
    out["tax_rate"] = _rate(get("tax_rate", "effective_tax_rate"))
    out["cost_of_debt"] = _rate(get("cost_of_debt", "interest_rate"))
    out["payout_ratio"] = _rate(get("dividend_payout", "payout_ratio"))
    out["dso"] = _plain(get("dso"))
    out["dio"] = _plain(get("dio"))
    out["dpo"] = _plain(get("dpo"))
    out["debt_growth"] = _rate(get("debt_growth"))
    out["min_cash"] = _plain(get("min_cash"))

    if out.get("ebitda_margin") is None:
        em, dp = _rate(get("ebit_margin")), out.get("dep_pct_sales")
        if em is not None and dp is not None:
            out["ebitda_margin"] = _add_paths(em, dp)
            notes.append("EBITDA margin derived as EBIT margin plus depreciation % sales")
    if out.get("gross_margin") is None and out.get("ebitda_margin") is not None:
        out["gross_margin"] = out["ebitda_margin"]
        notes.append("no gross margin in assumptions.json: set equal to the EBITDA "
                     "margin, which zeroes the opex line")

    return {k: v for k, v in out.items() if v is not None}


# ------------------------------------------------------------------- overrides
def apply_overrides(periods, vals, ov, notes, tol=0.02):
    """Merge annual-report actuals over the Screener spine and report conflicts."""
    recon, applied = [], set()
    for key, by_period in (ov.get("actuals") or {}).items():
        if key.startswith("_"):
            continue                     # template commentary
        if key not in R.BY_KEY:
            notes.append(f"overrides.actuals: unknown row '{key}' ignored")
            continue
        for p, new in by_period.items():
            if _num(new) is None:
                continue                 # an unfilled placeholder, not an override
            if p not in periods:
                notes.append(f"overrides.actuals.{key}: period '{p}' is not in the "
                             "historical range, ignored")
                continue
            j = periods.index(p)
            old = vals.get(key, [None] * len(periods))[j]
            new = _num(new)
            if old is not None and new is not None and old != 0:
                diff = abs(new - old) / abs(old)
                if diff > tol:
                    recon.append({"row": key, "period": p, "screener": old,
                                  "annual_report": new,
                                  "diff_pct": round(diff * 100, 2)})
            vals.setdefault(key, [None] * len(periods))[j] = new
            applied.add(key)

    # Trade payables coming in from the annual report must come out of other_liab,
    # or the balance sheet stops tying to the source.
    if "payables" in applied:
        for j, _ in enumerate(periods):
            pay = vals["payables"][j]
            if pay and vals.get("other_liab", [None])[j] is not None:
                vals["other_liab"][j] -= pay
        notes.append("trade payables supplied from the annual report were netted out "
                     "of other liabilities so the balance sheet still ties")
    return recon


# ------------------------------------------------------------------ forecast
def forecast_periods(last: str, n: int) -> list:
    m = re.match(r"^([A-Za-z]{3})-(\d{2,4})$", str(last).strip())
    if not m:
        return [f"F{i + 1}E" for i in range(n)]
    mon, yr = m[1], int(m[2])
    yr += 2000 if yr < 100 else 0
    return [f"{mon}-{str(yr + i + 1)[-2:]}E" for i in range(n)]


# --------------------------------------------------------------- strategy gate
# What this skill can execute. rows.py defines ONE revenue row,
# prev(revenue)*(1+rev_growth) — there are no segment rows and no driver
# build-up rows. Any approved architecture beyond that must arrive already
# translated into a consolidated growth path, or be refused. It is never
# flattened silently.
FM_CAPABILITY = "consolidated_growth_only"


def _load_gate():
    """Import check_strategy.py from the `modeling-strategy` skill."""
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


def capability_check(strategy: dict, asm: dict) -> list[str]:
    """Can this skill actually build the approved architecture? Refusals only.

    Returns a list of unsupported requirements. A non-empty list means STOP and
    report — never substitute a generic model for an approved one.
    """
    refuse: list[str] = []
    arch = strategy.get("model_architecture") or {}
    ex = arch.get("execution") or {}

    for u in ex.get("unsupported_requirements") or []:
        refuse.append(u)

    declared = ex.get("financial_model_capability")
    if declared and declared != FM_CAPABILITY:
        refuse.append(
            f"the strategy was built against financial-model capability "
            f"{declared!r}; this build supports {FM_CAPABILITY!r}")

    if arch.get("revenue_model") in ("segment_buildup", "consolidated_buildup"):
        if not ex.get("consolidated_growth_is_derived"):
            refuse.append(
                f"revenue_model is {arch['revenue_model']!r} but the strategy does "
                "not declare a derivation into a consolidated growth path")
        src = (asm.get("_strategy") or {}).get("revenue_growth_source")
        if not src:
            refuse.append(
                f"revenue_model is {arch['revenue_model']!r}, so revenue_growth must "
                "come from segment_build.py via "
                "`build_assumptions.py --segment-build`. assumptions.json carries no "
                "such provenance, which means the segment economics never reached "
                "this model. Refusing rather than modelling one growth rate and "
                "calling it a segment build.")
    return refuse


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--screener", required=True, help="Screener .xlsx or a parsed .json")
    ap.add_argument("--assumptions", help="assumptions.json from financial-model-assumptions")
    ap.add_argument("--overrides", help="annual-report actuals and driver overrides")
    ap.add_argument("--hist-years", type=int, default=10)
    ap.add_argument("--forecast-years", type=int, default=5)
    ap.add_argument("--dep-basis", choices=["net_block", "sales"], default="net_block")
    ap.add_argument("--avg-years", type=int, default=3,
                    help="trailing years averaged to fill a driver history cannot skip")
    ap.add_argument("-o", "--out", default="data/model_input.json")
    ap.add_argument("--strategy", help="model_strategy.json from the modeling-strategy "
                                       "skill. Optional: without it this script "
                                       "behaves exactly as before.")
    args = ap.parse_args()

    notes: list[str] = []
    fin = load_screener(args.screener, notes)
    periods, vals = canonical(fin, notes)

    if args.hist_years and len(periods) > args.hist_years:
        cut = len(periods) - args.hist_years
        periods = periods[cut:]
        vals = {k: v[cut:] for k, v in vals.items()}

    ov = {}
    if args.overrides:
        with open(args.overrides, encoding="utf-8") as f:
            ov = json.load(f)
    recon = apply_overrides(periods, vals, ov, notes)
    if not any(vals.get("payables") or []):
        notes.append("a Screener export does not carry trade payables and none were "
                     "supplied: payable days read zero, which overstates net "
                     "operating assets. Pull them from the annual report with "
                     "ar_tables.py find --for payables")

    asm = {}
    if args.assumptions:
        with open(args.assumptions, encoding="utf-8") as f:
            asm = json.load(f)
    drv = drivers_from_assumptions(asm, notes)
    for k, v in (ov.get("drivers") or {}).items():
        if v is None or k.startswith("_"):
            continue
        if k in RATE_DRIVERS:
            before, v = v, _rate(v)
            if isinstance(before, (int, float)) and abs(float(before)) > 1.5:
                notes.append(f"overrides.drivers['{k}'] read as a percentage: "
                             f"{before} -> {v}")
        drv[k] = v

    strategy = None
    if args.strategy:
        with open(args.strategy, encoding="utf-8") as f:
            strategy = json.load(f)
        gate = _load_gate()
        ok, why = gate.gate_ok(strategy, require_approved=True)
        if not ok:
            print(f"REFUSED: {why}", file=sys.stderr)
            print("         The modeling strategy decides what is being modelled; "
                  "this skill only executes it.", file=sys.stderr)
            return 3
        refuse = capability_check(strategy, asm)
        # A driver the approved architecture depends on must not quietly become a
        # trailing historical average. That is the silent fallback this refuses.
        for k in ("rev_growth", "ebitda_margin", "capex_pct_sales"):
            if k not in drv:
                refuse.append(
                    f"driver '{k}' is required by the approved architecture but is "
                    "absent from the assumption set; it would be held at the "
                    "historical average, which is a different model from the one "
                    "that was approved")
        if refuse:
            print("REFUSED: the approved modeling architecture cannot be executed "
                  "by this skill.", file=sys.stderr)
            for r in refuse:
                print(f"  - {r}", file=sys.stderr)
            print("\n  Not falling back to a generic model. Resolve the requirement, "
                  "or revise the strategy and re-approve it.", file=sys.stderr)
            return 4
        notes.append(
            f"built against modeling strategy: revenue_model="
            f"{(strategy.get('model_architecture') or {}).get('revenue_model')}, "
            f"modelability={(strategy.get('modelability') or {}).get('status')}, "
            f"decision={(strategy.get('analyst_decision') or {}).get('status')}")
    else:
        notes.append("no modeling strategy supplied (--strategy): the business "
                     "architecture behind these drivers is not recorded")

    unknown = [k for k in drv if k not in R.BY_KEY]
    for k in unknown:
        notes.append(f"driver '{k}' is not in the model, ignored")
        drv.pop(k)

    opts = {"dep_basis": args.dep_basis, "avg_years": args.avg_years}
    opts.update(ov.get("options") or {})
    fyears = int((ov.get("options") or {}).get("forecast_years", args.forecast_years))

    doc = {
        "company": fin.get("company") or asm.get("company") or "Company",
        "currency": asm.get("currency") or "INR cr",
        "sector": asm.get("sector") or (asm.get("_analyst", {}) or {}).get("sector"),
        "built": dt.date.today().isoformat(),
        "hist_periods": periods,
        "fcst_periods": forecast_periods(periods[-1], fyears),
        "actuals": vals,
        "drivers": drv,
        "driver_sources": {k: ("overrides" if k in (ov.get("drivers") or {})
                               else "assumptions") for k in drv},
        "citations": ov.get("citations") or {},
        "strategy_ref": ({
            "revenue_model": (strategy.get("model_architecture") or {}).get("revenue_model"),
            "modelability": (strategy.get("modelability") or {}).get("status"),
            "analyst_decision": (strategy.get("analyst_decision") or {}).get("status"),
            "revenue_growth_source": (asm.get("_strategy") or {}).get(
                "revenue_growth_source"),
        } if strategy else None),
        "options": opts,
        "reconciliation": recon,
        "notes": notes + list(fin.get("warnings") or []),
    }

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=1)

    print(f"company    : {doc['company']}  ({doc['currency']})")
    print(f"history    : {len(periods)}y  {periods[0]} .. {periods[-1]}")
    print(f"forecast   : {fyears}y  {doc['fcst_periods'][0]} .. {doc['fcst_periods'][-1]}")
    have = [k for k in R.ACTUAL_KEYS if any(x is not None for x in vals.get(k, []))]
    print(f"actuals    : {len(have)}/{len(R.ACTUAL_KEYS)} line items populated")
    missing = [k for k in R.ACTUAL_KEYS if k not in have]
    if missing:
        print(f"  missing  : {', '.join(missing)}")
    print(f"drivers    : {len(drv)}/{len(R.DRIVER_KEYS)} set from sources; "
          f"{len(R.DRIVER_KEYS) - len(drv)} will be held at the "
          f"{opts['avg_years']}y historical average")
    if recon:
        print(f"\n! {len(recon)} Screener / annual-report disagreement(s) above 2%:")
        for d in recon[:12]:
            print(f"    {d['row']:<16} {d['period']:<8} screener {d['screener']:>12,.1f}"
                  f"   annual report {d['annual_report']:>12,.1f}"
                  f"   ({d['diff_pct']}%)")
    for w in doc["notes"]:
        print(f"  ! {w}")
    print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
