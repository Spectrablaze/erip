# Assumption catalog

One entry per required assumption. Each gives: where the evidence lives in a
knowledge base, the derivation from history, the plausibility band, and the
trap that most often produces a wrong number.

`kb_search.py find --for <preset>` runs the search terms for the rows that name
a preset. `history.py` produces every metric named under "Anchor".

Order of authority for every assumption:

1. Explicit forward guidance from management (call, presentation, MD&A)
2. Disclosed contracted facts (order book, approved capex, signed contracts)
3. The company's own history (3y and 5y, with the trend)
4. Industry report or peer disclosure inside the knowledge base
5. Nothing above → `Not enough evidence`

Never let 3 silently override 1. If history and guidance disagree, that
disagreement is the analysis - report both, recommend one, say why.

---

## Revenue

### Revenue Growth
- **Preset** `revenue_growth`  |  **Anchor** `revenue_growth`, `revenue_cagr`
- **Where** MD&A, letter to shareholders, earnings call Q&A, investor deck
  guidance slide, order book / backlog disclosure.
- **Derivation** Start from the 3y and 5y CAGR, then adjust for stated guidance,
  capacity coming on stream, and base effects. Taper toward the terminal rate by
  the final forecast year - a flat growth rate to year 5 is almost never
  defensible.
- **Band** -20% to +40%. Above 25% sustained needs contracted backlog or
  commissioned capacity behind it.
- **Trap** Quoting a one-year rebound off a COVID or commodity-crash base as the
  run rate. Check whether the base year was itself abnormal before anchoring.

### Volume Growth
- **Preset** `volume_growth`  |  **Anchor** none (physical units are rarely in
  the financials file)
- **Where** MD&A operational review, capacity utilisation tables, investor deck.
- **Derivation** Volume and price must multiply back to revenue growth:
  `(1+g_rev) ≈ (1+g_vol)(1+g_price)`. State the residual if they do not.
- **Band** -25% to +40%, and capped by installed capacity - a volume assumption
  above nameplate utilisation is impossible, not merely aggressive.
- **Trap** Applying it to a services or software company where there is no
  volume unit. Mark `not applicable` rather than inventing one.

### Pricing Growth
- **Preset** `pricing_growth`
- **Where** Realisation per tonne/unit disclosures, price hike commentary,
  contract escalation clauses, MD&A cost pass-through discussion.
- **Derivation** Residual of revenue growth over volume growth, cross-checked
  against disclosed realisation. For pass-through businesses, tie it to the
  input price rather than to inflation.
- **Band** -15% to +25%.
- **Trap** Treating realisation growth as pricing power when it is really mix
  shift toward premium products. Read the mix commentary before claiming it.

### New Customers
- **Preset** `new_customers`
- **Where** Investor deck customer-count slides, earnings call, MD&A.
- **Note** Most manufacturers and commodity companies never disclose this.
  `Not enough evidence` is the correct and common answer.

### Customer Retention
- **Preset** `customer_retention`
- **Where** SaaS/services decks (NRR, GRR, churn), MD&A repeat-business claims.
- **Band** 0-105% (net revenue retention can exceed 100%; gross cannot).
- **Trap** Confusing net revenue retention with logo retention. They differ by
  the expansion rate and are not interchangeable.

---

## Margins

### Gross Margin
- **Preset** `gross_margin`  |  **Anchor** `gross_margin`
- **Where** P&L cost of materials line, MD&A raw-material commentary.
- **Derivation** `(Sales - COGS) / Sales`. If the export has no material-cost
  line, gross margin cannot be computed - say so rather than reusing EBITDA
  margin under a different name.
- **Band** 5-90%.
- **Trap** Indian P&Ls split materials across "cost of materials consumed",
  "purchases of stock-in-trade" and "changes in inventories". Missing the
  inventory-change line misstates margin in any year with a stock build.

### EBITDA Margin
- **Preset** `ebitda_margin`  |  **Anchor** `ebitda_margin`
- **Where** Investor deck headline, MD&A, guidance.
- **Derivation** Historical level plus a stated, dated reason for any expansion:
  operating leverage on a named fixed-cost base, mix shift, a commissioned
  plant. Unattributed margin expansion is the most common way a model is
  quietly inflated.
- **Band** 0-60%.
- **Trap** Other income sitting inside reported EBITDA. Strip non-operating
  income or the margin is not comparable to peers.

### EBIT / Operating Margin
- **Preset** `ebit_margin`  |  **Anchor** `ebit_margin`
- **Derivation** EBITDA margin less depreciation % of sales. **This is the one
  margin `model.py` actually discounts** - if only EBITDA margin is set,
  `build_assumptions.py` derives EBIT from it and flags the derivation.
- **Band** 0-55%.
- **Trap** Holding EBIT margin flat while raising capex. New assets raise
  depreciation, which compresses EBIT unless revenue rises with it.

---

## Expenses

Each expense assumption is expressed as **% of sales** so it scales with the
revenue forecast.

### SG&A — `sga` | anchor `sga_pct_sales`
Indian P&Ls report this as "other expenses", which also contains power, freight
and job work. Note the contamination rather than presenting it as clean SG&A.

### R&D — `rnd` | anchor `rnd_pct_sales`
Check whether R&D is expensed or capitalised; capitalised R&D belongs in capex
and amortisation, not here. Pharma and specialty chemicals disclose it, most
others do not.

### Sales & Marketing — `sales_marketing` | anchor `marketing_pct_sales`
Consumer companies disclose A&P separately and it is a genuine strategic lever;
industrials rarely split it out. If it is inside "other expenses", say so.

### Employee Cost — `employee_cost` | anchor `employee_pct_sales`
Anchor to the ratio, then sanity-check against headcount and wage inflation
commentary. In services businesses this is the single largest cost line and
deserves its own reasoning, not a ratio held flat.

Bands: SG&A 0-40%, R&D 0-25%, S&M 0-30%, employee 0-60%.

---

## Capital

### Capex
- **Preset** `capex`  |  **Anchor** `capex_pct_sales`
- **Where** Cash flow statement, MD&A expansion plans, board-approved outlays,
  capital-commitment note, investor deck project timelines.
- **Derivation** Where a rupee/dollar programme is disclosed, spread it across
  the stated years and convert to % of forecast sales - do **not** just hold the
  historical ratio if a programme is announced. Separate maintenance capex
  (roughly depreciation) from growth capex.
- **Band** 0-30% of sales.
- **Trap** Cash-flow exports carry capex as a negative outflow. `history.py`
  takes the magnitude; a hand-built ratio often keeps the sign and inverts the
  free cash flow.

### Depreciation
- **Preset** `depreciation`  |  **Anchor** `dep_pct_sales`, `dep_pct_gross_block`
- **Derivation** Prefer % of gross block over % of sales - it stays stable when
  revenue moves and it responds correctly to the capex programme. Useful lives
  are in the significant-accounting-policies note.
- **Band** 0-20% of sales.
- **Trap** Assuming a large capex programme with unchanged depreciation. Assets
  commissioned in year *t* depreciate from year *t*, not from the terminal year.

### Amortisation
- **Preset** `amortisation`  |  **Anchor** `amort_pct_sales`
- Only material where there are acquired intangibles or capitalised development
  cost. Goodwill is not amortised under Ind AS/IFRS - it is impairment-tested,
  so do not model it as a recurring charge.

---

## Working capital

`model.py` consumes a single `nwc_pct_sales`. Set the three day-counts and let
`build_assumptions.py` convert them; it rescales the COGS-based legs correctly.

### DSO — `dso` | anchor `dso` | band 0-300 days
Receivables / sales x 365. Cross-check against the stated credit period and the
ageing schedule in the notes. Rising DSO against flat revenue is a revenue
quality flag worth naming.

### DIO — `dio` | anchor `dio` | band 0-400 days
Inventory / COGS x 365. State the denominator: `history.py` uses COGS where the
material line exists and falls back to sales otherwise, and the two are not
comparable.

### DPO — `dpo` | anchor `dpo` | band 0-300 days
Payables / COGS x 365. Check for supply-chain finance or bill discounting in the
notes - either flatters DPO without the underlying terms having changed.

**Conversion used by the builder**

```
NWC/Sales = DSO/365 + (DIO - DPO)/365 x (COGS/Sales)
```

Adding the three day-counts and dividing by 365 without rescaling the COGS legs
is the standard error; it overstates working capital for any high-gross-margin
company.

---

## Tax

### Effective Tax Rate
- **Preset** `tax_rate`  |  **Anchor** `effective_tax_rate`
- **Where** Tax note and the reconciliation of the statutory to the effective
  rate; earnings call commentary on the regime.
- **Derivation** Tax expense / PBT, averaged over 3-5 years to smooth one-off
  credits. Indian companies on section 115BAA sit near 25.17% including cess.
- **Band** 0-45%.
- **Trap** Using a rate depressed by expiring incentives - SEZ benefits, unit
  holidays and accumulated MAT credit all run out. Check the note for the expiry
  year and step the rate up to the statutory rate after it.

---

## Financing

### Interest Rate — `interest_rate` | anchor `interest_rate` | band 0-20%
Finance cost / average debt. Maps to `cost_of_debt`. Cross-check against
disclosed coupons and refinancing commentary. Capitalised borrowing cost on
projects under construction is excluded from the P&L charge, so the computed
rate understates the true cost during a build.

### Debt Growth — `debt_growth` | anchor `debt_growth`, `net_debt_ebitda`
Only relevant where debt is material or a repayment schedule is disclosed. Take
the schedule from the borrowings note where it exists rather than trending the
balance. For a net-cash company, note that and move on.

---

## Valuation

### Terminal Growth
- **Preset** `terminal_growth`  |  **Band** 0-7%
- **Rule** Must be below long-run nominal GDP for the company's main market, and
  **strictly below WACC** - `model.py` exits rather than warns if it is not.
  `build_assumptions.py` catches this before the model runs.
- Within 2pp of WACC the terminal value dominates the valuation. When terminal
  value exceeds ~75% of enterprise value, say so explicitly.

### WACC
- **Preset** `wacc`
- **Components** `risk_free_rate` (10y sovereign), `equity_risk_premium`,
  `beta`, `cost_of_debt` (= the interest rate assumption),
  `target_debt_weight`, and the tax rate.
- **Honesty rule** The risk-free rate, ERP and beta are market data and are
  normally **not in a company knowledge base**. Mark them `external` in the
  evidence field rather than dressing them up as knowledge-base findings. The
  cost of debt and the capital structure usually *are* in the knowledge base.
- `model.py` may unlever peer betas and relever at the target structure, and can
  Blume-adjust; the WACC it prints can therefore differ slightly from the
  builder's check, which uses the simple form.

### Supporting inputs
`net_debt`, `shares_out` and `current_price` are not forecast assumptions but
`model.py` needs them for the per-share bridge. Shares outstanding and net debt
come from the balance sheet and the notes; the current price is external market
data.
