# Assumption evidence - Adani Ports and Special Economic Zone Ltd

As of 2026-08-07. 
Knowledge base: `reports/ADANIPORTS/kb/annual_report`
Forecast horizon: 5.0 years  |  Sector: realestate

| Assumption | Value | Confidence | Set by | Key reason |
|---|---|---|---|---|
| forecast_years | 5 | - | analyst |  |
| revenue_growth | 21.39, 13.02, 14.47, 14.81, 12.09 | Medium | analyst | Derived from the approved four-segment build in segment_build.json, not assumed directly.  |
| ebitda_margin | 58.5, 58.0, 57.5, 57.0, 56.5 | High | analyst | FY26 actual is 59.0% (derived EBITDA 22,868 cr on 38,736 cr; company-reported 22,851 cr, a |
| ebit_margin | 44.0, 43.5, 43.0, 42.5, 42.0 | High | analyst | EBITDA margin less depreciation and amortisation. FY26 actual EBIT margin is 44.8%, ten-ye |
| capex_pct_sales | 31.0, 30.0, 29.0, 28.0, 26.0 | High | analyst | Management's five-year plan is INR 84,000-92,000 cr over FY27-FY31: domestic ports 60,000- |
| dep_pct_sales | 14.5, 14.5, 14.8, 15.0, 15.2 | High | analyst | FY26 actual 14.24%, three-year average 14.39%, ten-year range 10.5% to 18.1%. |
| dso | 58 | Medium | analyst | FY26 actual 60.1 days, three-year average 54.5, five-year average 57.3, falling trend over |
| dio | 6.5 | High | analyst | FY26 actual 6.45 days, three-year average 6.23. Inventory is consumables and spares, not t |
| dpo | 26 | Medium | analyst | FY26 actual 25.78 days on a two-year history only (FY25 32.58). Held roughly at the FY26 l |
| effective_tax_rate | 18.5 | Medium | analyst | FY26 actual effective rate is 13.92% (tax 2,066.53 on PBT 14,848.56) against an Indian sta |
| interest_rate | 8.0 | High | analyst | Implied interest rate on average debt was 8.08% in FY26, up from a five-year average of 5. |
| terminal_growth | 5.0 | Medium | analyst | Below India's long-run nominal GDP growth of roughly 10-11%, deliberately. A port network  |
| risk_free_rate | 6.78 | High | analyst | India ten-year G-sec yield, 6.78%, following the RBI Monetary Policy Committee decision of |
| equity_risk_premium | 5.5 | Medium | analyst | Standard India mature-market ERP plus country premium. Held at 5.5%, the mid of the 5.0-6. |
| beta | 1.3 | Low | analyst | Peer-derived beta could not be computed. peer_beta.py regresses monthly returns and requir |
| target_debt_weight | 12.0 | Medium | analyst | At market values, net debt of INR 42,910 cr against equity of INR 3,89,376 cr gives D/(D+E |
| net_debt | 42910 | High | analyst | Gross borrowings of INR 55,103 cr (non-current 50,424.16 + current 4,678.81) less cash and |
| shares_out | 230.396 | High | analyst | 2,303,959,098 shares as at 30 June 2026, from the BSE shareholding pattern filing, and con |
| current_price | 1695.0 | High | analyst | Close as carried in the Screener export used for the subject company and all four peers, s |
| exit_multiple | 14.0 | Low | analyst | Cross-check on the perpetuity terminal value. APSEZ currently trades at roughly 18.9x EV/E |
| nwc_pct_sales | 11.1, 10.82, 10.55, 10.27, 10.0 | Medium | analyst | Supplied directly as a series rather than derived, for two reasons. First, derive_nwc in b |

## Detail

### forecast_years

**Value:** 5

**Confidence:** not stated

### revenue_growth

**Value:** 21.39, 13.02, 14.47, 14.81, 12.09 %

**Why**
- Derived from the approved four-segment build in segment_build.json, not assumed directly. Every segment ties out to its reported FY26 base.
- Implies FY26-FY31 revenue CAGR of 15.1% on the segment base, against management's Ambition 2031 guidance of 18.8% (INR 38,736 cr to INR 91,500 cr). The haircut is deliberate: management missed its own cargo volume guidance in three of the last four years (FY23 339 vs 350-360, FY25 450 vs 460-480, FY26 501 vs 505-515).
- FY27 at +21.4% is dominated by NQXT annualising, not underlying growth. It is consolidation: Q1 FY27 international volume was 22.8 MMT against 7.7 MMT, and annualising Q1 gives ~91 MMT against 49.8 MMT in FY26.
- The resulting FY27 consolidated revenue of ~INR 46.7k cr sits about 4% above the top of management's INR 43,000-45,000 cr guidance. That is consistent with the record: reported revenue beat the top of guidance in all four of FY23-FY26, by an average of 3.6%.

**Evidence**
- "APSEZ consolidated forecast: Revenue FY21 12,550, FY26 38,736, FY31F 91,500" (p. 22) - `inputs/ambition_2031.pdf deck page 22`
- "Comparison of guidance vs reported results FY23-26: Cargo MMT FY23 guidance 350-360 reported 339.2; FY25 guidance 460-480 reported 450; FY26 guidance 505-515 reported 501" (p. 33) - `inputs/ambition_2031.pdf deck page 33`
- "Revenue FY23 guidance 19,200-19,800 reported 20,852; FY24 24,000-25,000 reported 26,711; FY25 29,000-31,000 reported 31,079; FY26 38,000 reported 38,736" (p. 33) - `inputs/ambition_2031.pdf deck page 33`

**Confidence:** Medium

### ebitda_margin

**Value:** 58.5, 58.0, 57.5, 57.0, 56.5 %

**Why**
- FY26 actual is 59.0% (derived EBITDA 22,868 cr on 38,736 cr; company-reported 22,851 cr, a 0.07% difference). Ten-year range 50.1% to 69.2%, three-year average 59.3%.
- Faded 50 bps a year because mix moves against margin: Domestic Ports earns 73.2% EBITDA margin while International earns 28.6% and Logistics 19.3%, and both of the low-margin segments grow faster than Domestic in the build.
- Lands at 56.5% in FY31 against management's implied 56.8% (EBITDA 52,000 on revenue 91,500). The margin path is therefore close to management even though the revenue path is well below it.

**Evidence**
- "EBITDA INR 22,851 cr, +20% YoY, against revenue of INR 38,736 cr" - `FY26 media release`
- "Segment EBITDA margins FY26: Domestic Ports 73.2%, International Ports 28.6%, Logistics 19.3%, Marine 51.0%" - `FY26 media release segment table`
- "EBITDA FY21 8,063, FY26 22,851, FY31F 52,000" (p. 22) - `inputs/ambition_2031.pdf deck page 22`

**Confidence:** High

### ebit_margin

**Value:** 44.0, 43.5, 43.0, 42.5, 42.0 %

**Why**
- EBITDA margin less depreciation and amortisation. FY26 actual EBIT margin is 44.8%, ten-year range 35.9% to 52.7%.
- Falls slightly faster than EBITDA margin because depreciation rises as the FY27-FY31 capacity programme commissions.

**Evidence**
- "Depreciation INR 5,517.38 cr on revenue INR 38,735.77 cr in FY26, i.e. 14.24% of sales" - `data/financials.json, from screener.xlsx`

**Confidence:** High

### capex_pct_sales

**Value:** 31.0, 30.0, 29.0, 28.0, 26.0 % of sales

**Why**
- Management's five-year plan is INR 84,000-92,000 cr over FY27-FY31: domestic ports 60,000-63,000, international 6,000-7,000, logistics 7,000-9,000, marine 11,000-13,000. Applied to the revenue path this profile totals ~INR 87,000 cr, inside that range.
- FY26 actual capex was 39.5% of sales (15,320 cr). The path starts below that and declines as the capacity programme completes.
- Capex is the line where management's guidance is least reliable: it overshot in three of the last four years, by 65% in FY24 (7,416 against 4,000-4,500) and 33% in FY26 (15,320 against 11,000-12,000). The bear scenario flexes this rather than the top line.

**Evidence**
- "Business 5-year capex plan (FY27-FY31): Domestic ports INR 60,000-63,000 Cr, International ports INR 6,000-7,000 Cr, Logistics INR 7,000-9,000 Cr, Marine INR 11,000-13,000 Cr" (p. 22) - `inputs/ambition_2031.pdf deck page 22`
- "Capex FY23 guidance 8,600 reported 9,141; FY24 guidance 4,000-4,500 reported 7,416; FY25 guidance 10,500-11,500 reported 8,049; FY26 guidance 11,000-12,000 reported 15,320" (p. 33) - `inputs/ambition_2031.pdf deck page 33`
- "FY27 capex guidance INR 12,000-14,000 cr" - `FY26 media release`

**Confidence:** High

### dep_pct_sales

**Value:** 14.5, 14.5, 14.8, 15.0, 15.2 % of sales

**Why**
- FY26 actual 14.24%, three-year average 14.39%, ten-year range 10.5% to 18.1%.
- Rises through the forecast as INR 87,000 cr of new capacity commissions and begins depreciating, and as the NQXT and CWIT intangibles amortise over their concession lives.

**Evidence**
- "Depreciation FY26 INR 5,517.38 cr; FY25 INR 4,378.93 cr; FY24 INR 3,888.46 cr" - `data/financials.json, from screener.xlsx`

**Confidence:** High

### dso

**Value:** 58 days

**Why**
- FY26 actual 60.1 days, three-year average 54.5, five-year average 57.3, falling trend over ten years from a peak of 138.9.
- Eased one day a year toward the three-year average rather than held at the FY26 spot, which was inflated by the NQXT consolidation adding receivables at year end.

**Evidence**
- "Trade Receivables INR 6,382.54 cr at 31 March 2026 against INR 4,432.36 cr at 31 March 2025" (p. 659) - `kb/annual_report/tables/table_p0659_1.md`

**Confidence:** Medium

### dio

**Value:** 6.5 days

**Why**
- FY26 actual 6.45 days, three-year average 6.23. Inventory is consumables and spares, not tradable stock, so it is structurally negligible for a port operator and held flat.

**Evidence**
- "Inventories INR 685.00 cr at 31 March 2026 against INR 521.80 cr at 31 March 2025" (p. 659) - `kb/annual_report/tables/table_p0659_1.md`

**Confidence:** High

### dpo

**Value:** 26 days

**Why**
- FY26 actual 25.78 days on a two-year history only (FY25 32.58). Held roughly at the FY26 level.
- Low confidence on the history: Screener does not carry trade payables and only FY25 and FY26 are disclosed in the FY26 annual report, so there is no ten-year anchor. This is a stated limitation.

**Evidence**
- "Total outstanding dues of micro enterprises and small enterprises 242.31; other creditors 2,493.93; total 2,736.24 (FY25: 166.73 + 2,553.77 = 2,720.50)" (p. 725) - `kb/annual_report/tables/table_p0725_1.md, note 19`

**Confidence:** Medium

### effective_tax_rate

**Value:** 18.5 %

**Why**
- FY26 actual effective rate is 13.92% (tax 2,066.53 on PBT 14,848.56) against an Indian statutory rate of 25.17%. The ten-year range is 1.75% to 29.5%, five-year average 12.0%.
- The gap is SEZ and port-infrastructure tax relief: India provides a ten-year tax holiday for companies developing, maintaining and operating ports, and APSEZ operates a multi-product SEZ at Mundra.
- Faded toward statutory over the forecast for two reasons: new capacity is increasingly outside the original SEZ perimeter, and international profits (Australia, Sri Lanka, Israel, Tanzania) are taxed in their own jurisdictions at higher rates as they annualise. Holding 13.9% to perpetuity would assume the relief never expires, which the disclosure does not support.
- This is the single largest soft assumption in the model after terminal growth. The bear case runs it to statutory.

**Evidence**
- "It also provides a 10-year tax holiday for companies developing, maintaining and operating ports and inland waterways" (p. 404) - `kb/annual_report/sections/12_management_discussion_and_analysis.md`
- "Tax Expense 2,066.53 on Profit before tax 14,848.56" (p. 739) - `kb/annual_report/tables/table_p0739_1.md segment note`

**Confidence:** Medium

### interest_rate

**Value:** 8.0 %

**Why**
- Implied interest rate on average debt was 8.08% in FY26, up from a five-year average of 5.94% as the debt base repriced and NQXT debt consolidated.
- Held at 8.0%, roughly 122 bps over the 6.78% ten-year G-sec, which is a reasonable investment-grade corporate spread.

**Evidence**
- "Interest INR 4,653.98 cr in FY26 on borrowings of INR 63,565.52 cr (Screener basis, lease-inclusive)" - `data/financials.json, from screener.xlsx`
- "APSEZ completed bond buyback programmes of USD 386.03m in August 2025 and USD 199.57m in March 2026" - `FY26 media release`

**Confidence:** High

### terminal_growth

**Value:** 5.0 %

**Why**
- Below India's long-run nominal GDP growth of roughly 10-11%, deliberately. A port network cannot compound with nominal GDP forever once capacity is built out and the 1bn-tonne target is reached.
- The binding consideration is concession life, not growth. The Mundra concession runs 30 years from 17 February 2001 and therefore expires 16 February 2031, with the CT-1 and CT-3 sub-concessions co-terminus. Only the West Basin extension runs to 2040. Mundra is 274 MMT of 653 MMT of domestic capacity. A perpetuity assumes cash flows continue indefinitely, and the annual report contains no disclosure that renewal is secured.
- Management's behaviour implies it expects renewal: it plans INR 60,000-63,000 cr of largely Mundra-led domestic capex over FY27-FY31. But that is an inference, not a disclosure.
- 5.0% is used rather than something higher for that reason. The bear scenario takes it to 3.5%.

**Evidence**
- "The initial port infrastructure facilities at Mundra ... developed pursuant to the concession agreement with Government of Gujarat (GoG) and Gujarat Maritime Board (GMB) for 30 years period effective from February 17, 2001" (p. 665) - `kb/annual_report/pages/page_0665.md`
- "MICTL was given rights to handle container cargo at the CT 1 Terminal for a period that was co-terminus with the Concession Agreement of Mundra Port, i.e. till February 16, 2031" (p. 665) - `kb/annual_report/pages/page_0665.md`
- "At Mundra, the Company has expanded port infrastructure facilities at West Basin through GoG approval for which the concession period will be effective till the year 2040" (p. 665) - `kb/annual_report/pages/page_0665.md`

**Confidence:** Medium

### risk_free_rate

**Value:** 6.78 %

**Why**
- India ten-year G-sec yield, 6.78%, following the RBI Monetary Policy Committee decision of 5 August 2026 which held the repo rate at 5.25% for a fourth consecutive meeting.
- Must be reconciled against india_10y_gsec in the Phase 4 macro pack; if they diverge the macro page and the WACC would contradict each other.

**Evidence**
- "The 10-year G-Sec yield declined approximately 3 basis points to 6.78% post-announcement following the RBI's August 5 policy decision" - `Trading Economics / RBI policy, 5 August 2026`

**Confidence:** High

### equity_risk_premium

**Value:** 5.5 %

**Why**
- Standard India mature-market ERP plus country premium. Held at 5.5%, the mid of the 5.0-6.0% range typically used for Indian large caps.

**Evidence**
- "market convention" - `external`

**Confidence:** Medium

### beta

**Value:** 1.3 x

**Why**
- Peer-derived beta could not be computed. peer_beta.py regresses monthly returns and requires a price series; the Screener export carries only 10 annual price points (Mar-17 339.6 to Mar-26 1,312.6), and the script emits beta: null below its minimum observation count rather than a number nobody should use.
- Adopted as the median of four published estimates, which disperse widely: Alpha Spread 0.75, GuruFocus 1.2339 (as of 15 April 2026), TradingView 1.36, GuruFocus levered 1.44. Median 1.30.
- The dispersion is itself informative. Any five-year estimation window spans the January 2023 short-seller episode, in which the stock roughly halved. That was an idiosyncratic governance shock, not systematic risk, so long-window betas are inflated by it while short post-recovery windows understate the group risk the market still prices. 0.75 is not credible for a stock with that drawdown history.
- blume_adjust is true, so model.py applies 0.67 x 1.30 + 0.33 = 1.201 for the multi-year discount rate, which already reverts part of the way to the market.
- This remains the lowest-confidence input in the valuation and is carried into the tornado chart. At beta 1.00 the WACC falls roughly 100 bps and intrinsic value rises materially; at 1.44 it falls further.

**Evidence**
- "Adani Ports & Special Economic Zone's beta is 1.2339 as of April 15, 2026" - `GuruFocus, NSE:ADANIPORTS beta`
- "ADANIPORTS stock has a beta coefficient of 1.36" - `TradingView, NSE:ADANIPORTS`
- "levered beta of 1.44 with a cost of equity of 15.41%" - `GuruFocus, NSE:ADANIPORTS WACC`
- "beta of 0.75 with a risk-free rate of 6.3% and an equity risk premium of 4.12%" - `Alpha Spread, ADANIPORTS discount rate`

**Confidence:** Low

### target_debt_weight

**Value:** 12.0 %

**Why**
- At market values, net debt of INR 42,910 cr against equity of INR 3,89,376 cr gives D/(D+E) of 9.9%.
- Set slightly above spot at 12% because the FY27-FY31 capex programme of INR 84,000-92,000 cr will be part debt-funded, and management guides to a 2.2-2.5x net debt/EBITDA band against 1.9x today.

**Evidence**
- "Net Debt / EBITDA FY26 guidance 2.2x-2.5x, reported 1.9x" (p. 33) - `inputs/ambition_2031.pdf deck page 33`

**Confidence:** Medium

### net_debt

**Value:** 42910 cr

**Why**
- Gross borrowings of INR 55,103 cr (non-current 50,424.16 + current 4,678.81) less cash and equivalents of INR 12,193 cr (cash 5,161.55 + other bank balances 3,321.96 + bank deposits over twelve months 2,455.23 + current investments 1,254.65). Both figures tie exactly to the company's stated gross debt and cash.
- Excludes lease liabilities of INR 8,296.02 cr, per the analyst resolution recorded at the Phase 3b gate. Including them gives net debt of INR 51,206 cr and net debt/EBITDA of 2.24x against 1.88x. The report discloses both.

**Evidence**
- "Borrowings 50,424.16 non-current and 4,678.81 current; Cash and Cash Equivalents 5,161.55; Bank Balances other than Cash 3,321.96; Bank Deposits having maturity over twelve months 2,455.23; current Investments 1,254.65" (p. 659) - `kb/annual_report/tables/table_p0659_1.md`
- "Gross debt at INR 55,103 cr, cash balance at INR 12,193 cr, Net Debt/EBITDA 1.9x" - `FY26 media release`

**Confidence:** High

### shares_out

**Value:** 230.396 cr shares

**Why**
- 2,303,959,098 shares as at 30 June 2026, from the BSE shareholding pattern filing, and confirmed independently by equity share capital of INR 460.79 cr at INR 2 face value.
- Up from 2,160,138,945 in FY25. The 143,820,153 new shares were issued as consideration for NQXT and are held by Carmichael Rail And Port Singapore Holdings Pte. Ltd., 100% locked in.

**Evidence**
- "Promoter & Promoter Group 1,521,337,573 shares 66.03%; Public 782,621,525 33.97%; Total 2,303,959,098" (p. 3) - `inputs/shareholding.pdf, BSE filing for quarter ended 30-06-2026`
- "Equity Share Capital 460.79 (FY25: 432.03) at face value INR 2" (p. 659) - `kb/annual_report/tables/table_p0659_1.md`

**Confidence:** High

### current_price

**Value:** 1695.0 per share

**Why**
- Close as carried in the Screener export used for the subject company and all four peers, struck the same day. Cover date 7 August 2026.

**Evidence**
- "Current Price 1695.0" - `inputs/screener.xlsx, Data Sheet META block`

**Confidence:** High

### exit_multiple

**Value:** 14.0 x EV/EBITDA

**Why**
- Cross-check on the perpetuity terminal value. APSEZ currently trades at roughly 18.9x EV/EBITDA (EV of INR 4,32,286 cr on FY26 EBITDA of INR 22,851 cr).
- 14.0x assumes a fade from today's multiple as growth normalises, and is deliberately below the current trading multiple rather than at it. To be revisited against the peer median once Phase 3d computes it.

**Evidence**
- "to be reconciled against the peer median from build_comps.py" - `external`

**Confidence:** Low

### nwc_pct_sales

**Value:** 11.1, 10.82, 10.55, 10.27, 10.0 % of sales

**Why**
- Supplied directly as a series rather than derived, for two reasons. First, derive_nwc in build_assumptions.py accepts only scalar day counts and raises a TypeError on a per-year DSO path. Second, the derivation would apply the COGS-weighted formula unless wc_days_on_cogs is false, and APSEZ has effectively no COGS.
- Computed as (DSO + DIO - DPO)/365 with DSO easing 60 to 56 days, DIO 6.5 and DPO 26. FY27 11.10% falling to 10.00% by FY31.
- Reconciles to actual: FY26 NWC of (6,382.54 + 685.00 - 2,736.24) = 4,331.30 cr on revenue of 38,735.77 cr is 11.18%, against the same formula on FY26 day counts of 11.18%.

**Evidence**
- "Trade Receivables 6,382.54; Inventories 685.00; Trade Payables 2,736.24 at 31 March 2026" (p. 659) - `kb/annual_report/tables/table_p0659_1.md and note 19 table_p0725_1.md`

**Confidence:** Medium

## Checks raised at build time

- capex_pct_sales: 31.0 is outside the plausible band 0-30 - keep it only if the evidence is explicit

---

Every value above is a starting point, not a forecast. Change any of them in `decisions.json` and rebuild.