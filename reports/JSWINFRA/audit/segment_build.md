# Segment revenue build — JSW Infrastructure Ltd

*Base year FY26; strategy is APPROVED / GREEN*

Consolidated revenue is the sum of segment revenue, each built from its approved economic archetype on approved, cited drivers. The growth path below is DERIVED from that build — it is what financial-model's single revenue row consumes. Every figure traces back through segments[].rows to the drivers and their citations.

## Consolidated

| | FY26 | FY27 | FY28 | FY29 | FY30 | FY31 | FY32 | FY33 | FY34 | FY35 | FY36 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Revenue | 5,361 | 6,380 | 9,179 | 11,228 | 12,912 | 13,974 | 14,947 | 15,940 | 16,953 | 17,975 | 19,053 |
| **Derived growth %** | — | **+19.0** | **+43.9** | **+22.3** | **+15.0** | **+8.2** | **+7.0** | **+6.6** | **+6.4** | **+6.0** | **+6.0** |

This growth path is what `financial-model-assumptions` injects as `revenue_growth`, and what `financial-model`'s single revenue row executes.

## Port Operation — capacity_utilisation_realisation

`revenue = installed capacity x utilisation % x realisation per unit`

**Base-year tie-out:** calibrated — reported 4,647, rebuilt 4,647

> implied scale is a clean power of ten — a pure unit conversion

| Driver | FY26 | FY27 | FY28 | FY29 | FY30 | FY31 | FY32 | FY33 | FY34 | FY35 | FY36 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| capacity | 183 | 192 | 280 | 295 | 300 | 300 | 306 | 312 | 318 | 324 | 330 |
| additions | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| utilisation | 0.667 | 0.661 | 0.611 | 0.675 | 0.73 | 0.753 | 0.758 | 0.763 | 0.767 | 0.772 | 0.776 |
| realisation | 381 | 400 | 414 | 428 | 444 | 459 | 475 | 492 | 509 | 527 | 545 |
| **Revenue** | **4,647** | **5,080** | **7,079** | **8,527** | **9,712** | **10,373** | **11,022** | **11,702** | **12,417** | **13,167** | **13,957** |
| Growth % | — | +9.3 | +39.4 | +20.5 | +13.9 | +6.8 | +6.3 | +6.2 | +6.1 | +6.0 | +6.0 |

**Citations**

- `installed_capacity` — "Phase I to 300 MTPA by FY28E: VOC Tuticorin 7.0, slurry pipeline 30.0, Mangalore container 1.8, Jaigarh & Dharamtar 36.0, Jatadhar 30.0, SWPL 4.0, Jaigarh LPG 2.0, Kolkata container 6.3" — `kb/annual_report/images/charts/capacity_roadmap_400mtpa.jpg`, p. 8
- `installed_capacity` — "The slurry pipeline project has crossed a key milestone with 251 kilometres of pipeline lowering completed ... on track for completion by March 2027" — `kb/concall/pages/page_0002.md`, p. 3
- `installed_capacity` — "Jatadhar Port ... Capacity 30mtpa, Estimated Capex 3,050 Crore, Pile foundation work 80% completed ... Construction to be completed by March 2027; Slurry Pipeline ... Long term Take or Pay Agreement with JSW Steel ... Estimated Capex 4,000 Crore ... Construction to be completed by March 2027; Expansion at Dharamtar & Jaigarh 36mtpa ... on the back of expansion of 5mtpa Steel-making capacity of Anchor customer at Dolvi ... Targeting completion by March 2027" — `JSW Infrastructure corporate presentation, May 2026 (company website)`
- `utilisation` — "We should deliver you a number of around 127 million tonnes this year" — `kb/concall/pages/page_0006.md`, p. 7
- `utilisation` — "82% of total volume of cargo handled by the company comprises coking coal, iron ore and thermal coal ... the growth of coal traffic is expected to remain flattish" — `kb/annual_report/pages/page_0035.md`, p. 35
- `utilisation` — "We forecast that cargo volumes handled by JSWIL's ports, terminals and slurry pipeline to rise at a CAGR of 16% over FY27-FY30 ... take-or-pay contracts governing most of the volume uptake" — `Fitch Ratings, 'Fitch Affirms JSW Infrastructure at BBB-', 19 Aug 2026`
- `realisation` — "Operational revenue for the port segment increased by 11 percentage during the quarter ... driven by volume growth and a favorable product mix" — `kb/concall/pages/page_0004.md`, p. 5
- `realisation` — "cash flow projections ... based on estimated cargo quantities and WPI adjusted rates of cargo handling for the period up to respective concession period" — `kb/annual_report/pages/page_0193.md`, p. 193
- `realisation` — "revenues from those operations would more than double to INR97 billion by FY30, from INR46 billion in FY26. We assume an average tariff growth rate of 3% over FY27-FY30" — `Fitch Ratings, 19 Aug 2026`

## Logistic Operation — volume_price

`revenue = volume x average price`

**Base-year tie-out:** calibrated — reported 715, rebuilt 715

> implied scale is a clean power of ten — a pure unit conversion

| Driver | FY26 | FY27 | FY28 | FY29 | FY30 | FY31 | FY32 | FY33 | FY34 | FY35 | FY36 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| volume | 40 | 58 | 100 | 140 | 170 | 190 | 205 | 220 | 235 | 245 | 255 |
| price | 17.9 | 22.4 | 21 | 19.3 | 18.8 | 18.9 | 19.1 | 19.3 | 19.3 | 19.6 | 20 |
| **Revenue** | **715** | **1,300** | **2,100** | **2,701** | **3,200** | **3,601** | **3,924** | **4,238** | **4,536** | **4,808** | **5,096** |
| Growth % | — | +81.9 | +61.6 | +28.6 | +18.5 | +12.5 | +9.0 | +8.0 | +7.0 | +6.0 | +6.0 |

**Citations**

- `volume` — "this year, our entire orders of 40 rakes are supposed to come on stream by Jan or Feb latest. So at least we should be having a rake fleet of 80 rakes plus" — `kb/concall/pages/page_0013.md`, p. 14
- `volume` — "scaling our fleet to approximately 110 rail rakes and 140 container rakes, creating a combined fleet of around 250 rakes over the next 2 to 3 years" — `kb/concall/pages/page_0003.md`, p. 4
- `price` — "Logistics FY26A revenue INR 715 cr; FY27E INR 1,650 cr; FY28E INR 2,800 cr" — `kb/investor_presentation/images/charts/logistics_targets_fy28.jpg`, p. 14
- `price` — "transactions at Kudathini Multi-Modal Logistics Park, Karnataka amounting to INR 1,610 Crore (FY27 - INR 294 Crore; FY28 - INR 570 Crore; FY29 - INR 746 Crore)" — `kb/annual_report/pages/page_0238.md`, p. 238
- `price` — "we forecast JSWIL's revenue from the logistics segment to grow nine-fold to INR64 billion by FY30, from INR7 billion in FY26" — `Fitch Ratings, 19 Aug 2026`
