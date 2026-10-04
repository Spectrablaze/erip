#!/usr/bin/env python3
"""
build_comps.py — peers_raw.json -> peers.json (+ comps.md), model.py-ready

    python3 build_comps.py data/peers_raw.json -o data/peers.json --md data/comps.md
    python3 build_comps.py data/peers_raw.json --betas data/peer_betas.json \
        --patch-decisions data/decisions.json

Strikes the market cap, the enterprise-value bridge and the trailing multiples for the
subject and every peer, on one basis and one date, and emits the `peers` array that
`model.py`'s `relative()` consumes verbatim — subject first, as that function requires.

Three things this file refuses to do quietly:

  * mix reporting bases                — hard error
  * align mismatched fiscal calendars  — flagged, never adjusted
  * median a meaningless multiple      — a peer whose denominator is <= 0 has that one
                                         multiple emitted as null, so the downstream
                                         median skips it instead of averaging in a
                                         negative P/E

The enterprise-value bridge is the part most often got wrong from a Screener export.
See references/multiples.md before overriding anything.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys

MULT_KEYS = ["P/E (x)", "EV/EBITDA (x)", "EV/Sales (x)", "P/B (x)", "ROE (%)"]


# --------------------------------------------------------------- arithmetic
def div(a, b):
    """Guarded divide. None whenever the multiple would be meaningless."""
    if a is None or b in (None, 0):
        return None
    try:
        return float(a) / float(b)
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def pct(vals, q):
    """Linear-interpolated percentile of a list, q in [0,1]. None if empty."""
    v = sorted(x for x in vals if x is not None)
    if not v:
        return None
    if len(v) == 1:
        return v[0]
    pos = q * (len(v) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(v) - 1)
    return v[lo] + (v[hi] - v[lo]) * (pos - lo)


def median(vals):
    return pct(vals, 0.5)


def r1(x):
    return None if x is None else round(x, 1)


# --------------------------------------------------------------- per-company build
def build_one(c: dict, roe_on_average: bool, suppress_ev: bool) -> dict:
    """Market cap, EV bridge and the raw comparables for one company."""
    d = {
        "name": c["name"], "ticker": c.get("ticker"),
        "basis": c.get("basis"), "basis_source": c.get("basis_source"),
        "fy_end_label": c.get("fy_end_label"), "fy_end_month": c.get("fy_end_month"),
        "window": c.get("window"), "bs_period": c.get("bs_period"),
        "price": c.get("price"), "price_basis": c.get("price_basis"),
        "sales": c.get("sales"), "ebitda": c.get("ebitda"), "pat": c.get("pat"),
        "bv": c.get("bv"), "shares_cr": c.get("shares_cr"),
        "notes": [],
    }

    # ---- market cap ---------------------------------------------------------
    d["mcap"] = None
    if c.get("price") is not None and c.get("shares_cr"):
        d["mcap"] = float(c["price"]) * float(c["shares_cr"])

    # ---- enterprise value ---------------------------------------------------
    # Screener's "Investments" mixes surplus liquidity with strategic and
    # subsidiary holdings, so netting all of it out overstates cash. Only an
    # explicit `surplus_investments` override is netted; see references/multiples.md.
    borrow = c.get("borrowings") or 0.0
    cash = c.get("cash") or 0.0
    surplus = c.get("surplus_investments")
    mi = c.get("minority_interest") or 0.0
    pref = c.get("preference_capital") or 0.0

    net_debt = borrow - cash - (surplus or 0.0)
    d["net_debt"] = net_debt
    d["ev_bridge"] = {
        "market cap": d["mcap"], "+ borrowings": borrow, "- cash & bank": -cash,
        "- surplus investments": -(surplus or 0.0),
        "+ minority interest": mi, "+ preference capital": pref,
    }
    d["ev"] = None if d["mcap"] is None else d["mcap"] + net_debt + mi + pref

    if surplus is None and (c.get("investments") or 0) > 0:
        d["notes"].append(
            f"holds {c['investments']:,.0f} cr of Investments that were NOT netted from "
            "EV; set surplus_investments in the manifest for the genuinely surplus part")
    if mi == 0 and c.get("basis") == "consolidated":
        d["notes"].append(
            "consolidated EV carries no minority interest — Screener does not export it; "
            "add minority_interest from the balance sheet if the subsidiaries are "
            "materially not wholly owned")

    # ---- ROE, computed the same way for everyone ---------------------------
    if roe_on_average and c.get("bv") is not None and c.get("bv_prior") is not None:
        denom = (c["bv"] + c["bv_prior"]) / 2
        d["roe_basis"] = "average net worth"
    else:
        denom = c.get("bv")
        d["roe_basis"] = "closing net worth"
    roe = div(c.get("pat"), denom)
    d["roe"] = None if roe is None else round(roe * 100, 1)

    # ---- multiples ----------------------------------------------------------
    d["multiples"] = {
        "P/E (x)": r1(div(d["mcap"], c.get("pat"))),
        "EV/EBITDA (x)": None if suppress_ev else r1(div(d["ev"], c.get("ebitda"))),
        "EV/Sales (x)": None if suppress_ev else r1(div(d["ev"], c.get("sales"))),
        "P/B (x)": r1(div(d["mcap"], c.get("bv"))),
        "ROE (%)": d["roe"],
    }
    m = div(c.get("ebitda"), c.get("sales"))
    d["ebitda_margin"] = None if m is None else round(m * 100, 1)

    # ---- meaningfulness -----------------------------------------------------
    nm = []
    if (c.get("pat") or 0) <= 0:
        nm.append("P/E")
    if (c.get("ebitda") or 0) <= 0:
        nm.append("EV/EBITDA")
    if (c.get("bv") or 0) <= 0:
        nm.append("P/B")
    d["not_meaningful"] = nm

    d["forward"] = c.get("forward")
    d["market"] = c.get("market")
    d["warnings"] = list(c.get("warnings") or [])
    return d


# --------------------------------------------------------------- second source
# Tolerances are deliberately loose. The two sources have different definitions and
# different as-of dates, so a tight threshold would flag every company every time and
# train the reader to ignore flags. These catch "wrong ticker / wrong company / wrong
# basis", which is what a second source is actually for.
TOL = {"market cap": 0.03, "revenue": 0.10, "net debt": 0.25}


def crosscheck(details: list) -> list:
    """Compare the export-derived figures against the market feed, where present."""
    flags = []
    for d in details:
        m = d.get("market") or {}
        if not m:
            continue

        pairs = [
            # Both sides use the same price, so this really tests the SHARE COUNT —
            # which catches a stale count, a bonus issue or a split the export missed.
            ("market cap", d.get("mcap"), m.get("market_cap")),
            ("revenue", d.get("sales"), m.get("revenue")),
            ("net debt", d.get("net_debt"), m.get("net_debt")),
        ]
        for label, ours, theirs in pairs:
            if ours is None or theirs is None:
                continue
            base = max(abs(ours), abs(theirs))
            if base == 0:
                continue
            gap = abs(ours - theirs) / base
            if gap <= TOL[label]:
                continue
            sev = "high" if gap > 2 * TOL[label] else "medium"
            extra = ""
            if label == "revenue":
                extra = (" Windows differ (the export is TTM, the feed is the last "
                         "full year), so some gap is expected — but a large one "
                         "usually means the wrong ticker or a standalone/consolidated "
                         "mismatch.")
            if label == "market cap":
                extra = (" Both sides use the same price, so this is a share-count "
                         "disagreement — check for a bonus issue or split.")
            flags.append({
                "severity": sev, "kind": "crosscheck",
                "message": f"{d['name']}: {label} disagrees with the market feed — "
                           f"export {ours:,.0f} vs feed {theirs:,.0f} "
                           f"({gap * 100:.0f}% apart).{extra}",
            })
    return flags


def peers_array(details: list, nm_policy: str) -> list:
    """The list `model.py`'s relative() takes. Subject first."""
    out = []
    for d in details:
        row = {
            "name": d["name"], "price": d["price"], "mcap": d["mcap"], "ev": d["ev"],
            "sales": d["sales"], "ebitda": d["ebitda"], "pat": d["pat"],
            "bv": d["bv"], "roe": d["roe"],
        }
        if nm_policy == "exclude":
            # relative() divides by these directly and its median skips None, so
            # nulling a non-positive denominator is what keeps a loss-making peer
            # out of the P/E median without dropping its other multiples.
            if (row["pat"] or 0) <= 0:
                row["pat"] = None
            if (row["ebitda"] or 0) <= 0:
                row["ebitda"] = None
            if (row["bv"] or 0) <= 0:
                row["bv"] = None
        out.append(row)
    return out


# --------------------------------------------------------------- comparability
def comparability(details: list) -> list:
    """Fiscal-calendar and window checks. These are reported, never corrected."""
    flags = []

    bases = {d["basis"] for d in details if d["basis"]}
    if len(bases) > 1:
        raise SystemExit(
            "basis mismatch across the set: " + ", ".join(sorted(bases)) +
            ". Every multiple in a comps table must be struck on one basis. "
            "Re-download the odd one out from Screener on the subject's basis.")

    months = {}
    for d in details:
        if d["fy_end_month"]:
            months.setdefault(d["fy_end_month"], []).append(d["name"])
    if len(months) > 1:
        parts = [f"month {m:02d} ({', '.join(n)})" for m, n in sorted(months.items())]
        flags.append({
            "severity": "high", "kind": "fiscal_year_misalignment",
            "message": "peers close their books in different months: " + "; ".join(parts) +
                       ". Book value, net debt and therefore EV are measured on "
                       "different dates. State this in the report; do not adjust the "
                       "numbers to hide it.",
        })

    ends = {}
    for d in details:
        w = d.get("window") or {}
        if w.get("end"):
            ends.setdefault(w["end"], []).append(d["name"])
    if len(ends) > 1:
        parts = [f"{e} ({', '.join(n)})" for e, n in sorted(ends.items())]
        flags.append({
            "severity": "medium", "kind": "trailing_window_misalignment",
            "message": "trailing P&L windows end at different dates: " + "; ".join(parts) +
                       ". Earnings are compared over non-identical twelve-month periods.",
        })

    kinds = {(d.get("window") or {}).get("kind") for d in details}
    if len(kinds - {None}) > 1:
        flags.append({
            "severity": "high", "kind": "mixed_trailing_basis",
            "message": "some companies are on TTM and others on the last full year. "
                       "The full-year ones are up to four quarters stale relative to "
                       "the rest.",
        })

    for d in details:
        if d["basis_source"] != "file":
            flags.append({
                "severity": "medium", "kind": "unverified_basis",
                "message": f"{d['name']}: reporting basis was declared in the manifest, "
                           "not read from the export header.",
            })
        for nm in d["not_meaningful"]:
            flags.append({
                "severity": "medium", "kind": "not_meaningful",
                "message": f"{d['name']}: {nm} is not meaningful (denominator <= 0).",
            })

    # A multiple can be arithmetically fine and still be nonsense — a peer with a
    # collapsed but positive EBITDA prints a huge EV/EBITDA that is not "nm" and
    # will drag the median. Surface it; the analyst decides whether to drop the peer.
    peers_only = details[1:]
    for k in MULT_KEYS:
        if k == "ROE (%)":
            continue
        vals = [d["multiples"][k] for d in peers_only
                if d["multiples"][k] is not None and d["multiples"][k] > 0]
        if len(vals) < 3:
            continue
        med = median(vals)
        if not med:
            continue
        for d in peers_only:
            v = d["multiples"][k]
            if v is not None and v > 0 and (v > 3 * med or v < med / 3):
                flags.append({
                    "severity": "medium", "kind": "outlier",
                    "message": f"{d['name']}: {k} of {v} is more than 3x away from the "
                               f"peer median of {r1(med)}. It is included in the median "
                               "as it stands — drop the peer from the manifest if it is "
                               "not genuinely comparable.",
                })

    prices = {d["price_basis"] for d in details if d.get("price_basis")}
    if len(prices) > 1 and any("export price block" in str(p) for p in prices):
        flags.append({
            "severity": "medium", "kind": "price_date_mismatch",
            "message": "not every company was priced from the manifest, so the comps "
                       "are not all struck on the cover date.",
        })
    return flags


# --------------------------------------------------------------- summary stats
def stats(details: list, subject_idx: int) -> dict:
    peers = [d for i, d in enumerate(details) if i != subject_idx]
    subj = details[subject_idx]
    out = {"n_peers": len(peers), "median": {}, "p25": {}, "p75": {},
           "subject": {}, "premium_discount": {}}
    for k in MULT_KEYS:
        vals = [d["multiples"][k] for d in peers
                if d["multiples"][k] is not None
                and k.split()[0] not in d["not_meaningful"]]
        out["median"][k] = r1(median(vals))
        out["p25"][k] = r1(pct(vals, 0.25))
        out["p75"][k] = r1(pct(vals, 0.75))
        s = subj["multiples"][k]
        out["subject"][k] = s
        med = out["median"][k]
        out["premium_discount"][k] = (
            None if s is None or med in (None, 0) else f"{(s / med - 1) * 100:+.0f}%")
    return out


def football_field(details: list, subject_idx: int, st: dict,
                   admissible: set | None = None) -> list:
    """Relative-valuation bands for charts.football_field, in rupees per share.

    `admissible` is the set of method keys an approved modeling strategy did not
    rule out (`pe`, `ev_ebitda`, `ev_sales`, `pb`). None means no strategy was
    supplied and everything computable is emitted, as before. A method the
    strategy called NOT_APPROPRIATE is not plotted — a band on the chart is an
    implicit claim that the method means something for this company.
    """
    subj = details[subject_idx]
    sh = subj.get("shares_cr")
    bands = []
    if not sh:
        return bands

    def band(label, lo_x, mid_x, hi_x, to_equity, method=None):
        if admissible is not None and method is not None and method not in admissible:
            return
        if lo_x is None or hi_x is None:
            return
        lo, hi = to_equity(lo_x), to_equity(hi_x)
        mid = to_equity(mid_x) if mid_x is not None else None
        if lo is None or hi is None or lo <= 0 or hi <= 0:
            return
        b = {"label": label, "low": round(min(lo, hi)), "high": round(max(lo, hi))}
        if mid is not None and mid > 0:
            b["mid"] = round(mid)
        bands.append(b)

    if (subj.get("pat") or 0) > 0:
        eps = subj["pat"] / sh
        band("Peer P/E (25th-75th)", st["p25"]["P/E (x)"], st["median"]["P/E (x)"],
             st["p75"]["P/E (x)"], lambda x: x * eps, method="pe")

    nd = subj.get("net_debt") or 0.0
    if (subj.get("ebitda") or 0) > 0:
        band("Peer EV/EBITDA (25th-75th)", st["p25"]["EV/EBITDA (x)"],
             st["median"]["EV/EBITDA (x)"], st["p75"]["EV/EBITDA (x)"],
             lambda x: (x * subj["ebitda"] - nd) / sh, method="ev_ebitda")
    if (subj.get("sales") or 0) > 0:
        band("Peer EV/Sales (25th-75th)", st["p25"]["EV/Sales (x)"],
             st["median"]["EV/Sales (x)"], st["p75"]["EV/Sales (x)"],
             lambda x: (x * subj["sales"] - nd) / sh, method="ev_sales")
    if (subj.get("bv") or 0) > 0:
        bvps = subj["bv"] / sh
        band("Peer P/B (25th-75th)", st["p25"]["P/B (x)"], st["median"]["P/B (x)"],
             st["p75"]["P/B (x)"], lambda x: x * bvps, method="pb")
    return bands


# Multiples this skill computes, keyed to the modeling-strategy method library.
STRATEGY_METHODS = {"pe", "ev_ebitda", "ev_sales", "pb"}


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


def admissible_methods(strategy: dict) -> tuple[set, list]:
    """Which of this skill's multiples the approved strategy allows.

    Anything the strategy rejected, or classified NOT_APPROPRIATE, is dropped
    from the football field. The comps TABLE still reports every computable
    multiple — removing a number a reader can compute themselves looks like
    concealment. What changes is which of them is allowed to imply a valuation.
    """
    ruled_out = {r.get("method") for r in strategy.get("rejected_methods") or []}
    for m in strategy.get("valuation_methods") or []:
        if (m.get("role") or "").upper() in ("NOT_APPROPRIATE",) or \
                (m.get("applicability") or "").upper() == "NOT_APPROPRIATE":
            ruled_out.add(m.get("method"))
    ok = STRATEGY_METHODS - ruled_out
    return ok, sorted(ruled_out & STRATEGY_METHODS)


def forward_table(details: list, subject_idx: int) -> dict:
    """Forward multiples, kept strictly apart from anything computed."""
    rows = []
    for i, d in enumerate(details):
        f = d.get("forward")
        if not f:
            continue
        row = {"name": d["name"], "is_subject": i == subject_idx,
               "fy": f.get("fy"), "source": f.get("source"), "as_of": f.get("as_of")}
        if f.get("eps") and d.get("price"):
            row["Fwd P/E (x)"] = r1(div(d["price"], f["eps"]))
        if f.get("ebitda") and d.get("ev") is not None:
            row["Fwd EV/EBITDA (x)"] = r1(div(d["ev"], f["ebitda"]))
        if f.get("sales") and d.get("ev") is not None:
            row["Fwd EV/Sales (x)"] = r1(div(d["ev"], f["sales"]))
        rows.append(row)
    if not rows:
        return {}
    peers = [r for r in rows if not r["is_subject"]]
    med = {}
    for k in ("Fwd P/E (x)", "Fwd EV/EBITDA (x)", "Fwd EV/Sales (x)"):
        med[k] = r1(median([r.get(k) for r in peers if r.get(k) is not None]))
    return {
        "rows": rows, "median": med,
        "coverage": f"{len(peers)} of {len(details) - 1} peers",
        "caveat": "Forward figures are analyst-supplied consensus estimates, not "
                  "computed from the exports, and are not verified by this skill. "
                  "Forward EV uses today's net debt because forward net debt is not "
                  "estimated. Do not blend these with the trailing median.",
    }


# --------------------------------------------------------------- markdown
def to_md(doc: dict) -> str:
    st, det = doc["comps"], doc["detail"]
    L = [f"# Peer comparables — {doc['subject']}", "",
         f"Basis **{doc['basis']}** · priced **{doc['as_of']}** · "
         f"{st['n_peers']} peers · trailing multiples computed from Screener exports.", ""]

    def cell(v):
        if v is None:
            return "nm"
        if isinstance(v, float):
            return f"{v:,.1f}"
        if isinstance(v, int):
            return f"{v:,}"
        return str(v)

    hdr = ["Company", "Price", "Mkt Cap (Cr)", "EV (Cr)"] + MULT_KEYS + ["EBITDA Mgn (%)"]
    L += ["| " + " | ".join(hdr) + " |", "|" + "|".join(["---"] * len(hdr)) + "|"]
    for d in det:
        row = [d["name"], cell(d["price"]), cell(d["mcap"]), cell(d["ev"])]
        # Print "nm" for exactly the multiples the median excludes, so the table and
        # the median tell the same story. A printed -36.0 P/E reads as a datapoint.
        row += ["nm" if k.split()[0] in d["not_meaningful"] else cell(d["multiples"][k])
                for k in MULT_KEYS]
        row.append(cell(d["ebitda_margin"]))
        L.append("| " + " | ".join(row) + " |")
    L.append("| **Peer median** |  |  |  | " +
             " | ".join(cell(st["median"][k]) for k in MULT_KEYS) + " |  |")
    L.append(f"| **{doc['subject']} prem / (disc)** |  |  |  | " +
             " | ".join(st["premium_discount"][k] or "nm" for k in MULT_KEYS) + " |  |")

    iqr = "; ".join(f"{k} {st['p25'][k]}-{st['p75'][k]}"
                    for k in MULT_KEYS if st["p25"][k] is not None)
    L += ["", f"Peer interquartile range: {iqr}", "", "## Comparability", ""]
    if not doc["flags"]:
        L.append("No comparability flags raised.")
    for f in doc["flags"]:
        L.append(f"- **{f['severity'].upper()}** ({f['kind']}): {f['message']}")

    L += ["", "## Provenance", "",
          "| Company | Basis | FY end | Trailing window | Balance sheet | Price |",
          "|---|---|---|---|---|---|"]
    for d in det:
        w = d.get("window") or {}
        L.append(f"| {d['name']} | {d['basis']} ({d['basis_source']}) | "
                 f"{d['fy_end_label']} | {w.get('kind')} to {w.get('end')} | "
                 f"{d['bs_period']} | {d['price_basis']} |")
    L += ["", "ROE is computed as PAT / " + (det[0].get("roe_basis") or "net worth") +
          " for every company, so it is internally consistent but will not tie to a "
          "screen using a different convention.", ""]

    L += ["## Enterprise value bridge", "",
          "| Company | " + " | ".join(det[0]["ev_bridge"].keys()) + " | EV |",
          "|" + "|".join(["---"] * (len(det[0]["ev_bridge"]) + 2)) + "|"]
    for d in det:
        L.append(f"| {d['name']} | " +
                 " | ".join(cell(v) for v in d["ev_bridge"].values()) +
                 f" | {cell(d['ev'])} |")
    L.append("")

    notes = [(d["name"], n) for d in det for n in d["notes"]]
    if notes:
        L += ["### Bridge notes", ""] + [f"- {n}: {t}" for n, t in notes] + [""]

    if doc.get("forward"):
        f = doc["forward"]
        cols = [c for c in ("Fwd P/E (x)", "Fwd EV/EBITDA (x)", "Fwd EV/Sales (x)")
                if any(r.get(c) is not None for r in f["rows"])]
        L += ["## Forward multiples (analyst-supplied)", "", f"> {f['caveat']}", "",
              f"Coverage: {f['coverage']}", "",
              "| Company | FY | " + " | ".join(cols) + " | Source | As of |",
              "|" + "|".join(["---"] * (len(cols) + 4)) + "|"]
        for r in f["rows"]:
            L.append(f"| {r['name']} | {r.get('fy') or ''} | " +
                     " | ".join(cell(r.get(c)) for c in cols) +
                     f" | {r.get('source') or ''} | {r.get('as_of') or ''} |")
        L += ["| **Peer median** |  | " +
              " | ".join(cell(f["median"].get(c)) for c in cols) + " |  |  |", ""]

    if doc.get("football_field"):
        L += ["## Relative-valuation bands (INR / share)", "",
              "| Method | Low | Mid | High |", "|---|---|---|---|"]
        for b in doc["football_field"]:
            mid = f"{b['mid']:,}" if b.get("mid") is not None else ""
            L.append(f"| {b['label']} | {b['low']:,} | {mid} | {b['high']:,} |")
        L += ["", "Feed these to `charts.football_field` alongside the DCF scenario "
                  "range and the 52-week range.", ""]

    if doc.get("peer_betas"):
        L += ["## Peer betas", "",
              "| Company | Beta | D/E | Obs | R2 | Window |", "|---|---|---|---|---|---|"]
        for b in doc["peer_betas"]:
            L.append(f"| {b['name']} | {b.get('beta')} | {b.get('debt_equity')} | "
                     f"{b.get('n')} | {b.get('r2')} | {b.get('window')} |")
        L.append("")

    if doc["warnings"]:
        L += ["## Warnings", ""] + [f"- {w}" for w in doc["warnings"]] + [""]
    return "\n".join(L)


# --------------------------------------------------------------- decisions.json
def patch_decisions(path: str, peers: list, betas: list | None) -> str:
    with open(path, encoding="utf-8") as f:
        dec = json.load(f)
    if not isinstance(dec, dict):
        raise SystemExit(f"{path} is not a JSON object")
    shutil.copyfile(path, path + ".bak")
    # `peers` and `peer_betas` are top-level settings that pass straight through
    # build_assumptions.py into assumptions.json. Placed inside "assumptions"
    # they are silently dropped.
    dec["peers"] = peers
    if betas:
        dec["peer_betas"] = [{"name": b["name"], "beta": b["beta"],
                              "debt_equity": b["debt_equity"]}
                             for b in betas
                             if b.get("beta") is not None
                             and b.get("debt_equity") is not None]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(dec, f, indent=2)
    return path + ".bak"


# --------------------------------------------------------------- CLI
def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("raw", help="peers_raw.json from peer_ingest.py")
    ap.add_argument("-o", "--out", default="data/peers.json")
    ap.add_argument("--md", default=None, help="also write the comps table as markdown")
    ap.add_argument("--betas", help="peer_betas.json from peer_beta.py")
    ap.add_argument("--patch-decisions", metavar="PATH",
                    help="write peers/peer_betas into an existing decisions.json "
                         "(a .bak is kept)")
    ap.add_argument("--nm-policy", choices=["exclude", "keep"], default="exclude",
                    help="what to do with a multiple whose denominator is <= 0 "
                         "(default: exclude it from the downstream median)")
    ap.add_argument("--roe", choices=["average", "closing"], default="average",
                    help="net worth basis for ROE (default: average, falling back to "
                         "closing for everyone if any company lacks a prior year)")
    ap.add_argument("--sector", help="business model; 'financials' suppresses every "
                                     "EV-based multiple")
    ap.add_argument("--no-crosscheck", action="store_true",
                    help="skip the second-source comparison even when peer_ingest.py "
                         "was run with --market")
    ap.add_argument("--strategy", help="model_strategy.json from the modeling-strategy "
                                       "skill. Optional: without it every computable "
                                       "band is emitted, exactly as before.")
    args = ap.parse_args()

    with open(args.raw, encoding="utf-8") as f:
        raw = json.load(f)
    comps = list(raw["companies"])

    admissible = None
    strategy = None
    if args.strategy:
        with open(args.strategy, encoding="utf-8") as f:
            strategy = json.load(f)
        gate = _load_gate()
        ok, why = gate.gate_ok(strategy, require_approved=True)
        if not ok:
            raise SystemExit(f"refusing to build comps: {why}")
        admissible, dropped = admissible_methods(strategy)

    sector = (args.sector or raw.get("sector") or "").lower()
    suppress_ev = any(t in sector for t in ("financial", "bank", "nbfc", "insur"))

    # One ROE convention for the whole table, or the comparison is not a comparison.
    roe_avg = args.roe == "average" and all(c.get("bv_prior") is not None for c in comps)
    warnings = []
    if args.roe == "average" and not roe_avg:
        warnings.append("at least one company has no prior-year net worth, so ROE is on "
                        "closing net worth for every company")
    if admissible is not None and dropped:
        warnings.append(
            "the approved modeling strategy rules out " + ", ".join(dropped) +
            " for this company, so no relative-valuation band is emitted for "
            "them. The multiples still appear in the comps table — what is "
            "withheld is the implication that they value the business.")
    if suppress_ev:
        warnings.append(f"sector {sector!r}: EV/EBITDA and EV/Sales are suppressed. For "
                        "a bank or NBFC interest is revenue and net debt is not "
                        "meaningful, so an EV multiple has no interpretation. Compare on "
                        "P/E, P/B and ROE.")

    detail = [build_one(c, roe_avg, suppress_ev) for c in comps]

    subject = raw.get("subject")
    subject_idx = next((i for i, c in enumerate(comps)
                        if c.get("ticker") == subject or c.get("name") == subject), 0)
    if subject_idx != 0:
        detail.insert(0, detail.pop(subject_idx))
        comps.insert(0, comps.pop(subject_idx))
        subject_idx = 0

    flags = comparability(detail)
    if not args.no_crosscheck:
        flags += crosscheck(detail)
    st = stats(detail, subject_idx)

    betas = None
    if args.betas:
        with open(args.betas, encoding="utf-8") as f:
            betas = json.load(f).get("peer_betas")

    doc = {
        "as_of": raw.get("as_of"),
        "basis": raw.get("basis") or detail[0]["basis"],
        "subject": detail[0]["name"],
        "sector": sector or None,
        "peers": peers_array(detail, args.nm_policy),
        "detail": detail,
        "comps": st,
        "football_field": football_field(detail, subject_idx, st, admissible),
        "forward": forward_table(detail, subject_idx),
        "peer_betas": betas,
        "strategy_ref": ({
            "modelability": (strategy.get("modelability") or {}).get("status"),
            "analyst_decision": (strategy.get("analyst_decision") or {}).get("status"),
            "admissible_multiples": sorted(admissible),
            "ruled_out": dropped,
        } if strategy else None),
        "flags": flags,
        "warnings": warnings + [w for c in comps for w in (c.get("warnings") or [])],
    }

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=1, default=str)
    print(f"wrote {args.out}")

    if args.md:
        os.makedirs(os.path.dirname(args.md) or ".", exist_ok=True)
        with open(args.md, "w", encoding="utf-8") as f:
            f.write(to_md(doc))
        print(f"wrote {args.md}")

    if args.patch_decisions:
        bak = patch_decisions(args.patch_decisions, doc["peers"], betas)
        print(f"patched {args.patch_decisions}  (backup {bak})")
        print("  rebuild assumptions.json with build_assumptions.py — never edit it "
              "directly")

    # ---- console summary ----------------------------------------------------
    print(f"\nsubject {doc['subject']}  vs {st['n_peers']} peers  "
          f"basis {doc['basis']}  as of {doc['as_of']}")
    print(f"{'multiple':<16}{'subject':>10}{'peer med':>10}{'p25-p75':>16}{'prem/disc':>11}")
    for k in MULT_KEYS:
        rng = f"{st['p25'][k]}-{st['p75'][k]}" if st["p25"][k] is not None else "-"
        print(f"{k:<16}{str(st['subject'][k]):>10}{str(st['median'][k]):>10}"
              f"{rng:>16}{str(st['premium_discount'][k] or '-'):>11}")

    if doc["football_field"]:
        print("\nrelative-valuation bands (INR/share):")
        for b in doc["football_field"]:
            print(f"  {b['label']:<30}{b['low']:>9,} - {b['high']:<9,}"
                  f"  mid {b.get('mid', '-')}")

    if flags:
        print("\ncomparability flags:")
        for f_ in flags:
            print(f"  [{f_['severity']}] {f_['message']}")
    for w in doc["warnings"]:
        print(f"  ! {w}")


if __name__ == "__main__":
    main()
