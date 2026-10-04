#!/usr/bin/env python3
"""
rating.py — apply the house rating policy and print the reason chain.

    python3 rating.py --standing .../standing.json --variance .../variance.json \
                      --falsifiers .../falsifiers.json --new-target 5850 --cmp 4920

THE POLICY (hybrid: falsifier gates, band sets the letter)

  1. A rating change requires a THESIS REASON. There are exactly three:
        a) a logged falsifier has tripped;
        b) a tracked line breached tolerance in variance.py;
        c) an explicit analyst reason passed with --thesis-reason, which must
           name what changed in the business, not what changed in the price.
  2. Given a thesis reason, the letter is then MECHANICAL — it falls out of the
     upside to the re-struck target against the current price:
        BUY  > +15% | HOLD -10% to +15% | SELL < -10%      (override in decisions.json)
  3. Without a thesis reason the note REITERATES the standing rating. Price
     drift alone never changes the rating; it changes the upside line only.

WHY THE DIVERGENCE COUNTER EXISTS
  Rule 3 has an obvious failure mode: a BUY reiterated quarter after quarter at
  40% upside long after the market has repriced it, or a BUY sitting on -20%
  upside that nobody will downgrade because no falsifier ever tripped. So every
  time the band letter disagrees with the reiterated rating, the note records a
  divergence. At DIVERGENCE_LIMIT consecutive divergences the script stops
  returning a clean reiterate and demands the analyst either name a thesis
  reason or close the call as wrong. An unfalsifiable rating is not a rating.

Exit codes
  0  decision reached (reiterate or change)
  1  divergence limit hit — the note cannot ship as a plain reiterate
  3  missing or unusable input
"""
from __future__ import annotations

import argparse
import json
import os
import sys

# Upside thresholds, in percent, against the re-struck target.
BANDS = {"buy_above": 15.0, "sell_below": -10.0}
DIVERGENCE_LIMIT = 3
LETTERS = ["BUY", "HOLD", "SELL"]


def _load(path, what, required=True):
    if not path:
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except OSError:
        if required:
            sys.exit(f"cannot read {what}: {path}")
        return None
    except json.JSONDecodeError as exc:
        sys.exit(f"{what} is not valid JSON ({path}): {exc}")


def normalise(rating: str | None) -> str | None:
    if not rating:
        return None
    r = rating.strip().upper()
    alias = {"ACCUMULATE": "BUY", "ADD": "BUY", "OUTPERFORM": "BUY", "OVERWEIGHT": "BUY",
             "NEUTRAL": "HOLD", "MARKETPERFORM": "HOLD", "EQUALWEIGHT": "HOLD",
             "REDUCE": "SELL", "UNDERPERFORM": "SELL", "UNDERWEIGHT": "SELL"}
    return alias.get(r.replace(" ", ""), r if r in LETTERS else r)


def band_letter(upside_pct: float, bands: dict) -> str:
    if upside_pct > bands["buy_above"]:
        return "BUY"
    if upside_pct < bands["sell_below"]:
        return "SELL"
    return "HOLD"


def divergence_streak(report_dir: str, note_date: str) -> int:
    """Consecutive prior notes whose band disagreed with the reiterated rating."""
    updir = os.path.join(report_dir, "updates")
    if not os.path.isdir(updir):
        return 0
    dates = sorted(d for d in os.listdir(updir)
                   if os.path.isdir(os.path.join(updir, d)) and d < str(note_date))
    streak = 0
    for d in reversed(dates):
        r = _load(os.path.join(updir, d, "rating.json"), "prior rating", required=False)
        if not r:
            break
        if r.get("divergence"):
            streak += 1
        else:
            break
    return streak


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--standing", required=True)
    ap.add_argument("--variance", help="variance.json (omit for an event-driven note "
                                       "with no results attached)")
    ap.add_argument("--falsifiers", help="falsifiers.json — the Phase 3 adjudication")
    ap.add_argument("--new-target", type=float,
                    help="re-struck target. Omit to carry the standing target forward.")
    ap.add_argument("--cmp", type=float, required=True, help="current market price")
    ap.add_argument("--thesis-reason", action="append", default=[],
                    help="analyst reason a rating may change; name the business "
                         "change, not the price move. Repeatable.")
    ap.add_argument("--out", help="default: rating.json beside standing.json")
    args = ap.parse_args()

    st = _load(args.standing, "standing.json")
    va = _load(args.variance, "variance.json", required=False)
    fa = _load(args.falsifiers, "falsifiers.json", required=False)

    bands = dict(BANDS)
    bands.update({k: float(v) for k, v in (st.get("rating_bands") or {}).items()
                  if k in BANDS})
    if bands["sell_below"] >= bands["buy_above"]:
        sys.exit("rating_bands are inverted: sell_below must be below buy_above")

    call = st.get("call") or {}
    standing_rating = normalise(call.get("rating"))
    standing_target = call.get("target")
    target = args.new_target if args.new_target is not None else standing_target
    if target is None:
        sys.exit("no target: the standing call has none and --new-target was not given")
    if not args.cmp:
        sys.exit("--cmp must be non-zero")

    upside = round((float(target) / float(args.cmp) - 1) * 100, 1)
    letter = band_letter(upside, bands)

    # ---- gate 1: is there a thesis reason? -------------------------------
    reasons = []
    tripped = [f for f in (fa or {}).get("falsifiers", [])
               if str(f.get("status", "")).lower() == "tripped"]
    for f in tripped:
        reasons.append({"kind": "falsifier_tripped", "detail": f.get("text"),
                        "evidence": f.get("evidence")})
    for b in (va or {}).get("breaches", []):
        reasons.append({"kind": "tolerance_breach", "detail": b, "evidence": None})
    for r in args.thesis_reason:
        reasons.append({"kind": "analyst", "detail": r, "evidence": None})

    unassessed = [f for f in (fa or {}).get("falsifiers", [])
                  if str(f.get("status", "")).lower() in ("", "unassessed")]

    # ---- gate 2: decide --------------------------------------------------
    prior_streak = divergence_streak(st.get("report_dir") or ".", st.get("note_date"))
    if reasons:
        action = "CHANGE" if letter != standing_rating else "REITERATE"
        rating = letter
        divergence = False
        streak = 0
    else:
        rating = standing_rating
        action = "REITERATE"
        divergence = (letter != standing_rating)
        streak = prior_streak + 1 if divergence else 0

    forced = divergence and streak >= DIVERGENCE_LIMIT

    out = {
        "note_id": st.get("note_id"),
        "ticker": st.get("ticker"),
        "note_date": st.get("note_date"),
        "policy": "hybrid: falsifier gates, band sets the letter",
        "bands": bands,
        "standing": {"rating": standing_rating, "target": standing_target},
        "cmp": args.cmp,
        "target": float(target),
        "target_change_pct": (None if not standing_target else
                              round((float(target) / float(standing_target) - 1) * 100, 1)),
        "upside_pct": upside,
        "band_letter": letter,
        "thesis_reasons": reasons,
        "rating": rating,
        "action": action,
        "divergence": divergence,
        "divergence_streak": streak,
        "divergence_limit": DIVERGENCE_LIMIT,
        "forced_review": forced,
        "unassessed_falsifiers": [f.get("text") for f in unassessed],
    }

    outp = args.out or os.path.join(os.path.dirname(os.path.abspath(args.standing)),
                                    "rating.json")
    with open(outp, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)

    # ---- audit trail -----------------------------------------------------
    print("=" * 68)
    print(f"RATING DECISION — {out['ticker']}  {out['note_date']}")
    print("=" * 68)
    print(f"  standing      {standing_rating}  TP {standing_target}")
    if args.new_target is None:
        print(f"  target        {target}  (standing target carried forward)")
    else:
        print(f"  re-struck TP  {target}"
              + (f"  ({out['target_change_pct']:+.1f}% vs standing)"
                 if out["target_change_pct"] is not None else ""))
    print(f"  CMP           {args.cmp}   ->  upside {upside:+.1f}%")
    print(f"  band letter   {letter}   "
          f"(BUY >{bands['buy_above']:+.0f}%, SELL <{bands['sell_below']:+.0f}%)")
    print()
    if reasons:
        print(f"  THESIS REASON PRESENT ({len(reasons)}) — the band is allowed to set "
              "the letter:")
        for r in reasons:
            ev = f"  [{r['evidence']}]" if r.get("evidence") else ""
            print(f"    - {r['kind']}: {r['detail']}{ev}")
    else:
        print("  NO THESIS REASON — no falsifier tripped, no tolerance breached, no "
              "analyst reason given.")
        print("  Price drift alone does not move a rating. Reiterating.")
    print()
    print(f"  ==> {action}  {rating}   TP {target}")

    if unassessed:
        print(f"\n  ! {len(unassessed)} falsifier(s) still unassessed — the gate ran "
              "without them:")
        for t in unassessed:
            print(f"      {t}")
        print("  Adjudicate every falsifier before this note ships.")

    if divergence:
        print(f"\n  ! DIVERGENCE {streak}/{DIVERGENCE_LIMIT}: the band says {letter}, "
              f"the note reiterates {standing_rating}.")
        print("  That is legitimate once — the thesis has a horizon the price has not "
              "run yet. Say so in the note, in one sentence, naming the horizon.")
    if forced:
        print(f"\n  ** BLOCKED: {streak} consecutive notes have reiterated {rating} "
              f"against a band that says {letter}.")
        print("  A rating nothing can change is not a rating. This note must either:")
        print(f"    (a) name a thesis reason and re-rate to {letter}; or")
        print("    (b) close the call as wrong (kb.py close) and re-initiate; or")
        print("    (c) re-strike the target so the band and the rating agree, and "
              "explain what in the model changed.")
        print(f"\nwrote {outp}")
        return 1

    print(f"\nwrote {outp}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
