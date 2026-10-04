# How the model is built

## One definition, two outputs

Every projected line exists once, in `scripts/rows.py`, as a formula string:

```python
Row("net_block", "Net fixed assets", BS, "actual",
    fcst="prev(net_block)+capex-dep_charge", indent=1)
```

`scripts/engine.py` parses that string with Python's `ast` module and compiles
it twice - once to a number, once to an Excel formula against the workbook's
actual cell addresses. `model.json` and `model.xlsx` are therefore the same
model by construction. There is no second implementation that can drift.

The only thing that can go wrong is the address mapping, and that is mechanical:
a reference resolves to `(row key, column index)` from the sheet layout alone.

### The formula language

| Syntax | Meaning | Excel |
|---|---|---|
| `revenue` | that row, this column | `G12` |
| `prev(revenue)` | that row, previous column | `F12` |
| `12.5`, `0.08` | literal | as written |
| `+ - * / ^` | arithmetic | same; division becomes `IFERROR(a/b,0)` |
| `< <= > >= == !=` | comparison | `< <= > >= = <>` |
| `MIN MAX ABS SUM` | | same |
| `AVG(a,b)` | | `AVERAGE(a,b)` |
| `IF(c,a,b)` | | `IF(c,a,b)` |

`prev()` takes exactly one bare row name. Before the first column it reads zero
in Python and emits a literal `0` in Excel, so a roll-forward's first column is
meaningless by design - the checks skip it.

Division is guarded on both sides: Python returns `0.0` for a zero denominator
and Excel gets `IFERROR(...,0)`. Without that the two would disagree the moment
a denominator went to zero.

### Row kinds

| Kind | Historical columns | Forecast columns |
|---|---|---|
| `head` | a section label | - |
| `actual` | the reported figure, hardcoded | the `fcst` formula |
| `input` | back-solved by the `hist` formula | a hardcoded driver value |
| `calc` | `hist` if given, else `fcst` | the `fcst` formula |

A driver is an `input`: its history is *derived from* the reported statements
and its forecast is *set*. That is why history and forecast can sit on the same
row in the same units - the Drivers sheet reads as one continuous series.

## Circularity

Interest is struck on average debt. The revolver is drawn from a cash flow that
contains that interest. The model is therefore circular, on purpose - this is
how a real model behaves, and breaking it by using opening balances understates
interest for a company whose debt is moving.

- **Python**: `engine.solve()` evaluates the whole grid repeatedly until the
  largest cell-to-cell change is below `1e-7`, up to 200 passes. On a normal
  company it converges in about five.
- **Excel**: the workbook is saved with `iterate=True`, `iterateCount=200`,
  `iterateDelta=1e-6` and `fullCalcOnLoad=True`.

If the reported residual is not near zero, the debt schedule is oscillating -
usually a repayment larger than the balance combined with a high cost of debt.

## Why the balance sheet ties

This is the part to understand before editing `rows.py`. Writing out the change
in each side over one year:

```
ΔAssets = Δcash + Δreceivables + Δinventory + Δother_ca
        + Δnet_block + Δcwip + Δinvestments

Δcash   = CFO + CFI + CFF
        = (PAT + dep − Δnwc)
        + (−capex − Δcwip − Δinvestments)
        + (Δterm_debt + Δrevolver − dividends + equity_issued)

Δnet_block = capex − dep
Δnwc       = Δreceivables + Δinventory + Δother_ca − Δpayables − Δother_liab
Δreserves  = PAT − dividends + equity_issued
```

Substituting, `capex`, `dep`, `Δcwip` and `Δinvestments` all cancel, and the
working-capital terms collapse into `Δpayables + Δother_liab`:

```
ΔAssets = Δreserves + Δterm_debt + Δrevolver + Δpayables + Δother_liab
        = ΔLiabilities and equity            ∎
```

**The condition is that every balance sheet line appears in the cash flow
statement exactly once.** `nwc` is what enforces it:

```
nwc = receivables + inventory + other_ca − payables − other_liab
```

Note that `other_ca` and `other_liab` are inside it. They are residual buckets
that include non-current items, so treating them as operating is a
simplification - but leaving either one out breaks the tie immediately, which is
exactly what `chk_balance` catches.

**If you add a balance sheet row, you must also route it through the cash flow
statement**, either into `nwc` or as its own investing/financing line. Add it to
one side only and `chk_balance` fails on the first forecast column.

## Sheets

| Sheet | Holds |
|---|---|
| `Model info` | company, periods, options, the check results, the reconciliation, citations, build notes |
| `Drivers` | every assumption, history back-solved, forecast as blue inputs |
| `Income Statement` | revenue to EPS |
| `Balance Sheet` | the stock accounts - these are the canonical balances |
| `Cash Flow` | indirect CFO/CFI/CFF, the cash reconciliation, and the reported lines alongside |
| `Schedules` | the flows and workings: fixed assets, working capital, debt and revolver, equity |
| `Checks` | the residuals, conditionally formatted so a break is red |
| `Summary` | growth, margins, FCFF, FCFE, leverage, returns |

Colour follows the usual convention: **blue** is a hardcoded number, **black** a
formula on the same sheet, **green** a link to another sheet. Forecast columns
are shaded; driver input cells are shaded more strongly.

## Options that change a formula

- `dep_basis: "net_block"` (default) - depreciation is a rate on opening net
  block, capped at opening net block plus capex so the asset base cannot go
  negative. `"sales"` makes it a percentage of revenue instead, which is what
  `assumptions.json` supplies; use it when the asset base is being restructured
  and the roll-forward rate is not stable.
- `avg_years` (default 3) - the trailing window used for any driver the sources
  do not set.
- `forecast_years` (default 5).

## Adding a row

1. Add a `Row(...)` to `ROWS` in `rows.py`, in the position it should print.
2. If it is a balance sheet line, route it through the cash flow statement (see
   above) or `chk_balance` will fail.
3. Rebuild. The workbook lays itself out, the JSON picks it up, and the checks
   run. Nothing else needs editing.
