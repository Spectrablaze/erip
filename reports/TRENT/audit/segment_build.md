# Segment revenue build — Trent Ltd

*Base year FY26; strategy is APPROVED / GREEN*

Consolidated revenue is the sum of segment revenue, each built from its approved economic archetype on approved, cited drivers. The growth path below is DERIVED from that build — it is what financial-model's single revenue row consumes. Every figure traces back through segments[].rows to the drivers and their citations.

## Consolidated

| | FY26 | FY27 | FY28 | FY29 | FY30 | FY31 | FY32 | FY33 | FY34 | FY35 | FY36 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Revenue | 20,075 | 24,086 | 27,933 | 32,302 | 36,995 | 42,017 | 47,195 | 52,588 | 57,986 | 63,676 | 69,730 |
| **Derived growth %** | — | **+20.0** | **+16.0** | **+15.6** | **+14.5** | **+13.6** | **+12.3** | **+11.4** | **+10.3** | **+9.8** | **+9.5** |

This growth path is what `financial-model-assumptions` injects as `revenue_growth`, and what `financial-model`'s single revenue row executes.

## Fashion and lifestyle (Westside, Zudio, Samoh, Burnt Toast) — stores_sales_per_store

`revenue = average store count x sales per store, decomposed into new-store contribution and same-store sales growth`

**Base-year tie-out:** checked — reported 20,074, rebuilt 20,075 (+0.00%)

| Driver | FY26 | FY27 | FY28 | FY29 | FY30 | FY31 | FY32 | FY33 | FY34 | FY35 | FY36 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| opening_stores | 13.5 | 17.7 | 21.1 | 24.6 | 28.1 | 31.6 | 34.8 | 37.8 | 40.5 | 43.1 | 45.5 |
| adds | 4.2 | 3.45 | 3.5 | 3.5 | 3.4 | 3.2 | 3 | 2.8 | 2.6 | 2.4 | 2.2 |
| closing_stores | 17.7 | 21.1 | 24.6 | 28.1 | 31.6 | 34.8 | 37.8 | 40.5 | 43.1 | 45.5 | 47.8 |
| effective_stores | 15 | 18.9 | 22.4 | 25.9 | 29.3 | 32.7 | 35.8 | 38.7 | 41.5 | 44 | 46.3 |
| sales_per_store | 1.34e+03 | 1.27e+03 | 1.25e+03 | 1.25e+03 | 1.26e+03 | 1.29e+03 | 1.32e+03 | 1.36e+03 | 1.4e+03 | 1.45e+03 | 1.51e+03 |
| maturity_ramp | 0.35 | 0.35 | 0.35 | 0.35 | 0.35 | 0.35 | 0.35 | 0.35 | 0.35 | 0.35 | 0.35 |
| **Revenue** | **20,075** | **24,086** | **27,933** | **32,302** | **36,995** | **42,017** | **47,195** | **52,588** | **57,986** | **63,676** | **69,730** |
| Growth % | — | +20.0 | +16.0 | +15.6 | +14.5 | +13.6 | +12.3 | +11.4 | +10.3 | +9.8 | +9.5 |

**Citations**

- `opening_stores` — "Retail Area (Million square feet) FY25 13.5 (Westside 5.5, Zudio 8.0); FY26 17.7 (7.3, 10.4)" — `kb/annual_report/images/charts/retail_area_margin_shrinkage_fy22_fy26.jpg`, p. 118
- `store_adds` — "4 Million+ sq. ft. New Retail Area Added" — `kb/annual_report/pages/page_0007.md`, p. 7
- `sales_per_store` — "annualized fashion portfolio level SPSF for FY26 ... Metro/Tier I 15,318; Tier II 13,390; rest of India 12,504" — `kb/annual_report/sections/12_management_discussion_analysis.md`, p. 118
- `maturity_curve` — "Zudio net adds Q1-Q4 FY26: 1/40/48/109; Westside 0/13/17/22" — `kb/investor_presentation/images/charts/store_additions_westside_zudio_q1fy26_q1fy27.jpg`, p. 7
