# Reconciling Model State, Excel, and Audit Book

When reconciling outputs across the ERIP pipeline, check the following:

## Checks

The `checks` block in `model.json` is the authoritative truth. The workbook
Checks sheet is a formatted view of the same data.

Run:
```
python scripts/check_workbook.py --model data/model.json --workbook output.xlsx
```

Expected: all checks show PASS or OK with deviations within tolerance.

## Balance Sheet

For every period column j:
 total_assets[j] == total_liab_eq[j]
 total_current_assets[j] + total_non_current_assets[j] == total_assets[j]
 total_equity[j] + total_debt[j] + total_liabilities[j] == total_liab_eq[j]

## Cash Reconciliation

For every period j:
 cash_close[j] == cash_open[j] + net_change_cash[j]
 Where:
 cash_open[0] = cash from historical (first period)
 cash_open[j] = cash_close[j-1] for j > 0

## Historical Accuracy

For every historical period:
 Model workbook value == model.json row value == source document value
 (within rounding)

If source_registry.json exists (from model-audit), compare workbook values
against the registry entry.

## Screener Reconciliation

model.json > reconciliation array should show:
 - MATCH for all FY23-FY25 lines where screener matches annual report
 - ROUNDING where values differ by < 1%
 - DIFFERS where material gaps exist

Differences in `ebitda_margin` between screener and annual report are expected
for FY23 due to revised JVs.

## Output

Write reconciliation results to `data/workbook_reconciliation.md` with:

```markdown
# Workbook Reconciliation

- Model checks: PASS / FAIL
- Balance sheet: PASS / FAIL
- Cash reconciliation: PASS / FAIL
- Historical accuracy: PASS / FAIL (N/N items)
- Screener reconciliation: PASS / FAIL
- Audit book rows documented: N/N
```
