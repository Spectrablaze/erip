# Modeling strategy — Trent Ltd

*As of 2026-10-15 · sector `consumer` · schema v1.0*

## Modelability: GREEN — proceed once approved

- Validated archetype with store count, store additions, retail area and SPSF disclosed; LFL disclosed as a range
- Single reportable segment, so no segment split is being manufactured
- Primary method is computable by model.py; no analyst-manual method is required

## 1. What this business is

Trent earns revenue by selling own-label apparel, footwear, beauty and accessories through company-operated stores. Two formats carry almost all of it: Westside, a mid-premium fashion store of 20,000-30,000 sq ft (300 stores at FY26), and Zudio, a value-fashion store of 10,000-12,000 sq ft opened mainly in Tier II/III micro-markets (963 domestic stores plus 6 in the UAE). FY26 revenue from operations was INR 20,074 cr consolidated and INR 19,701 cr standalone, on 17.7 mn sq ft of retail area across 1,286 stores. Merchandise is almost all exclusive own brands, so revenue is store footprint times sales per sq ft rather than a wholesale or brand-licensing stream; the company reports a single business segment under Ind AS 108. Star food and grocery is run by Trent Hypermarket, a 50:50 JV with Tesco, and is equity-accounted, as are 20% stakes in Inditex's Zara and Massimo Dutti India businesses and a 50:50 sourcing JV with MAS; none of them is in consolidated revenue. Stores are leased, so rent sits below EBITDA as Ind AS 116 depreciation and interest, and lease payments of INR 797 cr in FY26 are a financing cash flow.

## 2. Segment decomposition and economic architecture

| Segment | % revenue | Archetype | Identity | Confidence |
|---|---:|---|---|---|
| Fashion and lifestyle (Westside, Zudio, Samoh, Burnt Toast) | 98.1 | Stores x Sales per Store | revenue = average store count x sales per store, decomposed into new-store contribution and same-store sales growth | Medium |

### Fashion and lifestyle (Westside, Zudio, Samoh, Burnt Toast)

**Revenue drivers** — opening_stores, store_adds, sales_per_store, sss_growth, maturity_curve

**Margin drivers** — segment_margin

**Capital drivers** — segment_capex_intensity

**Working-capital drivers** — segment_wc_days

**Evidence**

- "The capital employed for a new Zudio store is in the region of 3-4 Crores, including capex, deposits and inventory" — `annual_report/sections/12_management_discussion_analysis.md`, p. 117
- "Indian Accounting Standards 108 - Segment Information represents single reportable business segment" — `annual_report/pages/page_0230.md`, p. 230

> Trap for this archetype: Applying full-format sales to a store opened in month eleven. New stores ramp; a store-count model without a maturity assumption systematically overstates the first two forecast years. And SSS plus new stores is not additive with store-count growth — pick one decomposition and hold it.

## 3. Model architecture

- **Revenue model** — `consolidated_buildup`
- **Consolidation** — single consolidated revenue line; equity-accounted JVs and associates (Trent Hypermarket/Star, Inditex Trent Retail, Massimo Dutti India, Trent MAS Fashion) excluded from revenue and EBITDA and carried as non-operating assets in the equity bridge
- **Segment modelling** — One consolidated fashion build. Revenue = average retail area x sales per sq ft, with area rolled forward from opening area plus net store additions x average store size, and sales per sq ft grown at like-for-like plus a tier-mix drag as new area skews to lower-SPSF Tier II/III markets. Format revenue (Westside vs Zudio) is not disclosed, so formats are carried only in the store and area roll-forward, not as separate revenue lines. Store-count growth and like-for-like are not added together: one decomposition (area x SPSF) is held throughout.

**Required schedules**

- store and retail-area roll-forward by format (Westside, Zudio)
- capex per new store tied to the store additions modelled
- lease liability and right-of-use schedule (Ind AS 116); lease payments as a financing outflow
- Fashion and lifestyle (Westside, Zudio, Samoh, Burnt Toast): store roll-forward with the maturity ramp
- Fashion and lifestyle (Westside, Zudio, Samoh, Burnt Toast): capex per new store, tied to the store additions modelled
- Fashion and lifestyle (Westside, Zudio, Samoh, Burnt Toast): lease liability where stores are leased

**Execution against the existing pipeline**

- financial-model capability: `consolidated_growth_only`
- revenue build site: `assumptions_layer`
- consolidated growth is derived: `True`

Phase A: financial-model has one revenue row, prev(revenue)*(1+rev_growth). The segment driver maths runs in the assumptions layer via segment_build.py and lands as an auditable per-year consolidated revenue_growth path, with the full build preserved in segment_build.json and segment_build.md. financial-model refuses anything it cannot execute rather than flattening it.

## 4. Required drivers (the contract with financial-model-assumptions)

| Driver | Segment | Unit | Kind | Required |
|---|---|---|---|---|
| `opening_stores` | Fashion and lifestyle (Westside, Zudio, Samoh, Burnt Toast) | count | revenue | **yes** |
| `store_adds` | Fashion and lifestyle (Westside, Zudio, Samoh, Burnt Toast) | count p.a. | revenue | **yes** |
| `sales_per_store` | Fashion and lifestyle (Westside, Zudio, Samoh, Burnt Toast) | INR cr p.a. | revenue | **yes** |
| `sss_growth` | Fashion and lifestyle (Westside, Zudio, Samoh, Burnt Toast) | % | revenue | **yes** |
| `maturity_curve` | Fashion and lifestyle (Westside, Zudio, Samoh, Burnt Toast) | % | revenue | optional |
| `segment_margin` | Fashion and lifestyle (Westside, Zudio, Samoh, Burnt Toast) | % | common | **yes** |
| `segment_capex_intensity` | Fashion and lifestyle (Westside, Zudio, Samoh, Burnt Toast) | % of segment revenue | common | **yes** |
| `segment_wc_days` | Fashion and lifestyle (Westside, Zudio, Samoh, Burnt Toast) | days | common | **yes** |

`financial-model-assumptions` finds cited evidence and proposes values for each of these. A required driver with no entry is a check failure there, not a silent gap.

## 5. Valuation methodology

| Method | Applicability | Role | Who computes it |
|---|---|---|---|
| FCFF DCF | HIGH | **PRIMARY** | `model.py` |
| P/E | MEDIUM | **SECONDARY** | `peer-comps` |
| EV/EBITDA | MEDIUM | **CROSS_CHECK** | `peer-comps` |
| EV/Sales | ? | **LOW_RELIABILITY** | `peer-comps` |

**FCFF DCF — PRIMARY**

The operating cash flow is positive and rising (CFO INR 2,668 cr in FY26 against 1,661 cr in FY25) and its forecastable driver, store and area additions, is disclosed by format every quarter. The capital requirement is identifiable: management states INR 3-4 cr of capital employed per Zudio store, so capex and inventory scale with the store adds modelled. The value sits in a long runway of store openings, which only an explicit-period cash flow can express; a multiple applied to one year's earnings cannot. Leases must be treated consistently: EBITDA is post Ind AS 116, so lease liabilities are deducted as debt-like and the terminal value must fund store-level reinvestment.

Limitations: terminal value dominates when the horizon is short relative to the growth runway — report TV as % of EV; invalid where interest is revenue (lenders)

**P/E — SECONDARY**

Earnings are positive and the listed apparel-retail peers are all profitable, and P/E is how this sector is quoted. Comparability is weaker than usual: Trent's growth and ROCE sit well above V-Mart, V2 Retail, ABFRL and Shoppers Stop, so a peer median understates it and DMart is the only scale comparator.

Limitations: differences in leverage and in the effective tax rate reduce comparability directly; near-useless at a cyclical trough or peak, when earnings are the volatile term

**EV/EBITDA — CROSS_CHECK**

EBITDA is positive and every Indian peer reports after Ind AS 116, so the rent treatment is consistent across the set provided lease liabilities are included in EV for all of them. Lease intensity differs by format, which is why it is a cross-check rather than a primary lens.

Limitations: blind to depreciation, so it flatters capital-intensive businesses against asset-light ones; blind to differences in lease accounting

**EV/Sales — LOW_RELIABILITY**

Gross margin differs materially across the peers (own-label Trent near 44% against multi-brand and grocery peers), so revenue is not a common unit of value.

Limitations: ignores profitability entirely — only defensible when margins across the set are similar, or when the thesis is an explicit margin-recovery argument stated as such

## 6. Methods rejected as inappropriate

| Method | Why not |
|---|---|
| Sum of the parts | Ninety-eight per cent of revenue is one fashion business with a single reportable segment. The equity-accounted stakes (Star JV, Inditex associates, MAS JV) carry about INR 737 cr of non-current investments against a market value near INR 1.6 lakh cr; they are added as non-operating assets in the DCF bridge rather than justifying a sum of the parts. |
| P/B | Book value is not where a leased-store retailer's value sits; equity is a small fraction of the value created by store productivity. |
| NAV / asset-based | Stores are leased, not owned; the balance sheet does not carry the asset that generates the cash. |
| FCFE / equity DCF | Financial debt is a single INR 500 cr NCD due within a year, so FCFE adds nothing over FCFF once leases are treated as debt-like in both. |

## 7. Uncertainties

| Issue | Impact | How to resolve |
|---|---|---|
| Revenue by format (Westside vs Zudio) is not disclosed | The SPSF path is a blended fashion-portfolio figure; a faster Zudio mix shift lowers blended SPSF in a way the model cannot separate from like-for-like | Use the tier-level SPSF disclosure (15,318 / 13,390 / 12,504) and the area mix by format to set a mix drag explicitly, and state that format revenue is an estimate |
| Like-for-like growth is disclosed only qualitatively ('low single digits' for FY26) | The SSS driver rests on a range, not a number, at the point where growth has slowed from 39% to 17% | Carry LFL as a 2-4% band with the bear case at the bottom; flag it as a falsifier to watch in quarterly updates |
| No disclosed new-store maturity curve | Without a ramp the area-based build overstates revenue in the first one or two forecast years, the false positive the archetype warns about | Average area (opening plus half the additions) as a first-year ramp proxy, cross-checked against FY24-FY26 revenue per average sq ft |
| Store additions slowed sharply in FY27 to date (Zudio net +36 in H1 FY27 against 208 domestic in FY26) | The store-add path is the single largest value driver and current run-rate contradicts the 200-250 a year often cited | Set FY27 additions from the H1 run-rate plus disclosed H2 pipeline only; argue later years in Phase 3c with evidence |
| Value of the equity-accounted stakes, chiefly the Star JV | Carried at book they add little; a market value for Star could be several times book | Carry at book in the bridge by default and show a sensitivity; do not build a second DCF |

## 8. Checks

- none raised

## 9. Analyst decision

**Status: APPROVED**

The analyst must record one of `APPROVED`, `MODIFIED` or `REJECTED` in `strategy_decisions.json` and rebuild. Until then every downstream skill refuses to run.

- **APPROVE** — the decomposition, the drivers and the valuation methods stand.
- **MODIFY** — change `strategy_decisions.json` and rebuild; the original is kept under `recommended`.
- **REJECT / STOP** — the strategy is not defensible; the report does not proceed.
