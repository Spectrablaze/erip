#!/usr/bin/env python3
"""
fetch_macro.py -- pull what can honestly be pulled, and print a worksheet for the rest.

    python3 fetch_macro.py --out reports/<T>/data/macro_raw.json
    python3 fetch_macro.py --out ... --accept-vintage      # override the WEO gate
    python3 fetch_macro.py --worksheet-only                # no network, just the to-do

WHAT IT FETCHES
  IMF WEO real GDP growth and CPI for 8 geographies, plus India's GDP in USD, GDP per
  capita, current account and government debt -- via the DBnomics mirror, because
  imf.org returns HTTP 403 to programmatic clients across the entire domain.
  World Bank India GDP growth and CPI as an independent CROSS-CHECK only. World Bank
  figures are never citable in the report; they exist to catch a mirror serving nonsense.

WHAT IT REFUSES TO DO
  Write a WEO number from an edition older than the one that should exist today.
  DBnomics lags the IMF -- at the time this skill was built its newest vintage was
  2025-04 while 2026-04 was already published. Silently emitting the old vintage is
  exactly the failure this skill exists to prevent, so the vintage gate blocks it and
  routes those figures to the manual worksheet instead.

  Everything it cannot get comes out as a worksheet line with a URL, the page, the
  table, and the field name. That degradation is the design, not a shortfall.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import registry as R  # noqa: E402

UA = {"User-Agent": "Mozilla/5.0 (india-macro-pack)"}
TIMEOUT = 60


def _get(url: str):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return json.load(resp)


# ------------------------------------------------------------------ WEO vintage gate
def available_weo_vintages() -> dict:
    """Newest vintage present for each of the two WEO dataset families."""
    codes, off = [], 0
    while True:
        d = _get(f"{R.DBNOMICS}/datasets/IMF?limit=500&offset={off}")
        docs = d["datasets"]["docs"]
        codes += [x["code"] for x in docs]
        off += len(docs)
        if not docs or off >= d["datasets"]["num_found"]:
            break
    out = {}
    for fam in ("WEO", "WEOAGG"):
        v = sorted(c.split(":", 1)[1] for c in codes
                   if c.startswith(fam + ":") and ":" in c)
        out[fam] = v[-1] if v else None
    return out


def resolve_vintage(accept_stale: bool):
    """Returns (vintage_or_None, gate_dict). vintage None => route WEO to manual."""
    expected = R.expected_weo_vintage()
    try:
        avail = available_weo_vintages()
    except Exception as e:  # network, DNS, DBnomics down -- all the same outcome
        return None, {"status": "unreachable", "expected": expected,
                      "available": None, "error": f"{type(e).__name__}: {e}"}

    common = min(x for x in avail.values() if x) if all(avail.values()) else None
    if not common:
        return None, {"status": "no_vintage", "expected": expected, "available": avail}

    if common >= expected:
        return common, {"status": "current", "expected": expected, "available": avail,
                        "using": common}

    gate = {"status": "stale_vintage", "expected": expected, "available": avail,
            "using": common if accept_stale else None,
            "message": (f"DBnomics' newest WEO vintage is {common}; the edition that "
                        f"should exist today is {expected}.")}
    return (common if accept_stale else None), gate


# ------------------------------------------------------------------ WEO fetch
def _series(dataset: str, dims: dict) -> list[dict]:
    url = (f"{R.DBNOMICS}/series/IMF/{dataset}?observations=1&dimensions="
           + urllib.parse.quote(json.dumps(dims)))
    return _get(url)["series"]["docs"]


def fetch_weo(vintage: str, years: list[int], expected: str) -> tuple[dict, list[str]]:
    """-> ({key: figure_record}, [notes]).  Two requests: aggregates, then countries.

    If `vintage` is behind `expected` (only reachable via --accept-vintage) every
    record is stamped individually, not just the file header. A per-figure stamp is
    what makes audit_macro.py able to name the offending figures later; a header
    note would be lost the moment someone copied one number out of the pack."""
    figs, notes = {}, []
    vintage_stale = vintage < expected

    subj_codes = [R.WEO_SUBJECTS[s][0] for s in R.GLOBAL_SUBJECTS]
    india_only = [R.WEO_SUBJECTS[s][0] for s in R.INDIA_EXTRA_SUBJECTS]
    code_to_subject = {v[0]: k for k, v in R.WEO_SUBJECTS.items()}

    def absorb(docs, geo_by_code, extra_ok):
        for s in docs:
            parts = s["series_code"].split(".")
            geo_code, subj_code = parts[0], parts[1]
            geo = geo_by_code.get(geo_code)
            subject = code_to_subject.get(subj_code)
            if not geo or not subject:
                continue
            if subject in R.INDIA_EXTRA_SUBJECTS and geo != "india" and not extra_ok:
                continue
            if subject == "cpi" and geo not in R.CPI_GEOS:
                continue
            obs = dict(zip(s["period"], s["value"]))
            for y in years:
                v = obs.get(str(y))
                if v is None:
                    notes.append(f"WEO {geo}/{subject}: no observation for {y}")
                    continue
                _, label, unit = R.WEO_SUBJECTS[subject]
                key = R.global_key(geo, subject, y)
                # India in WEO is fiscal-year basis, labelled by the starting year.
                fy = R.weo_year_to_fy(y) if geo == "india" else None
                fam = "WEOAGG" if geo in R.WEO_AGGREGATES else "WEO"
                rec = {
                    "key": key, "num": round(float(v), 3), "unit": unit, "label": label,
                    "geo": geo, "subject": subject, "year": y, "fy": fy,
                    "cls": "weo", "method": "fetched",
                    "period": str(y), "retrieved": date.today().isoformat(),
                    "source": f"IMF WEO {vintage}",
                    "url": R.WEO_MANUAL_URL,
                    "via": f"DBnomics mirror, IMF/{fam}:{vintage}",
                }
                if vintage_stale:
                    rec["stale_override"] = (f"WEO vintage {vintage}; edition "
                                             f"{expected} should exist")
                figs[key] = rec

    agg_by_code = {c: g for g, (c, _) in R.WEO_AGGREGATES.items()}
    ctry_by_code = {c: g for g, (c, _) in R.WEO_COUNTRIES.items()}

    absorb(_series(f"WEOAGG:{vintage}",
                   {"weo-countries-group": list(agg_by_code), "weo-subject": subj_codes}),
           agg_by_code, extra_ok=False)
    absorb(_series(f"WEO:{vintage}",
                   {"weo-country": list(ctry_by_code),
                    "weo-subject": subj_codes + india_only}),
           ctry_by_code, extra_ok=False)

    expected_keys = [R.global_key(g, "gdp", y) for g in R.GLOBAL_CHART_ORDER
                     for y in years]
    expected_keys += [R.global_key(g, "cpi", y) for g in R.CPI_GEOS for y in years]
    missing = [k for k in expected_keys if k not in figs]
    if missing:
        notes.append(f"{len(missing)} expected WEO series missing: {', '.join(missing[:6])}"
                     + (" ..." if len(missing) > 6 else ""))
    return figs, notes


# ------------------------------------------------------------------ World Bank cross-check
WB = "https://api.worldbank.org/v2"
WB_INDICATORS = {"gdp": "NY.GDP.MKTP.KD.ZG", "cpi": "FP.CPI.TOTL.ZG"}


def fetch_worldbank_crosscheck() -> tuple[dict, list[str]]:
    """India GDP growth and CPI, most recent 3 observations. Cross-check only --
    build_pack.py will not let these into macro.json as citable figures."""
    out, notes = {}, []
    for subject, ind in WB_INDICATORS.items():
        try:
            d = _get(f"{WB}/country/IND/indicator/{ind}?format=json&mrv=3")
            rows = d[1] if isinstance(d, list) and len(d) > 1 and d[1] else []
            for r in rows:
                if r.get("value") is None:
                    continue
                out[f"wb_{subject}_india_{r['date']}"] = {
                    "num": round(float(r["value"]), 3), "unit": "%",
                    "year": int(r["date"]), "subject": subject,
                    "source": f"World Bank WDI ({ind})", "method": "crosscheck",
                    "period": r["date"], "retrieved": date.today().isoformat(),
                }
        except Exception as e:
            notes.append(f"World Bank {subject} cross-check unavailable: "
                         f"{type(e).__name__}: {e}")
    return out, notes


# ------------------------------------------------------------------ worksheet
def worksheet_lines(gate: dict, weo_gated: bool) -> list[str]:
    """The 'go and read this' output. Every line must be actionable on its own."""
    L = ["", "=" * 76,
         "MANUAL WORKSHEET -- figures this run could not fetch",
         "=" * 76,
         "Fill each of these into manual.json (copy assets/manual_template.json),",
         "then run build_pack.py. Nothing below may be carried forward from a previous",
         "quarter: if it is not re-read, it does not go in the report.", ""]

    if weo_gated:
        L += ["-" * 76,
              "IMF WEO -- BLOCKED BY THE VINTAGE GATE",
              "-" * 76,
              f"  {gate.get('message', gate.get('status'))}",
              f"  Expected edition : {gate.get('expected')}",
              f"  Mirror has       : {gate.get('available')}",
              "",
              "  " + R.WEO_FALLBACK.replace(". ", ".\n  "),
              "",
              "  Needed for the page-2 chart, all three horizon years "
              f"({', '.join(str(y) for y in R.horizon_years())}):",
              "    real GDP growth for: " + ", ".join(R.GLOBAL_CHART_ORDER),
              "    CPI inflation for  : " + ", ".join(R.CPI_GEOS),
              "",
              "  Or re-run with --accept-vintage to use the older edition anyway. It will",
              "  be stamped with its true vintage everywhere and the audit will flag it.",
              ""]

    L += ["-" * 76, "INDIA FIGURES -- always manual (no free machine-readable release)",
          "-" * 76]
    for f in R.INDIA_FIGURES:
        L += [f"  [{f['key']}]  {f['label']}  ({f['unit']}, max age "
              f"{R.FRESHNESS_DAYS[f['cls']]}d)",
              f"      url   : {f['url']}",
              f"      where : {f['fallback']}",
              f"      cite  : {f['cite']}"]
        if f["note"]:
            L += [f"      why   : {f['note']}"]
        L += [""]
    return L


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="macro_raw.json")
    ap.add_argument("--accept-vintage", action="store_true",
                    help="use the mirror's WEO edition even if older than expected; "
                         "figures stay stamped with their true vintage")
    ap.add_argument("--worksheet-only", action="store_true",
                    help="skip the network entirely and just print what to look up")
    ap.add_argument("--no-crosscheck", action="store_true")
    args = ap.parse_args()

    problems = R.validate_registry()
    if problems:
        print("REGISTRY INVALID -- refusing to run:")
        for p in problems:
            print("  -", p)
        return 2

    years = R.horizon_years()
    print(f"india-macro-pack fetch  |  {date.today().isoformat()}  |  horizon {years}")

    if args.worksheet_only:
        print("\n".join(worksheet_lines({"status": "skipped"}, weo_gated=True)))
        return 0

    vintage, gate = resolve_vintage(args.accept_vintage)
    print(f"\nWEO vintage gate: {gate['status']}")
    print(f"  expected {gate.get('expected')}  |  mirror has {gate.get('available')}")

    weo, notes = {}, []
    if vintage:
        if gate["status"] == "stale_vintage":
            print(f"  ** USING {vintage} UNDER --accept-vintage. Every figure below is "
                  f"stamped 'IMF WEO {vintage}'. **")
        try:
            weo, notes = fetch_weo(vintage, years, gate["expected"])
            print(f"  fetched {len(weo)} WEO figures from IMF/{{WEO,WEOAGG}}:{vintage}")
        except Exception as e:
            notes.append(f"WEO fetch failed: {type(e).__name__}: {e}")
            print(f"  WEO fetch FAILED ({type(e).__name__}) -- routed to worksheet")
            weo = {}
    else:
        print("  -> WEO figures routed to the manual worksheet (see below)")

    cross = {}
    if not args.no_crosscheck:
        cross, cnotes = fetch_worldbank_crosscheck()
        notes += cnotes
        print(f"  World Bank cross-check: {len(cross)} observations")

    raw = {
        "generated": date.today().isoformat(),
        "horizon_years": years,
        "weo_gate": gate,
        "weo_vintage_used": vintage,
        "figures": weo,
        "crosscheck": cross,
        "manual_required": sorted(R.INDIA_FIGURE_INDEX)
                           + ([] if weo else ["__weo_block__"]),
        "notes": notes,
    }
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(raw, f, indent=2, ensure_ascii=False)
    print(f"\nwrote {args.out}")

    for n in notes:
        print(f"  note: {n}")

    print("\n".join(worksheet_lines(gate, weo_gated=not weo)))
    print(f"Next: fill manual.json, then\n"
          f"  python3 build_pack.py --raw {args.out} --manual manual.json "
          f"--root reports --ticker <T>")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
