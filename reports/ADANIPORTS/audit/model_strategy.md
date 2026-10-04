# Modeling strategy — Adani Ports and Special Economic Zone Ltd

*As of 2026-08-07 · sector `realestate` · schema v1.0*

## Modelability: AMBER — proceed only on explicit analyst resolution

- The economic architecture is well evidenced: per-port installed capacity and throughput are disclosed individually, so utilisation is observable rather than assumed, and total domestic capacity of 653 MMT reconciles between the annual report (page 109) and the investor deck footprint map (page 4).
- AMBER rather than GREEN for two named reasons that require an analyst decision before assumptions are built: the four-segment architecture rests on unaudited management disclosure rather than the two-segment statutory note, and FY26 is a part-year base for International Ports because of the December 2025 NQXT consolidation.
- Neither item is a blocker. Both are resolved by an explicit analyst choice at this gate, recorded in analyst_decision.
- AMBER: Marine segment confidence is Low

## 1. What this business is

APSEZ earns revenue by handling third-party cargo across a concession-based network of 15 domestic ports and terminals with 653 MMT of installed capacity, plus four international assets (NQXT Australia, Colombo West, Haifa, Dar es Salaam). Revenue is a function of installed capacity, the utilisation achieved against it, and realisation per tonne, which varies by cargo type (container, bulk, liquid) and by contract structure. Two adjacent segments extend the same cargo flow inland and offshore: Logistics moves cargo by rail, trucking and warehousing across 95% of India's hinterland, and Marine provides towage, dredging and vessel services with 136 marine vessels. A land bank adjacent to the ports and the Mundra SEZ generates lease and development income. Interest income and customer security deposits appear in the accounts but are incidental to a port operator; this is not a lending business.

## 2. Segment decomposition and economic architecture

| Segment | % revenue | Archetype | Identity | Confidence |
|---|---:|---|---|---|
| Domestic Ports and SEZ | 66.5 | Capacity x Utilisation x Realisation | revenue = installed capacity x utilisation % x realisation per unit | High |
| International Ports | 11.7 | Capacity x Utilisation x Realisation | revenue = installed capacity x utilisation % x realisation per unit | Medium |
| Logistics | 11.6 | Volume x Price | revenue = volume x average price | Medium |
| Marine | 6.9 | Capacity x Utilisation x Realisation | revenue = installed capacity x utilisation % x realisation per unit | Low |

### Domestic Ports and SEZ

**Revenue drivers** — installed_capacity, capacity_addition, utilisation, realisation

**Margin drivers** — segment_margin

**Capital drivers** — segment_capex_intensity

**Working-capital drivers** — segment_wc_days

**Evidence**

- "Per-port installed capacity and throughput are disclosed individually for Mundra (274/192 MMT), Dahej (16/10.6 MMT), Karaikal (22/12.4 MMT) and others, so utilisation is observable rather than assumed" — `kb/annual_report/pages/page_0111.md through page_0120.md`, p. 111

> Trap for this archetype: Utilisation above 100% in the forecast, or capacity appearing in the revenue line the same year the capex is spent. Capacity commissions with a lag and ramps; a step change is almost always wrong. This archetype's whole value is that it puts a CEILING on the forecast — if the model can exceed capacity, the archetype is decorative.

### International Ports

**Revenue drivers** — installed_capacity, capacity_addition, utilisation, realisation

**Margin drivers** — segment_margin

**Capital drivers** — segment_capex_intensity

**Working-capital drivers** — segment_wc_days

**Evidence**

- "APSEZ completed the acquisition of 100% of NQXT Australia on 23 December 2025, so FY26 consolidates roughly one quarter of NQXT and FY26 is not a clean full-year base for this segment" — `adaniports.com media release, NQXT completion`

> Trap for this archetype: Utilisation above 100% in the forecast, or capacity appearing in the revenue line the same year the capex is spent. Capacity commissions with a lag and ramps; a step change is almost always wrong. This archetype's whole value is that it puts a CEILING on the forecast — if the model can exceed capacity, the archetype is decorative.

### Logistics

**Revenue drivers** — volume, price, mix_effect

**Margin drivers** — segment_margin

**Capital drivers** — segment_capex_intensity

**Working-capital drivers** — segment_wc_days

**Evidence**

- "Rail, trucking, warehousing and agri-silo activity priced per unit moved or stored rather than against a fixed installed capacity ceiling, which is why volume x price fits better than capacity x utilisation here" — `kb/investor_presentation/pages/page_0005.md`, p. 5

> Trap for this archetype: Claimed for any company that sells a physical thing. It is only right when volume is DISCLOSED. Deriving volume as revenue/price when price was itself derived as revenue/volume is circular and produces a bridge that always ties and never informs.

### Marine

**Revenue drivers** — installed_capacity, capacity_addition, utilisation, realisation

**Margin drivers** — segment_margin

**Capital drivers** — segment_capex_intensity

**Working-capital drivers** — segment_wc_days

**Evidence**

- "At 6.9% of revenue Marine sits below the 10% materiality threshold, but it grew 134% in FY26 at a 51% EBITDA margin. Folding it into the consolidated build would bury the fastest-growing and second-highest-margin line in the group, so it is modelled separately with explicitly lower confidence." — `FY26 media release segment table`

> Trap for this archetype: Utilisation above 100% in the forecast, or capacity appearing in the revenue line the same year the capex is spent. Capacity commissions with a lag and ramps; a step change is almost always wrong. This archetype's whole value is that it puts a CEILING on the forecast — if the model can exceed capacity, the archetype is decorative.

## 3. Model architecture

- **Revenue model** — `segment_buildup`
- **Consolidation** — sum of segment revenue less inter-segment eliminations; segment EBITDA margins weighted to a consolidated margin; unallocated corporate income and cost as a separate line; finance expense, interest income and exceptional items below the segment result, per the statutory segment note on annual report page 739
- **Segment modelling** — Four management-defined segments modelled separately and summed to a derived consolidated growth path via segment_build.py. Domestic Ports, International Ports and Marine run on capacity x utilisation x realisation; Logistics runs on volume x price. Inter-segment eliminations (roughly 3.3% of gross segment revenue in FY26) and unallocated corporate costs are held outside the segment build and carried as separate lines.

**Required schedules**

- concession_and_intangible_amortisation
- lease_liability_schedule
- Domestic Ports and SEZ: capacity roll-forward with commissioning lag
- Domestic Ports and SEZ: capex tied to the capacity additions being modelled
- International Ports: capacity roll-forward with commissioning lag
- International Ports: capex tied to the capacity additions being modelled
- Logistics: volume-price-mix bridge on revenue growth
- Marine: capacity roll-forward with commissioning lag
- Marine: capex tied to the capacity additions being modelled

**Execution against the existing pipeline**

- financial-model capability: `consolidated_growth_only`
- revenue build site: `assumptions_layer`
- consolidated growth is derived: `True`

Phase A: financial-model has one revenue row, prev(revenue)*(1+rev_growth). The segment driver maths runs in the assumptions layer via segment_build.py and lands as an auditable per-year consolidated revenue_growth path, with the full build preserved in segment_build.json and segment_build.md. financial-model refuses anything it cannot execute rather than flattening it.

## 4. Required drivers (the contract with financial-model-assumptions)

| Driver | Segment | Unit | Kind | Required |
|---|---|---|---|---|
| `installed_capacity` | Domestic Ports and SEZ | physical units p.a. | revenue | **yes** |
| `capacity_addition` | Domestic Ports and SEZ | physical units p.a. | revenue | **yes** |
| `utilisation` | Domestic Ports and SEZ | % | revenue | **yes** |
| `realisation` | Domestic Ports and SEZ | INR per unit | revenue | **yes** |
| `segment_margin` | Domestic Ports and SEZ | % | common | **yes** |
| `segment_capex_intensity` | Domestic Ports and SEZ | % of segment revenue | common | **yes** |
| `segment_wc_days` | Domestic Ports and SEZ | days | common | **yes** |
| `installed_capacity` | International Ports | physical units p.a. | revenue | **yes** |
| `capacity_addition` | International Ports | physical units p.a. | revenue | **yes** |
| `utilisation` | International Ports | % | revenue | **yes** |
| `realisation` | International Ports | INR per unit | revenue | **yes** |
| `segment_margin` | International Ports | % | common | **yes** |
| `segment_capex_intensity` | International Ports | % of segment revenue | common | **yes** |
| `segment_wc_days` | International Ports | days | common | **yes** |
| `volume` | Logistics | units | revenue | **yes** |
| `price` | Logistics | INR per unit | revenue | **yes** |
| `mix_effect` | Logistics | % of revenue growth | revenue | optional |
| `segment_margin` | Logistics | % | common | **yes** |
| `segment_capex_intensity` | Logistics | % of segment revenue | common | **yes** |
| `segment_wc_days` | Logistics | days | common | **yes** |
| `installed_capacity` | Marine | physical units p.a. | revenue | **yes** |
| `capacity_addition` | Marine | physical units p.a. | revenue | **yes** |
| `utilisation` | Marine | % | revenue | **yes** |
| `realisation` | Marine | INR per unit | revenue | **yes** |
| `segment_margin` | Marine | % | common | **yes** |
| `segment_capex_intensity` | Marine | % of segment revenue | common | **yes** |
| `segment_wc_days` | Marine | days | common | **yes** |

`financial-model-assumptions` finds cited evidence and proposes values for each of these. A required driver with no entry is a check failure there, not a silent gap.

## 5. Valuation methodology

| Method | Applicability | Role | Who computes it |
|---|---|---|---|
| FCFF DCF | HIGH | **PRIMARY** | `model.py` |
| EV/EBITDA | HIGH | **CROSS_CHECK** | `peer-comps` |
| Sum of the parts | MEDIUM | **SECONDARY** | `analyst_manual` |
| P/E | MEDIUM | **SECONDARY** | `peer-comps` |
| P/B | LOW | **SECONDARY** | `peer-comps` |

**FCFF DCF — PRIMARY**

Operating cash flow is large, positive and stable (CFO INR 20,356 cr in FY26, positive in all ten disclosed years), and the capital requirement is explicitly guided (FY27 capex INR 12,000-14,000 cr). Concession-based port assets have long, identifiable economic lives and contracted-to-quasi-contracted cargo flows, which is precisely the case an FCFF DCF is built for. Capital structure is actively managed and changed materially with the NQXT share issue, so FCFF is preferred to FCFE.

Limitations: terminal value dominates when the horizon is short relative to the growth runway — report TV as % of EV; invalid where interest is revenue (lenders)

**EV/EBITDA — CROSS_CHECK**

EBITDA is large and positive (INR 22,851 cr FY26) and the peer set contains four listed comparables of broadly similar capital intensity. This is the multiple the sector actually trades on, and it is the right cross-check on the DCF's terminal value.

Limitations: blind to depreciation, so it flatters capital-intensive businesses against asset-light ones; blind to differences in lease accounting

**Sum of the parts — SECONDARY**

The four segments have very different economics — EBITDA margins of 73.2%, 28.6%, 19.3% and 51.0% and RoCE of 23%, 8%, 10% and 13% — which is the classic argument for a sum-of-the-parts. It is deliberately NOT the primary lens because the segments are vertically integrated around the same cargo flows rather than separable businesses: Logistics and Marine exist substantially to feed and service the ports, and neither has standalone value independent of the port network. Used as a secondary cross-check on whether the consolidated DCF is mispricing the low-RoCE international book.

Limitations: the aggregate is only as good as the weakest part's valuation; double-counts central costs unless they are explicitly allocated or valued as a separate negative

**Must be completed by hand — this pipeline cannot compute it:**

- Value Domestic Ports and SEZ on segment EBITDA at a domestic port multiple
- Value International Ports on invested capital or a ramp-adjusted forward EBITDA, not trailing, given NQXT part-year consolidation
- Value Logistics against CONCOR's trading multiple
- Value Marine on segment EBITDA at a marine-services multiple
- Deduct net debt of INR 42,910 cr and add non-operating assets

**P/E — SECONDARY**

Earnings are positive and growing, but two things degrade comparability: the FY26 effective tax rate is 13.9% against a 25.17% statutory rate (SEZ and international structuring), so reported EPS is not a clean earnings stream; and peer leverage differs sharply, with GMR Airports reporting FY26 PAT of only INR 175 cr which makes its P/E meaningless. Reported alongside, not led with.

Limitations: differences in leverage and in the effective tax rate reduce comparability directly; near-useless at a cyclical trough or peak, when earnings are the volatile term

**P/B — SECONDARY**

Book value is distorted by INR 9,735.82 cr of goodwill and a 37% one-year balance sheet expansion from the NQXT consolidation. Reported for completeness because the peer set computes it, but it carries little signal here.

Limitations: meaningless where value sits in intangibles the balance sheet does not carry; distorted by historical-cost land and by revaluation reserves

## 6. Methods rejected as inappropriate

| Method | Why not |
|---|---|
| EV/Sales | Segment EBITDA margins span 19.3% to 73.2%. A single sales multiple applied across that dispersion implies a margin structure the company does not have, and would mis-value any change in segment mix — which is exactly what is happening as International and Logistics grow faster than Domestic Ports. |
| NAV / asset-based | Concession and port assets are carried at depreciated historical cost, not at fair value, and the value of the business is in the cash flow the concessions generate rather than in the recoverable value of the assets. NAV is the right lens for a property developer holding saleable land, not for an operating transport utility. The land bank is real but is a minority of value. |
| FFO / AFFO multiple or yield | APSEZ is not a REIT or an InvIT and does not distribute on an FFO basis. The metric has no constituency here. |
| FCFE / equity DCF | Leverage is actively managed and moved materially during FY26 (NQXT share issuance, bond buybacks of USD 386m in August 2025 and USD 200m in March 2026). FCFE would embed a financing path that is a management choice rather than an economic property of the assets. |

## 7. Uncertainties

| Issue | Impact | How to resolve |
|---|---|---|
| The four-segment split used for the architecture is management-defined and comes from the investor deck. The audited statutory segment note (annual report page 739) discloses only two reportable segments: 'Port and SEZ activities' (INR 33,461.68 cr external sales) and 'Others' (INR 5,274.09 cr). | Segment revenue and EBITDA for the four-way split are unaudited. Segment capital employed is disclosed only as a RoCE percentage, not as an absolute, so segment-level capex and invested capital must be inferred rather than read. | Analyst to accept the management segmentation as the modelling basis, on the condition that the report states plainly that the four-segment figures are management-defined and unaudited, and reconciles them to the two-segment statutory note. |
| NQXT Australia was consolidated only from 23 December 2025, so FY26 International Ports contains roughly one quarter of NQXT rather than a full year. Q1 FY27 international volumes were 22.8 MMT against 7.7 MMT in Q1 FY26. | FY26 is not a clean base year for the International segment. A driver series anchored on reported FY26 will show an artificial FY27 jump that is consolidation, not growth, and segment_build.py must reproduce the reported base year within 1%. | Analyst to decide whether the International base year is (a) reported FY26 as-is, with the FY27 step-up explained as consolidation, or (b) a pro-forma full-year FY26. Recommendation: use reported FY26 as the base so the build ties to the audited accounts, and decompose the FY27 increase explicitly into consolidation effect versus underlying ramp. |
| FY26 effective tax rate is 13.9% (tax INR 2,066.53 cr on PBT INR 14,848.56 cr) against a 25.17% statutory rate. | The DCF tax rate assumption swings valuation materially. Holding 13.9% to perpetuity assumes SEZ and international tax benefits never expire. | Establish the source and expiry of the SEZ benefit from the tax note, and fade the effective rate toward statutory over the forecast. To be resolved in Phase 3c with evidence. |
| Trade payables are disclosed for FY25 and FY26 only (annual report note 19). Screener does not carry the line and earlier years are not in this report. | Payable days have a two-point history, so the working-capital assumption cannot be anchored on a ten-year average. | Accept a two-year anchor and state the limitation on the working-capital page, or pull the line from FY22-FY24 annual reports. |
| Lease liabilities total INR 8,296.02 cr (non-current 7,786.56 + current 509.46) and are excluded from the company's stated net debt of INR 42,910 cr. | Net debt / EBITDA is 1.88x excluding leases and roughly 2.24x including them. The choice changes the leverage narrative and the equity bridge in the DCF. | Analyst to choose a convention. Recommendation: bridge at reported net debt for comparability with management and peers, and disclose the lease-inclusive figure alongside. |

## 8. Checks

- `WARN` **fake_granularity** — Marine: 6.9% of revenue carries its own driver architecture. Below the 10.0% floor this is granularity the disclosure probably does not support — consider folding it into the consolidated build.

## 9. Analyst decision

**Status: APPROVED**

The analyst must record one of `APPROVED`, `MODIFIED` or `REJECTED` in `strategy_decisions.json` and rebuild. Until then every downstream skill refuses to run.

- **APPROVE** — the decomposition, the drivers and the valuation methods stand.
- **MODIFY** — change `strategy_decisions.json` and rebuild; the original is kept under `recommended`.
- **REJECT / STOP** — the strategy is not defensible; the report does not proceed.
