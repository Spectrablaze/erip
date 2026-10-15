# Macro pack — TRENT

Built 2026-10-15 by `india-macro-pack`. Horizon: 2025A / 2026P / 2027P.

Every figure below is quotable as written — value, source and observation period travel together. Figures that could not be sourced are listed in §6, not silently omitted.

## 1. Global economy — blueprint page 2

Real GDP growth, % y-o-y.

| Geography | 2025A | 2026P | 2027P | Source |
|---|---|---|---|---|
| World | — | 3.1 | 3.4 | IMF WEO 2026-10 |
| China | — | 4.5 | 4.0 | IMF WEO 2026-10 |
| India | — | 7.0 | 7.0 | IMF WEO 2026-10 |

Exhibit: `macro_global_gdp` (`bar_grouped`, horizontal) — already written into `data/macro_charts.json`.

## 2. Indian economy — blueprint page 3

KPI strip (`.kpis` block):

| Metric | Value | As of | Source |
|---|---|---|---|
| RBI policy repo rate | 5.5% | 2026-10-07 | RBI Monetary Policy Statement, 7 October 2026 (Reuters, 7 Oct 2026) |
| India 10-year G-sec yield | 7.3% | 2026-10-13 | India 10Y G-sec yield, 13 October 2026 (Trading Economics, OTC interbank quotes); 7.24% close on 7 October after the RBI decision (Times of India / Reuters) |
| USD/INR reference rate | Rs 95.17 | 2026-10-14 | Interbank close (provisional), 14 October 2026 (The Hindu / PTI); fourth straight gain after RBI dollar-window measures |
| India CPI inflation, y-o-y | 5.5% | 2026-09 | MoSPI CPI (base 2024=100) release for September 2026, 12 October 2026 (provisional; food inflation 7.74%; August 4.83%) |
| India WPI inflation, y-o-y | 11.4% | 2026-09 | Office of the Economic Adviser, WPI provisional estimates for September 2026, 14 October 2026 (fuel and power 25.85%, manufactured products 9.76%; wearing apparel index 113.1) |

Real economy:

| Metric | Value | Period | Source |
|---|---|---|---|
| India real GDP growth, latest full FY | 7.4% | 2026-03 | NSO, FY2025-26 estimate as carried in reports/_knowledge/macro.json (4 October 2026) |
| India real GDP growth, latest quarter | 7.8% | 2026-06 | MoSPI/NSO, Press Note on GDP Estimates for Q1 2026-27, released 31 August 2026 (nominal GDP growth 10.3%) |
| India IIP growth, y-o-y | 8.0% | 2026-08 | MoSPI, IIP quick estimates for August 2026 (manufacturing +9.0%); September IIP due 28 October |

## 3. Cross-check (not for citation)

World Bank WDI, India. Used only to catch a mirror serving bad data — the report cites MoSPI/RBI/IMF, never this.

| Series | Year | World Bank | IMF WEO |
|---|---|---|---|
| cpi | 2023 | 5.6% | — |
| cpi | 2024 | 5.0% | — |
| cpi | 2025 | 2.4% | — |
| gdp | 2023 | 7.2% | — |
| gdp | 2024 | 7.1% | — |
| gdp | 2025 | 7.6% | — |

## 4. Industry layer — blueprint pages 4–9

| Figure | Value | Period | Forecast yr | Body | Source |
|---|---|---|---|---|---|
| Share of India apparel market in Tier II and smaller towns, FY25 | 69.5% | 2025-03 | — | Wazir Advisors | Wazir Advisors FY2025 city-tier analysis as cited by Indian Retailer (September 2026): total ~INR 9.5 trn, Tier II ~2.0 trn, Tier III and beyond ~4.6 trn |
| India apparel retail market, FY25 | 9.30 INR lakh cr | 2025-03 | — | CareEdge Ratings | CareEdge Ratings, 'India's Apparel Retail Market to Touch ~Rs 16 Lakh Crore by FY30', 14 January 2026 |
| India apparel retail market, FY30 forecast | 16.00 INR lakh cr | 2026-01 | 2030 | CareEdge Ratings | CareEdge Ratings, 14 January 2026 (~INR 16 lakh cr, US$176-193 bn depending on the rupee rate assumed) |
| Organised retail apparel sales growth, y-o-y, August 2026 | 10.0% | 2026-08 | — | Retailers Association of India | RAI Business Survey Round 74, August 2026 (via IBEF / Economic Times, 24 September 2026); overall retail +10%, footwear +8% |

**Never state a market size without its source and its forecast year.** A market-size number with no forecast year is unfalsifiable and will not survive being argued with.

## 5. Provenance — every figure in this pack

| Key | Value | Period | Age | Method | Source |
|---|---|---|---|---|---|
| `apparel_tier2_plus_share_fy25` | 69.5% | 2025-03 | 563d **OVER** | manual | Wazir Advisors FY2025 city-tier analysis as cited by Indian Retailer (September 2026): total ~INR 9.5 trn, Tier II ~2.0 trn, Tier III and beyond ~4.6 trn |
| `apsez_all_india_cargo_share_fy26` | 27.1% | 2026-03 | 198d **carried forward** | carried_forward | APSEZ FY26 media release, 30 April 2026 |
| `apsez_cargo_h1fy27` | 280.00 MMT | 2026-09 | 15d **carried forward** | carried_forward | APSEZ September 2026 business update: H1 FY27 cargo 280 MMT, +15% YoY |
| `apsez_container_share_fy26` | 45.5% | 2026-03 | 198d **carried forward** | carried_forward | APSEZ FY26 media release, 30 April 2026 |
| `bank_credit_growth` | 18.3% | 2026-09 | 15d **carried forward** | carried_forward | RBI Weekly Statistical Supplement, Scheduled Commercial Banks bank credit y-o-y, September 2026 (press release 63519) |
| `brent_crude` | US$106.0/bbl | 2026-10-14 | 1d | manual | Brent futures ~US$106/bbl on 14 October 2026 (Moneycontrol 105.93; The Hindu 106.37); EIA spot not yet read |
| `cad_pct_gdp` | 0.6% | 2026-03 | 198d **OVER** **carried forward** | carried_forward | RBI, Developments in India's Balance of Payments, full year FY2025-26 |
| `cpi_world_2026` | 4.7% | 2026 | -77d | manual | IMF WEO 2026-10 |
| `cpi_world_2027` | 4.1% | 2027 | -442d | manual | IMF WEO 2026-10 |
| `forex_reserves` | US$757bn | 2026-09-25 | 20d **carried forward** | carried_forward | RBI Weekly Statistical Supplement, week ended 25 September 2026 (record 785.7 on 4 September) |
| `gdp_china_2026` | 4.5% | 2026 | -77d | manual | IMF WEO 2026-10 |
| `gdp_china_2027` | 4.0% | 2027 | -442d | manual | IMF WEO 2026-10 |
| `gdp_emde_2026` | 3.9% | 2026 | -77d **carried forward** | carried_forward | IMF WEO 2026-04 |
| `gdp_india_2026` | 7.0% | 2026 | -77d | manual | IMF WEO 2026-10 |
| `gdp_india_2027` | 7.0% | 2027 | -442d | manual | IMF WEO 2026-10 |
| `gdp_world_2026` | 3.1% | 2026 | -77d | manual | IMF WEO 2026-10 |
| `gdp_world_2027` | 3.4% | 2027 | -442d | manual | IMF WEO 2026-10 |
| `india_10y_gsec` | 7.3% | 2026-10-13 | 2d | manual | India 10Y G-sec yield, 13 October 2026 (Trading Economics, OTC interbank quotes); 7.24% close on 7 October after the RBI decision (Times of India / Reuters) |
| `india_apparel_market_fy25` | 9.30 INR lakh cr | 2025-03 | 563d **OVER** | manual | CareEdge Ratings, 'India's Apparel Retail Market to Touch ~Rs 16 Lakh Crore by FY30', 14 January 2026 |
| `india_apparel_market_fy30` | 16.00 INR lakh cr | 2026-01 | 257d | manual | CareEdge Ratings, 14 January 2026 (~INR 16 lakh cr, US$176-193 bn depending on the rupee rate assumed) |
| `india_container_traffic_cagr` | 8.00 % CAGR | 2026-03 | 198d **carried forward** | carried_forward | Container traffic to grow 7-9% as major ports outpace, industry report 2026 |
| `india_cpi` | 5.5% | 2026-09 | 15d | manual | MoSPI CPI (base 2024=100) release for September 2026, 12 October 2026 (provisional; food inflation 7.74%; August 4.83%) |
| `india_freight_modal_share` | 65.0% | 2026-03 | 198d **carried forward** | carried_forward | JSW Infrastructure investor presentation, August 2026, p.10 (road 65%, rail 27%, others 8%) |
| `india_gdp_fy_actual` | 7.4% | 2026-03 | 198d | manual | NSO, FY2025-26 estimate as carried in reports/_knowledge/macro.json (4 October 2026) |
| `india_gdp_latest_q` | 7.8% | 2026-06 | 107d | manual | MoSPI/NSO, Press Note on GDP Estimates for Q1 2026-27, released 31 August 2026 (nominal GDP growth 10.3%) |
| `india_iip` | 8.0% | 2026-08 | 45d | manual | MoSPI, IIP quick estimates for August 2026 (manufacturing +9.0%); September IIP due 28 October |
| `india_port_capacity_fy26` | 2,810.00 MTPA | 2026-03 | 198d **carried forward** | carried_forward | JSW Infrastructure investor presentation, August 2026, p.10 |
| `india_wpi` | 11.4% | 2026-09 | 15d | manual | Office of the Economic Adviser, WPI provisional estimates for September 2026, 14 October 2026 (fuel and power 25.85%, manufactured products 9.76%; wearing apparel index 113.1) |
| `jswinfra_share_all_india_fy26` | 7.3% | 2026-03 | 198d **carried forward** | carried_forward | JSWINFRA FY26 cargo 122 MT (annual report p.12) over the ~1,664 MMT all-India total implied by APSEZ's FY26 disclosure (451.0 MMT = 27.1%) |
| `major_port_leaders_fy26` | 160.11 MMT | 2026-03 | 198d **carried forward** | carried_forward | IBEF, major ports FY26 performance |
| `major_ports_cargo_fy26` | 915.17 MMT | 2026-03 | 198d **carried forward** | carried_forward | Major ports handle record 915 million tonnes cargo in FY26, IBEF news, 2026 |
| `rai_apparel_growth_aug26` | 10.0% | 2026-08 | 45d | manual | RAI Business Survey Round 74, August 2026 (via IBEF / Economic Times, 24 September 2026); overall retail +10%, footwear +8% |
| `repo_rate` | 5.5% | 2026-10-07 | 8d | manual | RBI Monetary Policy Statement, 7 October 2026 (Reuters, 7 Oct 2026) |
| `usdinr` | Rs 95.17 | 2026-10-14 | 1d | manual | Interbank close (provisional), 14 October 2026 (The Hindu / PTI); fourth straight gain after RBI dollar-window measures |

## 6. NOT in this pack — go and get these

_Nothing refused._

Never attempted this run (no manual entry supplied):

- `bank_credit_growth` — Scheduled commercial bank credit growth, y-o-y · https://website.rbi.org.in/en/web/rbi/statistics
- `cad_pct_gdp` — India current account deficit · https://website.rbi.org.in/en/web/rbi/press-releases
- `fiscal_deficit_pct_gdp` — Union fiscal deficit · https://www.indiabudget.gov.in/
- `forex_reserves` — India foreign exchange reserves · https://website.rbi.org.in/en/web/rbi/statistics
- `india_cpi_core` — India core CPI inflation, y-o-y · https://www.mospi.gov.in/cpi
- `india_gdp_per_capita` — India GDP per capita · https://www.mospi.gov.in/data
- `india_gva_fy_actual` — India real GVA growth, latest full FY · https://www.mospi.gov.in/data

Carried forward from a previous run — re-read before quoting:

`apsez_all_india_cargo_share_fy26`, `apsez_cargo_h1fy27`, `apsez_container_share_fy26`, `bank_credit_growth`, `cad_pct_gdp`, `forex_reserves`, `gdp_emde_2026`, `india_container_traffic_cagr`, `india_freight_modal_share`, `india_port_capacity_fy26`, `jswinfra_share_all_india_fy26`, `major_port_leaders_fy26`, `major_ports_cargo_fy26`

