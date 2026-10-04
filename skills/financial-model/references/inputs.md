# Inputs: schemas and the Screener mapping

## Sources, in increasing order of authority

1. **Screener export** - the historical spine. Broad and consistent, but it has
   no trade payables and, for some companies, no expense detail.
2. **`overrides.actuals`** - figures read off the annual report, each with a page
   citation. These fill what Screener lacks and win where the two disagree.
3. **`assumptions.json`** - the forecast drivers, from the
   `financial-model-assumptions` skill.
4. **`overrides.drivers`** - the analyst's last word.

Disagreements between 1 and 2 above 2% are reported, never silently resolved.

## overrides.json

The only file the analyst edits. `assets/overrides_template.json` is a filled-in
starting point.

```json
{
  "actuals": {
    "payables": {"Mar-22": 980.4, "Mar-23": 1075.0, "Mar-24": 1183.6},
    "capex":    {"Mar-24": 470.0}
  },
  "citations": {
    "payables": {"source": "tables/table_p0198_1.md", "page": 198,
                 "quote": "Trade payables - total outstanding dues"}
  },
  "drivers": {
    "rev_growth": [0.11, 0.10, 0.095, 0.09, 0.085],
    "ebitda_margin": 0.185,
    "min_cash": 250.0
  },
  "options": {"forecast_years": 5, "avg_years": 3, "dep_basis": "net_block"}
}
```

- `actuals.<row>.<period>` - the period label must match the Screener column
  exactly (`Mar-24`). A label that does not match is reported and ignored, not
  guessed at.
- `citations.<row>` - required for anything taken from the annual report. It
  travels into `model.json`, the `Model info` sheet and the review.
- `drivers.<key>` - a number, or a list with one entry per forecast year. A
  short list is held flat and reported. Rates are decimals here.
- Supplying `payables` triggers one automatic adjustment: the same amount is
  netted out of `other_liab`, because Screener's "Other Liabilities" already
  contains payables. Without it the historical balance sheet stops tying.

## Screener → model line items

Screener's Data Sheet is read by block, not by row number. The mapping:

| Model row | From Screener |
|---|---|
| `revenue` | Sales |
| `ebitda` | Operating Profit |
| `cogs` | Raw Material Cost + Change in Inventory + Power and Fuel + Other Mfr. Exp, **else** revenue − EBITDA |
| `dep_charge` | Depreciation |
| `other_income` | Other Income |
| `interest_expense` | Interest |
| `pbt` | Profit before tax |
| `tax` | **PBT − PAT** (exact), falling back to the reported Tax row |
| `pat` | Net profit |
| `exceptional` | Exceptional / Extraordinary Items, else zero |
| `dividends` | Dividend Amount |
| `share_capital` | Equity Share Capital |
| `reserves` | Reserves |
| `term_debt` | Borrowings |
| `revolver` | zero - all reported borrowing is term debt |
| `net_block` | Net Block |
| `cwip` | Capital Work in Progress |
| `investments` | Investments |
| `receivables` | Receivables |
| `inventory` | Inventory |
| `cash` | Cash & Bank |
| `other_ca` | **Other Assets − receivables − inventory − cash** |
| `payables` | **not in the export** - zero until the annual report supplies it |
| `other_liab` | Other Liabilities (less payables once supplied) |
| `shares` | Adjusted Equity Shares in Cr |
| `capex` | **Δnet block + depreciation** - not disclosed, so it is backed out |
| `rep_cfo/cfi/cff` | Cash from Operating / Investing / Financing Activity |

Three of these are worth dwelling on:

- **Tax as PBT − PAT** is exact and survives Screener reporting tax as a rate.
  It also absorbs minority interest and share of associates, so on a company
  with large associates the effective rate reads high. Check it against the tax
  note.
- **`other_ca` as a residual** means everything Screener does not itemise ends
  up there, including non-current assets. It is modelled as a percentage of
  sales, which is a simplification. See `structure.md` for why it must stay
  inside net operating assets regardless.
- **Capex backed out of the net block roll** equals true capex only if there
  were no disposals, impairments or revaluations. Where the annual report gives
  additions to PPE, supply it in `overrides.actuals.capex`; the historical fixed
  asset roll check will then show you how large the difference was.

## assumptions.json → drivers

| assumptions.json | driver |
|---|---|
| `revenue_growth` | `rev_growth` |
| `ebitda_margin`, else `ebit_margin` + `dep_pct_sales` | `ebitda_margin` |
| `_analyst.gross_margin`, else the EBITDA margin | `gross_margin` |
| `capex_pct_sales` | `capex_pct_sales` |
| `dep_pct_sales` | `dep_pct_sales` |
| `_analyst.dso` / `dio` / `dpo` | `dso` / `dio` / `dpo` |
| `tax_rate` | `tax_rate` |
| `cost_of_debt` | `cost_of_debt` |
| `_analyst.dividend_payout` | `payout_ratio` |
| `_analyst.debt_growth` | `debt_growth` |
| `_analyst.min_cash` | `min_cash` |

Rates arrive as either percent (`12.0`) or decimal (`0.12`); anything with an
absolute value above 1.5 is read as percent. Day counts are taken as given.

**Every driver the sources do not set is held at its trailing historical
average** and listed in the build notes. That is a defensible default, but it is
still a decision - read the list.

## model_input.json

Written by `ingest.py`, read by `build_model.py`. Not meant to be hand-edited;
change `overrides.json` and re-run ingest instead.

```json
{
  "company": "...", "currency": "INR cr", "sector": null, "built": "2026-08-01",
  "hist_periods": ["Mar-16", ...], "fcst_periods": ["Mar-25E", ...],
  "actuals":   {"revenue": [...], "ebitda": [...], ...},
  "drivers":   {"rev_growth": [0.11, ...], ...},
  "driver_sources": {"rev_growth": "overrides", ...},
  "citations": {...},
  "options":   {"dep_basis": "net_block", "avg_years": 3},
  "reconciliation": [{"row": "capex", "period": "Mar-24",
                      "screener": 461.6, "annual_report": 470.0,
                      "diff_pct": 1.82}],
  "notes": ["..."]
}
```

## model.json

The solved model. `rows.<key>.values` is the full series, history then forecast.
`bridge` is the compact hand-off to the valuation layer:

```json
"bridge": {
  "periods": ["Mar-25E", ...],
  "revenue": [...], "ebitda": [...], "ebit": [...],
  "depreciation": [...], "capex": [...], "change_in_nwc": [...],
  "tax_rate": [...], "fcff": [...], "fcfe": [...],
  "net_debt_close": [...], "shares": [...], "eps": [...], "bvps": [...]
}
```

Read numbers from here, never from `model.xlsx` - a workbook written by openpyxl
holds formulas but no cached values until a spreadsheet application opens it.

## Day counts are not portable between skills

`financial-model` strikes inventory and payables off **its own COGS** — direct
operating costs, which on a typical industrial leaves a ~70% gross margin.
`financial-model-assumptions` and `history.py` compute DIO and DPO off **raw
materials only**, which on an asset-heavy business can read as a 98.7% gross margin.

The same DIO of 40 days therefore means two different rupee balances in the two
skills. Passing day counts straight across collapses forecast payables, and nothing
errors — the model still reports a converged circular solve.

**Restate DIO and DPO onto the COGS basis** in `overrides.drivers` before handing
them to this skill, or supply `nwc_pct_sales` directly as a series and bypass the
day-count conversion entirely. `build_assumptions.py` prints the basis it used in
its checks; read it rather than assuming.
