# Canonical section blueprint

Derived from the three reference reports: Eicher Motors (34pp), ITC (32pp),
Maruti Suzuki (45pp). Sections marked **R** are mandatory in every report; **C**
are conditional (include when the company or the data makes them meaningful).
All 66 sections are mandatory unless the data is genuinely unavailable.

One `<section class="page">` per row unless the row says otherwise. If a section's
content does not fill the page, merge it with its neighbour rather than padding.

| # | Section | R/C | Layout | Charts / tables | Images needed |
|---|---|---|---|---|---|
| 1 | **Cover** | R | `.cover-grid` | sidebar KV blocks + 1Y relative perf + financial summary | `logo.png` |
| 2 | Global economy | R | `.split` | `bar_grouped` horizontal — Global GDP projections (%) by geography, 2025A/2026P/2027P | — |
| 3 | Indian economy | R | `.split-r` | `line_multi` India vs global GDP; CPI/WPI, repo, INR, 10Y yield as `.kpis` | — |
| 4 | Global industry | R | `.split` | `bar_line_combo` market size + CAGR | — |
| 5 | Indian industry | R | `.split-r` | volumes / market size + growth | — |
| 6–8 | Industry growth drivers | R | `.split` ×3 | one driver per page: income & premiumisation, structural shift (EV/CNG/rural), distribution & financing | — |
| 9 | Industry risks & headwinds | R | `.cols-2` | input costs, regulation, import dependency, competitive intensity | optional exhibit |
| 10 | Company history | R | `.timeline` | milestone timeline | — |
| 11 | Business overview & profile | R | `.split` | segment revenue `donut` | — |
| 12 | Group structure, subsidiaries & JVs | R | full | org chart | `exhibits/group-structure.png` |
| 13 | Global footprint & distribution | C | `.split-r` | — | `plants/footprint.png` |
| 14 | Manufacturing sites & capacity | R | `.cols-2` | capacity table by plant, utilisation | `plants/*.png` |
| 15 | R&D / technical centres | C | `.cols-2` | R&D spend % of sales trend | — |
| 16 | Product / brand portfolio | R | `.photo-grid` | — | `products/*.png` ×6–12 |
| 17 | Revenue segmentation | R | `.split` | `stacked_bar` segment mix 5–10 yr | — |
| 18 | Market share & competitive position | R | `.split-r` | `line_multi` share trend vs peers | — |
| 19 | SWOT | R | `.swot` | — | — |
| 20 | Porter's five forces | R | table + `.pill` intensity | — | — |
| 21–23 | Board of directors | R | `.people` ×3 | headshot + 60–90 word profile each | `people/*.jpg` |
| 24 | Board skills & expertise matrix | R | `table.matrix` | — | — |
| 25 | Board / committee composition & attendance | R | table | — | — |
| 26–27 | Management team (KMP) | R | `.people` ×2 | — | `people/*.jpg` |
| 28 | Management commentary & assessment | R | prose | your verdict on the team | — |
| 29–30 | Remuneration analysis | R | tables | remuneration vs sales/PAT, ratio to median, % increase, peer benchmark | — |
| 31 | Shareholding pattern | R | `.split` | `stacked_bar` 10-yr; promoter pledge callout | — |
| 32 | Quarterly snapshot (8 quarters) | R | wide table | `table.sm` | — |
| 33–34 | Concall analysis (latest 2–4 quarters) | R | `.cols-2` ×2 | guidance, volumes, margins, capex, Q&A takeaways | — |
| 35 | Yearly snapshot / P&L 10-yr | R | wide table | `table.sm` | — |
| 36 | Revenue analysis | R | `.split` | `bar_line_combo` revenue + growth | — |
| 37 | Raw material, COGS & gross margin | R | `.split-r` | `line_multi` gross margin vs peers | — |
| 38 | EBITDA / EBIT / PAT margins | R | `.split` | `bar_line_combo` + peer `line_multi` | — |
| 39 | Balance sheet analysis | R | wide table | asset quality & composition | — |
| 40 | Liquidity | R | `.split` | current/quick ratio trend | — |
| 41 | Leverage & solvency | R | `.split-r` | D/E, net debt/EBITDA, interest coverage | — |
| 42 | Receivables analysis | R | `.split` | `bar_line_combo` receivables + days, vs sales growth | — |
| 43 | Inventory analysis | R | `.split-r` | same shape | — |
| 44 | Payables analysis | R | `.split` | same shape | — |
| 45 | Cash conversion cycle | R | `.split-r` | `line_multi` CCC vs peers | — |
| 46 | Capex — maintenance vs growth | R | `.split` | `bar_line_combo` capex + % of sales, peer comparison | — |
| 47 | Fixed assets & depreciation | R | `.split-r` | FA turnover, dep % of revenue vs peers | — |
| 48 | Cash flow statement analysis | R | wide table | CFO/CFI/CFF 10-yr | — |
| 49 | Free cash flow | R | `.split` | FCF trend + cumulative + conversion | — |
| 50 | Ratio analysis 1/3 — profitability | R | `table.sm` | with mean & median columns | — |
| 51 | Ratio analysis 2/3 — leverage & efficiency | R | `table.sm` | — | — |
| 52 | Ratio analysis 3/3 — cash & per-share | R | `table.sm` | — | — |
| 53 | ROCE / ROIC | R | `.split` | `line_multi` vs peers vs cost of capital | — |
| 54–55 | DuPont (3-step and 5-step) | R | `.tree` + table | driver decomposition | — |
| 56 | ROIIC profiling | R | table + `line_multi` | incremental returns on reinvestment | — |
| 57 | Forensic analysis | R | flag table | CFO/PAT, accruals, receivable & inventory divergence | — |
| 58 | Auditor's remarks, RPT & contingent liabilities | R | `.cols-2` | — | `exhibits/auditor.png` |
| 59 | Stories in charts | C | `.cols-2` 4 charts | the 4 charts that carry the thesis | — |
| 60–61 | **Primary valuation** | R | wide table + `sensitivity_heat` | the method the modeling strategy marked PRIMARY — for an FCFF DCF: WACC build-up, FCFF forecast, EV bridge, sensitivity | — |
| 62 | Relative valuation | R | wide table + `scatter_peers` | the multiples the strategy admitted, vs peer median | — |
| 63 | Indexed stock performance | R | full-width | `indexed_performance` vs Nifty + peers | — |
| 64 | Analyst coverage universe | C | table | date, house, rating, target | — |
| 65 | Investment rationale, risks & verdict | R | `.cols-2` | 3–5 rationale points, 3–5 risks, what would change your mind | — |
| 66 | Analyst profile & disclaimer | R | — | — | optional headshot |

Rows 6–8, 21–23, 26–27, 29–30, 33–34, 54–55 and 60–61 are multi-page groups; the
rest are one page each. Dropping all **C** rows is fine if the company has no global footprint or R&D centres to show.

### Rows 60–62 follow the approved methodology, not the template

Where `modeling-strategy` ran, `model.json` carries `valuation_strategy`. Write
rows 60–62 to it:

- **The PRIMARY method heads row 60–61**, whatever it is. A company valued on NAV
  does not get a page headed "DCF valuation"; it gets a NAV page, and the DCF
  appears — if at all — under its approved role.
- **Substitute, never delete.** Removing a valuation page leaves a hole in the analysis. An NAV or SOTP page replaces the DCF page; it does not leave a hole.
- **Where the PRIMARY method is `analyst_manual`**, the page still gets written —
  from the analyst's own workings — and says plainly that it was built outside the
  model. `valuation_strategy.manual_completion_required` lists what that was.
- **Row 62 carries only the multiples the strategy admitted.** A multiple ruled
  `NOT_APPROPRIATE` may appear in the comps table as a number, but never as a
  valuation band.
- **Rejected methods earn a paragraph**, not silence. Saying why a method was not
  used is what distinguishes a methodology from a habit — and it is the first
  question a reader asks when the obvious lens is missing.
- Where the architecture was a segment build, `segment_build.md` is an exhibit
  alongside `model_review.md`.

---

## Cover page data contract

The sidebar is fixed. Every report carries these blocks in this order:

1. **Recommendation** — `Recommendation`, `CMP`, `Target Price`, `Upside %`
   (academic reports in the samples print `XXX`; only print a real target if the
   DCF and relative valuation agree on a range, and say which one you anchored on)
2. **Stock data (as on <date>)** — Nifty, 52-week H/L, market cap, O/S shares,
   dividend yield, NSE code, BSE code, sector
3. **Relative stock performance – 1Y** — chart
4. **Absolute returns** — 1Y / 3Y / 5Y (and CAGR block if you have it)
5. **Shareholding (%) as on <quarter>** — promoters / FII / DII / government / public,
   plus number of shareholders and pledge %
6. **Financial summary** — FY(n), FY(n+1)E, FY(n+2)E: net revenue, YoY growth,
   EBITDA, EBITDA margin, PAT, YoY growth, ROE, EPS, EV/EBITDA
7. **Prepared by** — name, email, phone

Left column: title, tagline, *About the Company* (3–4 paragraphs), *Investment
Thesis* (1 paragraph), *Key Highlights* (6–8 bullets, each one number-led).

## Header / disclaimer

Every page carries the academic disclaimer top-left and the company name top-right,
via `string-set`. Put these two hidden divs once at the top of `<body>`:

```html
<div class="doc-disclaimer">Academic Research Project – Not a Recommendation</div>
<div class="doc-running">Eicher Motors Ltd</div>
```
