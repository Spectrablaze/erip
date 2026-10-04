#!/usr/bin/env python3
"""
revise.py — patch decisions.json with an audited revision, then print the rebuild chain.

    python3 revise.py --report-dir reports/EICHERMOT --note-date 2026-08-01 \
        --set ebitda_margin=23.4 --why ebitda_margin="Q1 margin 23.1% and guidance held" \
        --evidence ebitda_margin="Q1FY27 results, 24 Jul 2026, p.4" \
        --set current_price=4920 --evidence current_price="NSE close, 31 Jul 2026"

decisions.json is the only file to edit; assumptions.json is generated and any
hand-edit to it is destroyed on the next build. This script enforces that:

  * it writes into `assumptions.<key>.value`, keeping the schema
    financial-model-assumptions expects;
  * it refuses a value change with no `--evidence`, because an unsourced
    revision is how a forecast drifts to fit a price;
  * it appends the prior value to a top-level `revisions` array, so the note can
    print a real from/to bridge and the next note can see what this one moved;
  * a per-year series is revised in year 1 by default, keeping the rest of the
    curve, unless the value is given as a JSON list.

`revisions`, `rating_bands` and `tolerances` are top-level keys that
build_assumptions.py does not read and does not pass through — they are this
skill's record, and they are safely ignored downstream.

Exit codes
  0  patched (or --dry-run printed the patch)
  2  a change was rejected — unsourced, unknown key, or unparseable value
  3  decisions.json missing or unusable
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from datetime import date

# Settings that live TOP-LEVEL in decisions.json. Anything else goes inside
# `assumptions`. Putting a judgement top-level makes it silently vanish.
TOP_LEVEL = {"peers", "peer_betas", "scenarios", "mid_year_convention",
             "blume_adjust", "non_operating_assets", "wc_days_on_cogs",
             "sector", "as_of", "company", "ticker", "kb", "currency"}

# Revising these without evidence is always wrong.
EVIDENCE_REQUIRED = True


def _parse_value(raw: str):
    """Accept 23.4, [23.4, 23.0, 22.8], "text", true/null."""
    raw = raw.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def _kv(pairs: list[str], flag: str) -> dict:
    out = {}
    for p in pairs:
        if "=" not in p:
            sys.exit(f"{flag} expects key=value, got {p!r}")
        k, v = p.split("=", 1)
        out[k.strip()] = v.strip()
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--report-dir", required=True)
    ap.add_argument("--note-date", default=date.today().isoformat())
    ap.add_argument("--trigger", default="", help="what prompted the revision")
    ap.add_argument("--set", action="append", default=[], metavar="KEY=VALUE")
    ap.add_argument("--why", action="append", default=[], metavar="KEY=TEXT")
    ap.add_argument("--evidence", action="append", default=[], metavar="KEY=CITATION")
    ap.add_argument("--confidence", action="append", default=[],
                    metavar="KEY=High|Medium|Low")
    ap.add_argument("--rating", help="record the note's rating in the revision entry")
    ap.add_argument("--target", type=float, help="record the note's target")
    ap.add_argument("--whole-series", action="store_true",
                    help="apply a scalar to every year rather than year 1 only")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    path = os.path.join(args.report_dir, "decisions.json")
    try:
        with open(path, encoding="utf-8") as fh:
            dec = json.load(fh)
    except OSError:
        sys.exit(f"cannot read {path}")
    except json.JSONDecodeError as exc:
        sys.exit(f"{path} is not valid JSON: {exc}")

    sets = _kv(args.set, "--set")
    whys = _kv(args.why, "--why")
    evid = _kv(args.evidence, "--evidence")
    conf = _kv(args.confidence, "--confidence")

    A = dec.setdefault("assumptions", {})
    changes, rejected = [], []

    for key, raw in sets.items():
        new = _parse_value(raw)

        if key in TOP_LEVEL:
            old = dec.get(key)
            if old == new:
                continue
            changes.append({"key": key, "where": "top-level", "from": old, "to": new,
                            "why": whys.get(key), "evidence": evid.get(key)})
            if not args.dry_run:
                dec[key] = new
            continue

        entry = A.get(key)
        if entry is None:
            rejected.append(
                f"{key}: not in the standing assumptions block. An update note "
                f"revises drivers that already exist; introducing a new driver is a "
                f"re-initiation, not an update. Add it via financial-model-assumptions.")
            continue
        if not isinstance(entry, dict):
            rejected.append(f"{key}: assumptions.{key} is not an object — the "
                            "decisions.json schema is broken, fix it before revising")
            continue

        if EVIDENCE_REQUIRED and key not in evid:
            rejected.append(
                f"{key}: no --evidence given. Every revised driver must cite the "
                f"filing, page or release it came from. An unsourced revision is how "
                f"a forecast quietly drifts to fit the share price.")
            continue

        old = entry.get("value")
        if isinstance(old, list) and not isinstance(new, list) and not args.whole_series:
            merged = list(old)
            merged[0] = new
            new_val = merged
            how = "year 1 only, remainder of the curve held"
        elif isinstance(old, list) and not isinstance(new, list) and args.whole_series:
            new_val = [new] * len(old)
            how = f"flat across all {len(old)} years"
        else:
            new_val = new
            how = "replaced"

        if old == new_val:
            continue

        changes.append({"key": key, "where": "assumptions", "from": old, "to": new_val,
                        "how": how, "why": whys.get(key), "evidence": evid.get(key),
                        "confidence": conf.get(key) or entry.get("confidence")})
        if not args.dry_run:
            entry["value"] = new_val
            if whys.get(key):
                entry.setdefault("why", []).append(
                    f"[{args.note_date}] {whys[key]}")
            if evid.get(key):
                entry.setdefault("evidence", []).append(
                    {"quote": evid[key], "source": f"update note {args.note_date}"})
            if conf.get(key):
                entry["confidence"] = conf[key]

    if rejected:
        print("REJECTED:")
        for r in rejected:
            print(f"  - {r}")
        print("\nNothing was written.")
        return 2

    if not changes:
        print("no changes — every --set value already matches decisions.json")
        return 0

    print(f"{'DRY RUN — ' if args.dry_run else ''}{len(changes)} revision(s) to {path}\n")
    for c in changes:
        print(f"  {c['key']} ({c['where']}): {c['from']!r} -> {c['to']!r}"
              + (f"   [{c['how']}]" if c.get("how") else ""))
        if c.get("why"):
            print(f"      why: {c['why']}")
        if c.get("evidence"):
            print(f"      cite: {c['evidence']}")

    if args.dry_run:
        return 0

    entry = {"date": args.note_date, "note_id": f"{dec.get('ticker', '?')}-{args.note_date}",
             "trigger": args.trigger, "rating": args.rating, "target": args.target,
             "changes": changes}
    dec.setdefault("revisions", []).append(entry)
    dec["as_of"] = args.note_date

    shutil.copy2(path, path + f".bak-{args.note_date}")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(dec, fh, indent=2)
    print(f"\nwrote {path}  (backup: {os.path.basename(path)}.bak-{args.note_date})")

    print("\nNow rebuild, in this order — assumptions.json is generated, never edited:")
    rd = args.report_dir
    sector = dec.get("sector") or "<sector>"
    drivers_moved = any(
        c["key"] in ("revenue_growth", "ebitda_margin", "ebit_margin", "gross_margin",
                     "capex_pct_sales", "dep_pct_sales", "dso", "dio", "dpo",
                     "effective_tax_rate", "interest_rate", "debt_growth")
        for c in changes)

    print(f"""
  FMA=<financial-model-assumptions skill>
  FMD=<financial-model skill>
  ERR=<equity-research-report skill>

  python3 $FMA/scripts/build_assumptions.py --in {rd}/decisions.json \\
          --outdir {rd}/data/""")
    if drivers_moved:
        print(f"""
  # a driver moved, so the three-statement model is stale too
  python3 $FMD/scripts/ingest.py --screener {rd}/data/financials.json \\
          --assumptions {rd}/data/assumptions.json \\
          -o {rd}/data/three_statement/model_input.json

  python3 $FMD/scripts/build_model.py \\
          --in  {rd}/data/three_statement/model_input.json \\
          --outdir {rd}/data/three_statement/""")
    print(f"""
  python3 $ERR/scripts/model.py {rd}/data/financials.json \\
          {rd}/data/assumptions.json --sector "{sector}" \\
          --fm {rd}/data/three_statement/model.json \\
          -o {rd}/data/model.json""")
    if drivers_moved:
        print("\n  Read the FCFF cross-check gap in that last run before you use the "
              "valuation. Above ~15% the drivers no longer fund the balance sheet they\n"
              "  imply — fix the drivers, do not split the difference.")
    print("\n  Then re-run standing.py so the note scores against the REBUILT forecast:\n"
          f"    python3 <this skill>/scripts/standing.py --ticker {dec.get('ticker', '<T>')} "
          f"--asof {args.note_date}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
