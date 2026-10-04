# Sector overlays

Which assumptions matter, which are not applicable, and what the
industry-specific assumptions are. Profile keys match the
`equity-research-report` skill's `scripts/sectors.py`, so the `sector` field
carries straight through to the model.

Resolve the sector **before** generating assumptions - it decides which of the
required assumptions are genuinely not applicable, and marking one `not
applicable` is very different from marking it `insufficient evidence`.

---

## manufacturing — auto, industrials, engineering, capital goods

- **Drives value**: capacity utilisation, gross margin, fixed asset turn, capex
  cycle.
- **Industry-specific**: installed capacity and utilisation % by plant, the
  volume/realisation split of revenue growth, raw material as % of sales and the
  main input's price trend, order book and execution period, import/export mix
  and duty exposure.
- **Watch**: capex programmes that raise depreciation before they raise revenue.
  Model the commissioning lag explicitly.

## services — IT, consulting, platforms, software

- **Not applicable**: volume growth (no physical unit), DIO, and usually gross
  margin - there is no meaningful COGS line, so a "gross margin" here is EBITDA
  margin rebadged.
- **Drives value**: employee cost % of sales, utilisation, revenue per employee,
  DSO.
- **Industry-specific**: headcount growth vs revenue growth, wage inflation and
  the offshore/onshore mix, attrition, client concentration, net revenue
  retention, deal TCV and its conversion period, currency mix.
- **Watch**: employee cost is the dominant lever - never hold it flat as a ratio
  without a stated productivity or pyramid argument.

## consumer — FMCG, retail, pharma

- **Drives value**: gross margin, A&P spend, inventory days, distribution reach.
- **Industry-specific**: volume vs price/mix growth (consumer companies disclose
  this split, so use it rather than inferring), A&P as % of sales, same-store
  sales growth and store additions for retail, new product contribution, channel
  mix (modern trade, e-commerce, general trade), for pharma the R&D %, ANDA
  filings and US price erosion.
- **Watch**: A&P is discretionary and is the first line cut to protect a margin
  guidance. A margin expansion funded by cutting A&P is not durable.

## commodity — cement, metals, mining, chemicals

- **Drives value**: realisation per tonne, EBITDA per tonne, capacity
  utilisation, net debt/EBITDA.
- **Industry-specific**: realisation and EBITDA per tonne, spread over the key
  input, capacity additions across the industry (not just the company), cost
  curve position, cyclical mid-cycle margin rather than the last twelve months.
- **Watch**: never extrapolate a peak-cycle margin. Anchor to a mid-cycle level
  across a full cycle and say which years you treated as the cycle. Terminal
  growth for a cyclical must reflect a mid-cycle base, not the current year.

## realestate — developers, infrastructure

- **Drives value**: pre-sales, collections, project completion timing.
- **Industry-specific**: pre-sales bookings vs recognised revenue, collection
  efficiency, land bank and its cost, project-level margins, debt against
  project cash flows.
- **Watch**: revenue recognition is completion-linked and disconnected from cash
  collection. Working capital assumptions built off reported revenue are wrong;
  build them off collections.

## financials — banks, NBFCs, insurers: **do not model with this skill**

The `equity-research-report` model blocks this sector, and the block is correct
here too. For a lender, interest is revenue, so EBITDA, net debt, EV multiples
and FCFF are undefined or meaningless. Working-capital days and capex intensity
have no interpretation on a bank balance sheet.

If the company is a bank, NBFC or insurer, stop and say so rather than producing
assumptions that look plausible and are structurally invalid. The right frame is
NII and margin, credit cost, loan growth, capital adequacy, and a P/B or excess
return valuation - a different model, not a re-parameterisation of this one.

---

## Applicability matrix

| Assumption | manufacturing | services | consumer | commodity | realestate |
|---|---|---|---|---|---|
| Volume growth | yes | n/a | yes | yes | yes (sq ft) |
| Pricing growth | yes | rate/realisation | yes | yes (realisation) | yes (psf) |
| New customers | rare | yes | rare | rare | n/a |
| Customer retention | rare | yes | rare | rare | n/a |
| Gross margin | yes | n/a | yes | yes | project margin |
| DIO | yes | n/a | yes | yes | inventory = projects |
| R&D | sometimes | sometimes | pharma yes | sometimes | n/a |
| S&M | rare split | yes | yes | rare | yes |
| Capex intensity | high | low | medium | high | land, not PPE |

"n/a" means the assumption does not exist for the business model - say that
explicitly. It is not the same as the knowledge base failing to disclose it.
