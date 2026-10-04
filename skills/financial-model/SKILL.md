---
name: financial-model
description: "Builds a linked three-statement financial model - projected P&L, balance sheet and cash flow with fixed asset, working capital, debt, revolver and equity schedules - from Screener historicals, annual report figures and an evidence-based assumption set. Emits a live-formula Excel workbook plus a model.json, and refuses to hand over a model whose balance sheet does not tie. Use this skill when the user asks to build a financial model, a three-statement model, an operating model, a forecast model, projections, a driver model, or to project revenue, margins, working capital, debt or cash flow for a company."
---

# Financial model

Act as an equity analyst building the operating model for one company: ten years
of history, five to ten years of projections, three statements that articulate,
and a set of checks that make it obvious when they do not.

The deliverable is a workbook the user can open and drive - change a driver on
the Drivers sheet and the whole model recalculates - together with a solved JSON
of the same model for everything downstream.

## Where this sits

```
annual report PDF ──annual-report-kb──► <Company> Annual Report/   knowledge base
Screener export ─────────────────────►  historical spine
                                              │
   financial-model-assumptions ──────► assumptions.json (cited drivers)
                                              │
                                        ►  THIS SKILL  ◄
                                              │
                          model.xlsx  +  model.json  +  model_review.md
                                              │
              equity-research-report: model.py ──► DCF, comps, the report
```

This skill does **not** value the company. Discounting, WACC, sensitivity and
relative valuation belong to `equity-research-report/scripts/model.py`, which
already does them. `model.json` carries a `bridge` block - FCFF, FCFE, net debt,
shares - for exactly that hand-off.

## Non-negotiables

1. **A blocking check failure means there is no model.** Report it and fix the
   cause. Never quote a number out of a model whose balance sheet does not tie.
2. **The workbook is an output, not a source.** Edits made by hand in Excel are
   lost on the next build. Every change goes into `overrides.json` (or
   `decisions.json` upstream) and the model is rebuilt. Say this to the user the
   first time you hand them the file.
3. **Never invent an actual.** A line the sources do not carry is zero and
   appears in the notes as zero. Do not fill a gap with a plausible number.
4. **Every figure taken from the annual report carries a page citation** in
   `overrides.citations`. Screener figures need no citation; annual report
   figures always do.
5. **Do not silence an advisory by moving a driver.** An advisory says the
   forecast is a claim. Defend the claim or change it because the evidence
   changed - not because the check was noisy.
6. **Stop on banks, NBFCs and insurers.** Interest is revenue for a lender, so
   EBITDA, net operating assets and this whole model structure are meaningless.
   Resolve the sector before building anything.
7. **Never silently substitute a generic model for an approved one.** This skill
   has exactly one revenue row, `prev(revenue)*(1+rev_growth)`. Given
   `ingest.py --strategy`, an architecture it cannot execute - segment revenue
   rows, or a segment build-up whose derived growth path never arrived - is
   **refused**, with the unsupported requirement named. It does not flatten and
   it does not approximate. See `references/integration.md`.

## Workflow

### 1. Assemble the history

```bash
python scripts/ingest.py --screener export.xlsx \
                         --assumptions data/assumptions.json \
                         --overrides overrides.json \
                         --hist-years 10 --forecast-years 5 \
                         -o data/model_input.json
```

`--screener` takes the Screener "Export to Excel" file or an
already-parsed `financials.json`. When the `equity-research-report` skill is
installed, ingest uses its parser so the learned Screener label aliases apply.

Read the output. It tells you which line items are populated, which drivers came
from the assumption set, and which will be held at the trailing historical
average. Those last ones are decisions being made by default - go and look at
them.

### 2. Fill what Screener does not carry, from the annual report

A Screener export has **no trade payables** and, for some companies, no expense
detail. Payable days therefore read zero and net operating assets are overstated
until you fix it. Find the figures:

```bash
python scripts/ar_tables.py presets
python scripts/ar_tables.py find --kb "<Company> Annual Report" --for payables
python scripts/ar_tables.py show --kb "<Company> Annual Report" --file tables/table_p0198_1.md
```

Put what you read into `overrides.json` from `assets/overrides_template.json` -
figures under `actuals`, the page under `citations` - and re-run ingest.
`references/kb-inputs.md` lists what is worth pulling and what it feeds.

Where the annual report and Screener disagree by more than 2%, ingest reports
both and uses the annual report. Show that table to the user; a large gap is
usually consolidated-versus-standalone or a restatement, and it matters.

### 3. Get the forecast drivers

Run the `financial-model-assumptions` skill to produce `assumptions.json`. That
skill is where a driver is argued for and cited; this one only consumes the
result. Anything it does not cover falls back to the trailing historical
average, which is a defensible default and a reported one.

Last-word overrides go in `overrides.drivers`.

### 4. Build

```bash
python scripts/build_model.py --in data/model_input.json --outdir data/ --strict
```

Writes `data/model.xlsx` and `data/model.json`. `--strict` exits non-zero on a
blocking check, so it can gate a pipeline.

The model is deliberately circular - interest is struck on average debt, and the
revolver is drawn from a cash flow that contains that interest. Python iterates
to a fixed point and the workbook is saved with iterative calculation enabled.
Report the residual; it should be zero or near it.

### 5. Review before anyone reads a number

```bash
python scripts/check_model.py --in data/model.json --md data/model_review.md
```

This is the step that turns a spreadsheet into a model you can defend. It
separates blocking checks from advisory ones, and puts every driver's forecast
next to its own history so a forecast that steps outside the historical range is
visible rather than buried. Walk the user through it using
`assets/output_template.md`.

### 6. Iterate

Change `overrides.json`, rebuild, re-review. Never edit `model.json`, and never
edit `model.xlsx` and expect it to survive.

## What the model contains

**Drivers** - growth, gross and EBITDA margin, other income, capex and
depreciation intensity, CWIP, DSO/DIO/DPO, other current assets and liabilities,
tax rate, cost of debt, yield on cash, debt growth and repayment, equity issued,
payout, minimum cash. Historical columns back-solve every one from the reported
figures, so history and forecast sit in the same units on the same row.

**Income statement** - revenue to EPS, with the operating expense line falling
out of gross profit less EBITDA.

**Balance sheet** - cash, receivables, inventories, other current assets, net
block, CWIP, investments; share capital, reserves, term debt, revolver, trade
payables, other liabilities.

**Cash flow** - indirect operating, investing, financing, and a reconciliation
to closing cash; plus the reported cash flow lines alongside, so the gap between
what the driver model reconstructs and what the company reported is visible.

**Schedules** - fixed asset roll-forward, net operating assets and their change,
debt with a revolver plug that funds any shortfall against the minimum cash
balance, and the equity roll.

**Checks** - four residuals that must read zero, four balances that must not go
negative, the historical ties, and plausibility bands. `references/checks.md`
says which have real teeth and which are identities by construction; read it
before telling anyone "all checks pass".

**Summary** - growth, margins, FCFF, FCFE, net debt, leverage, interest cover,
ROCE and ROE.

## Traps worth knowing before you build

- **A workbook written by openpyxl holds no cached values.** The formulas are
  real, but nothing has calculated them yet. Excel, LibreOffice and Google
  Sheets will compute them on open; `pandas.read_excel` will not. Read numbers
  from `model.json`, never from `model.xlsx`.
- **No expense detail means gross margin equals EBITDA margin** and the opex
  line is zero. That is honest, not broken - but inventory and payable days are
  then struck on a cost base that is total operating cost, so do not compare
  them to a peer's reported days.
- **`interest_income_rate` defaults to zero on purpose.** Reported other income
  already contains treasury income, and the other income driver is back-solved
  from it. Raising the yield without cutting `other_income_pct` counts the same
  income twice.
- **Payables from the annual report are netted out of other liabilities.** They
  are already inside Screener's "Other Liabilities" bucket; if they were simply
  added, the historical balance sheet would stop tying.
- **A revolver that grows every year is the model telling you something.** It
  means the plan does not fund itself. That is a finding, not a bug to suppress.

## Bundled resources

| File | Use |
|---|---|
| `scripts/ingest.py` | Screener + annual report + assumptions → `model_input.json`, with a reconciliation |
| `scripts/ar_tables.py` | find the statement tables in an annual-report-kb knowledge base |
| `scripts/build_model.py` | solve the model and write `model.xlsx` + `model.json` |
| `scripts/check_model.py` | the review: checks, drivers against history, outputs |
| `scripts/rows.py` | the model definition - every row and formula, defined once |
| `scripts/engine.py` | compiles one formula to both a value and an Excel cell |
| `references/structure.md` | sheets, rows, the formula language, how the balance sheet is made to tie |
| `references/inputs.md` | `model_input.json` and `overrides.json` schemas, the Screener mapping |
| `references/checks.md` | every check: what it means, which have teeth, how to fix a failure |
| `references/kb-inputs.md` | what to pull from the annual report and what it feeds |
| `references/integration.md` | the hand-offs to and from the three neighbouring skills |
| `assets/overrides_template.json` | the file the analyst edits |
| `assets/output_template.md` | how to present the model to the user |

`rows.py`, `engine.py` and `check_model.py` are standard library only. `ingest.py`
and `build_model.py` need `openpyxl`.

## Tone

Concise and plain. State what the model does, what it assumes, and where it is
weak. A model that balances is not a model that is right, and the difference is
worth saying out loud.
