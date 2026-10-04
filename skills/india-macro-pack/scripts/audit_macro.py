#!/usr/bin/env python3
"""
audit_macro.py -- is the stored macro pack still safe to quote?

    python3 audit_macro.py --root reports
    python3 audit_macro.py --root reports --strict     # exit 1 on any warning

WHY THIS EXISTS SEPARATELY FROM kb.py
  kb.py applies one blanket rule: the whole macro.json goes stale 90 days after
  `as_of`. That is the right coarse guard, but it fails in both directions --
  a repo rate is wrong long before 90 days, and an annual per-capita figure is fine
  well after. This checks each figure against its own class, and against its
  OBSERVATION period rather than the date somebody wrote it down.

  Run it in Phase 0 alongside `kb.py brief`, and again before Phase 6 writes prose.
  Between those two points a report can sit for days.

EXIT CODES
  0  everything inside its window
  1  at least one figure is over its window, carried forward, or unattributed
  2  no macro.json at all
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import registry as R  # noqa: E402

KB_BLANKET_DAYS = 90  # what kb.py itself enforces, restated here for the comparison


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default="reports")
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--json", action="store_true", help="machine-readable summary")
    args = ap.parse_args()

    path = os.path.join(args.root, "_knowledge", "macro.json")
    if not os.path.exists(path):
        print(f"no macro.json at {path} -- nothing has been recorded yet.")
        print("Run fetch_macro.py, fill manual.json, then build_pack.py.")
        return 2

    with open(path, encoding="utf-8") as f:
        m = json.load(f)

    figures = m.get("figures") or {}
    as_of_age = R.days_old(m.get("as_of"))
    rows, problems = [], []

    for k in sorted(figures):
        r = figures[k]
        cls = r.get("cls") or ""
        period = r.get("period") or r.get("recorded")
        age = R.days_old(period)
        known = cls in R.FRESHNESS_DAYS
        limit = R.effective_limit(cls, r.get("lag")) if known else KB_BLANKET_DAYS
        status, why = "ok", ""

        src = (r.get("source") or "").strip().lower()
        if not src or src == "unattributed":
            status, why = "UNATTRIBUTED", "no source recorded"
        elif r.get("method") == "carried_forward":
            status, why = "CARRIED", "not refreshed this cycle"
        elif r.get("stale_override"):
            status, why = "OVERRIDE", r["stale_override"]
        elif age is None:
            status, why = "NO PERIOD", f"cannot date {period!r}"
        elif age > limit:
            status, why = "STALE", (f"{age}d old, limit {limit}d ({cls})" if known
                                    else f"{age}d old, kb.py blanket limit {limit}d")
        elif not known:
            status, why = "UNCLASSED", ("no freshness class -- written by kb.py directly "
                                        "rather than build_pack.py?")

        rows.append({"key": k, "value": r.get("value"), "period": period,
                     "age_days": age, "cls": cls, "limit": limit,
                     "method": r.get("method"), "status": status, "why": why,
                     "source": r.get("source")})
        if status != "ok":
            problems.append(rows[-1])

    if args.json:
        print(json.dumps({"path": path, "as_of": m.get("as_of"),
                          "as_of_age_days": as_of_age,
                          "n_figures": len(figures), "n_problems": len(problems),
                          "rows": rows}, indent=2))
        return 1 if problems else 0

    print("=" * 78)
    print(f"MACRO AUDIT  --  {path}")
    print(f"as_of {m.get('as_of')} ({as_of_age}d ago)   figures: {len(figures)}")
    gate = (m.get("_pack") or {}).get("weo_gate") or {}
    if gate.get("resolved_by"):
        print(f"WEO: {gate['resolved_by']}")
    if gate and gate.get("status") not in (None, "current"):
        print(f"WEO vintage at build time: {gate.get('status')} "
              f"(expected {gate.get('expected')}, mirror {gate.get('available')})")
    print("=" * 78)
    print(f"{'key':<26}{'value':<14}{'period':<12}{'age':>6}  {'status':<13}why")
    print("-" * 78)
    for r in rows:
        age = f"{r['age_days']}d" if r["age_days"] is not None else "?"
        print(f"{r['key']:<26}{str(r['value'])[:13]:<14}{str(r['period'] or '-'):<12}"
              f"{age:>6}  {r['status']:<13}{r['why']}")

    print("-" * 78)
    if not problems:
        print("All figures inside their freshness windows. Safe to quote.")
        return 0

    print(f"{len(problems)} figure(s) need attention before they appear in a report:")
    for p in problems:
        spec = R.INDIA_FIGURE_INDEX.get(p["key"])
        print(f"\n  {p['key']}  [{p['status']}]  {p['why']}")
        if spec:
            print(f"    url  : {spec['url']}")
            print(f"    where: {spec['fallback']}")
        elif p["key"].startswith(("gdp_", "cpi_")):
            print(f"    url  : {R.WEO_MANUAL_URL}")
            print("    where: WEO database, By Countries, read the row for the year. "
                  "India is fiscal-year basis.")
    print("\nRe-run fetch_macro.py / update manual.json, then build_pack.py.")
    print("Do NOT quote the figures above in the meantime.")
    return 1 if (args.strict or problems) else 0


if __name__ == "__main__":
    raise SystemExit(main())
