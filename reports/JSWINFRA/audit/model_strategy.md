# Modeling strategy — JSW Infrastructure Ltd

*As of 2026-10-04 · sector `realestate` · schema v1.0*

## Modelability: GREEN — proceed once approved

- The architecture is well evidenced: capacity, utilisation and volume are disclosed annually from FY21, the capacity bridge is itemised by project and year, and the two segments are audited (note 41).
- AMBER rather than GREEN because two decisions belong to the analyst before assumptions are built: whether uncommitted Phase II capacity enters the base case, and how related-party cargo is priced as captive capacity grows.
- Neither blocks the report; both are resolved at this gate.

## 1. What this business is

JSW Infrastructure earns revenue by handling cargo across 13 port concessions on India's west and east coasts with 183 MTPA of installed capacity at FY26 (186 MTPA at Q1 FY27), plus a 465,000 m3 liquid storage terminal and two O&M contracts at Fujairah, UAE. Port revenue is a function of installed capacity, the utilisation achieved against it (62.3% in FY26) and realisation per tonne (about INR 381 on 122 MT in FY26). The cargo base is concentrated twice over: 52% of FY26 volume came from JSW Group related parties, partly under take-or-pay contracts, and 82% of volume was coking coal, iron ore and thermal coal. A logistics segment built on the Navkar Corp acquisition and a rail rakes fleet moves cargo inland and is priced per unit moved rather than against a capacity ceiling. Interest income on surplus treasury is incidental; this is not a lending business.

## 2. Segment decomposition and economic architecture

| Segment | % revenue | Archetype | Identity | Confidence |
|---|---:|---|---|---|
| Port Operation | 86.7 | Capacity x Utilisation x Realisation | revenue = installed capacity x utilisation % x realisation per unit | High |
| Logistic Operation | 13.3 | Volume x Price | revenue = volume x average price | Medium |

### Port Operation

**Revenue drivers** — installed_capacity, capacity_addition, utilisation, realisation

**Margin drivers** — segment_margin

**Capital drivers** — segment_capex_intensity

**Working-capital drivers** — segment_wc_days

**Evidence**

- "In FY2025-26, Cargo handled from related parties was 52% as compared 51% in FY 2024-25 ... a portion of the business from related parties is secured under arm's-length Take-or-Pay arrangements" — `kb/annual_report/pages/page_0035.md`, p. 35
- "82% of total volume of cargo handled by the company comprises coking coal, iron ore and thermal coal" — `kb/annual_report/pages/page_0035.md`, p. 35

> Trap for this archetype: Utilisation above 100% in the forecast, or capacity appearing in the revenue line the same year the capex is spent. Capacity commissions with a lag and ramps; a step change is almost always wrong. This archetype's whole value is that it puts a CEILING on the forecast — if the model can exceed capacity, the archetype is decorative.

### Logistic Operation

**Revenue drivers** — volume, price, mix_effect

**Margin drivers** — segment_margin

**Capital drivers** — segment_capex_intensity

**Working-capital drivers** — segment_wc_days

**Evidence**

- "Logistic operation segment result INR 82.55 cr on segment assets INR 3,455.04 cr (FY25: 8.33 on 1,890.76)" — `kb/annual_report/pages/page_0219.md`, p. 219

> Trap for this archetype: Claimed for any company that sells a physical thing. It is only right when volume is DISCLOSED. Deriving volume as revenue/price when price was itself derived as revenue/volume is circular and produces a bridge that always ties and never informs.

## 3. Model architecture

- **Revenue model** — `segment_buildup`
- **Consolidation** — sum of segment revenue (no inter-segment eliminations disclosed in FY26 note 41); segment EBITDA margins weighted to a consolidated margin; interest income, finance expense and exceptional items below the segment result, per note 41 (KB page 219)
- **Segment modelling** — Two audited segments modelled separately and summed to a derived consolidated growth path via segment_build.py. Port Operation runs on capacity x utilisation x realisation, with capacity stepped by named project and commissioning year; Logistic Operation runs on volume x price. Base case carries Phase I capacity only (to ~300 MTPA by FY28E); Phase II (Murbe, Oman, Keni, potential projects) is a bull-scenario input, not base case, because none of it has reached construction.

**Required schedules**

- concession_and_intangible_amortisation
- lease_liability_schedule
- project_capex_schedule
- Port Operation: capacity roll-forward with commissioning lag
- Port Operation: capex tied to the capacity additions being modelled
- Logistic Operation: volume-price-mix bridge on revenue growth

**Execution against the existing pipeline**

- financial-model capability: `consolidated_growth_only`
- revenue build site: `assumptions_layer`
- consolidated growth is derived: `True`

Phase A: financial-model has one revenue row, prev(revenue)*(1+rev_growth). The segment driver maths runs in the assumptions layer via segment_build.py and lands as an auditable per-year consolidated revenue_growth path, with the full build preserved in segment_build.json and segment_build.md. financial-model refuses anything it cannot execute rather than flattening it.

## 4. Required drivers (the contract with financial-model-assumptions)

| Driver | Segment | Unit | Kind | Required |
|---|---|---|---|---|
| `installed_capacity` | Port Operation | physical units p.a. | revenue | **yes** |
| `capacity_addition` | Port Operation | physical units p.a. | revenue | **yes** |
| `utilisation` | Port Operation | % | revenue | **yes** |
| `realisation` | Port Operation | INR per unit | revenue | **yes** |
| `segment_margin` | Port Operation | % | common | **yes** |
| `segment_capex_intensity` | Port Operation | % of segment revenue | common | **yes** |
| `segment_wc_days` | Port Operation | days | common | **yes** |
| `volume` | Logistic Operation | units | revenue | **yes** |
| `price` | Logistic Operation | INR per unit | revenue | **yes** |
| `mix_effect` | Logistic Operation | % of revenue growth | revenue | optional |
| `segment_margin` | Logistic Operation | % | common | **yes** |
| `segment_capex_intensity` | Logistic Operation | % of segment revenue | common | **yes** |
| `segment_wc_days` | Logistic Operation | days | common | **yes** |

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

CFO is positive in all ten disclosed years (INR 2,022 cr FY26) and the capital programme is explicitly guided (INR 30,000 cr ports plus INR 9,000 cr logistics to FY30). Value sits in a long but finite stream of concession cash flows, which is what an FCFF DCF prices. The capital structure is changing sharply (net debt to net cash after the June 2026 QIP, with large capex ahead), so FCFF is preferred to FCFE. The terminal value must respect a capacity-weighted average remaining concession life of about 21 years (Jaigarh 32 years, KB page 79): terminal growth is set low and TV share of EV is reported, not hidden.

Limitations: terminal value dominates when the horizon is short relative to the growth runway — report TV as % of EV; invalid where interest is revenue (lenders)

**EV/EBITDA — CROSS_CHECK**

EBITDA is large and positive (INR 2,604 cr FY26) and the sector trades on it. ADANIPORTS is the one like-for-like listed comparable; GPPL and CONCOR bracket it. This is the cross-check on the DCF terminal value.

Limitations: blind to depreciation, so it flatters capital-intensive businesses against asset-light ones; blind to differences in lease accounting

**Sum of the parts — SECONDARY**

The two segments have very different economics: port segment result INR 1,978 cr on INR 15,704 cr assets versus logistics INR 83 cr on INR 3,455 cr (KB page 219). A SOTP shows how much of the price rests on the logistics plan delivering its guided FY28 EBITDA of INR 700 cr. Secondary rather than primary because logistics exists largely to feed the ports and has no separable listed value.

Limitations: the aggregate is only as good as the weakest part's valuation; double-counts central costs unless they are explicitly allocated or valued as a separate negative

**Must be completed by hand — this pipeline cannot compute it:**

- Value Port Operation on segment EBITDA at a port multiple anchored on ADANIPORTS
- Value Logistic Operation against CONCOR's EV/EBITDA, on FY27E rather than trailing EBITDA given the Navkar ramp
- Add post-QIP net cash of INR 2,769 cr (30 June 2026) and divide by ~233.0 cr shares

**P/E — SECONDARY**

Earnings are positive, but FY26 PAT carries an INR 79.73 cr exceptional item, other income of INR 346 cr (much of it treasury interest that falls as QIP cash is deployed into capex), and an effective tax rate of about 17%. Reported alongside, not led with.

Limitations: differences in leverage and in the effective tax rate reduce comparability directly; near-useless at a cyclical trough or peak, when earnings are the volatile term

**P/B — SECONDARY**

Book value jumped with the INR 6,555 cr primary QIP in June 2026, after the FY26 balance sheet date, so trailing P/B overstates the multiple. Reported for completeness only.

Limitations: meaningless where value sits in intangibles the balance sheet does not carry; distorted by historical-cost land and by revaluation reserves

## 6. Methods rejected as inappropriate

| Method | Why not |
|---|---|
| EV/Sales | Port EBITDA margin is about 53% and logistics about 20%; a single sales multiple would mis-value the shift in mix that the guidance itself forecasts (logistics from 13% to 26% of revenue by FY28E). |
| NAV / asset-based | Concession assets are carried at depreciated cost and revert to the port authorities at concession end; value lies in the cash flow during the concession, not in saleable assets. |
| FFO / AFFO multiple or yield | Not a REIT or InvIT; no FFO distribution policy. |
| FCFE / equity DCF | Leverage is a management choice in transition: net debt/EBITDA went from 0.03x (FY24) to 1.19x (FY26) to net cash after the QIP, with INR 39,000 cr of capex ahead. FCFE would embed an assumed financing path. |

## 7. Uncertainties

| Issue | Impact | How to resolve |
|---|---|---|
| Capacity scope. Guidance of 400 MTPA by FY30 includes 100 MTPA of Phase II projects (Murbe 33, Oman 27, Keni 30, potential 10) that have not reached construction; Keni is still fulfilling conditions precedent (KB page 83). | Management's FY28 EBITDA of ~INR 5,000 cr and the 400 MTPA headline rest partly on uncommitted projects. Including them in the base case values capacity that may not be built. | Analyst to confirm: base case = Phase I only (~300 MTPA by FY28E, with a commissioning lag), Phase II in the bull scenario only. |
| Related-party realisation and concentration. 52% of FY26 cargo is JSW Group; Phase I adds at least 60 MTPA of captive anchor infrastructure (30 MTPA slurry pipeline, 30 MTPA Jatadhar beside JSW Steel's Odisha plant), and the AGM notice approves group rake contracts through FY41 (KB pages 225-241). | The third-party share that rose from 25% (FY21) to 48% (FY26) is likely to fall as Phase I commissions. Group cargo realisation and take-or-pay terms decide whether captive capacity earns port-like returns or a utility return. | Analyst to accept modelling related-party and third-party realisation separately where the disclosure allows, and to treat the related-party share as a disclosed forensic item, not a footnote. |
| Cargo mix. 82% of FY26 volume is coking coal, iron ore and thermal coal (KB page 35); the company itself expects coal traffic to be flattish. | Terminal-year utilisation and growth assumptions inherit the steel cycle and the energy transition. | Carry into Phase 3c: terminal growth below nominal GDP and a bear scenario with flat coal volumes. |
| Finite concessions. Capacity-weighted average remaining concession life is ~21 years (Jaigarh 32 years, KB page 79); per-port expiry dates are not tabulated in the annual report. | A Gordon-growth terminal value assumes renewal on comparable terms. TV is likely to exceed 60% of EV. | Analyst to accept a low terminal growth rate as the proxy for finite life, with TV share and the implied exit multiple stated in the report; seek per-port expiry dates from the DRHP in Phase 3c. |
| Balance-sheet timing. The FY26 base year is pre-QIP (cash INR 2,318 cr, borrowings INR 6,899 cr). At 30 June 2026 the company reports net cash of INR 2,769 cr after a INR 6,555 cr primary raise and ~233.0 cr shares outstanding. | Bridging at FY26 net debt would understate equity value by about INR 7,350 cr and use the wrong share count. | Bridge equity value at 30 June 2026 net cash and post-QIP shares; state the convention on the valuation page. |
| Logistics returns. The segment earned INR 82.55 cr on INR 3,455 cr of assets in FY26 (~2.4%), while management guides EBITDA of INR 700 cr by FY28E on a further INR 9,000 cr of planned investment. | The logistics plan is where ROIIC could fall well below WACC; the guided ramp is unproven. | Model the logistics ramp below guidance in the base case unless Phase 3c finds contracted volume evidence. |

## 8. Checks

- `WARN` **modelability_adjusted** — declared modelability AMBER -> derived GREEN. The derived value governs.

## 9. Analyst decision

**Status: APPROVED**

The analyst must record one of `APPROVED`, `MODIFIED` or `REJECTED` in `strategy_decisions.json` and rebuild. Until then every downstream skill refuses to run.

- **APPROVE** — the decomposition, the drivers and the valuation methods stand.
- **MODIFY** — change `strategy_decisions.json` and rebuild; the original is kept under `recommended`.
- **REJECT / STOP** — the strategy is not defensible; the report does not proceed.
