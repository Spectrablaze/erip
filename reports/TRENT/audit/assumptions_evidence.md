# Assumption evidence - Trent Ltd

As of 2026-10-15. 
Knowledge base: `reports/TRENT/kb/annual_report`
Forecast horizon: 10.0 years  |  Sector: consumer

| Assumption | Value | Confidence | Set by | Key reason |
|---|---|---|---|---|
| forecast_years | 10 | Medium | analyst | Ten years to FY36. Area growth is still 25% in FY27; a five-year horizon would capitalise  |
| revenue_growth | 19.99, 15.97, 15.64, 14.53, 13.58, 12.32, 11.43, 10.26, 9.82, 9.51 | Medium | analyst | Derived from segment_build.json (approved area x sales-per-sq-ft architecture); replaced b |
| gross_margin | 43.0 | Medium | analyst | Purchases basis (1 - Raw Material Cost / Sales): FY26 42.7%, three-year average 42.0%. Use |
| ebitda_margin | 19.5, 19.8, 20.0, 20.0, 20.0, 20.0, 20.0, 20.0, 20.0, 20.0 | Medium | analyst | Post Ind AS 116 (rent on fixed leases is below EBITDA), the Screener basis. FY24 15.9%, FY |
| dep_pct_sales | 7.1, 7.1, 7.0, 6.9, 6.7, 6.5, 6.4, 6.3, 6.2, 6.0 | Medium | analyst | Includes right-of-use depreciation (909.59 cr of 1,361.19 cr in FY26). D&A/sales rose from |
| ebit_margin | 12.4, 12.7, 13.0, 13.1, 13.3, 13.5, 13.6, 13.7, 13.8, 14.0 | Medium | analyst | EBITDA margin less D&A % of sales. FY26 actual 11.9% (Screener basis, before other income) |
| capex_pct_sales | 11.8, 11.1, 10.4, 9.6, 8.9, 8.2, 7.7, 7.2, 6.8, 6.4 | Medium | analyst | Capex here includes new leases. EBITDA is after Ind AS 116, so the rent on every store ope |
| dso | 1.0 | High | analyst | Cash retail; receivables 51.14 cr = 0.9 days of FY26 sales. |
| dio | 71.0 | Medium | analyst | Days of purchases: 72.7 FY26, 73.6 FY25, 81.1 FY24 (falling every year as Zudio's faster-t |
| dpo | 38.0 | Medium | analyst | Days of purchases: 38.4 FY26, 33.4 FY25 (trade payables available for two years only). |
| effective_tax_rate | 24.0 | Medium | analyst | FY26 23.0%, three-year average 23.5%, statutory 25.17%. 24% allows for JV and associate pr |
| interest_rate | 8.5 | Low | analyst | Financial debt was a single 5.78% NCD, redeemed on 29 May 2026; the remaining debt-like it |
| terminal_growth | 6.0 | Medium | analyst | Below India's long-run nominal GDP growth (~10%) and above the 4.0-5.0% used for port conc |
| terminal_ronic | 20.0 | Medium | analyst | Return on new invested capital in perpetuity. model.py's roiic block puts Trent's ROIC at  |
| risk_free_rate | 7.35 | High | analyst | India 10-year G-sec 7.35% on 13 Oct 2026, the last close before the 14 Oct cover date (Tra |
| equity_risk_premium | 5.5 | Medium | analyst | House convention for Indian large caps; same as the APSEZ and JSWINFRA reports. |
| beta | 1.2 | Medium | analyst | Raw beta 1.2 (Blume-adjusted 1.13). Published betas: 1.28-1.30 (Moneycontrol) and 1.82 (Gu |
| target_debt_weight | 2.0 | Medium | analyst | No financial debt after the May 2026 NCD redemption; lease liabilities of 2,061 cr are ~1. |
| net_debt | -430.64 | High | analyst | Net CASH at 31 Mar 2026: NCD 499.89 less cash 281.36, other bank balances 1.64 and current |
| shares_out | 53.3232301 | High | analyst | 53,32,32,301 shares at 30 Sep 2026 after the 1:2 bonus (record date 4 June 2026); no emplo |
| current_price | 2971.0 | High | analyst | NSE close on the cover date, 14 October 2026, as carried in the Screener export. |
| exit_multiple | 25.0 | Low | analyst | Cross-check on the perpetuity terminal value only. Trent trades at ~40x trailing EV/EBITDA |
| lease_liabilities | 2061.36 | High | analyst | Ind AS 116 lease liabilities at 31 Mar 2026: non-current 1,206.80 + current 854.56. Rent o |
| minority_interest | 123.28 | High | analyst | Non-controlling interest at 31 Mar 2026, at book. NCI earned 1.68 cr in FY26, so a market- |

## Detail

### forecast_years

**Value:** 10 years

**Why**
- Ten years to FY36. Area growth is still 25% in FY27; a five-year horizon would capitalise FY31, a year still carrying 9% capex/sales and depreciation inflated by young stores. Ten years lets area growth fade to ~5% a year before the terminal.

**Confidence:** Medium

### revenue_growth

**Value:** 19.99, 15.97, 15.64, 14.53, 13.58, 12.32, 11.43, 10.26, 9.82, 9.51 %

**Why**
- Derived from segment_build.json (approved area x sales-per-sq-ft architecture); replaced by --segment-build at build time.
- Area: 17.7 mn sq ft at FY26 plus 3.45 mn FY27 (H1 FY27 net adds of 47 stores against 54 in H1 FY26, with the same back-ended H2 as FY26), ~3.5 mn a year FY28-FY30, fading to 2.2 mn by FY36. Closing area FY36 47.8 mn sq ft (if ~60% of new area is Zudio at ~12,000 sq ft, about 2,400-2,500 Zudio stores, against a long-run opportunity of ~5,000 cited by brokers, not by the company).
- Sales per sq ft: revenue per average sq ft fell ~14% in FY26 (area +36%, revenue +17%) because new area is in lower-SPSF Tier II/III markets and trades only ~30-35% of its first year (FY26 openings were back-ended: Zudio 109 of 198 net adds in Q4). Path -5% FY27, -2% FY28, flat FY29, then +1% rising to +4% as area growth slows and LFL of 2-4% shows through.
- Cross-check: FY27 +20.0% against Q1 FY27 +18% (consolidated) and H1 FY27 +21% (standalone).

**Evidence**
- "Retail Area (Million square feet) 5.3 / 7.0 / 9.4 / 13.5 / 17.7, FY22-FY26" (p. 118) - `kb/annual_report/images/charts/retail_area_margin_shrinkage_fy22_fy26.jpg`
- "Standalone revenue grew 23 per cent year-on-year in Q2 FY27 to 5,788 crore ... For the first half of FY27, growth stood at 21 per cent YoY to 11,454 crore" - `Business Standard, 6 Oct 2026 (Q2 FY27 business update)`
- "Revenue from operations Q1 FY27 5,755 (consolidated), growth over Q1FY26 18%" (p. 3) - `inputs/press_release_q1fy27.pdf`

**Confidence:** Medium

### gross_margin

**Value:** 43.0 %

**Why**
- Purchases basis (1 - Raw Material Cost / Sales): FY26 42.7%, three-year average 42.0%. Used only to convert DIO and DPO into NWC. The company's own fashion gross margin was 44.5% in FY26 and it states the gross margin profile of Westside and Zudio remains stable.

**Evidence**
- "Gross Margin 51.0 / 45.4 / 45.2 / 44.4 / 44.5 (FY22-FY26)" (p. 118) - `kb/annual_report/images/charts/retail_area_margin_shrinkage_fy22_fy26.jpg`
- "The gross margin profile of Westside and Zudio remains stable." (p. 2) - `inputs/press_release_q1fy27.pdf`

**Confidence:** Medium

### ebitda_margin

**Value:** 19.5, 19.8, 20.0, 20.0, 20.0, 20.0, 20.0, 20.0, 20.0, 20.0 %

**Why**
- Post Ind AS 116 (rent on fixed leases is below EBITDA), the Screener basis. FY24 15.9%, FY25 16.5%, FY26 18.7%; Q1 FY27 19.4% against 17.4% in Q1 FY26.
- 19.5% FY27 and 19.8% FY28 rising to 20.0%: operating leverage as area growth slows and the FY26 cohort matures, held back by the falling sales per sq ft. Variable rent of 1,563.94 cr (FY26) stays inside EBITDA.

**Evidence**
- "Q1 FY27 operating profit 1,119.16 on sales 5,754.71 (19.4%); Q1 FY26 847.86 on 4,883.48 (17.4%)" - `inputs/screener.xlsx, Quarters sheet`
- "In addition to fixed rent the Group has paid variable lease rentals ... amounting to 1,563.94 Crores ... which has not been considered in calculation right of use asset and lease liabilities" (p. 239) - `kb/annual_report/pages/page_0239.md`

**Confidence:** Medium

### dep_pct_sales

**Value:** 7.1, 7.1, 7.0, 6.9, 6.7, 6.5, 6.4, 6.3, 6.2, 6.0 % of sales

**Why**
- Includes right-of-use depreciation (909.59 cr of 1,361.19 cr in FY26). D&A/sales rose from 5.2% (FY25) to 6.8% (FY26) and 7.1% in Q1 FY27 because area grew faster than revenue. It fades to 6.0% by FY36 as area growth slows from 25% to ~5%.

**Evidence**
- "Newer stores carry higher depreciation relative to revenues, impacting EBITDA in early years. Profitability normalises as stores mature" (p. 125) - `kb/annual_report/pages/page_0125.md`
- "Right of Use Asset accumulated amortisation additions 909.59 (FY26), 597.99 (FY25)" (p. 223) - `kb/annual_report/pages/page_0223.md`

**Confidence:** Medium

### ebit_margin

**Value:** 12.4, 12.7, 13.0, 13.1, 13.3, 13.5, 13.6, 13.7, 13.8, 14.0 %

**Why**
- EBITDA margin less D&A % of sales. FY26 actual 11.9% (Screener basis, before other income); the company's operating EBIT margin was 11.9% (fashion) in FY26 and 12.9% in Q1 FY27.

**Evidence**
- "Operating EBIT margin for Q1 FY27 was 12.9% (11.5% for Q1FY26)." (p. 2) - `inputs/press_release_q1fy27.pdf`

**Confidence:** Medium

### capex_pct_sales

**Value:** 11.8, 11.1, 10.4, 9.6, 8.9, 8.2, 7.7, 7.2, 6.8, 6.4 % of sales

**Why**
- Capex here includes new leases. EBITDA is after Ind AS 116, so the rent on every store opened after the balance date would never be charged unless the right-of-use asset is treated as an investment when the lease is signed. Existing leases are handled by deducting lease_liabilities.
- FY26: PP&E 1,762.85 + right-of-use additions 1,241.87 = 3,004.72 cr (15.0% of sales). Split into sustaining capex at 4.0% of sales (lease renewals and refits; ROU depreciation alone was 4.5% of sales) and growth capex of INR 524 cr per mn sq ft added, escalating 4% a year. That reproduces FY26 exactly and gives 11.8% FY27 falling to 6.4% by FY36 as area additions slow.
- Cross-check: management puts capital employed for a new Zudio store at INR 3-4 cr including capex, deposits and inventory (about INR 2,900 per sq ft on 12,000 sq ft, before the lease).

**Evidence**
- "Purchase of Property, Plant and Equipments & Investment Property (1,762.85) FY26, (1,268.19) FY25" (p. 214) - `kb/annual_report/pages/page_0214.md (consolidated cash flow)`
- "Right of Use Asset additions 1,241.87 (FY26), 1,152.48 (FY25)" (p. 223) - `kb/annual_report/pages/page_0223.md`
- "The capital employed for a new Zudio store is in the region of ` 3-4 Crores, including capex, deposits and inventory" (p. 117) - `kb/annual_report/pages/page_0117.md`

**Confidence:** Medium

### dso

**Value:** 1.0 days

**Why**
- Cash retail; receivables 51.14 cr = 0.9 days of FY26 sales.

**Evidence**
- "Trade Receivables considered good - Unsecured 51.14 (FY26), 62.95 (FY25)" (p. 224) - `kb/annual_report/pages/page_0224.md`

**Confidence:** High

### dio

**Value:** 71.0 days

**Why**
- Days of purchases: 72.7 FY26, 73.6 FY25, 81.1 FY24 (falling every year as Zudio's faster-turning model grows). 71 days holds most of the gain without assuming it continues.

**Evidence**
- "Inventories 2,289.01 (FY26), 2,045.05 (FY25); purchases 11,496.89 / 10,143.39 (Screener)" (p. 212) - `kb/annual_report/pages/page_0212.md`

**Confidence:** Medium

### dpo

**Value:** 38.0 days

**Why**
- Days of purchases: 38.4 FY26, 33.4 FY25 (trade payables available for two years only).

**Evidence**
- "Trade payables: MSE 43.21 / others 1,167.45 (FY26); 31.25 / 896.94 (FY25)" (p. 212) - `kb/annual_report/pages/page_0212.md`

**Confidence:** Medium

### effective_tax_rate

**Value:** 24.0 %

**Why**
- FY26 23.0%, three-year average 23.5%, statutory 25.17%. 24% allows for JV and associate profits taxed at source rolling off.

**Evidence**
- "Profit before tax 2,236.48; Total tax expenses 515.15" (p. 212) - `kb/annual_report/pages/page_0212.md`

**Confidence:** Medium

### interest_rate

**Value:** 8.5 %

**Why**
- Financial debt was a single 5.78% NCD, redeemed on 29 May 2026; the remaining debt-like item is lease liabilities. 8.5% approximates the incremental borrowing rate on store leases.
- The annual report says leases are discounted at the incremental borrowing rate but does not disclose it, so 8.5% is an analyst estimate (about 115 bp over the 10-year G-sec). It only affects the 2% debt weight, so it barely moves WACC.

**Evidence**
- "These Debentures carry an interest @ 5.78% p.a and are redeemable on 29th May 2026." (p. 226) - `kb/annual_report/pages/page_0226.md`

**Confidence:** Low

### terminal_growth

**Value:** 6.0 %

**Why**
- Below India's long-run nominal GDP growth (~10%) and above the 4.0-5.0% used for port concessions, because a fashion retailer's addressable market is household consumption, which has no concession expiry. 6.0% is roughly 4% inflation plus 2% real growth in a mature store base; by FY36 area growth has already slowed to ~5%.

**Evidence**
- "india_gdp_latest_q 7.8% [MoSPI/NSO, Q1 2026-27, nominal GDP growth 10.3%]" - `reports/_knowledge/macro.json`
- "india_cpi 4.8% [MoSPI, CPI August 2026]" - `reports/_knowledge/macro.json`

**Confidence:** Medium

### terminal_ronic

**Value:** 20.0 %

**Why**
- Return on new invested capital in perpetuity. model.py's roiic block puts Trent's ROIC at 18.1% FY24, 19.8% FY25 and 19.8% FY26 (NOPAT 1,000 / 1,455 / 1,835 cr on invested capital 5,523 / 7,359 / 9,263 cr); FY26 incremental return 20.7%. 20% is at, not below, the company's own return: it assumes new stores keep earning what the portfolio earns today, even though sales per sq ft on new area is falling. The bear case is the place to test lower.

**Evidence**
- "ROIC = NOPAT / Invested Capital: 1,000/5,523 (FY24), 1,455/7,359 (FY25), 1,835/9,263 (FY26); ROIIC FY26 20.7%" - `data/model.json (roiic block)`

**Confidence:** Medium

### risk_free_rate

**Value:** 7.35 %

**Why**
- India 10-year G-sec 7.35% on 13 Oct 2026, the last close before the 14 Oct cover date (Trading Economics). Up from 7.20% on 1 Oct after the RBI raised the repo rate 25 bp to 5.50% on 7 Oct and moved to 'calibrated tightening'. Phase 4 re-checks it against CCIL.

**Evidence**
- "The yield on India 10Y Bond Yield eased to 7.35% on October 13, 2026" - `tradingeconomics.com/india/government-bond-yield`
- "India's central bank raised its benchmark repo rate by 25 basis points to 5.5% on Wednesday ... benchmark 10-year bond yield was slightly higher at 7.2269%" - `Reuters, 7 Oct 2026, https://www.reuters.com/world/india/india-raises-policy-rate-by-25-bps-first-hike-nearly-four-years-2026-10-07/`

**Confidence:** High

### equity_risk_premium

**Value:** 5.5 %

**Why**
- House convention for Indian large caps; same as the APSEZ and JSWINFRA reports.

**Evidence**
- "equity_risk_premium 5.5% (house convention)" - `reports/JSWINFRA/decisions.json`

**Confidence:** Medium

### beta

**Value:** 1.2 x

**Why**
- Raw beta 1.2 (Blume-adjusted 1.13). Published betas: 1.28-1.30 (Moneycontrol) and 1.82 (GuruFocus, Aug 2026). The stock's beta is inflated by a momentum run and a 39% drawdown from its 52-week high; a fashion retailer's earnings are more cyclical than staples but less than discretionary durables. Revisit with peer betas from peer-comps in Phase 3d.
- Peer check (same source, Moneycontrol, Oct 2026): Avenue Supermarts 0.48-0.52, V-Mart 0.94-0.95 (Yahoo 5y monthly 0.71), Trent itself 1.28-1.30. The peers argue for 0.9-1.0; Trent's own history argues for 1.3. 1.2 sits closer to the stock's own beta. Peer betas could not be regressed: the Screener exports carry no price history.

**Evidence**
- "Beta 1.30 / 1.28" - `moneycontrol.com/india/stockpricequote/retail/trent/T04`
- "Trent (NSE:TRENT) Beta is 1.8199 (Aug. 19, 2026)" - `gurufocus.com/term/beta/NSE:TRENT`
- "Avenue Supermarts Beta 0.52 / 0.48" - `moneycontrol.com/india/stockpricequote/retail/avenuesupermarts/AS19`
- "V-Mart Retail Beta 0.94 / 0.95" - `moneycontrol.com/india/stockpricequote/retail/v-martretail/VR03`

**Confidence:** Medium

### target_debt_weight

**Value:** 2.0 %

**Why**
- No financial debt after the May 2026 NCD redemption; lease liabilities of 2,061 cr are ~1.3% of market value. 2%.

**Evidence**
- "Lease Liabilities 1,206.80 (non-current), 854.56 (current); Borrowings 499.89 (current NCD, redeemed 29 May 2026)" (p. 212) - `kb/annual_report/pages/page_0212.md`
- "Market Capitalization 158518.82" - `inputs/screener.xlsx, Data Sheet META`

**Confidence:** Medium

### net_debt

**Value:** -430.64 cr

**Why**
- Net CASH at 31 Mar 2026: NCD 499.89 less cash 281.36, other bank balances 1.64 and current mutual-fund investments 647.53. Lease liabilities are excluded here and deducted separately.

**Evidence**
- "Borrowings (current) 499.89; Cash and Cash Equivalents 281.36; Bank Balances 1.64; Current Investments 647.53" (p. 212) - `kb/annual_report/pages/page_0212.md`

**Confidence:** High

### shares_out

**Value:** 53.3232301 cr shares

**Why**
- 53,32,32,301 shares at 30 Sep 2026 after the 1:2 bonus (record date 4 June 2026); no employee-trust (treasury) shares.

**Evidence**
- "Total (A+B+C2) 533232301" (p. 3) - `inputs/shareholding.pdf (BSE filing, quarter ended 30-09-2026)`
- "issue of bonus shares in the ratio of 1 (One) equity share ... for every 2 (Two) fully paid-up equity shares ... as on 4th June 2026" (p. 102) - `kb/annual_report/pages/page_0102.md`

**Confidence:** High

### current_price

**Value:** 2971.0 per share

**Why**
- NSE close on the cover date, 14 October 2026, as carried in the Screener export.

**Evidence**
- "Current Price 2971.0; Market Capitalization 158518.82" - `inputs/screener.xlsx, Data Sheet META`

**Confidence:** High

### exit_multiple

**Value:** 25.0 x EV/EBITDA

**Why**
- Cross-check on the perpetuity terminal value only. Trent trades at ~40x trailing EV/EBITDA (EV ~INR 1.59 lakh cr on TTM EBITDA 3,928 cr); a mature FY36 store network growing ~6% should trade well below that. Revisit against the peer set in Phase 3d.
- Peer check: Avenue Supermarts trades at 40.4x trailing EV/EBITDA, the apparel peers at 9.8-17.0x (median 14.0x). 25x for a mature FY36 Trent sits between the two.

**Evidence**
- "Market Cap 1,58,519 cr; TTM operating profit 3,928 cr" - `screener.in/company/TRENT/consolidated (14 Oct 2026)`
- "EV/EBITDA: Trent 40.8x, Avenue Supermarts 40.4x, peer median 14.0x (IQR 13.7-17.0x)" - `data/comps.md (peer-comps, priced 14 Oct 2026)`

**Confidence:** Low

### lease_liabilities

**Value:** 2061.36 cr

**Why**
- Ind AS 116 lease liabilities at 31 Mar 2026: non-current 1,206.80 + current 854.56. Rent on existing leases is outside EBITDA, so the liability is debt-like and comes off enterprise value. New leases are charged through capex (see capex_pct_sales).

**Evidence**
- "Lease Liabilities 1,206.80 (non-current), 854.56 (current)" (p. 212) - `kb/annual_report/pages/page_0212.md`

**Confidence:** High

### minority_interest

**Value:** 123.28 cr

**Why**
- Non-controlling interest at 31 Mar 2026, at book. NCI earned 1.68 cr in FY26, so a market-value basis would move the answer by well under INR 1 a share.

**Evidence**
- "Non-Controlling Interest 123.28 (FY26), 121.62 (FY25)" (p. 212) - `kb/annual_report/pages/page_0212.md`

**Confidence:** High

## Checks raised at build time

- nwc_pct_sales derived as 5.43% of sales - DSO 1d on sales; DIO 71d and DPO 38d on COGS rescaled at COGS/Sales = 0.57 (gross margin 43%)
- revenue_growth replaced by the segment build ([19.98, 15.97, 15.64, 14.53, 13.58, 12.32, 11.43, 10.27, 9.81, 9.51]) - decisions.json had [19.99, 15.97, 15.64, 14.53, 13.58, 12.32, 11.43, 10.26, 9.82, 9.51]. The derived path wins; change the segment drivers, not this value.

---

Every value above is a starting point, not a forecast. Change any of them in `decisions.json` and rebuild.