# Macro pack — JSWINFRA

Built 2026-10-04 by `india-macro-pack`. Horizon: 2025A / 2026P / 2027P.

Every figure below is quotable as written — value, source and observation period travel together. Figures that could not be sourced are listed in §6, not silently omitted.

## 1. Global economy — blueprint page 2

Real GDP growth, % y-o-y.

| Geography | 2025A | 2026P | 2027P | Source |
|---|---|---|---|---|
| World | — | 3.1 | 3.2 | IMF WEO 2026-04 |
| Emerging market and developing economies | — | 3.9 | — | IMF WEO 2026-04 |
| India | — | 6.5 | — | IMF WEO 2026-04 |

Exhibit: `macro_global_gdp` (`bar_grouped`, horizontal) — already written into `data/macro_charts.json`.

## 2. Indian economy — blueprint page 3

KPI strip (`.kpis` block):

| Metric | Value | As of | Source |
|---|---|---|---|
| RBI policy repo rate | 5.2% | 2026-08-05 | RBI Monetary Policy Statement, August 2026 (unchanged fourth meeting, neutral stance); next decision 7 October 2026 with a 25 bp hike to 5.50% expected by 8 of 10 economists polled by Business Standard |
| India 10-year G-sec yield | 7.2% | 2026-10-01 | CCIL tenor-wise indicative yields, 6.94% GS 2036, 1 October 2026 |
| USD/INR reference rate | Rs 95.99 | 2026-10-01 | RBI / FBIL reference rate, 1 October 2026 |
| India CPI inflation, y-o-y | 4.8% | 2026-08 | MoSPI, CPI (base 2024=100) press release for August 2026; July final 4.45% |
| India WPI inflation, y-o-y | 9.9% | 2026-08 | Office of the Economic Adviser, WPI provisional estimates for August 2026 (July 9.78%) |

Real economy:

| Metric | Value | Period | Source |
|---|---|---|---|
| India real GDP growth, latest quarter | 7.8% | 2026-06 | MoSPI/NSO, Press Note on GDP Estimates for Q1 2026-27, released 31 August 2026 (nominal GDP growth 10.3%) |
| India IIP growth, y-o-y | 8.0% | 2026-08 | MoSPI, IIP quick estimates for August 2026 (manufacturing +9.0%; April-August +6.7%) |

## 3. Cross-check (not for citation)

World Bank WDI, India. Used only to catch a mirror serving bad data — the report cites MoSPI/RBI/IMF, never this.

| Series | Year | World Bank | IMF WEO |
|---|---|---|---|
| cpi | 2023 | 5.6% | — |
| cpi | 2024 | 5.0% | — |
| cpi | 2025 | 2.4% | — |
| gdp | 2024 | 7.1% | — |
| gdp | 2025 | 7.6% | — |

## 4. Industry layer — blueprint pages 4–9

| Figure | Value | Period | Forecast yr | Body | Source |
|---|---|---|---|---|---|
| APSEZ cargo, H1 FY27 (largest peer) | 280.00 MMT | 2026-09 | — | Company (APSEZ) | APSEZ September 2026 business update: H1 FY27 cargo 280 MMT, +15% YoY |
| India freight modal share, road | 65.0% | 2026-03 | — | Company presentation | JSW Infrastructure investor presentation, August 2026, p.10 (road 65%, rail 27%, others 8%) |
| India port capacity, FY26, and target | 2,810.00 MTPA | 2026-03 | 2047 | Company presentation citing Maritime Amrit Kaal Vision | JSW Infrastructure investor presentation, August 2026, p.10 |
| JSWINFRA share of all-India port cargo, FY26 (derived) | 7.3% | 2026-03 | — | Derived | JSWINFRA FY26 cargo 122 MT (annual report p.12) over the ~1,664 MMT all-India total implied by APSEZ's FY26 disclosure (451.0 MMT = 27.1%) |
| India major ports cargo traffic, FY26 | 915.17 MMT | 2026-03 | — | Ministry of Ports, Shipping and Waterways / IBEF | Major ports handle record 915 million tonnes cargo in FY26, IBEF news, 2026 |

**Never state a market size without its source and its forecast year.** A market-size number with no forecast year is unfalsifiable and will not survive being argued with.

## 5. Provenance — every figure in this pack

| Key | Value | Period | Age | Method | Source |
|---|---|---|---|---|---|
| `apsez_all_india_cargo_share_fy26` | 27.1% | 2026-03 | 187d **carried forward** | carried_forward | APSEZ FY26 media release, 30 April 2026 |
| `apsez_cargo_h1fy27` | 280.00 MMT | 2026-09 | 4d | manual | APSEZ September 2026 business update: H1 FY27 cargo 280 MMT, +15% YoY |
| `apsez_container_share_fy26` | 45.5% | 2026-03 | 187d **carried forward** | carried_forward | APSEZ FY26 media release, 30 April 2026 |
| `bank_credit_growth` | 18.3% | 2026-09 | 4d | manual | RBI Weekly Statistical Supplement, Scheduled Commercial Banks bank credit y-o-y, September 2026 (press release 63519) |
| `brent_crude` | US$114.0/bbl | 2026-09-29 | 5d | manual | EIA Europe Brent spot price FOB, 29 September 2026 (peak 130.80 on 15 September) |
| `cad_pct_gdp` | 0.6% | 2026-03 | 187d **OVER** **carried forward** | carried_forward | RBI, Developments in India's Balance of Payments, full year FY2025-26 |
| `forex_reserves` | US$757bn | 2026-09-25 | 9d | manual | RBI Weekly Statistical Supplement, week ended 25 September 2026 (record 785.7 on 4 September) |
| `gdp_emde_2026` | 3.9% | 2026 | -88d | manual | IMF WEO 2026-04 |
| `gdp_india_2026` | 6.5% | 2026 | -88d | manual | IMF WEO 2026-04 |
| `gdp_world_2026` | 3.1% | 2026 | -88d | manual | IMF WEO 2026-04 |
| `gdp_world_2027` | 3.2% | 2027 | -453d | manual | IMF WEO 2026-04 |
| `india_10y_gsec` | 7.2% | 2026-10-01 | 3d | manual | CCIL tenor-wise indicative yields, 6.94% GS 2036, 1 October 2026 |
| `india_container_traffic_cagr` | 8.00 % CAGR | 2026-03 | 187d **carried forward** | carried_forward | Container traffic to grow 7-9% as major ports outpace, industry report 2026 |
| `india_cpi` | 4.8% | 2026-08 | 34d | manual | MoSPI, CPI (base 2024=100) press release for August 2026; July final 4.45% |
| `india_freight_modal_share` | 65.0% | 2026-03 | 187d | manual | JSW Infrastructure investor presentation, August 2026, p.10 (road 65%, rail 27%, others 8%) |
| `india_gdp_fy_actual` | 7.4% | 2026-03 | 187d **carried forward** | carried_forward | NSO First Advance Estimates, FY2025-26 |
| `india_gdp_latest_q` | 7.8% | 2026-06 | 96d | manual | MoSPI/NSO, Press Note on GDP Estimates for Q1 2026-27, released 31 August 2026 (nominal GDP growth 10.3%) |
| `india_iip` | 8.0% | 2026-08 | 34d | manual | MoSPI, IIP quick estimates for August 2026 (manufacturing +9.0%; April-August +6.7%) |
| `india_port_capacity_fy26` | 2,810.00 MTPA | 2026-03 | 187d | manual | JSW Infrastructure investor presentation, August 2026, p.10 |
| `india_wpi` | 9.9% | 2026-08 | 34d | manual | Office of the Economic Adviser, WPI provisional estimates for August 2026 (July 9.78%) |
| `jswinfra_share_all_india_fy26` | 7.3% | 2026-03 | 187d | manual | JSWINFRA FY26 cargo 122 MT (annual report p.12) over the ~1,664 MMT all-India total implied by APSEZ's FY26 disclosure (451.0 MMT = 27.1%) |
| `major_port_leaders_fy26` | 160.11 MMT | 2026-03 | 187d **carried forward** | carried_forward | IBEF, major ports FY26 performance |
| `major_ports_cargo_fy26` | 915.17 MMT | 2026-03 | 187d | manual | Major ports handle record 915 million tonnes cargo in FY26, IBEF news, 2026 |
| `repo_rate` | 5.2% | 2026-08-05 | 60d | manual | RBI Monetary Policy Statement, August 2026 (unchanged fourth meeting, neutral stance); next decision 7 October 2026 with a 25 bp hike to 5.50% expected by 8 of 10 economists polled by Business Standard |
| `usdinr` | Rs 95.99 | 2026-10-01 | 3d | manual | RBI / FBIL reference rate, 1 October 2026 |

## 6. NOT in this pack — go and get these

_Nothing refused._

Never attempted this run (no manual entry supplied):

- `cad_pct_gdp` — India current account deficit · https://website.rbi.org.in/en/web/rbi/press-releases
- `fiscal_deficit_pct_gdp` — Union fiscal deficit · https://www.indiabudget.gov.in/
- `india_cpi_core` — India core CPI inflation, y-o-y · https://www.mospi.gov.in/cpi
- `india_gdp_fy_actual` — India real GDP growth, latest full FY · https://www.mospi.gov.in/data
- `india_gdp_per_capita` — India GDP per capita · https://www.mospi.gov.in/data
- `india_gva_fy_actual` — India real GVA growth, latest full FY · https://www.mospi.gov.in/data

Carried forward from a previous run — re-read before quoting:

`apsez_all_india_cargo_share_fy26`, `apsez_container_share_fy26`, `cad_pct_gdp`, `india_container_traffic_cagr`, `india_gdp_fy_actual`, `major_port_leaders_fy26`

