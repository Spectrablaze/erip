#!/usr/bin/env python3
"""
parse_screener.py — turn a Screener.in Excel export into normalised JSON.

    python3 parse_screener.py <export.xlsx> -o data/financials.json

The Screener "Export to Excel" file is one sheet ("Data Sheet") containing
labelled blocks: PROFIT & LOSS / Quarters / BALANCE SHEET / CASH FLOW / DERIVED /
PRICE. This parser scans every sheet for those block markers instead of relying on
fixed row numbers, so it survives Screener's periodic layout changes.

Output shape:
{
  "company": "Eicher Motors Ltd",
  "meta": {"face_value": 1.0, "current_price": 7312.0, ...},
  "annual":   {"periods": ["Mar-17", ...], "Sales": [...], "Net profit": [...], ...},
  "quarterly":{"periods": ["Jun-24", ...], "Sales": [...], ...},
  "balance":  {"periods": [...], "Reserves": [...], ...},
  "cashflow": {"periods": [...], "Cash from Operating Activity": [...], ...},
  "price":    {"periods": ["Mar-24", ...], "Price": [...]},
  "warnings": ["..."]
}
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys

try:
    import openpyxl
except ImportError:
    sys.exit("pip install openpyxl --break-system-packages")

BLOCKS = {
    "annual":    re.compile(r"^\s*profit\s*&?\s*(and)?\s*loss", re.I),
    "quarterly": re.compile(r"^\s*quarter", re.I),
    "balance":   re.compile(r"^\s*balance\s*sheet", re.I),
    "cashflow":  re.compile(r"^\s*cash\s*flow", re.I),
    "derived":   re.compile(r"^\s*derived", re.I),
    "price":     re.compile(r"^\s*price", re.I),
}
STOP = re.compile(r"^\s*(profit\s*&|quarter|balance\s*sheet|cash\s*flow|derived|price)", re.I)
# The price series row, whatever Screener happens to label it.
PRICE_ROW = re.compile(r"price|close|adj", re.I)


def _starts_other_block(head: str, key: str) -> bool:
    """True when this row label opens a block *other than* the one being read.

    A block must not be stopped by its own marker. The PRICE block's data row is
    itself labelled "Price", so a blanket stop test ends that block on its first
    data row and returns nothing but `periods`.
    """
    h = head.strip()
    return any(pat.match(h) for k, pat in BLOCKS.items() if k != key)


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
    """Normalise a period header to 'Mar-24' / 'Jun-25'."""
    if isinstance(v, (dt.datetime, dt.date)):
        return v.strftime("%b-%y")
    s = str(v).strip()
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        return dt.date(int(m[1]), int(m[2]), int(m[3])).strftime("%b-%y")
    return s


def _date_label(v):
    """Strict date detector -> a 'Mar-24' label, or None when it is not a date.

    `_period` normalises but never rejects — it hands back anything it does not
    recognise — so it cannot be used to decide whether a cell is a date at all.
    """
    if isinstance(v, (dt.datetime, dt.date)):
        return v.strftime("%b-%y")
    if not isinstance(v, str):
        return None
    s = v.strip()
    if re.match(r"^[A-Za-z]{3}[-\s]?\d{2,4}$", s):
        return s
    m = re.match(r"^(\d{4})-(\d{1,2})$", s)
    if m:
        return dt.date(int(m[1]), int(m[2]), 1).strftime("%b-%y")
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d-%b-%Y", "%d-%b-%y", "%Y/%m/%d"):
        try:
            return dt.datetime.strptime(s[:10], fmt).strftime("%b-%y")
        except ValueError:
            continue
    return None


def _rows(ws):
    return list(ws.iter_rows(values_only=True))


def _name_case(raw: str) -> str:
    """Screener writes names in capitals. Title-case them, but keep short acronyms (JSW, NMDC)
    upper and minor words lower: 'JSW INFRASTRUCTURE LTD' -> 'JSW Infrastructure Ltd'."""
    minor, words = {"OF", "AND", "THE", "&", "FOR", "IN"}, raw.strip().split()
    out = []
    for i, wd in enumerate(words):
        u = wd.upper()
        if u in ("LTD", "LTD."):
            out.append("Ltd")
        elif u in minor and i:
            out.append(wd.lower() if u != "&" else "&")
        elif wd.isupper() and wd.isalpha() and (len(wd) <= 3 or not any(v in u for v in "AEIOU")):
            out.append(wd)
        else:
            out.append(wd.capitalize())
    return " ".join(out)


def parse(path: str, root: str | None = None) -> dict:
    wb = openpyxl.load_workbook(path, data_only=True)
    out = {"company": None, "meta": {}, "warnings": []}

    # Screener exports carry an explicit "COMPANY NAME" row on the Data Sheet. Prefer it:
    # the first-non-empty-cell heuristic below reads v2.1 exports as "Years".
    for ws in wb.worksheets:
        for r in _rows(ws)[:10]:
            if r and isinstance(r[0], str) and r[0].strip().upper() == "COMPANY NAME":
                nm = next((c for c in r[1:] if isinstance(c, str) and c.strip()), None)
                if nm:
                    out["company"] = _name_case(nm)
                break
        if out["company"]:
            break

    for ws in wb.worksheets:
        rows = _rows(ws)
        if not rows:
            continue

        # Company name = first non-empty cell in the sheet
        if out["company"] is None:
            for r in rows[:6]:
                for c in r or []:
                    if isinstance(c, str) and len(c.strip()) > 2 and not STOP.match(c):
                        out["company"] = c.strip()
                        break
                if out["company"]:
                    break

        # Loose key:value metadata anywhere on the sheet (Face Value, Current Price...)
        for r in rows:
            if not r or not isinstance(r[0], str):
                continue
            k = r[0].strip().rstrip(":").lower()
            if k in ("face value", "current price", "market capitalization", "market cap",
                     "number of shares", "no. of shares", "promoter holding"):
                v = next((_num(x) for x in r[1:] if _num(x) is not None), None)
                if v is not None:
                    out["meta"][k.replace(" ", "_")] = v

        # Labelled blocks
        for i, r in enumerate(rows):
            head = r[0] if r else None
            if not isinstance(head, str):
                continue
            for key, pat in BLOCKS.items():
                if not pat.match(head.strip()):
                    continue
                block = _read_block(rows, i, key)
                if block and (key not in out or len(block) > len(out.get(key, {}))):
                    out[key] = block

    _post(out, root)
    return out


def _read_block(rows, start, key: str = "") -> dict:
    """Read a block: find its period header row, then every labelled data row below.

    `key` is the block being read, so its own marker does not terminate it.
    """
    periods, header_at = None, None
    for j in range(start, min(start + 6, len(rows))):
        r = rows[j] or []
        vals = list(r[1:])
        # A header row: >=3 cells and mostly dates / period-looking strings
        looks = [v for v in vals if _date_label(v)]
        if len(looks) >= 3:
            periods = [_period(v) for v in vals if v not in (None, "")]
            header_at = j
            break
    if periods is None:
        # Screener also ships the price section as a Date/Price column pair
        # running down the sheet, which has no header row of dates at all.
        return _read_vertical(rows, start) if key == "price" else {}

    block = {"periods": periods}
    for j in range(header_at + 1, len(rows)):
        r = rows[j] or []
        head = r[0]
        if isinstance(head, str) and _starts_other_block(head, key):
            break
        if not isinstance(head, str) or not head.strip():
            if all(v is None for v in r[1:]):
                # two consecutive blank rows end the block
                if j + 1 < len(rows) and all(v is None for v in (rows[j + 1] or [])):
                    break
            continue
        vals = [_num(v) for v in r[1:1 + len(periods)]]
        if any(v is not None for v in vals):
            block[head.strip().rstrip(":")] = vals
    return block


def _read_vertical(rows, start) -> dict:
    """Read a Date/Price column pair running down the sheet, oldest first.

    Returned in the same shape as every other block, so callers do not have to
    know which of Screener's two price layouts the export happened to use.
    """
    periods, closes, blanks = [], [], 0
    for j in range(start + 1, len(rows)):
        r = rows[j] or []
        lab = _date_label(r[0]) if r else None
        val = next((_num(v) for v in r[1:4] if _num(v) is not None), None) \
            if len(r) > 1 else None
        if lab and val is not None:
            periods.append(lab)
            closes.append(val)
            blanks = 0
        else:
            blanks += 1
            # A run of unusable rows means the section has ended. Tolerated up
            # to 8 so a mid-series gap or a spacer row does not truncate it.
            if blanks > 8 and periods:
                break
    if len(periods) < 3:
        return {}
    return {"periods": periods, "Price": closes}


ALIASES = {
    "Sales": ["Sales", "Revenue", "Net Sales", "Sales +"],
    "Net profit": ["Net profit", "Net Profit", "Profit after tax", "PAT"],
    "Operating Profit": ["Operating Profit", "EBITDA"],
    "Depreciation": ["Depreciation"],
    "Interest": ["Interest"],
    "Tax": ["Tax"],
    "Profit before tax": ["Profit before tax", "PBT"],
    "Reserves": ["Reserves"],
    "Borrowings": ["Borrowings"],
    "Equity Share Capital": ["Equity Share Capital", "Share Capital"],
    "Net Block": ["Net Block", "Fixed Assets"],
    "Inventory": ["Inventory", "Inventories"],
    "Receivables": ["Receivables", "Trade Receivables"],
    "Cash & Bank": ["Cash & Bank", "Cash and Bank", "Cash"],
    "Cash from Operating Activity": ["Cash from Operating Activity", "Cash Flow from Operations", "CFO"],
    "Cash from Investing Activity": ["Cash from Investing Activity", "CFI"],
    "Cash from Financing Activity": ["Cash from Financing Activity", "CFF"],
}


def learned_aliases(root: str | None = None) -> dict:
    """Screener labels taught via `kb.py alias`, merged over the built-in table.

    This is the mechanical half of the skill's learning loop: a label that broke
    the parser once is recognised on every later run, in every report, without
    editing this file.
    """
    if not root:
        root = os.environ.get("EQR_REPORTS_ROOT", "reports")
    path = os.path.join(root, "_knowledge", "aliases.json")
    if not os.path.exists(path):
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _canon(block: dict, extra: dict | None = None) -> dict:
    """Add canonical keys pointing at whatever alias Screener actually used."""
    if not block:
        return block
    table = {k: list(v) for k, v in ALIASES.items()}
    for canon, names in (extra or {}).items():
        table.setdefault(canon, [])
        table[canon].extend(n for n in names if n not in table[canon])

    lower = {k.lower(): k for k in block}
    for canon, names in table.items():
        if canon in block:
            continue
        for n in names:
            if n.lower() in lower:
                block[canon] = block[lower[n.lower()]]
                break
    return block


def _post(out: dict, root: str | None = None) -> None:
    extra = learned_aliases(root)
    if extra:
        out["warnings"].append(
            f"applied {sum(len(v) for v in extra.values())} learned alias(es) from the "
            "knowledge base")
    for k in ("annual", "quarterly", "balance", "cashflow", "derived"):
        if k in out:
            out[k] = _canon(out[k], extra)
        else:
            out["warnings"].append(f"block '{k}' not found in the export")

    # Derive the essentials the report always needs
    a, b = out.get("annual", {}), out.get("balance", {})
    if a.get("Sales") and a.get("Operating Profit"):
        out.setdefault("derived", {})["EBITDA Margin %"] = [
            None if not s else round(o / s * 100, 2)
            for s, o in zip(a["Sales"], a["Operating Profit"])]
    if a.get("Net profit") and b.get("Adjusted Equity Shares in Cr"):
        out.setdefault("derived", {})["EPS"] = [
            None if not sh else round(np / sh, 2)
            for np, sh in zip(a["Net profit"], b["Adjusted Equity Shares in Cr"])]

    # Screener labels the series row "Price", "Close", "Adjusted Price"... —
    # republish it under the canonical "Price" so callers need one key, not a regex.
    price = out.get("price") or {}
    if price:
        out["price"] = {"periods": price.get("periods", []),
                        **{k: v for k, v in price.items() if k != "periods"}}
        row = next((k for k in price if k != "periods" and PRICE_ROW.search(k)), None)
        if row:
            out["price"]["Price"] = price[row]
        else:
            out["warnings"].append(
                "price block found but no price series row inside it")
    else:
        out["warnings"].append("block 'price' not found in the export")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("xlsx")
    ap.add_argument("-o", "--out", default="data/financials.json")
    ap.add_argument("--root", default=None,
                    help="reports root holding _knowledge/ (default: $EQR_REPORTS_ROOT or ./reports)")
    args = ap.parse_args()

    data = parse(args.xlsx, args.root)
    import os
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    json.dump(data, open(args.out, "w"), indent=1, default=str)

    print(f"company : {data['company']}")
    for k in ("annual", "quarterly", "balance", "cashflow", "derived"):
        blk = data.get(k) or {}
        n = len(blk.get("periods", []))
        print(f"{k:<10}: {len(blk) - 1 if blk else 0:>3} line items x {n} periods"
              + (f"  [{blk['periods'][0]} .. {blk['periods'][-1]}]" if n else ""))
    p = data.get("price") or {}
    pn = len(p.get("periods", []))
    print(f"{'price':<10}: {pn:>3} observations"
          + (f"  [{p['periods'][0]} .. {p['periods'][-1]}]" if pn else ""))
    for w in data["warnings"]:
        print(f"  ! {w}")
    print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
