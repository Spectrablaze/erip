# Hand-offs to and from the neighbouring skills

```
                    annual report PDF
                           │
                  ┌────────▼─────────┐
                  │ annual-report-kb │   PDF → <Company> Annual Report/
                  └────────┬─────────┘
                           │  pages/ sections/ tables/ context/ entities/
              ┌────────────┼─────────────────────┐
              │            │                     │
   ar_tables.py           │            financial-model-assumptions
   (statement tables,     │            kb_search + history + build
    figures + page cite)  │                      │
              │            │            assumptions.json (cited drivers)
              │            │                     │
  Screener export ─────────┼─────────────────────┤
              │            │                     │
         ┌────▼────────────▼─────────────────────▼────┐
         │              THIS SKILL                    │
         │  ingest.py → build_model.py → check_model  │
         └────┬───────────────────────────────────────┘
              │
   model.xlsx  model.json  model_review.md
              │
              │  bridge: fcff, fcfe, net debt, shares, eps, bvps
              ▼
   equity-research-report/scripts/model.py → DCF, comps, forensics, the report
```

## From `annual-report-kb`

Needs a built knowledge base directory. `ar_tables.py` reads
`metadata/table_index.json` and `tables/*.md`, falling back to whatever markdown
is on disk if the index is missing. It never loads the whole report.

If the user has a PDF and no knowledge base, build one first. The parse is the
slow step and is resumable; see that skill's `preflight.py`.

## From `financial-model-assumptions`

Consumes `assumptions.json`. That skill owns the argument for each driver - the
evidence, the page citation, the confidence, the user's confirmation. This skill
owns only the arithmetic.

The two are usable independently. Without `assumptions.json` every driver is
held at its trailing historical average, which produces a working model and a
build note saying so. That is a fine starting point and a bad ending point.

The mapping is in `inputs.md`. Keys this skill needs that live in `_analyst`
rather than at the top level: `gross_margin`, `dso`, `dio`, `dpo`,
`dividend_payout`, `debt_growth`, `min_cash`.

## From the Screener parser in `equity-research-report`

`ingest.py` looks for `equity-research-report/scripts/parse_screener.py` and
uses it when found, so the learned Screener label aliases in
`reports/_knowledge/aliases.json` apply here too - a label that broke the parser
once stays fixed for both skills. A self-contained fallback reader handles the
case where that skill is not installed; the build note says which was used.

## To `equity-research-report`

`model.json` carries a `bridge` block sized to the forecast: revenue, EBITDA,
EBIT, depreciation, capex, change in net operating assets, tax rate, FCFF, FCFE,
closing net debt, shares, EPS and BVPS.

Valuation stays there. `model.py` already does the FCFF DCF, the WACC build-up,
the sensitivity grid, scenarios, relative valuation, DuPont, ROIIC and the
forensic screens; duplicating any of it here would create two answers that can
disagree. What this skill adds is the thing `model.py` does not have - a
projected balance sheet and cash flow, so the FCFF being discounted comes out of
a model that funds itself rather than out of a margin assumption applied to a
revenue line.

Practical sequencing for a full report:

1. `annual-report-kb` on the PDFs.
2. `financial-model-assumptions` → `decisions.json` → `assumptions.json`.
3. This skill → `model.xlsx`, `model.json`, `model_review.md`.
4. `equity-research-report` phase 3 onwards, with the model review as an exhibit
   and `bridge.fcff` as a cross-check on the DCF's own forecast.

If `bridge.fcff` and the DCF's implied free cash flow diverge materially, the
DCF is being run on drivers that do not fund the balance sheet. That is worth
knowing before the report is written, not after.

## From `modeling-strategy` (optional)

`ingest.py --strategy model_strategy.json` binds this build to an approved
architecture. Three things change; without the flag nothing does.

1. **The gate.** A strategy that is `PENDING`, `REJECTED` or RED stops the
   build. `check_strategy.gate_ok()` is called, so the rule is identical in all
   four consumers.
2. **A capability check.** This skill declares `consolidated_growth_only` —
   `rows.py` has one revenue row and no segment rows. An approved architecture
   that needs more is refused, with the requirement named. In particular: where
   `revenue_model` is `segment_buildup`, `assumptions.json` must carry
   `_strategy.revenue_growth_source` from `build_assumptions.py --segment-build`.
   Its absence means the segment economics never reached this model, so the build
   refuses rather than modelling one growth rate and calling it a segment build.
3. **No silent fallback for required drivers.** `rev_growth`, `ebitda_margin` and
   `capex_pct_sales` must come from the assumption set. Held at a trailing
   historical average they would be a different model from the approved one, and
   that difference would be invisible in the output.

Refusals exit 3 (gate) and 4 (capability), so a pipeline can distinguish them.

## Sector handling

`sectors.py` and `references/sectors.md` in the two neighbouring skills are the
authority. The relevant constraint here: **banks, NBFCs and insurers are not
modelled.** Interest is revenue for a lender, so EBITDA, net operating assets,
the revolver plug and the FCFF line are all undefined. Resolve the sector before
building and stop if it is `financials`.
