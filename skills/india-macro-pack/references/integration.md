# Integration — how this fits the equity-research-report pipeline

## Where it sits

```
Phase 0  kb.py brief          reads reports/_knowledge/macro.json  <- written by this skill
Phase 4  THIS SKILL           fetch -> manual -> build_pack
Phase 5  charts.py            consumes data/macro_charts.json      <- written by this skill
Phase 6  report.html          pages 2-9 written from macro_pack.md <- written by this skill
```

`equity-research-report` currently states Phase 4 as four bullet points of instruction —
"search for current data; do not write macro from memory". This skill is the executable
form of those bullets, plus the provenance discipline they cannot enforce on their own.

## The contract with kb.py

`macro.json` lives at `<root>/_knowledge/macro.json`, **outside the skill directory**,
next to the reports. That placement is deliberate in `equity-research-report` and this
skill must not change it: the store survives skill re-installs and is shared by all
copies of the skill. Do not relocate it.

`kb.py` reads exactly two fields per figure:

```python
figures[key]["value"]    # a STRING -- kb.py formats it with f"{v['value']:<12}"
figures[key]["source"]
```

`build_pack.py` writes those two, plus extensions (`num`, `unit`, `period`, `cls`,
`lag`, `method`, `url`, `geo`, `subject`, `year`, `fy`, `stale_override`) that survive
the JSON round-trip and drive `audit_macro.py`. `kb.py` ignores them.

Two consequences worth knowing:

- **`value` is written as a string by convention**, and `registry.validate_registry()`
  enforces it. The numeric form lives in `num`. (Verified 2026-08-01: a float or int in
  `value` does *not* in fact break `kb.py brief` — `f"{6.5:<12}"` is valid for numeric
  types. The convention is still worth keeping so `value` renders exactly as it should
  read, units and all, but it is not load-bearing.)
- **Keys must stay under 28 characters** — that is the brief's column width.
  `registry.validate_registry()` enforces both rules.

`kb.py macro --set k=v --source ...` still works and writes the same file. Figures put
there by hand have no `period` or `cls`, so `audit_macro.py` reports them as
`UNCLASSED` and falls back to kb.py's blanket 90 days. That is a correct degradation,
not a bug — but prefer `build_pack.py`, which will not accept a figure without a period.

### The 90-day rule still applies on top

`kb.py` marks the whole of `macro.json` stale 90 days after `as_of`, and
`build_pack.py` sets `as_of` to the build date. Quarterly refresh therefore keeps the
brief clean. This skill's per-figure windows are *additional* and tighter, never looser:
a 10-year yield fails at 7 days regardless of what kb.py thinks.

## Charts

`build_pack.py` writes `<out-dir>/data/macro_charts.json` as a `charts.py` spec:

```bash
python3 <eqr>/scripts/charts.py reports/<T>/data/macro_charts.json
```

Two exhibits, matching blueprint rows 2 and 3:

| Name | Archetype | Blueprint row |
|---|---|---|
| `macro_global_gdp` | `bar_grouped`, `horizontal=True` | 2 — Global economy |
| `macro_india_vs_world` | `line_multi` | 3 — Indian economy |

Both are sized `w=3.5, h=2.4` for a `.split` half-column, per the sizing rule in the
parent skill. Neither passes `title=` — titles belong in the HTML as
`<div class="fig-title">`.

The spec picks up the company palette automatically: `charts.py` looks for `brand.json`
one level above the chart outdir, which is where Phase 2c puts it. Run this skill after
Phase 2 and the macro charts match the rest of the report without any extra argument.

**A chart is only emitted when every figure it needs was accepted this run.** Figures
carried forward from a previous build are deliberately not charted — drawing them would
imply they were refreshed for this report.

## Writing pages 2–9 from the pack

`macro_pack.md` is organised in blueprint order, so §1 fills page 2 and §2 fills page 3.
Copy figures from the tables; the source column is the citation.

Three things to carry into the prose:

1. **India's IMF figures are fiscal-year.** The pack prints the FY label next to each.
   Use `FY27`, never `2026`. See `sources.md`.
2. **NSO and IMF will disagree** on the overlapping year and that is correct. Cite NSO
   for what happened, IMF for what is forecast, and say which is which in the sentence.
3. **§6 is the honest list** of what could not be sourced. Anything there must be absent
   from the report or explicitly marked as unavailable — never filled from memory. A
   figure in §6 that appears in the report anyway is the exact failure this skill exists
   to prevent.

## Refresh cadence

Quarterly, matching kb.py's 90-day rule. A refresh is a full re-run — fetch, re-read the
manual figures, rebuild. `market`-class figures (yields, INR, crude) go stale in a week
and must be re-entered per report regardless of when the last full refresh ran; the
audit will name them.

Run `audit_macro.py` twice per report: in Phase 0 next to `kb.py brief`, and again
before Phase 6 writes prose. A report can sit for days between those points, and a
`market`-class figure will have expired in that gap.

## Reconciling with the valuation

`india_10y_gsec` is the risk-free rate. If it disagrees with `risk_free` in
`assumptions.json`, one of the two is wrong — reconcile before Phase 5, not after the
DCF is built. Likewise `usdinr` should match the cover date `peer-comps` struck its
multiples on, or the comps table and the macro page are quoting different days.

## Sector knowledge

`kb.py sector` stores industry bodies per sector:

```bash
python3 <eqr>/scripts/kb.py --root reports sector --sector "two-wheelers" \
        --body SIAM --body FADA --market-size "domestic_2w_fy26=18.2 mn units"
```

Phase 8 should write back the bodies actually used and any market-size figure sourced,
so the next report in the sector starts from a known source list rather than
rediscovering it. `references/industry-bodies.md` is the starting map; the sector store
is what the house has actually verified.

## Note for whoever maintains this

`equity-research-report` exists in three copies that do not auto-sync (personal skills
dir, project-local, Cowork). This skill is a companion, not bundled — like
`annual-report-kb`, `peer-comps` and `financial-model`, it must be installed wherever
the parent runs. The parent's Phase 4 section should point at it; if that pointer is
edited, edit it in all three copies.
