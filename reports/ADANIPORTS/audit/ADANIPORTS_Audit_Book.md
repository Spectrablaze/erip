# Adani Ports and Special Economic Zone Ltd — ERIP Audit Book

**Sector:** realestate | **Currency:** INR cr | **Generated:** 2026-10-14 12:32

---

## Model Metadata

| Field | Value |
|-------|-------|
| Company | Adani Ports and Special Economic Zone Ltd |
| Currency | INR cr |
| Sector | realestate |
| Model built | 2026-10-14 |
| Depreciation basis | net_block |
| History | Mar-17 – Mar-26 (10 yr) |
| Forecast | Mar-27E – Mar-31E (5 yr) |

---

## Source Register

This register documents the origin of every material input to the model.

| Row Key | Source | Page | Provenance | Confidence | Period | Notes |
|---------|--------|------|------------|------------|--------|-------|
| rf | assumptions.json > rf |  | ASSUMPTION | MEDIUM |  | Analyst-assumed Risk-free rate: 6.78 |
| erp | assumptions.json > erp |  | ASSUMPTION | MEDIUM |  | Analyst-assumed Equity risk premium: 5.5 |
| beta | assumptions.json > beta |  | ASSUMPTION | MEDIUM |  | Analyst-assumed Equity beta: 1.3 |
| cost_of_debt | assumptions.json > cost_of_debt |  | ASSUMPTION | MEDIUM |  | Analyst-assumed Cost of debt: 8.0 |
| tax_rate | assumptions.json > tax_rate |  | ASSUMPTION | MEDIUM |  | Analyst-assumed Effective tax rate: 18.5 |
| terminal_growth | assumptions.json > terminal_growth |  | ASSUMPTION | MEDIUM |  | Analyst-assumed Terminal growth rate: 5.0 |

### Provenance Type Definitions

| Type | Definition |
|------|-----------|
| REPORTED | Directly from audited financial statements or regulatory filings |
| DERIVED | Calculated from reported figures (e.g., margin %) |
| ASSUMPTION | Analyst judgment not directly observable |
| MARKET | External market data (beta, WACC inputs, comps) |
| MODEL_DERIVED | Output of the model's own calculations |

### Confidence Level Definitions

| Level | Definition |
|-------|-----------|
| HIGH | Audited / regulatory filing |
| MEDIUM | Estimated / management guidance |
| LOW | Analyst judgment / no external source |

---

## Assumption Register

This register documents every significant assumption, its provenance, rationale, and approval status.

| Key | Value | Unit | Provenance | Rationale | Approval | Downstream Dependencies |
|-----|-------|------|------------|-----------|----------|------------------------|
| forecast_years | 5.0 |  | DERIVED | Set in assumptions.json for model | PENDING | model.json, model-workbook.xlsx, audit_book.md |
| tax_rate | 18.5 | % | ASSUMPTION | Set in assumptions.json for model | APPROVED | model.json, model-workbook.xlsx, audit_book.md |
| terminal_growth | 5.0 | % | ASSUMPTION | Set in assumptions.json for model | PENDING | model.json, model-workbook.xlsx, audit_book.md |
| cost_of_debt | 8.0 |  | ASSUMPTION | Set in assumptions.json for model | APPROVED | model.json, model-workbook.xlsx, audit_book.md |
| rf | 6.78 |  | ASSUMPTION | Set in assumptions.json for model | APPROVED | model.json, model-workbook.xlsx, audit_book.md |
| erp | 5.5 |  | ASSUMPTION | Set in assumptions.json for model | APPROVED | model.json, model-workbook.xlsx, audit_book.md |
| beta | 1.3 |  | ASSUMPTION | Set in assumptions.json for model | APPROVED | model.json, model-workbook.xlsx, audit_book.md |
| target_debt_weight | 12.0 |  | DERIVED | Set in assumptions.json for model | PENDING | model.json, model-workbook.xlsx, audit_book.md |
| net_debt | 42910.0 |  | DERIVED | Set in assumptions.json for model | PENDING | model.json, model-workbook.xlsx, audit_book.md |
| shares_out | 230.396 |  | DERIVED | Set in assumptions.json for model | PENDING | model.json, model-workbook.xlsx, audit_book.md |
| current_price | 1695.0 |  | DERIVED | Set in assumptions.json for model | PENDING | model.json, model-workbook.xlsx, audit_book.md |
| exit_multiple | 14.0 |  | DERIVED | Set in assumptions.json for model | PENDING | model.json, model-workbook.xlsx, audit_book.md |
| terminal_ronic | 10.5 |  | DERIVED | Set in assumptions.json for model | PENDING | model.json, model-workbook.xlsx, audit_book.md |
| mid_year_convention | True |  | DERIVED | Set in assumptions.json for model | PENDING | model.json, model-workbook.xlsx, audit_book.md |
| blume_adjust | True |  | DERIVED | Set in assumptions.json for model | PENDING | model.json, model-workbook.xlsx, audit_book.md |
| non_operating_assets | 3340.86 |  | DERIVED | Set in assumptions.json for model | PENDING | model.json, model-workbook.xlsx, audit_book.md |
| bull.revenue_growth | [5 values] | % | ASSUMPTION | Management delivers close to Ambition 2031: the 1bn-tonne capacity target lands on time, Colombo and Vizhinjam phase 2 ramp faster than modelled, the SEZ tax shield persists longer, and capex comes in at the bottom of the guided range. Mundra concession renewal is granted on existing terms. | PENDING | Scenario analysis (bull) |
| bull.ebitda_margin | [5 values] | % | ASSUMPTION | Management delivers close to Ambition 2031: the 1bn-tonne capacity target lands on time, Colombo and Vizhinjam phase 2 ramp faster than modelled, the SEZ tax shield persists longer, and capex comes in at the bottom of the guided range. Mundra concession renewal is granted on existing terms. | PENDING | Scenario analysis (bull) |
| bull.capex_pct_sales | [5 values] |  | ASSUMPTION | Management delivers close to Ambition 2031: the 1bn-tonne capacity target lands on time, Colombo and Vizhinjam phase 2 ramp faster than modelled, the SEZ tax shield persists longer, and capex comes in at the bottom of the guided range. Mundra concession renewal is granted on existing terms. | PENDING | Scenario analysis (bull) |
| bull.terminal_growth | 5.5 | % | ASSUMPTION | Management delivers close to Ambition 2031: the 1bn-tonne capacity target lands on time, Colombo and Vizhinjam phase 2 ramp faster than modelled, the SEZ tax shield persists longer, and capex comes in at the bottom of the guided range. Mundra concession renewal is granted on existing terms. | PENDING | Scenario analysis (bull) |
| bear.revenue_growth | [5 values] | % | ASSUMPTION | The volume-miss pattern continues and worsens: domestic cargo grows mid single digit rather than high single digit, the international book stays sub-scale at NQXT's lower realisation, and capex overshoots guidance as it did by 65% in FY24 and 33% in FY26. The SEZ tax shield unwinds to statutory. Terminal growth cut to 3.5% to reflect unresolved Mundra concession renewal beyond February 2031. | PENDING | Scenario analysis (bear) |
| bear.ebitda_margin | [5 values] | % | ASSUMPTION | The volume-miss pattern continues and worsens: domestic cargo grows mid single digit rather than high single digit, the international book stays sub-scale at NQXT's lower realisation, and capex overshoots guidance as it did by 65% in FY24 and 33% in FY26. The SEZ tax shield unwinds to statutory. Terminal growth cut to 3.5% to reflect unresolved Mundra concession renewal beyond February 2031. | PENDING | Scenario analysis (bear) |
| bear.capex_pct_sales | [5 values] |  | ASSUMPTION | The volume-miss pattern continues and worsens: domestic cargo grows mid single digit rather than high single digit, the international book stays sub-scale at NQXT's lower realisation, and capex overshoots guidance as it did by 65% in FY24 and 33% in FY26. The SEZ tax shield unwinds to statutory. Terminal growth cut to 3.5% to reflect unresolved Mundra concession renewal beyond February 2031. | PENDING | Scenario analysis (bear) |
| bear.terminal_growth | 3.5 | % | ASSUMPTION | The volume-miss pattern continues and worsens: domestic cargo grows mid single digit rather than high single digit, the international book stays sub-scale at NQXT's lower realisation, and capex overshoots guidance as it did by 65% in FY24 and 33% in FY26. The SEZ tax shield unwinds to statutory. Terminal growth cut to 3.5% to reflect unresolved Mundra concession renewal beyond February 2031. | PENDING | Scenario analysis (bear) |

---

## Data Lineage

Data lineage traces how inputs flow through the model to produce outputs.

### Stage 1: Sources (Raw Inputs)

Raw inputs from source documents

**Inputs:** 

### Stage 2: Assumptions (Analyst Judgment)

Analyst assumptions from assumptions.json

**Inputs:** forecast_years, sector, revenue_growth, ebit_margin, capex_pct_sales, dep_pct_sales, nwc_pct_sales, tax_rate, terminal_growth, cost_of_debt, rf, erp, beta, target_debt_weight, net_debt, shares_out, current_price, exit_multiple, terminal_ronic, peers, scenarios, mid_year_convention, blume_adjust, non_operating_assets, balance_date, first_fy_end, valuation_date

### Stage 3: Calculations (Model-Derived)

Model-generated values (model-derived)

**Inputs:** gross_profit, opex, ebit, eps, total_assets, debt_total, total_liab_eq, cf_pat, cf_dep, cf_wc, cfo, cf_capex, cf_invest, cfi, cf_debt, cf_revolver, cf_div, cf_equity, cff, net_change_cash, cash_open, cash_close, cfo_gap, nb_open, sch_dep, nb_close, nwc, d_nwc, wc_days, td_open, cff_ex_rev, cash_pre_rev, revolver_draw, revolver_repay, avg_debt, equity, bvps, chk_balance, chk_cash_tie, chk_reserves, chk_fa_roll, chk_min_cash, chk_revolver_pos, chk_nb_pos, chk_equity_pos, s_revenue, s_rev_growth, s_ebitda, s_ebitda_margin, s_ebit, s_pat, s_eps, s_fcff, s_fcfe, s_cash_conv, s_net_debt, s_nd_ebitda, s_int_cover, s_capemp, s_roce, s_roe

### Stage 4: Outputs

Final model outputs

**Outputs:** model.json, Company_ERIP_Model.xlsx, Company_ERIP_Audit_Book

---

## Material Valuation Inputs

This section explains the key inputs that drive the DCF valuation output.

| Input | Value | Format | Source | Provenance | Rationale |
|-------|-------|--------|--------|------------|-----------|
| Terminal Growth | 5.0 | 0.00% | assumptions.json | ASSUMPTION | Long-run GDP-equivalent growth rate for terminal value |

---

## Model Checks

| Status | Count | Description |
|--------|-------|-------------|
| Total checks | 16 | All integrity checks in model.json |
| Passed | 15 | Checks within tolerance |
| Failed | 1 | Checks outside tolerance |
| Blocking | 9 | Severity: blocking |
| Warning | 0 | Severity: warning |
| Overall | **PASS** | All checks within tolerance |

### Check Detail

| Check ID | Label | Status | Worst Value | Severity | Period |
|----------|-------|--------|-------------|----------|--------|
| chk_balance | Total assets less total liabilities and equity (forecast) | PASS | 0.0 | blocking | Mar-29E |
| chk_cash_tie | Balance sheet cash less cash flow closing cash (forecast) | PASS | 0.0 | blocking | Mar-31E |
| chk_reserves | Reserves roll-forward residual (forecast) | PASS | 0.0 | blocking | Mar-31E |
| chk_fa_roll | Net block roll-forward residual (forecast) | PASS | 0.0 | blocking | Mar-31E |
| chk_reserves_hist | Reserves roll-forward residual (history) | FAIL | 22582.9 | advisory | Mar-26 |
| chk_fa_roll_hist | Net block roll-forward residual (history) | PASS | 0.0 | advisory | Mar-21 |
| cfo_reconstruction | Reconstructed CFO close to reported CFO | PASS | 4415.24 | advisory | Mar-22 |
| chk_min_cash | Cash less the minimum cash balance | PASS | 10550.461 | blocking | Mar-27E |
| chk_revolver_pos | Revolver balance | PASS | 0.0 | blocking | Mar-27E |
| chk_nb_pos | Net block | PASS | 138607.4628 | blocking | Mar-27E |
| chk_equity_pos | Shareholders' equity | PASS | 107697.64 | blocking | Mar-27E |
| hist_balance | Historical balance sheet ties to the source | PASS | 0.0 | blocking | Mar-26 |
| band_tax_rate | Effective tax rate inside a plausible band | PASS | 0.0 | advisory | - |
| band_ebitda_margin | EBITDA margin inside a plausible band | PASS | 0.0 | advisory | - |
| band_rev_growth | Revenue growth inside a plausible band | PASS | 0.0 | advisory | - |
| band_payout_ratio | Dividend payout inside a plausible band | PASS | 0.0 | advisory | - |

---

## Screener vs Annual Report Reconciliation

This section documents the reconciliation between Screener.in data and the company's audited Annual Report.

| Line | Period | Screener Value | Annual Report Value | Difference % |
|------|--------|---------------|--------------------|--------------|

---

## Annual Report Citations

| Key | Source | Page |
|------|--------|------|

---

## Build Notes

- overrides.actuals.payables: period '_page' is not in the historical range, ignored
- trade payables supplied from the annual report were netted out of other liabilities so the balance sheet still ties
- no gross margin in assumptions.json: set equal to the EBITDA margin, which zeroes the opex line
- built against modeling strategy: revenue_model=segment_buildup, modelability=AMBER, decision=APPROVED
- block 'derived' not found in the export
- block 'price' not found in the export
- held at the trailing historical average (no value in assumptions.json or overrides): other_income_pct, dep_pct_nb, cwip_pct_sales, other_ca_pct, other_liab_pct, interest_income_rate, debt_growth, term_debt_repay, equity_issued, payout_ratio, min_cash
- not in the source at all, held at zero for every year: exceptional
- no actual for 'capex' in Mar-17: set to zero

---

## Appendices

### A. Input File Paths

| File | Path |
|------|------|
| model.json | data/three_statement/scenarios/base/model.json |
| assumptions.json | data/assumptions.json |

### B. Approval Signatures

| Role | Name | Date | Status |
|------|------|------|--------|
| Analyst | | | PENDING |
| Reviewer | | | PENDING |
| Sign-off Authority | | | PENDING |

---

*This audit book was generated automatically from model.json and assumptions.json. All values trace back to the authoritative model state. The audit book does not recalculate the financial model.*