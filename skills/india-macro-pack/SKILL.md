---
name: india-macro-pack
description: Assemble the macro and industry layer of an Indian equity research report - global and India GDP, CPI, WPI, IIP, repo rate, G-sec yield, INR, and industry-body volumes and market size - with every figure carrying its source, its observation period and a staleness check. Produces a cited macro_pack.md and populates reports/_knowledge/macro.json for kb.py. This skill should be used when the user asks for macro data, macro context, the macro or industry section of a research report, India GDP or inflation figures, IMF WEO forecasts, RBI or MoSPI data, industry volumes or market size, or asks to refresh a stale macro knowledge base.
---

# India macro pack

Fills Phase 4 of `equity-research-report`: the macro and industry layer behind blueprint
pages 2–9. Produces cited figures, a `macro_pack.md` ready to write those pages from, and
a `reports/_knowledge/macro.json` that `kb.py` reads unchanged, 90-day staleness warning
and all.

## The design principle

**A fetch failure degrades to "here is the URL and the field name, go and read it" — never
to a silently stale number.**

Macro figures going quietly a year out of date across several reports would be worse than
having no skill at all, because a stale number is indistinguishable from a fresh one once
it is in a PDF. Every mechanism here exists to keep that from happening:

- Every figure carries its **observation period** separately from when it was recorded,
  and staleness is judged on the period. Writing down April-2025 CPI today does not make
  it current.
- Every figure carries a **source**. `build_pack.py` refuses to emit one without it.
- A figure past its freshness window is **refused and listed in §6 of the pack** with the
  URL and the field name — not quietly included.
- IMF figures are gated on the **WEO vintage**, not just on the fetch succeeding.
- Figures kept from a previous run are stamped `carried_forward` and never charted.

This is the most brittle of the research skills. Government portals change layout, publish
as PDFs and rename series. It is built to fail loudly and locally rather than degrade
quietly.

## Orient

```
scripts/registry.py       the vocabulary: figure keys, source recipes, freshness policy
scripts/fetch_macro.py    pulls IMF WEO (via mirror) + World Bank; prints the worksheet
scripts/build_pack.py     merges fetched + manual -> macro.json, macro_pack.md, chart spec
scripts/audit_macro.py    is the stored pack still safe to quote?
assets/manual_template.json   the fill-in form for everything that cannot be fetched
references/sources.md         authority order, the WEO fiscal-year trap, freshness reasoning
references/industry-bodies.md 12 bodies, what each publishes, and where the figure sits
references/integration.md     the kb.py contract, chart wiring, refresh cadence
```

No dependencies beyond the standard library. No API keys — every source used is free and
unauthenticated.

Read `references/sources.md` before entering any figure by hand.

## What is automated and what is not

| Layer | How | Why |
|---|---|---|
| IMF WEO — global + India GDP and CPI, plus India's GDP in USD, per-capita, current account, government debt | **fetched**, two requests, via the DBnomics mirror | WEO is the one bulk machine-readable release in this set |
| World Bank India GDP + CPI | **fetched**, cross-check only | catches a mirror serving corrupted data; never cited |
| India actuals — CPI, WPI, IIP, GDP, GVA, per-capita | **manual**, with a per-figure recipe | MoSPI publishes PDFs; no free stable API |
| RBI — repo, 10Y G-sec, INR, credit, reserves, BoP | **manual**, with a per-figure recipe | no API; the portal redirects and reorganises |
| Industry bodies — volumes, market size | **manual**, `references/industry-bodies.md` | PDFs and press releases, some members-only |

**`imf.org` returns HTTP 403 to every programmatic client across the whole domain** —
DataMapper API included. This is not transient, and retrying with a different user-agent
does not help. The DBnomics mirror (`api.db.nomics.world`) is the working route, and it
lags: verify the vintage rather than trusting it. Dataset codes in `references/sources.md`.

## Workflow

### 1. Fetch, and read the worksheet

```bash
python3 scripts/fetch_macro.py --out reports/<T>/data/macro_raw.json
```

Pulls what it can and prints a worksheet of everything it could not: the URL, the page,
the table, the field name and the citation format for each figure.

The **WEO vintage gate** runs first. `fetch_macro.py` computes which WEO edition should
exist for today's date (they publish April and October) and compares it to the mirror's
newest. If the mirror is behind, WEO figures are routed to the worksheet rather than
written — the mirror has been more than a year behind in practice, and writing that
silently is exactly the failure this skill prevents.

`--accept-vintage` overrides the gate. Every affected figure is then stamped with its true
vintage, flagged in the pack, and named individually by the audit. Reasonable for a draft;
do not ship a report on it without saying so.

`--worksheet-only` prints everything a complete pack needs without touching the network.

### 2. Fill in the manual figures

Copy `assets/manual_template.json` to `reports/<T>/manual.json` and work down the
worksheet. Each entry needs three things or it is refused:

- `value` — the number
- `period` — **what it observes**, not today. `2026-06` for the June CPI print. An Indian
  fiscal year uses its **end** month: FY26 is `2026-03`, never `2026`.
- `source` — the citation string, in the format the worksheet gives

Delete any block that was not looked up. An omitted figure is reported honestly in §6 of
the pack; a guessed one is not.

Keys must exist in `registry.py`. Unknown keys are rejected on purpose — two spellings of
one figure fragment the shared store and `kb.py brief` stops recalling it.

For the industry layer work through `references/industry-bodies.md`. Note especially that
**SIAM is wholesale despatches and FADA is retail registrations**; a volume figure without
its basis stated is unfalsifiable.

### 3. Build

```bash
python3 scripts/build_pack.py --raw reports/<T>/data/macro_raw.json \
        --manual reports/<T>/manual.json --root reports \
        --out-dir reports/<T> --ticker <T>
```

Writes three things:

| File | For |
|---|---|
| `reports/_knowledge/macro.json` | `kb.py brief` in Phase 0 of this and every later report |
| `reports/<T>/macro_pack.md` | writing blueprint pages 2–9 in Phase 6 |
| `reports/<T>/data/macro_charts.json` | `charts.py` in Phase 5 |

It prints every refusal with the reason. Refusals are the point — read them.

`--dry-run` validates and writes nothing. `--allow-stale` admits figures past their
window, each stamped `stale_override` and flagged everywhere downstream.

Figures already in `macro.json` that this run did not refresh are kept but re-stamped
`carried_forward` with their original period, so their true age stays visible. They are
never charted — drawing them would imply they were refreshed for this report.

### 4. Build the charts

```bash
python3 <eqr>/scripts/charts.py reports/<T>/data/macro_charts.json
```

`macro_global_gdp` (horizontal `bar_grouped`) for blueprint page 2 and
`macro_india_vs_world` (`line_multi`) for page 3, both sized for a `.split` half-column
and picking up the company palette from `brand.json` automatically.

### 5. Audit before quoting

```bash
python3 scripts/audit_macro.py --root reports
```

Run it in Phase 0 next to `kb.py brief`, and **again before Phase 6 writes prose** — a
report can sit for days between those points and a market-class figure expires in a week.
Exit 0 means everything is inside its window; exit 1 lists what is not, with the URL to go
and fix it.

## Freshness — why one blanket rule is not enough

`kb.py` marks the whole store stale after 90 days. That stays in force. On top of it each
figure has its own window, because 90 days is simultaneously far too long for a G-sec
yield and too short for per-capita income:

`market` 7d · `policy` 75d · `weekly` 14d · `monthly` 45d · `quarterly` 100d ·
`annual` 400d · `weo` 250d · `industry` 200d

**Publication lag is added on top of the window.** IIP is released about 40 days after the
month it covers, so the freshest IIP that exists is already 40 days old — a flat 45-day
rule would reject nearly all of them. The effective limit is `window + lag`, recorded per
figure. Ages are measured from the **end** of the observation period. Reasoning in
`references/sources.md`.

## The two traps that produce wrong reports

**1. IMF WEO reports India on a fiscal-year basis, labelled by the year the fiscal year
starts.** Every other country is calendar year. WEO `2026` for India is FY2026-27 — FY27.
Copy the bare WEO year into an Indian report and the whole forecast reads one year early,
invisibly, because the number is plausible either way. The pack prints the FY label
alongside every India WEO figure; use it.

**2. NSO and IMF will not agree, and are not supposed to.** MoSPI/NSO prints what
happened; IMF forecasts what is expected. Cite NSO for actuals and IMF for forward years,
and say which is which in the sentence. Quoting IMF's estimate for a year the NSO has
already printed reads as not having opened the national accounts.

## Authority order

India actuals → **MoSPI/NSO**. Rates, currency, credit, BoP → **RBI**. Global and forward
years → **IMF WEO, with the edition month**. Industry volumes and market size → **the body
itself**, not a consultancy repeating it. World Bank is a **cross-check only** and never
appears in the report. Full table in `references/sources.md`.

## Relationship to equity-research-report

A companion skill, not bundled — install it wherever the parent runs, alongside
`annual-report-kb`, `peer-comps` and `financial-model`. It writes to `reports/_knowledge/`,
which deliberately sits outside every skill directory so the store survives re-installs and
is shared across skill copies. Do not relocate it.

Two figures must reconcile with the valuation, and it is cheaper to check now than after
the DCF is built: `india_10y_gsec` against `risk_free` in `assumptions.json`, and `usdinr`
against the cover date `peer-comps` struck its multiples on. See
`references/integration.md`.

## Refresh cadence

Quarterly, matching the 90-day rule. A refresh is a full re-run: fetch, re-read the manual
figures, rebuild. Market-class figures are re-entered per report regardless — the audit
will name them.

## Adding a figure

Add a `Fig(...)` to `INDIA_FIGURES` in `scripts/registry.py`. The validator refuses an
entry with no fallback instruction, no citation format, an unknown freshness class, or a
key over 28 characters (`kb.py brief`'s column width). Check with:

```bash
python3 scripts/registry.py
```
