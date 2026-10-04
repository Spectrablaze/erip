# Segment revenue build — Adani Ports and Special Economic Zone Ltd

*Base year FY26; strategy is APPROVED / AMBER*

Consolidated revenue is the sum of segment revenue, each built from its approved economic archetype on approved, cited drivers. The growth path below is DERIVED from that build — it is what financial-model's single revenue row consumes. Every figure traces back through segments[].rows to the drivers and their citations.

## Consolidated

| | FY26 | FY27 | FY28 | FY29 | FY30 | FY31 |
|---|---:|---:|---:|---:|---:|---:|
| Revenue | 37,453 | 45,464 | 51,384 | 58,818 | 67,530 | 75,693 |
| **Derived growth %** | — | **+21.4** | **+13.0** | **+14.5** | **+14.8** | **+12.1** |

This growth path is what `financial-model-assumptions` injects as `revenue_growth`, and what `financial-model`'s single revenue row executes.

## Domestic Ports and SEZ — capacity_utilisation_realisation

`revenue = installed capacity x utilisation % x realisation per unit`

**Base-year tie-out:** calibrated — reported 25,755, rebuilt 25,755

> implied scale is a clean power of ten — a pure unit conversion

| Driver | FY26 | FY27 | FY28 | FY29 | FY30 | FY31 |
|---|---:|---:|---:|---:|---:|---:|
| capacity | 653 | 700 | 760 | 830 | 910 | 1e+03 |
| additions | 0 | 47 | 60 | 70 | 80 | 90 |
| utilisation | 0.691 | 0.695 | 0.695 | 0.69 | 0.685 | 0.68 |
| realisation | 571 | 588 | 606 | 624 | 643 | 662 |
| **Revenue** | **25,755** | **28,605** | **32,008** | **35,735** | **40,080** | **45,015** |
| Growth % | — | +11.1 | +11.9 | +11.7 | +12.2 | +12.3 |

**Citations**

- `installed_capacity` — "cargo handling capacity of 653 MMT and ~27% share of India's total port volumes" — `kb/annual_report/pages/page_0109.md`, p. 109
- `installed_capacity` — "Domestic port capacity will increase to 1bn tonne from current 653 MMT, on a five-year capex plan of INR 60,000-63,000 cr for domestic ports" — `inputs/ambition_2031.pdf deck page 22`, p. 22
- `capacity_addition` — "Business 5-year capex plan (FY27-FY31): Domestic ports INR 60,000-63,000 Cr" — `inputs/ambition_2031.pdf deck page 22`, p. 22
- `utilisation` — "Domestic volume FY26 451.0 MMT vs FY25 430.6 MMT, +5%" — `kb/investor_presentation/pages/page_0035.md`, p. 35
- `utilisation` — "Mundra installed capacity 274 MMT against throughput 192 MMT, i.e. 70% utilisation" — `kb/annual_report/pages/page_0111.md`, p. 111
- `realisation` — "Domestic Ports FY26 revenue INR 25,755 cr on 451.0 MMT of domestic cargo implies a blended realisation of INR 571 per tonne, inclusive of SEZ and land lease income" — `derived: FY26 media release segment table and deck page 35`, p. 35

## International Ports — capacity_utilisation_realisation

`revenue = installed capacity x utilisation % x realisation per unit`

**Base-year tie-out:** calibrated — reported 4,539, rebuilt 4,539

> implied scale is a clean power of ten — a pure unit conversion

| Driver | FY26 | FY27 | FY28 | FY29 | FY30 | FY31 |
|---|---:|---:|---:|---:|---:|---:|
| capacity | 144 | 144 | 144 | 168 | 192 | 192 |
| additions | 0 | 0 | 0 | 24 | 24 | 0 |
| utilisation | 0.346 | 0.62 | 0.66 | 0.66 | 0.68 | 0.7 |
| realisation | 911 | 900 | 910 | 920 | 930 | 940 |
| **Revenue** | **4,539** | **8,032** | **8,645** | **10,197** | **12,137** | **12,628** |
| Growth % | — | +77.0 | +7.6 | +17.9 | +19.0 | +4.0 |

**Citations**

- `installed_capacity` — "NQXT 50 MMT, CWIT 48 MMT, Haifa 26 MMT, Dar es Salaam 20 MMT = 144 MMT" — `kb/investor_presentation/images/maps/footprint.jpg, deck page 4`, p. 4
- `installed_capacity` — "Phase 2 developments at Vizhinjam and Colombo starting in October 2027" — `kb/investor_presentation/pages/page_0004.md`, p. 4
- `capacity_addition` — "International ports capex INR 6,000-7,000 Cr, largely CWIT phase 2" — `inputs/ambition_2031.pdf deck page 22`, p. 22
- `utilisation` — "International volume FY26 49.8 MMT vs FY25 19.6 MMT, +154%" — `kb/investor_presentation/pages/page_0035.md`, p. 35
- `utilisation` — "Q1 FY27 international volumes 22.8 MMT vs 7.7 MMT in Q1 FY26; NQXT contributed 10 MMT and Colombo 6.9 MMT. Annualising Q1 FY27 gives roughly 91 MMT, i.e. 63% of the 144 MMT capacity base." — `inputs/q1fy27_operational.pdf`
- `realisation` — "International Ports FY26 revenue INR 4,539 cr on 49.8 MMT implies INR 911 per tonne. Held roughly flat because NQXT is lower-realisation bulk coal and dilutes the Colombo container mix as it annualises." — `derived: FY26 media release segment table and deck page 35`, p. 35

## Logistics — volume_price

`revenue = volume x average price`

**Base-year tie-out:** calibrated — reported 4,478, rebuilt 4,478

> implied scale is a clean power of ten — a pure unit conversion

| Driver | FY26 | FY27 | FY28 | FY29 | FY30 | FY31 |
|---|---:|---:|---:|---:|---:|---:|
| volume | 6.96e+05 | 8.3e+05 | 9.7e+05 | 1.12e+06 | 1.28e+06 | 1.45e+06 |
| price | 6.44e+04 | 6.9e+04 | 7.35e+04 | 7.8e+04 | 8.25e+04 | 8.7e+04 |
| **Revenue** | **4,478** | **5,727** | **7,129** | **8,736** | **10,560** | **12,615** |
| Growth % | — | +27.9 | +24.5 | +22.5 | +20.9 | +19.5 |

**Citations**

- `volume` — "8% growth in container rail volume (695,517 TEUs vs. 643,480 TEUs)" — `kb/investor_presentation/pages/page_0015.md`, p. 15
- `volume` — "GPWIS volume lower by 1% (21.7 MMT vs. 22.0 MMT) — the bulk stream is flat, so growth has to come from rail containers and warehousing" — `kb/investor_presentation/pages/page_0015.md`, p. 15
- `price` — "Logistics FY26 revenue INR 4,478 cr over 695,517 container rail TEUs gives a blended INR 64,384 per TEU. This is a blended figure covering rail, GPWIS bulk, trucking, warehousing and agri silos, not a pure rail haulage rate." — `derived: FY26 media release segment table and deck page 15`, p. 15
- `mix_effect` — "Mix held at zero: the blended per-TEU price already absorbs the shift toward warehousing and agri silos, so a separate mix term would double count." — `analyst judgement`

## Marine — capacity_utilisation_realisation

`revenue = installed capacity x utilisation % x realisation per unit`

**Base-year tie-out:** calibrated — reported 2,681, rebuilt 2,681

> implied scale is a clean power of ten — a pure unit conversion

| Driver | FY26 | FY27 | FY28 | FY29 | FY30 | FY31 |
|---|---:|---:|---:|---:|---:|---:|
| capacity | 135 | 150 | 168 | 186 | 205 | 225 |
| additions | 0 | 15 | 18 | 18 | 19 | 20 |
| utilisation | 0.97 | 0.97 | 0.97 | 0.97 | 0.97 | 0.97 |
| realisation | 20.5 | 21.3 | 22.1 | 23 | 23.9 | 24.9 |
| **Revenue** | **2,681** | **3,100** | **3,602** | **4,150** | **4,753** | **5,435** |
| Growth % | — | +15.6 | +16.2 | +15.2 | +14.5 | +14.3 |

**Citations**

- `installed_capacity` — "244 vessels include 135 vessels owned by APSEZ's Marine vertical. The remaining vessels (comprising of 47 captive vessels (tugs, workboats, etc.) & 62 dredgers) are consolidated under Domestic ports" — `inputs/ambition_2031.pdf deck page 4`, p. 4
- `installed_capacity` — "Marine capex INR 11,000-13,000 Cr over FY27-FY31, fleet expansion" — `inputs/ambition_2031.pdf deck page 22`, p. 22
- `capacity_addition` — "Marine capex INR 11,000-13,000 Cr over FY27-FY31 is the largest capex per rupee of incremental revenue in the plan: INR 11-13k cr of spend against INR 3.3k cr of incremental revenue to FY31" — `inputs/ambition_2031.pdf deck page 22`, p. 22
- `utilisation` — "integration of the cloud-based SeaFlux marine platform was crucial in delivering a robust 97% availability of vessels" — `kb/annual_report/pages/page_0042.md`, p. 42
- `realisation` — "Marine FY26 revenue INR 2,681 cr over 135 owned vessels at 97% availability implies INR 20.5 cr of revenue per available vessel per year. Grown at roughly 4% a year for day-rate inflation and fleet mix." — `derived: FY26 media release segment table and deck page 4`, p. 4
