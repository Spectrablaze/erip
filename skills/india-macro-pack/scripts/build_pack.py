#!/usr/bin/env python3
"""
build_pack.py -- merge fetched + manual figures into the three deliverables.

    python3 build_pack.py --raw macro_raw.json --manual manual.json \
                          --root reports --out-dir reports/<T>

WRITES
  <root>/_knowledge/macro.json   kb.py's format, so `kb.py brief` reads it unchanged
  <out-dir>/macro_pack.md        the cited pack, laid out against blueprint pages 2-9
  <out-dir>/data/macro_charts.json   a charts.py spec for the two macro exhibits

THE ONE RULE
  A figure reaches macro.json only if it carries a source AND an observation period,
  and only if that period is inside the freshness window for its class. Anything else
  is refused and listed under "NOT IN THIS PACK" in macro_pack.md, with the URL and
  field name needed to go and get it. There is no path through this script that
  produces a number without provenance.

CARRY-FORWARD
  macro.json is a single shared store (kb.py keeps one file for all reports). A figure
  already in it that this run did not refresh is kept -- losing it would be worse --
  but re-stamped `method: "carried_forward"` and its original period is preserved, so
  audit_macro.py and the pack's provenance table both show its true age. It is never
  silently renewed.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import registry as R  # noqa: E402


def _load(path, default=None, label=""):
    """Missing is fine (the caller decides); malformed is not, and must say so by
    name -- a JSONDecodeError traceback on a hand-edited manual.json is the least
    helpful thing this script could produce."""
    if not path or not os.path.exists(path):
        return default
    try:
        with open(path, encoding="utf-8") as f:
            txt = f.read().strip()
        return json.loads(txt) if txt else default
    except json.JSONDecodeError as e:
        print(f"ERROR: {label or path} is not valid JSON -- {e}")
        print(f"  fix {path} and re-run. Nothing was written.")
        raise SystemExit(2)


def _fmt(num, unit):
    if num is None:
        return "n/a"
    if unit == "%" or unit.endswith("of GDP"):
        return f"{num:.1f}%"
    if unit == "USD bn":
        return f"US${num:,.0f}bn"
    if unit == "USD":
        return f"US${num:,.0f}"
    if unit == "USD/bbl":
        return f"US${num:.1f}/bbl"
    if unit == "INR":
        return f"Rs {num:,.0f}" if abs(num) >= 1000 else f"Rs {num:,.2f}"
    return f"{num:,.2f} {unit}".strip()


# ------------------------------------------------------------------ validation
def check_figure(rec, allow_stale):
    """-> (ok, [reasons]). The gate every figure passes through."""
    bad = []
    if rec.get("num") is None and not str(rec.get("value", "")).strip():
        bad.append("no value")
    src = (rec.get("source") or "").strip()
    if not src or src.lower() in {"unattributed", "tbd", "?"}:
        bad.append("no source")
    period = rec.get("period")
    if not period:
        bad.append("no observation period (which month/quarter/year is this?)")
    else:
        age = R.days_old(period)
        limit = R.effective_limit(rec.get("cls", "monthly"), rec.get("lag"))
        if age is None:
            bad.append(f"unparseable period {period!r}")
        elif age < 0 and rec.get("cls") != "weo":
            # WEO series legitimately observe future years -- they are forecasts.
            # Nothing else can. The usual cause is an Indian FY written as a bare
            # year: FY26 ended 31 March 2026, so it is period '2026-03', not '2026'
            # (which this code reads as 31 December 2026).
            bad.append(f"period {period!r} is in the future. For an Indian fiscal "
                       f"year use the FY-END month, e.g. FY26 -> '2026-03'")
        elif age > limit and not allow_stale:
            bad.append(f"observation {age}d old; limit {limit}d "
                       f"(class '{rec.get('cls')}' + {rec.get('lag', 0)}d publication lag)")
    return (not bad), bad


def normalise_weo_manual(manual):
    """Manually-read WEO figures, from the `weo` block of manual.json.

    This is the other half of the vintage gate. When the gate blocks the mirror, the
    worksheet sends the analyst to imf.org -- and those figures have to be able to come
    back in. Without this block the gate would be a dead end and the only way past it
    would be --accept-vintage, which is exactly the wrong incentive.

    One `vintage` string covers every figure in the block, because they all come off the
    same WEO edition; typing it once is also the only way it stays consistent."""
    out, errors = {}, []
    w = manual.get("weo") or {}
    if not w:
        return out, errors
    vintage = str(w.get("vintage") or "").strip()
    if not vintage:
        errors.append("weo block has no `vintage` (e.g. '2026-04'). The edition IS the "
                      "citation -- 'IMF WEO' without a month is not a source.")
        return out, errors
    # An UNFILLED template is not an empty one. `vintage` still carries the literal
    # 'YYYY-MM' placeholder, which is truthy, so the emptiness test above passes it
    # and every figure in the block lands in macro.json cited to 'IMF WEO YYYY-MM'.
    # The figures block already refuses placeholder periods; this is the same rule.
    if not re.fullmatch(r"\d{4}-\d{2}", vintage):
        errors.append(f"weo vintage {vintage!r} is not a real edition (expected e.g. "
                      "'2026-04'). The block looks unfilled -- fill it from the manual "
                      "worksheet or delete it; it must not reach the report.")
        return out, errors
    # A wholly zero block is the other shape an unfilled template takes.
    numbers = [v for subj, by_geo in w.items() if subj != "vintage"
               for by_year in (by_geo or {}).values()
               for v in (by_year or {}).values()
               if isinstance(v, (int, float))]
    if numbers and not any(numbers):
        errors.append("every WEO figure in the manual block is 0.0 -- the block is "
                      "unfilled. Fill it or delete it; a 0.0% growth forecast cited to "
                      "the IMF is worse than a missing one.")
        return out, errors
    expected = R.expected_weo_vintage()
    known_geo = set(R.WEO_AGGREGATES) | set(R.WEO_COUNTRIES)

    for subject, by_geo in w.items():
        if subject == "vintage":
            continue
        if subject not in R.WEO_SUBJECTS:
            errors.append(f"weo: unknown subject {subject!r}; expected one of "
                          f"{', '.join(sorted(R.WEO_SUBJECTS))}")
            continue
        _, label, unit = R.WEO_SUBJECTS[subject]
        for geo, by_year in (by_geo or {}).items():
            if geo not in known_geo:
                errors.append(f"weo/{subject}: unknown geography {geo!r}; expected one "
                              f"of {', '.join(sorted(known_geo))}")
                continue
            for year, val in (by_year or {}).items():
                try:
                    num, y = float(val), int(year)
                except (TypeError, ValueError):
                    errors.append(f"weo/{subject}/{geo}/{year}: {val!r} is not a number")
                    continue
                key = R.global_key(geo, subject, y)
                rec = {
                    "key": key, "num": round(num, 3), "unit": unit, "label": label,
                    "geo": geo, "subject": subject, "year": y,
                    "fy": R.weo_year_to_fy(y) if geo == "india" else None,
                    "cls": "weo", "lag": 0, "method": "manual",
                    "period": str(y), "retrieved": date.today().isoformat(),
                    "source": f"IMF WEO {vintage}", "url": R.WEO_MANUAL_URL,
                }
                if vintage < expected:
                    rec["stale_override"] = (f"WEO vintage {vintage}; edition {expected} "
                                             "should exist")
                out[key] = rec
    return out, errors


def normalise_manual(manual):
    """Turn the manual.json entries into full figure records."""
    out, errors = {}, []
    for key, m in (manual.get("figures") or {}).items():
        spec = R.INDIA_FIGURE_INDEX.get(key)
        if not spec:
            errors.append(f"unknown figure key {key!r} -- not in the registry. "
                          "Add it to registry.py rather than inventing a key here, or "
                          "the store fragments across quarters.")
            continue
        try:
            num = float(m["value"])
        except (KeyError, TypeError, ValueError):
            num = None
        out[key] = {
            "key": key, "num": num, "unit": spec["unit"], "label": spec["label"],
            "cls": spec["cls"], "lag": spec["lag"], "method": "manual",
            "period": m.get("period"), "retrieved": m.get("retrieved") or date.today().isoformat(),
            "source": m.get("source", ""), "url": m.get("url") or spec["url"],
            "owner": spec["owner"], "note": m.get("note") or spec["note"],
        }
    for i, m in enumerate(manual.get("industry") or []):
        key = m.get("key") or f"industry_{i}"
        try:
            num = float(m["value"])
        except (KeyError, TypeError, ValueError):
            num = None
        out[key] = {
            "key": key, "num": num, "unit": m.get("unit", ""),
            "label": m.get("label", key), "cls": "industry",
            "lag": R.DEFAULT_LAG["industry"], "method": "manual",
            "period": m.get("period"), "retrieved": date.today().isoformat(),
            "source": m.get("source", ""), "url": m.get("url", ""),
            "owner": m.get("body", ""), "note": m.get("note", ""),
            "forecast_year": m.get("forecast_year"),
        }
    return out, errors


# ------------------------------------------------------------------ merge
def merge(raw, manual_figs, root, allow_stale):
    accepted, refused = {}, {}
    incoming = dict(raw.get("figures") or {})
    incoming.update(manual_figs)

    for k, rec in incoming.items():
        ok, why = check_figure(rec, allow_stale)
        if ok:
            rec = dict(rec)
            if allow_stale:
                age = R.days_old(rec.get("period"))
                limit = R.effective_limit(rec.get("cls", "monthly"), rec.get("lag"))
                if age is not None and age > limit:
                    rec["stale_override"] = f"{age}d old vs {limit}d limit"
            accepted[k] = rec
        else:
            refused[k] = why

    # Carry forward anything already stored that this run did not refresh.
    prev = _load(os.path.join(root, "_knowledge", "macro.json"), {}) or {}
    carried = {}
    for k, v in (prev.get("figures") or {}).items():
        if k in accepted:
            continue
        v = dict(v)
        v["method"] = "carried_forward"
        v.setdefault("period", v.get("recorded"))
        carried[k] = v
    return accepted, refused, carried


def to_kb_format(accepted, carried, weo_gate):
    """kb.py reads figures[k]['value'] (a string) and ['source']. Extra keys survive
    json round-tripping untouched, so the richer record rides along with it."""
    figures = {}
    for k, r in list(accepted.items()) + list(carried.items()):
        val = r.get("value") if r.get("num") is None else _fmt(r["num"], r.get("unit", ""))
        figures[k] = {
            "value": str(val),
            "source": r.get("source", "unattributed"),
            "recorded": r.get("retrieved") or date.today().isoformat(),
            # --- extensions, ignored by kb.py, used by audit_macro.py ---
            "num": r.get("num"), "unit": r.get("unit", ""), "label": r.get("label", ""),
            "period": r.get("period"), "cls": r.get("cls", ""), "lag": r.get("lag", 0),
            "method": r.get("method", ""), "url": r.get("url", ""),
            "geo": r.get("geo"), "subject": r.get("subject"), "year": r.get("year"),
            "fy": r.get("fy"), "note": r.get("note", ""),
            "stale_override": r.get("stale_override"),
        }
    sources = sorted({r.get("source") for r in figures.values() if r.get("source")})
    return {
        "as_of": date.today().isoformat(),
        "figures": figures,
        "sources": sources,
        "_pack": {
            "built_by": "india-macro-pack/build_pack.py",
            "weo_gate": weo_gate,
            "freshness_policy_days": R.FRESHNESS_DAYS,
            "carried_forward": sorted(carried),
        },
    }


# ------------------------------------------------------------------ charts spec
def charts_spec(accepted, outdir, years):
    """Two exhibits, matching blueprint rows 2 and 3."""
    charts, series = [], {}
    have_any = False
    for y in years:
        lab = f"{y}A" if y == years[0] else f"{y}P"
        col = []
        for geo in R.GLOBAL_CHART_ORDER:
            rec = accepted.get(R.global_key(geo, "gdp", y))
            col.append(rec["num"] if rec else None)
        if any(v is not None for v in col):
            have_any = True
        series[lab] = col
    cats = [R.WEO_AGGREGATES.get(g, R.WEO_COUNTRIES.get(g, (None, g)))[1]
            for g in R.GLOBAL_CHART_ORDER]

    if have_any and not any(None in v for v in series.values()):
        charts.append({"fn": "bar_grouped", "args": {
            "name": "macro_global_gdp", "categories": cats, "series": series,
            "horizontal": True, "pct": True, "w": 3.5, "h": 2.4}})

    ind = [accepted.get(R.global_key("india", "gdp", y)) for y in years]
    wor = [accepted.get(R.global_key("world", "gdp", y)) for y in years]
    if all(ind) and all(wor):
        charts.append({"fn": "line_multi", "args": {
            "name": "macro_india_vs_world",
            "x": [f"{y}A" if y == years[0] else f"{y}P" for y in years],
            "series": {"India": [r["num"] for r in ind],
                       "World": [r["num"] for r in wor]},
            "pct": True, "w": 3.5, "h": 2.4}})

    return {"outdir": outdir, "charts": charts}


# ------------------------------------------------------------------ macro_pack.md
def render_pack(kb, accepted, refused, carried, raw, years, ticker):
    A = accepted
    gate = raw.get("weo_gate") or {}
    L = [f"# Macro pack{f' — {ticker}' if ticker else ''}",
         "",
         f"Built {date.today().isoformat()} by `india-macro-pack`. "
         f"Horizon: {years[0]}A / {years[1]}P / {years[2]}P.",
         "",
         "Every figure below is quotable as written — value, source and observation "
         "period travel together. Figures that could not be sourced are listed in "
         "§6, not silently omitted.",
         ""]

    if gate.get("status") != "current":
        L += ["> **IMF WEO vintage warning.** "
              f"{gate.get('message') or gate.get('status')} "
              f"Expected `{gate.get('expected')}`, mirror has `{gate.get('available')}`. "
              + ("WEO figures in this pack were entered manually from imf.org."
                 if raw.get("weo_vintage_used") is None
                 else f"WEO figures carry vintage `{raw.get('weo_vintage_used')}` and are "
                      "flagged in §5."),
              ""]

    # ---- §1 Global economy (blueprint page 2)
    L += ["## 1. Global economy — blueprint page 2", ""]
    gdp_rows = [g for g in R.GLOBAL_CHART_ORDER
                if any(R.global_key(g, "gdp", y) in A for y in years)]
    if gdp_rows:
        L += ["Real GDP growth, % y-o-y.", "",
              "| Geography | " + " | ".join(f"{y}{'A' if y == years[0] else 'P'}"
                                            for y in years) + " | Source |",
              "|---|" + "---|" * (len(years) + 1)]
        for g in gdp_rows:
            name = R.WEO_AGGREGATES.get(g, R.WEO_COUNTRIES.get(g, (None, g)))[1]
            cells, src = [], ""
            for y in years:
                r = A.get(R.global_key(g, "gdp", y))
                cells.append(f"{r['num']:.1f}" if r else "—")
                src = src or (r or {}).get("source", "")
            L.append(f"| {name} | " + " | ".join(cells) + f" | {src or '—'} |")
        L += ["", "Exhibit: `macro_global_gdp` (`bar_grouped`, horizontal) — already "
                  "written into `data/macro_charts.json`.", ""]
    else:
        L += ["_No WEO GDP figures sourced. See §6._", ""]

    # ---- §2 Indian economy (blueprint page 3)
    L += ["## 2. Indian economy — blueprint page 3", ""]
    kpi_keys = ["repo_rate", "india_10y_gsec", "usdinr", "india_cpi", "india_wpi"]
    kpis = [(k, A[k]) for k in kpi_keys if k in A]
    if kpis:
        L += ["KPI strip (`.kpis` block):", "",
              "| Metric | Value | As of | Source |", "|---|---|---|---|"]
        for k, r in kpis:
            L.append(f"| {r['label']} | {_fmt(r['num'], r['unit'])} | "
                     f"{r.get('period')} | {r.get('source')} |")
        L.append("")

    real = [(k, A[k]) for k in ("india_gdp_fy_actual", "india_gva_fy_actual",
                                "india_gdp_latest_q", "india_iip",
                                "india_gdp_per_capita") if k in A]
    if real:
        L += ["Real economy:", "", "| Metric | Value | Period | Source |",
              "|---|---|---|---|"]
        for k, r in real:
            L.append(f"| {r['label']} | {_fmt(r['num'], r['unit'])} | "
                     f"{r.get('period')} | {r.get('source')} |")
        L.append("")

    ind_gdp = [A.get(R.global_key("india", "gdp", y)) for y in years]
    if all(ind_gdp):
        fy = [r.get("fy") for r in ind_gdp]
        L += [f"IMF forecast for India, **fiscal-year basis**: "
              + ", ".join(f"{fy[i]} {ind_gdp[i]['num']:.1f}%" for i in range(len(years)))
              + f" ({ind_gdp[0]['source']}).",
              "",
              "> WEO labels India by the calendar year its fiscal year *starts*, so WEO "
              f"{years[1]} is {R.weo_year_to_fy(years[1])}. Write the FY label in the "
              "report, never the bare WEO year — a reader will otherwise take it as a "
              "calendar year and the whole forecast reads one year early.",
              ""]
        if "india_gdp_fy_actual" in A:
            n = A["india_gdp_fy_actual"]
            L += [f"NSO's actual print is {_fmt(n['num'], n['unit'])} "
                  f"({n.get('period')}, {n.get('source')}). It will not equal the IMF "
                  "figure for the overlapping year; cite NSO for what happened and IMF "
                  "for what is forecast, and say which is which.", ""]

    # ---- §3 cross-check
    cross = raw.get("crosscheck") or {}
    if cross:
        L += ["## 3. Cross-check (not for citation)", "",
              "World Bank WDI, India. Used only to catch a mirror serving bad data — "
              "the report cites MoSPI/RBI/IMF, never this.", "",
              "| Series | Year | World Bank | IMF WEO |", "|---|---|---|---|"]
        for k, r in sorted(cross.items()):
            imf = A.get(R.global_key("india", r["subject"], r["year"]))
            L.append(f"| {r['subject']} | {r['year']} | {r['num']:.1f}% | "
                     + (f"{imf['num']:.1f}%" if imf else "—") + " |")
        L.append("")
        for k, r in sorted(cross.items()):
            imf = A.get(R.global_key("india", r["subject"], r["year"]))
            if imf and abs(imf["num"] - r["num"]) > 1.0:
                L += [f"> **Divergence:** {r['subject']} {r['year']} — World Bank "
                      f"{r['num']:.1f}% vs IMF {imf['num']:.1f}%. A gap above 1pp usually "
                      "means different vintages or a revised national account series. "
                      "Resolve it before quoting either.", ""]

    # ---- §4 industry layer
    L += ["## 4. Industry layer — blueprint pages 4–9", ""]
    ind_figs = {k: r for k, r in A.items() if r.get("cls") == "industry"}
    if ind_figs:
        L += ["| Figure | Value | Period | Forecast yr | Body | Source |",
              "|---|---|---|---|---|---|"]
        for k, r in sorted(ind_figs.items()):
            L.append(f"| {r['label']} | {_fmt(r['num'], r['unit'])} | {r.get('period')} | "
                     f"{r.get('forecast_year') or '—'} | {r.get('owner') or '—'} | "
                     f"{r.get('source')} |")
        L.append("")
    else:
        L += ["_Nothing recorded._ Industry-body data is PDFs and press releases — this "
              "step is assisted, not automated. Work through "
              "`references/industry-bodies.md`, which gives the body, the exact release, "
              "and where the figure sits inside it for the sector in hand. Add each as an "
              "`industry` entry in `manual.json` and rebuild.", ""]
    L += ["**Never state a market size without its source and its forecast year.** "
          "A market-size number with no forecast year is unfalsifiable and will not "
          "survive being argued with.", ""]

    # ---- §5 provenance
    L += ["## 5. Provenance — every figure in this pack", "",
          "| Key | Value | Period | Age | Method | Source |", "|---|---|---|---|---|---|"]
    for k in sorted(kb["figures"]):
        r = kb["figures"][k]
        age = R.days_old(r.get("period"))
        limit = R.effective_limit(r.get("cls", ""), r.get("lag"))
        flag = ""
        if age is not None and age > limit:
            flag = " **OVER**"
        method = r.get("method", "")
        if method == "carried_forward":
            flag += " **carried forward**"
        L.append(f"| `{k}` | {r['value']} | {r.get('period') or '—'} | "
                 f"{age if age is not None else '?'}d{flag} | {method} | {r['source']} |")
    L.append("")

    # ---- §6 what is not here
    L += ["## 6. NOT in this pack — go and get these", ""]
    if not refused:
        L += ["_Nothing refused._", ""]
    else:
        for k, why in sorted(refused.items()):
            spec = R.INDIA_FIGURE_INDEX.get(k)
            L += [f"- **`{k}`** — {'; '.join(why)}"]
            if spec:
                L += [f"  - where: {spec['fallback']}",
                      f"  - url: {spec['url']}",
                      f"  - cite as: {spec['cite']}"]
        L.append("")
    missing = [k for k in R.INDIA_FIGURE_INDEX if k not in accepted and k not in refused]
    if missing:
        L += ["Never attempted this run (no manual entry supplied):", ""]
        for k in sorted(missing):
            s = R.INDIA_FIGURE_INDEX[k]
            L.append(f"- `{k}` — {s['label']} · {s['url']}")
        L.append("")
    if carried:
        L += ["Carried forward from a previous run — re-read before quoting:", "",
              ", ".join(f"`{k}`" for k in sorted(carried)), ""]

    return "\n".join(L) + "\n"


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raw", default="macro_raw.json")
    ap.add_argument("--manual", default="manual.json")
    ap.add_argument("--root", default="reports", help="the dir holding _knowledge/")
    ap.add_argument("--out-dir", default=".", help="where macro_pack.md goes")
    ap.add_argument("--ticker", default="")
    ap.add_argument("--allow-stale", action="store_true",
                    help="admit figures past their freshness window; each is stamped "
                         "with stale_override and flagged in the pack and the audit")
    ap.add_argument("--dry-run", action="store_true", help="validate, write nothing")
    args = ap.parse_args()

    probs = R.validate_registry()
    if probs:
        print("REGISTRY INVALID -- refusing to run:")
        [print("  -", p) for p in probs]
        return 2

    raw = _load(args.raw, {}, "macro_raw.json") or {}
    manual = _load(args.manual, {}, "manual.json") or {}
    if not raw and not manual:
        print(f"nothing to build: neither {args.raw} nor {args.manual} exists.")
        return 2

    years = raw.get("horizon_years") or R.horizon_years()
    manual_figs, merrs = normalise_manual(manual)
    weo_figs, werrs = normalise_weo_manual(manual)
    merrs += werrs
    # A hand-read WEO figure beats a mirror-fetched one: it came off the edition the
    # analyst actually opened, so it wins the key.
    manual_figs.update(weo_figs)
    if merrs:
        print("manual.json problems:")
        [print("  -", e) for e in merrs]
        return 2

    accepted, refused, carried = merge(raw, manual_figs, args.root, args.allow_stale)

    # If the analyst read WEO by hand, the fetch-time gate status no longer describes
    # what is in the pack -- recording it unqualified would make a resolved problem
    # look outstanding on every future audit.
    gate = dict(raw.get("weo_gate") or {})
    if weo_figs:
        vint = next(iter(weo_figs.values()))["source"].replace("IMF WEO ", "")
        gate["resolved_by"] = f"manual entry from imf.org, vintage {vint}"
        if vint >= R.expected_weo_vintage():
            gate["status"] = "current"
    raw["weo_gate"] = gate
    kb = to_kb_format(accepted, carried, gate)

    print(f"accepted {len(accepted)}  refused {len(refused)}  "
          f"carried_forward {len(carried)}")
    for k, why in sorted(refused.items()):
        print(f"  REFUSED {k}: {'; '.join(why)}")

    if not accepted:
        print("\nNo figure passed the gate. macro.json not written -- an empty pack is "
              "the honest outcome, and kb.py will keep saying 'nothing stored'.")
        return 1

    if args.dry_run:
        print("\n--dry-run: nothing written.")
        return 0

    kb_path = os.path.join(args.root, "_knowledge", "macro.json")
    os.makedirs(os.path.dirname(kb_path), exist_ok=True)
    with open(kb_path, "w", encoding="utf-8") as f:
        json.dump(kb, f, indent=2, ensure_ascii=False)
    print(f"\nwrote {kb_path}  ({len(kb['figures'])} figures)")

    os.makedirs(args.out_dir, exist_ok=True)
    pack_path = os.path.join(args.out_dir, "macro_pack.md")
    with open(pack_path, "w", encoding="utf-8") as f:
        f.write(render_pack(kb, accepted, refused, carried, raw, years, args.ticker))
    print(f"wrote {pack_path}")

    data_dir = os.path.join(args.out_dir, "data")
    os.makedirs(data_dir, exist_ok=True)
    spec = charts_spec(accepted, os.path.join(args.out_dir, "charts").replace("\\", "/"),
                       years)
    spec_path = os.path.join(data_dir, "macro_charts.json")
    with open(spec_path, "w", encoding="utf-8") as f:
        json.dump(spec, f, indent=2)
    print(f"wrote {spec_path}  ({len(spec['charts'])} chart(s))")
    if not spec["charts"]:
        print("  (no macro chart is buildable: the WEO block is incomplete. Figures "
              "carried forward from a previous run are deliberately NOT charted -- a "
              "chart implies the data was refreshed for this report.)")

    print("\nNext:")
    print(f"  python3 <eqr>/scripts/charts.py {spec_path}")
    # kb.py takes --root BEFORE the subcommand -- it is a global option there.
    print(f"  python3 <eqr>/scripts/kb.py --root {args.root} brief "
          f"--ticker {args.ticker or '<T>'}   # confirm it reads back")
    print(f"  python3 audit_macro.py --root {args.root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
