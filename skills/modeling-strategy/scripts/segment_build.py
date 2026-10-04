#!/usr/bin/env python3
"""
segment_build.py — run the approved segment economics and derive ONE consolidated
revenue growth path, with the whole build preserved.

    python3 segment_build.py --strategy data/model_strategy.json \
                             --values  data/segment_values.json \
                             --outdir  data/ --md segment_build.md

This is the Phase A translation. `financial-model` has a single revenue row driven
by one growth rate, so an approved segment architecture cannot be executed
natively. Rather than flattening it silently, the driver mathematics runs HERE —
deterministically, on approved drivers with approved values — and lands as a
per-year consolidated `revenue_growth` path that `financial-model-assumptions`
injects into `assumptions.json` with full provenance.

Nothing is lost: `segment_build.json` carries every segment, every driver, every
intermediate row and every citation, and `segment_build.md` is the audit exhibit.
The consolidated growth rate is a DERIVED figure that can always be walked back
to the segment economics it came from.

THE BASE-YEAR TIE-OUT
---------------------
Every driver series starts at the BASE year, not the first forecast year. The
build therefore reproduces the last reported year from the drivers, and that
reconstruction is checked against reported segment revenue. An architecture that
cannot reproduce the year it can see has no business forecasting five it cannot.
That check is the reason this file exists rather than a spreadsheet.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import archetypes as AR        # noqa: E402
import check_strategy as CHK   # noqa: E402

# Drivers expressed as a percentage. Supplied as 38 or 0.38, normalised to 0.38.
RATE_DRIVERS = {
    "utilisation", "execution_rate", "churn", "occupancy", "sss_growth",
    "realisation_spread", "non_room_revenue", "collection_efficiency",
    "completion_schedule", "revenue_growth", "net_revenue_retention",
    "attrition", "maturity_curve",
}

TIE_TOLERANCE_PCT = 1.0     # base-year reconstruction vs reported segment revenue


class BuildError(Exception):
    pass


def _series(drivers: dict, key: str, n: int, required: bool = True,
            default=None) -> list[float]:
    """One driver as an n-long series. Scalars repeat; short lists hold flat."""
    d = drivers.get(key)
    if d is None:
        if required:
            raise BuildError(f"driver {key!r} is missing")
        return [float(default if default is not None else 0.0)] * n
    v = d.get("value") if isinstance(d, dict) else d
    if isinstance(v, str):
        raise BuildError(f"driver {key!r} has no numeric value ({v!r}) — "
                         "an unevidenced driver cannot be built through")
    if isinstance(v, (int, float)):
        out = [float(v)] * n
    else:
        out = [float(x) for x in v][:n]
        while len(out) < n:
            out.append(out[-1] if out else 0.0)
    if key in RATE_DRIVERS and any(abs(x) > 1.5 for x in out):
        out = [x / 100.0 for x in out]
    return out


# --------------------------------------------------------------- archetypes
def _volume_price(dr, n):
    vol = _series(dr, "volume", n)
    px = _series(dr, "price", n)
    return [v * p for v, p in zip(vol, px)], {"volume": vol, "price": px}


def _units_asp(dr, n):
    u = _series(dr, "units", n)
    a = _series(dr, "asp", n)
    return [x * y for x, y in zip(u, a)], {"units": u, "asp": a}


def _capacity(dr, n):
    cap = _series(dr, "installed_capacity", n)
    add = _series(dr, "capacity_addition", n, required=False, default=0.0)
    util = _series(dr, "utilisation", n)
    real = _series(dr, "realisation", n)
    # Additions commission during the year: only the opening capacity is
    # available for the full year unless the analyst supplied capacity directly.
    eff = []
    running = cap[0]
    for i in range(n):
        running = cap[i] if cap[i] else running + add[i]
        eff.append(running)
    rev = [c * u * r for c, u, r in zip(eff, util, real)]
    return rev, {"capacity": eff, "additions": add, "utilisation": util,
                 "realisation": real,
                 "_volume": [c * u for c, u in zip(eff, util)]}


def _production(dr, n):
    vol = _series(dr, "production_volume", n)
    ref = _series(dr, "reference_price", n)
    spr = _series(dr, "realisation_spread", n, required=False, default=0.0)
    real = [p * (1 + s) for p, s in zip(ref, spr)]
    return [v * r for v, r in zip(vol, real)], {
        "production_volume": vol, "reference_price": ref,
        "realisation_spread": spr, "net_realisation": real}


def _order_book(dr, n):
    ob0 = _series(dr, "opening_order_book", n)[0]
    inflow = _series(dr, "order_inflow", n)
    ex = _series(dr, "execution_rate", n)
    rev, opening, closing = [], [], []
    book = ob0
    for i in range(n):
        opening.append(book)
        r = book * ex[i]
        rev.append(r)
        book = book + inflow[i] - r
        closing.append(book)
    return rev, {"opening_book": opening, "inflow": inflow,
                 "execution_rate": ex, "closing_book": closing,
                 "book_to_bill": [(i / r if r else None)
                                  for i, r in zip(inflow, rev)]}


def _pipeline(dr, n):
    pv0 = _series(dr, "pipeline_value", n)[0]
    comp = _series(dr, "completion_schedule", n)
    bookings = _series(dr, "presales_bookings", n, required=False, default=0.0)
    coll = _series(dr, "collection_efficiency", n, required=False, default=1.0)
    rev, opening, closing = [], [], []
    pipe = pv0
    for i in range(n):
        opening.append(pipe)
        r = pipe * comp[i]
        rev.append(r)
        pipe = pipe + bookings[i] - r
        closing.append(pipe)
    return rev, {"opening_pipeline": opening, "completion": comp,
                 "bookings": bookings, "closing_pipeline": closing,
                 "collections": [b * c for b, c in zip(bookings, coll)]}


def _counts_arpu(dr, n, open_key, add_key, arpu_key="arpu"):
    o0 = _series(dr, open_key, n)[0]
    adds = _series(dr, add_key, n)
    churn = _series(dr, "churn", n, required=False, default=0.0)
    arpu = _series(dr, arpu_key, n)
    rev, opening, closing, avg = [], [], [], []
    cnt = o0
    for i in range(n):
        opening.append(cnt)
        lost = cnt * churn[i]
        close = cnt + adds[i] - lost
        closing.append(close)
        a = (cnt + close) / 2.0
        avg.append(a)
        rev.append(a * arpu[i])
        cnt = close
    return rev, {"opening": opening, "adds": adds, "churn_rate": churn,
                 "closing": closing, "average": avg, "arpu": arpu}


def _customers(dr, n):
    return _counts_arpu(dr, n, "opening_customers", "customer_adds")


def _subscribers(dr, n):
    return _counts_arpu(dr, n, "opening_subscribers", "net_adds")


def _stores(dr, n):
    o0 = _series(dr, "opening_stores", n)[0]
    adds = _series(dr, "store_adds", n)
    sps = _series(dr, "sales_per_store", n)
    ramp = _series(dr, "maturity_curve", n, required=False, default=0.5)
    rev, opening, closing, eff = [], [], [], []
    cnt = o0
    for i in range(n):
        opening.append(cnt)
        close = cnt + adds[i]
        closing.append(close)
        # New stores contribute at the maturity ramp for their first year.
        e = cnt + adds[i] * ramp[i]
        eff.append(e)
        rev.append(e * sps[i])
        cnt = close
    return rev, {"opening_stores": opening, "adds": adds, "closing_stores": closing,
                 "effective_stores": eff, "sales_per_store": sps,
                 "maturity_ramp": ramp}


def _rooms(dr, n):
    keys = _series(dr, "keys", n)
    occ = _series(dr, "occupancy", n)
    arr = _series(dr, "arr", n)
    other = _series(dr, "non_room_revenue", n, required=False, default=0.0)
    nights = [k * 365 for k in keys]
    room_rev = [x * o * a for x, o, a in zip(nights, occ, arr)]
    return [r * (1 + o) for r, o in zip(room_rev, other)], {
        "keys": keys, "room_nights": nights, "occupancy": occ, "arr": arr,
        "revpar": [o * a for o, a in zip(occ, arr)],
        "room_revenue": room_rev, "non_room_pct": other}


def _headcount(dr, n):
    hc = _series(dr, "headcount", n)
    util = _series(dr, "utilisation", n)
    real = _series(dr, "realisation", n)
    return [h * u * r for h, u, r in zip(hc, util, real)], {
        "headcount": hc, "utilisation": util, "realisation": real,
        "_billable": [h * u for h, u in zip(hc, util)]}


def _generic(dr, n, base_revenue=None):
    g = _series(dr, "revenue_growth", n)
    rev, prev = [], base_revenue if base_revenue else 100.0
    for i in range(n):
        # index 0 is the base year: it IS the base revenue, growth starts at 1
        rev.append(prev if i == 0 else prev * (1 + g[i]))
        prev = rev[-1]
    return rev, {"revenue_growth": g}


BUILDERS = {
    "volume_price": _volume_price,
    "units_asp": _units_asp,
    "capacity_utilisation_realisation": _capacity,
    "production_realisation": _production,
    "order_book_execution": _order_book,
    "project_pipeline_completion": _pipeline,
    "customers_arpu": _customers,
    "subscribers_arpu": _subscribers,
    "stores_sales_per_store": _stores,
    "rooms_occupancy_arr": _rooms,
    "headcount_utilisation_realisation": _headcount,
    "generic_growth": _generic,
}


def build(strategy: dict, values: dict) -> dict:
    ok, why = CHK.gate_ok(strategy, require_approved=True)
    if not ok:
        raise BuildError(
            f"refusing to build: {why}. The segment build runs on an APPROVED "
            "strategy only — that is the gate, not a formality.")

    years = values.get("years")
    if not years or len(years) < 2:
        raise BuildError("values.years must list the base year followed by every "
                         "forecast year")
    n = len(years)
    warnings: list[str] = []
    segs_out = []

    by_name = {s.get("name"): s for s in strategy.get("segments") or []}
    for name, spec in (values.get("segments") or {}).items():
        sg = by_name.get(name)
        if sg is None:
            raise BuildError(f"segment {name!r} is not in the approved strategy")
        res = AR.resolve(sg.get("economic_archetype"))
        if res is None:
            raise BuildError(
                f"segment {name!r} has no validated archetype — it cannot be built "
                "through. This is the refusal, not a fallback.")
        akey = res[0]
        fn = BUILDERS.get(akey)
        if fn is None:
            raise BuildError(
                f"archetype {akey!r} has no builder. financial-model cannot execute "
                "it and it must not be approximated — refusing.")

        drivers = spec.get("drivers") or {}
        base_rev = spec.get("base_revenue")
        try:
            if akey == "generic_growth":
                raw, rows = fn(drivers, n, base_rev)
            else:
                raw, rows = fn(drivers, n)
        except BuildError as e:
            raise BuildError(f"segment {name!r}: {e}")

        # --- unit reconciliation and the base-year tie-out -------------------
        scale = spec.get("unit_scale")
        tie = None
        if akey == "generic_growth":
            scale = 1.0
            tie = {"status": "n/a", "note": "generic_growth is anchored on reported "
                                            "base revenue by construction"}
        elif base_rev in (None, 0):
            if scale is None:
                raise BuildError(
                    f"segment {name!r}: needs base_revenue (to tie the build out) or "
                    "an explicit unit_scale. Guessing the unit is how a build that "
                    "looks right comes out 1000x wrong.")
            tie = {"status": "unchecked",
                   "note": "no base_revenue supplied — the build was not tied out"}
            warnings.append(f"{name}: build not tied to reported base-year revenue")
        else:
            if raw[0] in (0, None):
                raise BuildError(f"segment {name!r}: base-year build is zero — "
                                 "the driver series must start at the base year")
            implied = base_rev / raw[0]
            if scale is None:
                scale = implied
                mag = abs(implied)
                clean = any(abs(mag / 10 ** k - 1) < 0.02 for k in range(-9, 10))
                tie = {"status": "calibrated", "implied_scale": implied,
                       "base_reported": base_rev, "base_raw": raw[0],
                       "note": ("implied scale is a clean power of ten — a pure unit "
                                "conversion" if clean else
                                "implied scale is NOT a clean power of ten: the "
                                "drivers do not reproduce the base year, so part of "
                                "this revenue is not explained by the architecture")}
                if not clean:
                    warnings.append(
                        f"{name}: base-year reconstruction implies a scale of "
                        f"{implied:.4g}, which is not a unit conversion. "
                        f"{100 * (1 - 1 / implied):+.1f}% of base revenue is "
                        "unexplained by the declared drivers.")
            else:
                got = raw[0] * scale
                err = (got / base_rev - 1) * 100 if base_rev else None
                tie = {"status": "checked", "base_reported": base_rev,
                       "base_rebuilt": got, "error_pct": round(err, 3)}
                if err is not None and abs(err) > TIE_TOLERANCE_PCT:
                    raise BuildError(
                        f"segment {name!r}: the drivers rebuild base-year revenue as "
                        f"{got:,.1f} against {base_rev:,.1f} reported ({err:+.1f}%). "
                        f"Above the {TIE_TOLERANCE_PCT}% tolerance the architecture "
                        "does not describe this segment. Fix the drivers or change "
                        "the architecture — do not scale the gap away.")

        rev = [r * scale for r in raw]
        segs_out.append({
            "name": name,
            "archetype": akey,
            "identity": res[1]["identity"],
            "materiality_pct": sg.get("materiality_pct"),
            "unit_scale": scale,
            "tie_out": tie,
            "revenue": [round(x, 2) for x in rev],
            "growth_pct": [None] + [round((rev[i] / rev[i - 1] - 1) * 100, 2)
                                    if rev[i - 1] else None for i in range(1, n)],
            "rows": {k: [round(x, 4) if isinstance(x, (int, float)) else x
                         for x in v] for k, v in rows.items()},
            "evidence": {k: (v.get("evidence") if isinstance(v, dict) else None)
                         for k, v in drivers.items()},
            "confidence": sg.get("confidence"),
        })

    if not segs_out:
        raise BuildError("no segments were built")

    unalloc = values.get("unallocated") or {}
    un_series = [0.0] * n
    if unalloc:
        un_series = _series({"u": unalloc}, "u", n, required=False, default=0.0)

    total = [sum(s["revenue"][i] for s in segs_out) + un_series[i] for i in range(n)]
    growth = [round((total[i] / total[i - 1] - 1) * 100, 2) if total[i - 1] else None
              for i in range(1, n)]

    # Sanity: the declared materiality should look like the built base-year mix.
    for s in segs_out:
        share = 100 * s["revenue"][0] / total[0] if total[0] else 0
        dec = s.get("materiality_pct")
        if isinstance(dec, (int, float)) and abs(share - dec) > 10:
            warnings.append(
                f"{s['name']}: built base-year share {share:.0f}% against declared "
                f"materiality {dec:.0f}% — the decomposition and the build disagree")

    return {
        "schema_version": "1.0",
        "company": strategy.get("company"),
        "ticker": strategy.get("ticker"),
        "strategy_ref": {
            "revenue_model": (strategy.get("model_architecture") or {}).get("revenue_model"),
            "modelability": (strategy.get("modelability") or {}).get("status"),
            "analyst_decision": (strategy.get("analyst_decision") or {}).get("status"),
        },
        "years": years,
        "base_year": years[0],
        "segments": segs_out,
        "unallocated": [round(x, 2) for x in un_series] if unalloc else None,
        "consolidated_revenue": [round(x, 2) for x in total],
        "derived_revenue_growth_pct": growth,
        "derivation": (
            "Consolidated revenue is the sum of segment revenue, each built from its "
            "approved economic archetype on approved, cited drivers. The growth path "
            "below is DERIVED from that build — it is what financial-model's single "
            "revenue row consumes. Every figure traces back through segments[].rows "
            "to the drivers and their citations."),
        "warnings": warnings,
    }


def _md(B: dict) -> str:
    L, A = [], None
    A = L.append
    yrs = B["years"]
    A(f"# Segment revenue build — {B.get('company') or B.get('ticker')}")
    A("")
    A(f"*Base year {B['base_year']}; strategy is "
      f"{B['strategy_ref']['analyst_decision']} / "
      f"{B['strategy_ref']['modelability']}*")
    A("")
    A(B["derivation"])
    A("")
    A("## Consolidated")
    A("")
    A("| | " + " | ".join(yrs) + " |")
    A("|---|" + "---:|" * len(yrs))
    A("| Revenue | " + " | ".join(f"{x:,.0f}" for x in B["consolidated_revenue"]) + " |")
    A("| **Derived growth %** | — | " +
      " | ".join(f"**{g:+.1f}**" if g is not None else "—"
                 for g in B["derived_revenue_growth_pct"]) + " |")
    A("")
    A("This growth path is what `financial-model-assumptions` injects as "
      "`revenue_growth`, and what `financial-model`'s single revenue row executes.")
    A("")
    for s in B["segments"]:
        A(f"## {s['name']} — {s['archetype']}")
        A("")
        A(f"`{s['identity']}`")
        A("")
        t = s["tie_out"] or {}
        A(f"**Base-year tie-out:** {t.get('status')}"
          + (f" — reported {t['base_reported']:,.0f}, rebuilt "
             f"{t.get('base_rebuilt', t.get('base_raw', 0)) * (1 if 'base_rebuilt' in t else s['unit_scale']):,.0f}"
             if t.get("base_reported") else "")
          + (f" ({t['error_pct']:+.2f}%)" if t.get("error_pct") is not None else ""))
        if t.get("note"):
            A("")
            A(f"> {t['note']}")
        A("")
        A("| Driver | " + " | ".join(yrs) + " |")
        A("|---|" + "---:|" * len(yrs))
        for k, v in s["rows"].items():
            if k.startswith("_"):
                continue
            A(f"| {k} | " + " | ".join(
                f"{x:,.3g}" if isinstance(x, (int, float)) else "—" for x in v) + " |")
        A("| **Revenue** | " + " | ".join(f"**{x:,.0f}**" for x in s["revenue"]) + " |")
        A("| Growth % | " + " | ".join(
            f"{g:+.1f}" if g is not None else "—" for g in s["growth_pct"]) + " |")
        A("")
        ev = {k: v for k, v in (s.get("evidence") or {}).items() if v}
        if ev:
            A("**Citations**")
            A("")
            for k, items in ev.items():
                for e in items:
                    pg = f", p. {e['page']}" if isinstance(e, dict) and e.get("page") else ""
                    q = e.get("quote", "") if isinstance(e, dict) else str(e)
                    src = e.get("source", "?") if isinstance(e, dict) else "?"
                    A(f"- `{k}` — \"{q}\" — `{src}`{pg}")
            A("")
    if B["warnings"]:
        A("## Warnings")
        A("")
        for w in B["warnings"]:
            A(f"- {w}")
        A("")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--strategy", required=True)
    ap.add_argument("--values", required=True)
    ap.add_argument("--outdir", default="data")
    ap.add_argument("--md")
    a = ap.parse_args()

    S = json.load(open(a.strategy, encoding="utf-8"))
    V = json.load(open(a.values, encoding="utf-8"))
    try:
        B = build(S, V)
    except BuildError as e:
        print(f"REFUSED: {e}", file=sys.stderr)
        raise SystemExit(2)

    os.makedirs(a.outdir, exist_ok=True)
    p = os.path.join(a.outdir, "segment_build.json")
    json.dump(B, open(p, "w", encoding="utf-8"), indent=1)
    md = a.md or os.path.join(a.outdir, "segment_build.md")
    open(md, "w", encoding="utf-8").write(_md(B))

    print(f"wrote {p}")
    print(f"wrote {md}")
    print(f"  base {B['base_year']}  revenue {B['consolidated_revenue'][0]:,.0f}")
    print("  derived revenue_growth %: " +
          ", ".join(f"{g:+.2f}" for g in B["derived_revenue_growth_pct"]))
    for s in B["segments"]:
        print(f"    {s['name']:<24} {s['archetype']:<34} "
              f"tie-out {(s['tie_out'] or {}).get('status')}")
    for w in B["warnings"]:
        print(f"  ! {w}")


if __name__ == "__main__":
    main()
