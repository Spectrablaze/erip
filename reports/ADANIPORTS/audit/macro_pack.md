# Macro pack — ADANIPORTS

Built 2026-08-07 by `india-macro-pack`. Horizon: 2025A / 2026P / 2027P.

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
| RBI policy repo rate | 5.2% | 2026-08-05 | RBI Monetary Policy Statement, August 2026 |
| India 10-year G-sec yield | 6.8% | 2026-08-05 | India 10-year G-sec benchmark yield, 5 August 2026, post RBI policy |
| USD/INR reference rate | Rs 95.23 | 2026-08-06 | USD/INR market close, 6 August 2026 |
| India CPI inflation, y-o-y | 4.4% | 2026-06 | MoSPI, CPI press release for June 2026, released 13 July 2026 |
| India WPI inflation, y-o-y | 9.9% | 2026-06 | Office of the Economic Adviser / PIB, WPI provisional estimates for June 2026 |

Real economy:

| Metric | Value | Period | Source |
|---|---|---|---|
| India real GDP growth, latest full FY | 7.4% | 2026-03 | NSO First Advance Estimates, FY2025-26 |
| India IIP growth, y-o-y | 7.3% | 2026-06 | MoSPI, Index of Industrial Production, June 2026 |

## 3. Cross-check (not for citation)

World Bank WDI, India. Used only to catch a mirror serving bad data — the report cites MoSPI/RBI/IMF, never this.

| Series | Year | World Bank | IMF WEO |
|---|---|---|---|
| cpi | 2023 | 5.6% | — |
| cpi | 2024 | 5.0% | — |
| cpi | 2025 | 2.4% | — |

## 4. Industry layer — blueprint pages 4–9

| Figure | Value | Period | Forecast yr | Body | Source |
|---|---|---|---|---|---|
| APSEZ share of all-India port cargo, FY26 | 27.1% | 2026-03 | — | Company (APSEZ) | APSEZ FY26 media release, 30 April 2026 |
| APSEZ share of all-India container volumes, FY26 | 45.5% | 2026-03 | — | Company (APSEZ) | APSEZ FY26 media release, 30 April 2026 |
| India container traffic growth outlook | 8.00 % CAGR | 2026-03 | 2030 | Industry estimate | Container traffic to grow 7-9% as major ports outpace, industry report 2026 |
| Largest Indian major ports by cargo, FY26 | 160.11 MMT | 2026-03 | — | Ministry of Ports, Shipping and Waterways / IBEF | IBEF, major ports FY26 performance |
| India major ports cargo traffic, FY26 | 915.17 MMT | 2026-03 | — | Ministry of Ports, Shipping and Waterways / IBEF | Major ports handle record 915 million tonnes cargo in FY26, IBEF news, 2026 |

**Never state a market size without its source and its forecast year.** A market-size number with no forecast year is unfalsifiable and will not survive being argued with.

## 5. Provenance — every figure in this pack

| Key | Value | Period | Age | Method | Source |
|---|---|---|---|---|---|
| `apsez_all_india_cargo_share_fy26` | 27.1% | 2026-03 | 129d | manual | APSEZ FY26 media release, 30 April 2026 |
| `apsez_container_share_fy26` | 45.5% | 2026-03 | 129d | manual | APSEZ FY26 media release, 30 April 2026 |
| `brent_crude` | US$83.3/bbl | 2026-08-06 | 1d | manual | Brent crude spot, 6 August 2026 |
| `cad_pct_gdp` | 0.6% | 2026-03 | 129d | manual | RBI, Developments in India's Balance of Payments, full year FY2025-26 |
| `gdp_emde_2026` | 3.9% | 2026 | -146d | manual | IMF WEO 2026-04 |
| `gdp_india_2026` | 6.5% | 2026 | -146d | manual | IMF WEO 2026-04 |
| `gdp_world_2026` | 3.1% | 2026 | -146d | manual | IMF WEO 2026-04 |
| `gdp_world_2027` | 3.2% | 2027 | -511d | manual | IMF WEO 2026-04 |
| `india_10y_gsec` | 6.8% | 2026-08-05 | 2d | manual | India 10-year G-sec benchmark yield, 5 August 2026, post RBI policy |
| `india_container_traffic_cagr` | 8.00 % CAGR | 2026-03 | 129d | manual | Container traffic to grow 7-9% as major ports outpace, industry report 2026 |
| `india_cpi` | 4.4% | 2026-06 | 38d | manual | MoSPI, CPI press release for June 2026, released 13 July 2026 |
| `india_gdp_fy_actual` | 7.4% | 2026-03 | 129d | manual | NSO First Advance Estimates, FY2025-26 |
| `india_iip` | 7.3% | 2026-06 | 38d | manual | MoSPI, Index of Industrial Production, June 2026 |
| `india_wpi` | 9.9% | 2026-06 | 38d | manual | Office of the Economic Adviser / PIB, WPI provisional estimates for June 2026 |
| `major_port_leaders_fy26` | 160.11 MMT | 2026-03 | 129d | manual | IBEF, major ports FY26 performance |
| `major_ports_cargo_fy26` | 915.17 MMT | 2026-03 | 129d | manual | Major ports handle record 915 million tonnes cargo in FY26, IBEF news, 2026 |
| `repo_rate` | 5.2% | 2026-08-05 | 2d | manual | RBI Monetary Policy Statement, August 2026 |
| `usdinr` | Rs 95.23 | 2026-08-06 | 1d | manual | USD/INR market close, 6 August 2026 |

## 6. NOT in this pack — go and get these

- **`bank_credit_growth`** — observation 23d old; limit 21d (class 'weekly' + 7d publication lag)
  - where: RBI Weekly Statistical Supplement, Table 5 'Scheduled Commercial Banks -- Business in India'. Take y-o-y % on 'Bank Credit'.
  - url: https://website.rbi.org.in/en/web/rbi/statistics
  - cite as: RBI Weekly Statistical Supplement, <DD Month Year>
- **`forex_reserves`** — observation 99d old; limit 21d (class 'weekly' + 7d publication lag)
  - where: RBI Weekly Statistical Supplement, Table 2 'Foreign Exchange Reserves'. Take the total, and note the week-ended date.
  - url: https://website.rbi.org.in/en/web/rbi/statistics
  - cite as: RBI Weekly Statistical Supplement, week ended <DD Month Year>

Never attempted this run (no manual entry supplied):

- `fiscal_deficit_pct_gdp` — Union fiscal deficit · https://www.indiabudget.gov.in/
- `india_cpi_core` — India core CPI inflation, y-o-y · https://www.mospi.gov.in/cpi
- `india_gdp_latest_q` — India real GDP growth, latest quarter · https://www.mospi.gov.in/data
- `india_gdp_per_capita` — India GDP per capita · https://www.mospi.gov.in/data
- `india_gva_fy_actual` — India real GVA growth, latest full FY · https://www.mospi.gov.in/data

