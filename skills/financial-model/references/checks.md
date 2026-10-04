# The checks

A model that balances is not a model that is right. Read this before telling
anyone "all checks pass" - some of these checks have real teeth and some are
identities that only fail if the model definition itself is broken. Saying which
is which is the whole point.

## Blocking - a failure means there is no model

| Check | What it compares | Teeth |
|---|---|---|
| `chk_balance` (forecast) | total assets − total liabilities and equity | **Real.** The only forecast residual that is not true by construction. It fails the moment a balance sheet line stops being routed through the cash flow statement. This is the check that carries the model. |
| `hist_balance` | the same, on the historical columns | **Real.** History comes straight from the source, so a break here is an ingest mapping error, not a modelling one. |
| `chk_cash_tie` (forecast) | balance sheet cash − cash flow closing cash | Identity by construction. |
| `chk_reserves` (forecast) | reserves − (opening + PAT − dividends + equity issued) | Identity by construction. |
| `chk_fa_roll` (forecast) | net block − the fixed asset schedule's closing balance | Identity by construction. |
| `chk_min_cash` | cash − the minimum cash balance | **Real.** Negative means the revolver failed to fund a shortfall. |
| `chk_revolver_pos` | the revolver balance | **Real.** Negative means the model repaid more than it drew. |
| `chk_nb_pos` | net block | **Real.** Negative means depreciation outran the asset base. |
| `chk_equity_pos` | shareholders' equity | **Real.** Negative equity is a going-concern statement, not a rounding issue. |

The three identities are kept because they are cheap and they are the regression
test for `rows.py`: change a formula carelessly and they go red immediately.
They are not evidence that the forecast is sound.

Tolerance is one paisa or one part per million of total assets, whichever is
larger.

## Advisory - a flag is a judgement to defend, not a defect to fix

| Check | Means |
|---|---|
| `chk_reserves_hist` | Reserves moved by more than profit less dividends. Look for other comprehensive income, a buyback, a share issue, or a restatement. On the historical columns this is **not** an identity - it is a real statement about the source data. |
| `chk_fa_roll_hist` | Once real capex is supplied from the annual report, the fixed asset roll no longer closes on the reported net block. The gap is disposals, impairment or revaluation. |
| `cfo_reconstruction` | Reconstructed CFO (PAT + D&A − change in net operating assets) is more than 25% away from reported CFO. A persistent gap means profit is not converting to operating cash the way the driver model assumes - an accrual-quality signal. |
| `band_tax_rate` | Effective tax rate outside 0-50%. |
| `band_ebitda_margin` | EBITDA margin outside −20% to 70%. |
| `band_rev_growth` | Revenue growth outside −30% to 60%. |
| `band_payout_ratio` | Payout outside 0-150%. |
| `drift_<driver>` | The forecast steps outside the driver's own historical range by more than the wider of that range and 15% of its level. Drivers whose history is zero by construction - minimum cash, equity issued, scheduled repayment - are exempt. |

## Fixing a blocking failure

**`chk_balance` fails in the forecast.** A balance sheet row is not in the cash
flow statement, or is in it twice. Check that every stock account appears in
`nwc`, or as its own investing or financing line, exactly once. See the
derivation in `structure.md`.

**`hist_balance` fails.** The Screener mapping is wrong for this company.
Usually `other_ca` - it is a residual (`Other Assets − receivables − inventory −
cash`) and goes negative if the export labels one of those differently. Check
what `ingest.py` reported as missing.

**`chk_min_cash` negative.** The revolver did not fund the shortfall. Either the
draw is being computed off a cash figure that excludes something, or the
repayment line is taking cash back out in the same year. Look at
`cash_pre_rev`, `revolver_draw` and `revolver_repay` on the Schedules sheet.

**`chk_nb_pos` negative.** Depreciation exceeded the asset base. The
`net_block` basis caps the charge at opening net block plus capex, so this only
happens on the `sales` basis with a depreciation rate that is too high for the
capex being spent. Switch `dep_basis` or cut the rate.

**`chk_equity_pos` negative.** Accumulated losses or a payout above earnings has
exhausted reserves. This is a real result. Report it.

**The circular solve did not converge** (residual not near zero). The debt
schedule is oscillating - usually a scheduled repayment larger than the balance
combined with a high cost of debt. Cap the repayment or use `debt_growth`.

## What is deliberately not checked

- **Whether the forecast is any good.** The drift and band checks say a number
  is unusual, not that it is wrong. The argument for it lives in the evidence
  trail from `financial-model-assumptions`.
- **Whether the accounting is right.** This model reads what the sources report.
  Forensic screens - accrual ratios, Altman, Piotroski, related-party exposure -
  are in `equity-research-report/scripts/model.py`.
- **Whether the workbook recalculates to the same numbers.** The Excel formulas
  and the JSON values are compiled from one definition, so the arithmetic cannot
  differ, and every cell reference has been round-trip verified against the row
  layout. But no spreadsheet application has been run over the file here. If you
  need certainty, open it and compare the Summary sheet to `model.json`.
