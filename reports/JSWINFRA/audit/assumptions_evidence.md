# Assumption evidence - JSW Infrastructure Ltd

As of 2026-10-04. 
Knowledge base: `reports/JSWINFRA/kb/annual_report`
Forecast horizon: 10.0 years  |  Sector: realestate

| Assumption | Value | Confidence | Set by | Key reason |
|---|---|---|---|---|
| forecast_years | 10 | Medium | analyst | Ten years to FY36. A five-year horizon ends in FY31, the year Phase I finishes ramping, so |
| revenue_growth | 19.0, 43.87, 22.32, 15.0, 8.22, 6.96, 6.65, 6.36, 6.03, 6.0 | Medium | analyst | Derived from segment_build.json (Phase I only, approved architecture). Replaced by --segme |
| ebitda_margin | 45.1, 49.7, 48.1, 47.6, 47.3, 47.3, 47.1, 47.0, 47.0, 46.9 | Medium | analyst | Weighted from segment margins. Ports 51.0% FY27 (Fujairah drag: Q1 port margin 49.8% vs 51 |
| ebit_margin | 33.8, 38.8, 37.4, 37.3, 37.3, 37.6, 37.7, 37.8, 38.0, 38.1 | Medium | analyst | EBITDA margin less D&A % sales. FY26 actual EBIT margin 37.1%; three-year average 38.7%. |
| capex_pct_sales | 125.4, 92.6, 31.2, 15.5, 13.0, 13.1, 13.4, 13.5, 13.7, 13.8 | High | analyst | Absolute path: INR 8,000 cr FY27 and 8,500 cr FY28 (= the guided INR 16,500 cr for FY27-FY |
| dep_pct_sales | 11.3, 10.9, 10.7, 10.3, 10.0, 9.7, 9.4, 9.2, 9.0, 8.9 | Medium | analyst | Built from a fixed-asset roll: opening net block plus CWIP of INR 13,715 cr, D&A of ~4.5%  |
| nwc_pct_sales | 15.0, 14.7, 14.4, 14.1, 13.8, 13.5, 13.5, 13.5, 13.5, 13.5 | Medium | analyst | Supplied as a series. FY26 NWC/sales 15.5% = (DSO 72.0 + DIO 10.0 - DPO 25.5)/365 on sales |
| effective_tax_rate | 22.0 | Medium | analyst | FY26 effective rate 17.4%, three-year average 17.9%. Held at 22% as a forecast average: ne |
| interest_rate | 7.0 | Medium | analyst | Implied rate on average debt 6.41% FY26, five-year average 8.29%. The Baa3 investment-grad |
| terminal_growth | 4.0 | Medium | analyst | Below India's long-run nominal GDP growth (~10%) and below the 5.0% used for APSEZ, for th |
| risk_free_rate | 7.2 | High | analyst | India 10-year G-sec 7.20% (6.94% GS 2036 at 7.2036%), CCIL, 1 October 2026 = the cover dat |
| equity_risk_premium | 5.5 | Medium | analyst | House convention for Indian large caps, mid of 5.0-6.0%; identical to the APSEZ report for |
| beta | 0.9 | Medium | analyst | Raw beta 0.9 (Blume-adjusted 0.93). Published market betas for JSWINFRA are 0.76 (1-year,  |
| target_debt_weight | 12.0 | Medium | analyst | Fitch's rating case (which includes Phase II) has debt/EBITDA rising from 2.3x FY27 to 3.5 |
| net_debt | -2769.0 | High | analyst | Net CASH of INR 2,769 cr at 30 June 2026 (gross debt 7,094, cash and bank 9,863) after the |
| shares_out | 232.35 | High | analyst | 2,330,001,567 shares outstanding at 30 June 2026 less 6,537,830 held by the employee welfa |
| current_price | 357.45 | High | analyst | NSE close on the cover date, 1 October 2026 (2 October a market holiday), as carried in th |
| exit_multiple | 14.0 | Low | analyst | Cross-check on the perpetuity terminal value only. JSWINFRA trades at ~30x trailing EV/EBI |
| capacity_addition | 9, 63, 30, 15, 0, 5, 5, 5, 5, 5 | Medium | analyst | Change in effective average capacity, FY27-FY36: Tuticorin bulk and Kolkata interim (+9),  |

## Detail

### forecast_years

**Value:** 10 years

**Why**
- Ten years to FY36. A five-year horizon ends in FY31, the year Phase I finishes ramping, so the terminal value would capitalise a year still carrying 13% capex/sales and a utilisation trough; ten years lets capex fade to a sustaining level before the terminal year. Proposed at the assumption gate.
- Second pass: with Phase I complete by FY30 and capex at sustaining levels from FY31, six steady-state years precede the FY36 terminal year; the terminal still assumes concession renewal, which the report states.

**Confidence:** Medium

### revenue_growth

**Value:** 19.0, 43.87, 22.32, 15.0, 8.22, 6.96, 6.65, 6.36, 6.03, 6.0 %

**Why**
- Derived from segment_build.json (Phase I only, approved architecture). Replaced by --segment-build at build time.

**Evidence**
- "Consolidated revenue is the sum of segment revenue ... reproduces FY26 within tolerance (Port Operation 4,646.91, Logistic Operation 714.53)" (p. 219) - `segment_build.md / kb/annual_report/pages/page_0219.md`

**Confidence:** Medium

### ebitda_margin

**Value:** 45.1, 49.7, 48.1, 47.6, 47.3, 47.3, 47.1, 47.0, 47.0, 46.9 %

**Why**
- Weighted from segment margins. Ports 51.0% FY27 (Fujairah drag: Q1 port margin 49.8% vs 51.8%), 52.5% FY28, 53.5% FY29, 54.0% from FY30, matching Fitch's rating case (52% FY26 to 54% FY29-FY30 as owned ports outgrow landlord-port terminals). Logistics 22% FY27 rising to 25%, against FY26 19.9%, Q1 FY27 30.6% (rake revenue booked net of haulage) and Fitch's 24% by FY30.
- Consolidated EBITDA INR 2877 cr FY27 (guidance 3,000) and 4199 cr FY28 (guidance ~5,000).
- Slurry pipeline uplift: the take-or-pay contract pays on contracted volume from 1 April 2027 and management put its EBITDA at INR 800 cr; the segment build earns only ~INR 435 cr on it in FY28 at blended realisation and port margin. The difference (INR 365 cr FY28, 130 cr FY30, 130 cr FY36) is added explicitly. Consolidated EBITDA FY28 becomes INR 4565 cr against guidance of ~5,000.

**Evidence**
- "Operational EBITDA for port segment stood at INR601 crores ... EBITDA margin was close to 49.8% vis-a-vis 51.8% a year ago. The dip ... mainly attributable to the lower contribution of volumes from Fujairah" (p. 5) - `kb/concall/pages/page_0004.md`
- "Ports FY26A revenue 4,647 / EBITDA 2,462; Logistics FY26A 715 / 142; FY27E 1,650 / 400; FY28E 2,800 / 700" (p. 14) - `kb/investor_presentation/images/charts/ports_targets_fy28.jpg, logistics_targets_fy28.jpg`
- "We forecast the EBITDA margin for the ports segment to improve to 54% in FY29-FY30, from 52% in FY26 ... For the logistics segment, we assume that the EBITDA margin would improve to 24% by FY30, from 20% in FY26" - `Fitch Ratings, 19 Aug 2026`
- "So slurry, you know that we have a take-or-pay contract, which can throw out INR800 crores if constructed on time. Jatadhar can give another INR300 crores to INR400 crores." - `Q3 FY26 earnings call transcript (Nagarajan J., CFO), January 2026`
- "Slurry pipeline has already got the take-or-pay agreement which will trigger from 1st of April '27." - `Q1 FY26 earnings call transcript (Lalit Singhvi), July 2025`

**Confidence:** Medium

### ebit_margin

**Value:** 33.8, 38.8, 37.4, 37.3, 37.3, 37.6, 37.7, 37.8, 38.0, 38.1 %

**Why**
- EBITDA margin less D&A % sales. FY26 actual EBIT margin 37.1%; three-year average 38.7%.

**Evidence**
- "Total operating profit 2,060.90 on revenue 5,361.44 (segment results before finance expense)" (p. 219) - `kb/annual_report/pages/page_0219.md`

**Confidence:** Medium

### capex_pct_sales

**Value:** 125.4, 92.6, 31.2, 15.5, 13.0, 13.1, 13.4, 13.5, 13.7, 13.8 % of sales

**Why**
- Absolute path: INR 8,000 cr FY27 and 8,500 cr FY28 (= the guided INR 16,500 cr for FY27-FY28, of which 13,000 ports and 3,500 logistics), 3,500 cr FY29 (Jatadhar tail and rakes), 2,000 cr FY30, then sustaining capex of 13-14% of sales.
- Phase II capex (Murbe, Oman, Keni) is excluded from the base case consistently with its capacity; it sits in the bull scenario. Terminal capex 13.8% of sales exceeds D&A of 10.0% to fund real volume growth of 1-2% a year.
- Absolute capex unchanged from the first pass (analyst-locked); only the % of sales moves because revenue was re-derived.

**Evidence**
- "For FY27 and FY28, company plans to invest approximately INR16,500 crores with a significant portion around INR13,000 crores allocated to the port segment and INR3,500 crores earmarked for logistics space." (p. 5) - `kb/concall/pages/page_0004.md`
- "the company has already committed further INR5,500 crores of capex by placing orders for machinery, long lead items and other civil work" (p. 6) - `kb/concall/pages/page_0005.md`

**Confidence:** High

### dep_pct_sales

**Value:** 11.3, 10.9, 10.7, 10.3, 10.0, 9.7, 9.4, 9.2, 9.0, 8.9 % of sales

**Why**
- Built from a fixed-asset roll: opening net block plus CWIP of INR 13,715 cr, D&A of ~4.5% of opening net fixed assets (concession amortisation over a ~21-year weighted remaining life). Absolute D&A INR 720 cr FY27 (Q1 run-rate 166 cr a quarter), 1,000 cr FY28 (Jatadhar, pipeline and Jaigarh/Dharamtar all commission by March 2027), 1,200 cr FY29 as the pipeline and Jaigarh/Dharamtar commission, 1,690 cr by FY36. FY26 actual 11.45% of sales.

**Evidence**
- "Consolidated depreciation was INR166 crores ... in the current quarter" (p. 5) - `kb/concall/pages/page_0004.md`
- "These assets are amortized based on the lower of their useful lives or concession period." (p. 184) - `kb/annual_report/pages/page_0184.md`

**Confidence:** Medium

### nwc_pct_sales

**Value:** 15.0, 14.7, 14.4, 14.1, 13.8, 13.5, 13.5, 13.5, 13.5, 13.5 % of sales

**Why**
- Supplied as a series. FY26 NWC/sales 15.5% = (DSO 72.0 + DIO 10.0 - DPO 25.5)/365 on sales; the company has no raw-material line so day counts are on sales (see wc_days_on_cogs). DSO eased toward ~63 days as logistics grows; DPO held. DPO rests on two years of history only (FY25-FY26, AR p.179).

**Evidence**
- "Trade payables: MSE 74.62 / others 299.87 (FY26); 42.59 / 306.77 (FY25)" (p. 179) - `kb/annual_report/pages/page_0179.md`

**Confidence:** Medium

### effective_tax_rate

**Value:** 22.0 %

**Why**
- FY26 effective rate 17.4%, three-year average 17.9%. Held at 22% as a forecast average: new port and logistics entities pay the 25.17% concessional rate while holiday-era profits roll off. Scalar because build_assumptions collapses a tax path to its final year.

**Evidence**
- "Profit before tax 1,872.84; Less: Tax expense 325.94 (17.4%)" (p. 219) - `kb/annual_report/pages/page_0219.md`

**Confidence:** Medium

### interest_rate

**Value:** 7.0 %

**Why**
- Implied rate on average debt 6.41% FY26, five-year average 8.29%. The Baa3 investment-grade upgrade supports pricing, but project debt for INR 16,500 cr of capex reprices the book upward: 7.0%.

**Evidence**
- "Moody's has assigned JSW Infrastructure an investment grade rating of Baa3 from Ba1 with a stable outlook" (p. 6) - `kb/concall/pages/page_0005.md`

**Confidence:** Medium

### terminal_growth

**Value:** 4.0 %

**Why**
- Below India's long-run nominal GDP growth (~10%) and below the 5.0% used for APSEZ, for three company-specific reasons: concessions are finite (capacity-weighted remaining life ~21 years, so a perpetuity assumes renewal); 82% of cargo is coal and iron ore with coal traffic expected flattish; and the anchor Dharamtar cargo agreement with JSW Steel runs only to June 2030.
- 4.0% is roughly WPI-type tariff indexation plus 0-1% real volume growth.
- Second pass: Fitch puts the capacity-weighted remaining concession life at 23 years (annual report: ~21) and notes the Goa terminal concession expires in 2029 with extension likely. Tariff growth of ~3-3.5% (Fitch: 3%) plus 0.5-1% real volume = 4.0%; unchanged.

**Evidence**
- "The operational facilities have a capacity-weighted average remaining concession period of around 21 years, with one of its largest, Jaigarh Port, holding a remaining concession period of 32 years." (p. 79) - `kb/annual_report/pages/page_0079.md`
- "providing cargo handling & allied services to JSL ... effective from 1st April, 2026 to 30th June, 2030 i.e., for the remaining term of the cargo handling agreements" (p. 226) - `kb/annual_report/pages/page_0226.md`
- "the average remaining life of its concessions, weighted by capacity, is 23 years. The concession for the JSWIL-operated terminal in Goa expires in 2029, but an extension is likely." - `Fitch Ratings, 19 Aug 2026`

**Confidence:** Medium

### risk_free_rate

**Value:** 7.2 %

**Why**
- India 10-year G-sec 7.20% (6.94% GS 2036 at 7.2036%), CCIL, 1 October 2026 = the cover date. Reconciled to macro_pack.md per Phase 4; replaces the provisional 6.8% from the August macro snapshot. Yields rose ~42 bp since August on a Brent spike to US$114-131/bbl and an expected repo hike on 7 October.

**Evidence**
- "2026-10-01, 9Y-10Y, 6.94% GS 2036, 7.2036" - `ccilindia.com tenor-wise indicative yields`

**Confidence:** High

### equity_risk_premium

**Value:** 5.5 %

**Why**
- House convention for Indian large caps, mid of 5.0-6.0%; identical to the APSEZ report for comparability.

**Evidence**
- "equity_risk_premium 5.5% (house convention)" - `reports/ADANIPORTS/decisions.json, 7 Aug 2026`

**Confidence:** Medium

### beta

**Value:** 0.9 x

**Why**
- Raw beta 0.9 (Blume-adjusted 0.93). Published market betas for JSWINFRA are 0.76 (1-year, Finbox) and 0.82 (TradingView), on under three years of history with a ~14% free float until June 2026, which biases an observed beta down. Peers: CONCOR ~0.9-1.0, APSEZ ~1.3 (house figure). Global port operators carry asset betas around 0.6-0.7, which relever to ~0.7 at a 12% debt weight. 0.9 sits between the stock's own beta and the peer median, and above the infrastructure asset beta because of the coal and single-customer concentration.

**Evidence**
- "JSW Infrastructure's beta (1 year) is 0.76" - `finbox.com/NSEI:JSWINFRA/explorer/beta_1y`
- "JSWINFRA stock ... has beta coefficient of 0.82" - `tradingview.com/symbols/NSE-JSWINFRA`

**Confidence:** Medium

### target_debt_weight

**Value:** 12.0 %

**Why**
- Fitch's rating case (which includes Phase II) has debt/EBITDA rising from 2.3x FY27 to 3.5x FY29. Excluding Phase II, base-case net debt peaks around INR 9,000-10,000 cr in FY28-FY29, ~11-12% of market capitalisation. 12%.

**Evidence**
- "we forecast JSWIL's total debt/EBITDA leverage to rise to 3.5x by FY29, from 2.3x in FY27" - `Fitch Ratings, 19 Aug 2026`

**Confidence:** Medium

### net_debt

**Value:** -2769.0 cr

**Why**
- Net CASH of INR 2,769 cr at 30 June 2026 (gross debt 7,094, cash and bank 9,863) after the INR 6,555 cr primary QIP. Negative = net cash added to EV. Bridged at June 2026 per analyst resolution 4.

**Evidence**
- "Given the QIP receipts of INR6,555 crores into the company, as of June '26, we have a net cash position of INR2,769 crores." (p. 6) - `kb/concall/pages/page_0005.md`

**Confidence:** High

### shares_out

**Value:** 232.35 cr shares

**Why**
- 2,330,001,567 shares outstanding at 30 June 2026 less 6,537,830 held by the employee welfare trust (treasury) = 232.35 cr, from the BSE shareholding pattern for the quarter ended 30-06-2026 (Table I). Supersedes the 231.52 cr derived earlier from FY26 equity capital plus QIP shares.

**Evidence**
- "Total 2330001567 ... (C2) Shares held by Employee Trusts 6537830" (p. 4) - `inputs/shareholding.pdf, Table I`

**Confidence:** High

### current_price

**Value:** 357.45 per share

**Why**
- NSE close on the cover date, 1 October 2026 (2 October a market holiday), as carried in the Screener export.

**Evidence**
- "Current Price 357.45; Market Capitalization 83285.91" - `inputs/screener.xlsx, Data Sheet META`

**Confidence:** High

### exit_multiple

**Value:** 14.0 x EV/EBITDA

**Why**
- Cross-check on the perpetuity terminal value only. JSWINFRA trades at ~30x trailing EV/EBITDA (EV ~INR 80,500 cr on TTM EBITDA INR 2,696 cr) and APSEZ at ~19x; a mature, ex-growth port network in FY36 should trade well below both. 14x matches the APSEZ report.

**Evidence**
- "Market Cap 83,286 cr; TTM operating profit 2,696 cr" - `screener.in/company/JSWINFRA/consolidated (1 Oct 2026 close)`

**Confidence:** Low

### capacity_addition

**Value:** 9, 63, 30, 15, 0, 5, 5, 5, 5, 5 MTPA (effective, in-year)

**Why**
- Change in effective average capacity, FY27-FY36: Tuticorin bulk and Kolkata interim (+9), slurry pipeline and Jaigarh/Dharamtar (+63), Jatadhar (+30), Phase I completion (+15), then ~5 MTPA a year of debottlenecking. Phase II excluded from base (analyst resolution 1).

**Evidence**
- "Phase I to 300 MTPA by FY28E ... Phase II to 400 MTPA by FY30E" (p. 8) - `kb/annual_report/images/charts/capacity_roadmap_400mtpa.jpg`
- "expanding our capacity from the current 186 million tonnes per annum to 300 million tonnes by FY28 and further to 400 million tonnes per annum by FY 2030 or earlier" (p. 3) - `kb/concall/pages/page_0002.md`

**Confidence:** Medium

## Checks raised at build time

- revenue_growth: 43.87 is outside the plausible band -20-40 - keep it only if the evidence is explicit
- capex_pct_sales: 125.4 is outside the plausible band 0-30 - keep it only if the evidence is explicit
- capex_pct_sales: 92.6 is outside the plausible band 0-30 - keep it only if the evidence is explicit
- capex_pct_sales: 31.2 is outside the plausible band 0-30 - keep it only if the evidence is explicit
- revenue_growth replaced by the segment build ([19.0, 43.87, 22.32, 15.0, 8.22, 6.96, 6.64, 6.36, 6.03, 6.0]) - decisions.json had [19.0, 43.87, 22.32, 15.0, 8.22, 6.96, 6.65, 6.36, 6.03, 6.0]. The derived path wins; change the segment drivers, not this value.

---

Every value above is a starting point, not a forecast. Change any of them in `decisions.json` and rebuild.