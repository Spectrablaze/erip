# Adani Ports and Special Economic Zone Ltd — Audit Book

- **Company:** Adani Ports and Special Economic Zone Ltd
- **Ticker:** ADANIPORTS
- **Sector:** Real estate / infrastructure / EPC
- **Currency:** INR (crore)
- **Built:** 2026-08-13 09:15 UTC
- **Overall:** PASS

## 1. Source Register

### Altman Z

| Key | Label | Source | Provenance | Confidence |
|-----|-------|--------|-----------|------------|
| altman_z | Altman Z | model.json (computed by model.py) | **MODEL_DERIVED** | 🟢 |

### Dcf

| Key | Label | Source | Provenance | Confidence |
|-----|-------|--------|-----------|------------|
| dcf | Dcf | model.json (computed by model.py) | **MODEL_DERIVED** | 🟢 |

### Dupont

| Key | Label | Source | Provenance | Confidence |
|-----|-------|--------|-----------|------------|
| dupont | Dupont | model.json (computed by model.py) | **MODEL_DERIVED** | 🟢 |

### Forensic

| Key | Label | Source | Provenance | Confidence |
|-----|-------|--------|-----------|------------|
| forensic | Forensic | model.json (computed by model.py) | **MODEL_DERIVED** | 🟢 |

### Piotroski F

| Key | Label | Source | Provenance | Confidence |
|-----|-------|--------|-----------|------------|
| piotroski_f | Piotroski F | model.json (computed by model.py) | **MODEL_DERIVED** | 🟢 |

### Ratios

| Key | Label | Source | Provenance | Confidence |
|-----|-------|--------|-----------|------------|
| ratios | Ratios | model.json (computed by model.py) | **MODEL_DERIVED** | 🟢 |

### Relative

| Key | Label | Source | Provenance | Confidence |
|-----|-------|--------|-----------|------------|
| relative | Relative | model.json (computed by model.py) | **MODEL_DERIVED** | 🟢 |

### Roiic

| Key | Label | Source | Provenance | Confidence |
|-----|-------|--------|-----------|------------|
| roiic | Roiic | model.json (computed by model.py) | **MODEL_DERIVED** | 🟢 |

### Scenarios

| Key | Label | Source | Provenance | Confidence |
|-----|-------|--------|-----------|------------|
| scenarios | Scenarios | model.json (computed by model.py) | **MODEL_DERIVED** | 🟢 |

### Sector Profile

| Key | Label | Source | Provenance | Confidence |
|-----|-------|--------|-----------|------------|
| sector_profile | Sector Profile | model.json (computed by model.py) | **MODEL_DERIVED** | 🟢 |

### Valuation Strategy

| Key | Label | Source | Provenance | Confidence |
|-----|-------|--------|-----------|------------|
| valuation_strategy | Valuation Strategy | model.json (computed by model.py) | **MODEL_DERIVED** | 🟢 |

## 2. Assumption Registers

**Total assumptions:** 23

| ID | Description | Value | Unit | Provenance | Confidence | Source |
|----|-----------|-------|------|-----------|------------|--------|
| forecast_years | Forecast Years | 5.0000 | various | **ASSUMPTION** | 🟡 | assumptions.json |
| sector | Sector | realestate | various | **ASSUMPTION** | 🟡 | assumptions.json |
| revenue_growth | Revenue Growth | [21.39, 13.02, 14.47, 14.81, 12.09] | various | **ASSUMPTION** | 🟡 | assumptions.json |
| ebit_margin | Ebit Margin | [44.0, 43.5, 43.0, 42.5, 42.0] | various | **ASSUMPTION** | 🟡 | assumptions.json |
| capex_pct_sales | Capex Pct Sales | [31.0, 30.0, 29.0, 28.0, 26.0] | various | **ASSUMPTION** | 🟡 | assumptions.json |
| dep_pct_sales | Dep Pct Sales | [14.5, 14.5, 14.8, 15.0, 15.2] | various | **ASSUMPTION** | 🟡 | assumptions.json |
| nwc_pct_sales | Nwc Pct Sales | [11.1, 10.82, 10.55, 10.27, 10.0] | various | **ASSUMPTION** | 🟡 | assumptions.json |
| tax_rate | Tax Rate | 18.5000 | various | **ASSUMPTION** | 🟡 | assumptions.json |
| terminal_growth | Terminal Growth | 5.0000 | various | **ASSUMPTION** | 🟡 | assumptions.json |
| cost_of_debt | Cost Of Debt | 8.0000 | various | **ASSUMPTION** | 🟡 | assumptions.json |
| rf | Rf | 6.7800 | various | **ASSUMPTION** | 🟡 | assumptions.json |
| erp | Erp | 5.5000 | various | **ASSUMPTION** | 🟡 | assumptions.json |
| beta | Beta | 1.3000 | various | **ASSUMPTION** | 🟡 | assumptions.json |
| target_debt_weight | Target Debt Weight | 12.0000 | various | **ASSUMPTION** | 🟡 | assumptions.json |
| net_debt | Net Debt | 42910.0000 | various | **ASSUMPTION** | 🟡 | assumptions.json |
| shares_out | Shares Out | 230.3960 | various | **ASSUMPTION** | 🟡 | assumptions.json |
| current_price | Current Price | 1695.0000 | various | **ASSUMPTION** | 🟡 | assumptions.json |
| exit_multiple | Exit Multiple | 14.0000 | various | **ASSUMPTION** | 🟡 | assumptions.json |
| peers | Peers | [{'name': 'Adani Ports and Special Economic Zone Ltd', 'price': 1695.0, 'mcap': 390521.0505, 'ev': 448459.2405, 'sales': 40430.43, 'ebitda': 23398.73, 'pat': 13112.02, 'bv': 95958.76999999999, 'roe': 16.6}, {'name': 'JSW Infrastructure Ltd', 'price': 327.5, 'mcap': 68775.0655, 'ev': 73356.2855, 'sales': 5582.42, 'ebitda': 2696.4, 'pat': 1485.26, 'bv': 10877.5, 'roe': 14.4}, {'name': 'Gujarat Pipavav Port Ltd', 'price': 151.26, 'mcap': 7312.51344, 'ev': 6673.4634399999995, 'sales': 1158.9, 'ebitda': 709.23, 'pat': 500.36, 'bv': 2155.23, 'roe': 23.4}, {'name': 'Container Corporation of India Ltd', 'price': 512.0, 'mcap': 31195.8528, 'ev': 28673.1028, 'sales': 9085.1, 'ebitda': 1961.53, 'pat': 1242.0, 'bv': 12942.35, 'roe': 9.8}] | various | **ASSUMPTION** | 🟡 | assumptions.json |
| scenarios | Scenarios | {'bull': {'probability': 0.25, 'revenue_growth': [24.0, 16.0, 17.0, 17.0, 15.0], 'ebitda_margin': [59.5, 59.5, 59.0, 59.0, 58.5], 'capex_pct_sales': [30.0, 28.0, 27.0, 25.0, 23.0], 'terminal_growth': 5.5, 'effective_tax_rate': 16.0, '_why': 'Management delivers close to Ambition 2031: the 1bn-tonne capacity target lands on time, Colombo and Vizhinjam phase 2 ramp faster than modelled, the SEZ tax shield persists longer, and capex comes in at the bottom of the guided range. Mundra concession renewal is granted on existing terms.'}, 'base': {'probability': 0.5, '_why': 'The assumption set above as recommended.'}, 'bear': {'probability': 0.25, 'revenue_growth': [16.0, 8.0, 8.0, 8.0, 7.0], 'ebitda_margin': [57.0, 55.5, 54.0, 53.0, 52.0], 'capex_pct_sales': [34.0, 34.0, 33.0, 32.0, 30.0], 'terminal_growth': 3.5, 'effective_tax_rate': 23.0, '_why': "The volume-miss pattern continues and worsens: domestic cargo grows mid single digit rather than high single digit, the international book stays sub-scale at NQXT's lower realisation, and capex overshoots guidance as it did by 65% in FY24 and 33% in FY26. The SEZ tax shield unwinds to statutory. Terminal growth cut to 3.5% to reflect unresolved Mundra concession renewal beyond February 2031."}} | various | **ASSUMPTION** | 🟡 | assumptions.json |
| mid_year_convention | Mid Year Convention | True | various | **ASSUMPTION** | 🟡 | assumptions.json |
| blume_adjust | Blume Adjust | True | various | **ASSUMPTION** | 🟡 | assumptions.json |
| non_operating_assets | Non Operating Assets | 3340.8600 | various | **ASSUMPTION** | 🟡 | assumptions.json |

## 3. Lineage

### Phase 1 — Data ingestion

- **Source:** Screener.in XLSX export (consolidated, FY17–FY26)
- **Output:** reports/ADANIPORTS/data/financials_raw.json
- **Description:** Ten-year historical income statement, balance sheet and cash flow extracted from Screener.in export.

### Phase 3f — Model computation

- **Source:** model.py (ratios, DuPont, ROIIC, forensic, DCF, relative valuation)
- **Output:** reports/ADANIPORTS/data/model.json
- **Description:** All ratios, ratios, DCF parameters, scenarios and sensitivity arrays computed from historical data and assumptions.

### Phase 3c — Assumptions

- **Source:** assumptions.json (analyst-cited)
- **Output:** reports/ADANIPORTS/data/assumptions.json
- **Description:** Operating and valuation assumptions set by analyst with source citations.

### Phase 5 — Workbook

- **Source:** model.json + assumptions.json → model_workbook_adapter.py → build_workbook.py
- **Output:** reports/ADANIPORTS/output/ADANIPORTS_Model.xlsx
- **Description:** Formula-driven Excel workbook with 13 sheets, cross-sheet references, DCF and sensitivity tables.

### This audit book

- **Source:** model_audit_adapter.py + build_audit_book.py
- **Output:** reports/ADANIPORTS/output/ADANIPORTS_Audit_Book.md
- **Description:** Provenance trace from source files through every model layer.

## 4. Valuation Inputs

| Parameter | Value | Unit | Source | Provenance | Confidence | Notes |
|-----------|-------|------|--------|-----------|------------|-------|
| WACC | 12.5600 | % | model.json > dcf.wacc_build | **MARKET** | 🟡 | Built from Rf=6.78%, Beta=1.2, ERP=5.5% |
| Cost of equity | 13.3900 | % | model.json > dcf.wacc_build | **MARKET** | 🟡 | CAPM: Rf=6.78%, Beta=1.2, ERP=5.5% |
| Cost of debt (post-tax) | 6.5200 | % | model.json > dcf.wacc_build | **MARKET** | 🟡 | Pre-tax: 8.0%, Tax rate: 18.5% |
| Target debt weight | 12.0000 | % | model.json > dcf.wacc_build | **ASSUMPTION** | 🟡 | Analyst-set target capital structure |
| Enterprise value | 187180 | INR crore | model.json > dcf.bridge | **MODEL_DERIVED** | 🟢 | PV explicit FCFF: 44518 + PV TV: 142663 |
| Equity value per share | — | INR | model.json > dcf.bridge | **MODEL_DERIVED** | 🟢 | EV: 187180 cr, Net debt: None cr |
| Terminal EBIT margin | 42.0000 | % | model.json > dcf.forecast[-1] | **ASSUMPTION** | 🟡 | Exit margin from final forecast year |

## 5. Checks

| Check | Severity | Result |
|-------|----------|--------|
| block 'derived' not found in the export | info | ✅ Pass |
| block 'price' not found in the export | info | ✅ Pass |

**Total:** 2 | **Passed:** 2 | **Failed:** 0 | **Blocking:** 0

