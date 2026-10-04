#!/usr/bin/env python3
"""
kb.py — the knowledge base that makes each report better than the last.

    python3 kb.py brief   --root reports --ticker EICHERMOT --sector "two-wheelers"
    python3 kb.py alias   --root reports --canon Sales --alias "Revenue from Operations"
    python3 kb.py sector  --root reports --sector "two-wheelers" --peers "BAJAJ-AUTO,TVSMOTOR,HEROMOTOCO"
    python3 kb.py macro   --root reports --set india_gdp_fy27=6.5 --source "IMF WEO, Apr 2026"
    python3 kb.py call    --root reports --ticker EICHERMOT --target 6800 --cmp 7312 \
                          --rating REDUCE --review-months 6 --falsifier "volume growth < 8% in H1FY27"
    python3 kb.py lesson  --root reports --text "Screener labelled EBITDA as 'Operating Profit +'"
    python3 kb.py review  --root reports

WHERE THIS LIVES, AND WHY
Everything is written to <root>/_knowledge/, i.e. NEXT TO the reports — never inside
the skill directory. Re-installing or re-packaging the skill would otherwise wipe the
accumulated knowledge, and the three copies of the skill (personal, project, Cowork)
would each keep a private and diverging store.

WHAT ACCUMULATES
  macro.json      macro figures + as-of date; goes stale on a timer
  sectors/*.json  peer sets, market sizing, industry bodies, per sector
  aliases.json    Screener line-item labels learned the hard way; parse_screener
                  loads these, so a parsing failure fixed once stays fixed
  calls.json      every published target + falsifiers, with a review date — this is
                  the calibration ledger, the part that makes the loop honest
  lessons.md      append-only process learnings
"""
from __future__ import annotations

import argparse
import json
import os
import re
from datetime import date, datetime, timedelta

MACRO_MAX_AGE_DAYS = 90


# ----------------------------------------------------------------- plumbing
def kb_dir(root: str) -> str:
    d = os.path.join(root, "_knowledge")
    os.makedirs(os.path.join(d, "sectors"), exist_ok=True)
    return d


def _load(path, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default


def _save(path, obj):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-") or "unclassified"


def _today() -> str:
    return date.today().isoformat()


def _days_since(iso: str | None):
    if not iso:
        return None
    try:
        return (date.today() - datetime.fromisoformat(iso).date()).days
    except ValueError:
        return None


# ----------------------------------------------------------------- commands
def cmd_alias(args):
    """Teach the parser a Screener label it did not recognise."""
    p = os.path.join(kb_dir(args.root), "aliases.json")
    data = _load(p, {})
    lst = data.setdefault(args.canon, [])
    if args.alias in lst:
        print(f"already known: {args.canon} <- {args.alias!r}")
        return
    lst.append(args.alias)
    _save(p, data)
    print(f"learned: {args.canon} <- {args.alias!r}")
    print("parse_screener.py picks this up automatically on the next run.")


def cmd_sector(args):
    p = os.path.join(kb_dir(args.root), "sectors", f"{_slug(args.sector)}.json")
    s = _load(p, {"sector": args.sector, "peers": [], "bodies": [], "notes": [],
                  "market_size": {}, "archetypes": [], "updated": None})
    s.setdefault("archetypes", [])
    for x in getattr(args, "archetype", None) or []:
        if x not in s["archetypes"]:
            s["archetypes"].append(x)
    if args.peers:
        for x in [t.strip() for t in args.peers.split(",") if t.strip()]:
            if x not in s["peers"]:
                s["peers"].append(x)
    if args.body:
        for x in args.body:
            if x not in s["bodies"]:
                s["bodies"].append(x)
    if args.note:
        for x in args.note:
            s["notes"].append({"date": _today(), "text": x})
    if args.market_size:
        for kv in args.market_size:
            k, _, v = kv.partition("=")
            s["market_size"][k.strip()] = v.strip()
    s["updated"] = _today()
    _save(p, s)
    print(f"sector '{s['sector']}' -> {p}")
    print(f"  peers: {', '.join(s['peers']) or '(none)'}")
    print(f"  bodies: {', '.join(s['bodies']) or '(none)'}  notes: {len(s['notes'])}")
    if s["archetypes"]:
        print(f"  archetypes used: {', '.join(s['archetypes'])}")


def cmd_macro(args):
    p = os.path.join(kb_dir(args.root), "macro.json")
    m = _load(p, {"as_of": None, "figures": {}, "sources": []})
    for kv in args.set or []:
        k, _, v = kv.partition("=")
        m["figures"][k.strip()] = {"value": v.strip(),
                                   "source": args.source or "unattributed",
                                   "recorded": _today()}
    if args.source and args.source not in m["sources"]:
        m["sources"].append(args.source)
    m["as_of"] = _today()
    _save(p, m)
    print(f"macro updated ({len(m['figures'])} figures), as_of {m['as_of']}")
    unattributed = [k for k, v in m["figures"].items() if v.get("source") == "unattributed"]
    if unattributed:
        print(f"  ! no source recorded for: {', '.join(unattributed)}")


def cmd_call(args):
    """Record a published call so it can be scored later. This is the honest part."""
    p = os.path.join(kb_dir(args.root), "calls.json")
    calls = _load(p, [])
    review = (date.today() + timedelta(days=30 * int(args.review_months))).isoformat()
    calls.append({
        "ticker": args.ticker, "date": _today(), "rating": args.rating,
        "target": args.target, "cmp_at_call": args.cmp,
        "thesis": args.thesis, "falsifiers": args.falsifier or [],
        "review_on": review, "outcome": None,
    })
    _save(p, calls)
    print(f"recorded {args.rating} on {args.ticker}: TP {args.target} vs CMP {args.cmp}")
    print(f"  review due {review}  ({len(args.falsifier or [])} falsifiers logged)")


def cmd_close(args):
    """Score a past call once the review date has passed."""
    p = os.path.join(kb_dir(args.root), "calls.json")
    calls = _load(p, [])
    open_calls = [c for c in calls if c["ticker"].upper() == args.ticker.upper()
                  and c["outcome"] is None]
    if not open_calls:
        print(f"no open call on {args.ticker}")
        return
    c = open_calls[-1]
    err = None
    if c.get("target") and args.actual:
        err = round((float(args.actual) / float(c["target"]) - 1) * 100, 1)
    c["outcome"] = {"closed": _today(), "actual_price": args.actual,
                    "target_error_%": err, "note": args.note}
    _save(p, calls)
    print(f"closed {c['rating']} on {args.ticker} ({c['date']}): "
          f"TP {c['target']} vs actual {args.actual}"
          + (f"  -> {err:+.1f}% error" if err is not None else ""))


def cmd_lesson(args):
    p = os.path.join(kb_dir(args.root), "lessons.md")
    new = not os.path.exists(p)
    with open(p, "a", encoding="utf-8") as f:
        if new:
            f.write("# Lessons\n\nAppend-only. One line per learning, newest last.\n\n")
        tag = f" _[{args.tag}]_" if args.tag else ""
        f.write(f"- **{_today()}**{tag} {args.text}\n")
    print(f"logged -> {p}")


def cmd_brief(args):
    """Print everything already known that bears on this report. Run in Phase 0."""
    d = kb_dir(args.root)
    print("=" * 68)
    print(f"KNOWLEDGE BRIEF  —  {args.ticker or '(no ticker)'}"
          + (f"  |  sector: {args.sector}" if args.sector else ""))
    print("=" * 68)

    # --- macro, with staleness ---
    m = _load(os.path.join(d, "macro.json"), None)
    if not m or not m.get("figures"):
        print("\nMACRO: nothing stored. Research it in Phase 4 and record with "
              "`kb.py macro --set k=v --source ...`.")
    else:
        age = _days_since(m.get("as_of"))
        stale = age is not None and age > MACRO_MAX_AGE_DAYS
        print(f"\nMACRO  (as of {m.get('as_of')}, {age} days old)"
              + ("   ** STALE — refresh before use **" if stale else ""))
        for k, v in m["figures"].items():
            print(f"  {k:<28} {v['value']:<12} [{v.get('source','?')}]")
        if stale:
            print(f"  Older than {MACRO_MAX_AGE_DAYS} days. Re-research and re-record; "
                  "do not copy these into a new report.")

    # --- sector ---
    if args.sector:
        sp = os.path.join(d, "sectors", f"{_slug(args.sector)}.json")
        s = _load(sp, None)
        if not s:
            print(f"\nSECTOR '{args.sector}': nothing stored yet — this report will "
                  "create it.")
        else:
            print(f"\nSECTOR '{s['sector']}'  (updated {s.get('updated')})")
            print(f"  peer set     : {', '.join(s.get('peers') or []) or '(none)'}")
            print(f"  industry bodies: {', '.join(s.get('bodies') or []) or '(none)'}")
            if s.get("archetypes"):
                print(f"  archetypes used before: {', '.join(s['archetypes'])}"
                      "   (a starting point for modeling-strategy, not a verdict)")
            for k, v in (s.get("market_size") or {}).items():
                print(f"  market size  : {k} = {v}")
            for n in (s.get("notes") or [])[-6:]:
                print(f"  note ({n['date']}): {n['text']}")
    else:
        secs = sorted(os.listdir(os.path.join(d, "sectors")))
        if secs:
            print("\nSECTORS on file: " + ", ".join(x[:-5] for x in secs if x.endswith(".json")))

    # --- learned parser aliases ---
    al = _load(os.path.join(d, "aliases.json"), {})
    if al:
        total = sum(len(v) for v in al.values())
        print(f"\nLEARNED SCREENER ALIASES: {total} across {len(al)} line items "
              "(loaded automatically by parse_screener.py)")

    # --- prior coverage of this name ---
    calls = _load(os.path.join(d, "calls.json"), [])
    mine = [c for c in calls if args.ticker and c["ticker"].upper() == args.ticker.upper()]
    if mine:
        print(f"\nPRIOR COVERAGE OF {args.ticker.upper()}:")
        for c in mine:
            oc = c.get("outcome")
            tail = (f"closed {oc['closed']}, error {oc['target_error_%']:+}%"
                    if oc and oc.get("target_error_%") is not None
                    else (f"closed {oc['closed']}" if oc else f"OPEN, review {c['review_on']}"))
            print(f"  {c['date']}  {c['rating']:<8} TP {c['target']} (CMP {c['cmp_at_call']}) — {tail}")
            for fx in c.get("falsifiers") or []:
                print(f"      falsifier: {fx}")
        print("  Re-read the old thesis before writing a new one. If the rating changes, "
              "say what changed and why.")

    # --- calibration + due reviews ---
    _print_calibration(calls)
    due = [c for c in calls if c["outcome"] is None
           and (_days_since(c["review_on"]) or -1) >= 0]
    if due:
        print(f"\n** {len(due)} CALL(S) DUE FOR REVIEW — score before starting new work **")
        for c in due:
            print(f"  {c['ticker']:<12} {c['rating']:<8} TP {c['target']} "
                  f"set {c['date']}, review was {c['review_on']}")
        print("  Close each with: kb.py close --ticker X --actual <price> --note '...'")

    # --- lessons ---
    lp = os.path.join(d, "lessons.md")
    if os.path.exists(lp):
        lines = [l for l in open(lp, encoding="utf-8").read().splitlines()
                 if l.startswith("- ")]
        if lines:
            print(f"\nLESSONS ({len(lines)} logged, last 8):")
            for l in lines[-8:]:
                print("  " + l[2:])
    print()


def _print_calibration(calls):
    closed = [c for c in calls if c.get("outcome")
              and c["outcome"].get("target_error_%") is not None]
    if not closed:
        return
    errs = [c["outcome"]["target_error_%"] for c in closed]
    mean = sum(errs) / len(errs)
    mae = sum(abs(e) for e in errs) / len(errs)
    print(f"\nCALIBRATION over {len(closed)} closed call(s):")
    print(f"  mean error {mean:+.1f}%   mean ABSOLUTE error {mae:.1f}%")
    if mean > 10:
        print("  Targets have run consistently BELOW the outcome — persistently "
              "conservative. Check whether terminal growth or exit margins are too low.")
    elif mean < -10:
        print("  Targets have run consistently ABOVE the outcome — persistently "
              "optimistic. Check terminal growth, exit margins and the TV share of EV.")
    else:
        print("  No systematic directional bias.")


def cmd_review(args):
    calls = _load(os.path.join(kb_dir(args.root), "calls.json"), [])
    if not calls:
        print("no calls recorded yet")
        return
    _print_calibration(calls)
    op = [c for c in calls if c["outcome"] is None]
    print(f"\n{len(op)} open call(s):")
    for c in op:
        d = _days_since(c["review_on"])
        flag = "  ** DUE **" if (d or -1) >= 0 else ""
        print(f"  {c['ticker']:<12} {c['rating']:<8} TP {c['target']:<8} "
              f"review {c['review_on']}{flag}")


def load_aliases(root: str) -> dict:
    """Used by parse_screener.py — learned Screener labels."""
    return _load(os.path.join(root, "_knowledge", "aliases.json"), {})


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--root", default="reports", help="reports directory (default: reports)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("brief", help="what is already known (run in Phase 0)")
    b.add_argument("--ticker"); b.add_argument("--sector")
    b.set_defaults(fn=cmd_brief)

    a = sub.add_parser("alias", help="teach the parser a Screener label")
    a.add_argument("--canon", required=True); a.add_argument("--alias", required=True)
    a.set_defaults(fn=cmd_alias)

    s = sub.add_parser("sector", help="record sector peers / bodies / sizing")
    s.add_argument("--sector", required=True); s.add_argument("--peers")
    s.add_argument("--body", action="append"); s.add_argument("--note", action="append")
    s.add_argument("--market-size", action="append", dest="market_size")
    s.add_argument("--archetype", action="append",
                   help="the economic driver archetype this sector's companies were "
                        "actually modelled on (a modeling-strategy key)")
    s.set_defaults(fn=cmd_sector)

    m = sub.add_parser("macro", help="record macro figures with a source")
    m.add_argument("--set", action="append", required=True)
    m.add_argument("--source")
    m.set_defaults(fn=cmd_macro)

    c = sub.add_parser("call", help="log a published target for later scoring")
    c.add_argument("--ticker", required=True); c.add_argument("--rating", required=True)
    c.add_argument("--target", type=float); c.add_argument("--cmp", type=float)
    c.add_argument("--thesis"); c.add_argument("--falsifier", action="append")
    c.add_argument("--review-months", default=6)
    c.set_defaults(fn=cmd_call)

    cl = sub.add_parser("close", help="score a past call")
    cl.add_argument("--ticker", required=True); cl.add_argument("--actual", type=float)
    cl.add_argument("--note")
    cl.set_defaults(fn=cmd_close)

    le = sub.add_parser("lesson", help="append a process learning")
    le.add_argument("--text", required=True); le.add_argument("--tag")
    le.set_defaults(fn=cmd_lesson)

    r = sub.add_parser("review", help="calibration + open calls")
    r.set_defaults(fn=cmd_review)

    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
