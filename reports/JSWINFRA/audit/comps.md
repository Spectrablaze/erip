# Peer comparables — JSW Infrastructure Ltd

Basis **consolidated** · priced **2026-10-01** · 3 peers · trailing multiples computed from Screener exports.

| Company | Price | Mkt Cap (Cr) | EV (Cr) | P/E (x) | EV/EBITDA (x) | EV/Sales (x) | P/B (x) | ROE (%) | EBITDA Mgn (%) |
|---|---|---|---|---|---|---|---|---|---|
| JSW Infrastructure Ltd | 357.4 | 83,053.5 | 81,099.7 | 55.9 | 30.1 | 14.5 | 4.8 | 11.0 | 48.3 |
| Adani Ports and Special Economic Zone Ltd | 1,737.8 | 400,382.0 | 458,320.2 | 30.5 | 19.6 | 11.3 | 4.2 | 16.6 | 57.9 |
| Gujarat Pipavav Port Ltd | 165.9 | 8,019.3 | 7,380.3 | 16.0 | 10.4 | 6.4 | 3.7 | 23.4 | 61.2 |
| Container Corporation of India Ltd | 442.0 | 33,663.6 | 31,140.9 | 27.1 | 15.9 | 3.4 | 2.6 | 9.8 | 21.6 |
| **Peer median** |  |  |  | 27.1 | 15.9 | 6.4 | 3.7 | 16.6 |  |
| **JSW Infrastructure Ltd prem / (disc)** |  |  |  | +106% | +89% | +127% | +30% | -34% |  |

Peer interquartile range: P/E (x) 21.6-28.8; EV/EBITDA (x) 13.2-17.8; EV/Sales (x) 4.9-8.9; P/B (x) 3.2-4.0; ROE (%) 13.2-20.0

## Comparability

- **MEDIUM** (trailing_window_misalignment): trailing P&L windows end at different dates: Jun-26 (JSW Infrastructure Ltd, Adani Ports and Special Economic Zone Ltd, Container Corporation of India Ltd); Mar-26 (Gujarat Pipavav Port Ltd). Earnings are compared over non-identical twelve-month periods.
- **MEDIUM** (unverified_basis): JSW Infrastructure Ltd: reporting basis was declared in the manifest, not read from the export header.
- **MEDIUM** (unverified_basis): Adani Ports and Special Economic Zone Ltd: reporting basis was declared in the manifest, not read from the export header.
- **MEDIUM** (unverified_basis): Gujarat Pipavav Port Ltd: reporting basis was declared in the manifest, not read from the export header.
- **MEDIUM** (unverified_basis): Container Corporation of India Ltd: reporting basis was declared in the manifest, not read from the export header.

## Provenance

| Company | Basis | FY end | Trailing window | Balance sheet | Price |
|---|---|---|---|---|---|
| JSW Infrastructure Ltd | consolidated (declared) | Mar-26 | TTM to Jun-26 | Mar-26 | NSE close 2026-10-01 (Screener export) |
| Adani Ports and Special Economic Zone Ltd | consolidated (declared) | Mar-26 | TTM to Jun-26 | Mar-26 | NSE close 2026-10-01 (Screener peer table) |
| Gujarat Pipavav Port Ltd | consolidated (declared) | Mar-26 | TTM to Mar-26 | Mar-26 | NSE close 2026-10-01 (Screener peer table) |
| Container Corporation of India Ltd | consolidated (declared) | Mar-26 | TTM to Jun-26 | Mar-26 | NSE close 2026-10-01 (Yahoo Finance / Bajaj Finserv) |

ROE is computed as PAT / average net worth for every company, so it is internally consistent but will not tie to a screen using a different convention.

## Enterprise value bridge

| Company | market cap | + borrowings | - cash & bank | - surplus investments | + minority interest | + preference capital | EV |
|---|---|---|---|---|---|---|---|
| JSW Infrastructure Ltd | 83,053.5 | 7,094.0 | -9,863.0 | -0.0 | 815.2 | 0.0 | 81,099.7 |
| Adani Ports and Special Economic Zone Ltd | 400,382.0 | 63,565.5 | -8,483.5 | -0.0 | 2,856.2 | 0.0 | 458,320.2 |
| Gujarat Pipavav Port Ltd | 8,019.3 | 36.9 | -675.9 | -0.0 | 0.0 | 0.0 | 7,380.3 |
| Container Corporation of India Ltd | 33,663.6 | 964.6 | -3,487.3 | -0.0 | 0.0 | 0.0 | 31,140.9 |

### Bridge notes

- JSW Infrastructure Ltd: holds 25 cr of Investments that were NOT netted from EV; set surplus_investments in the manifest for the genuinely surplus part
- Adani Ports and Special Economic Zone Ltd: holds 5,449 cr of Investments that were NOT netted from EV; set surplus_investments in the manifest for the genuinely surplus part
- Gujarat Pipavav Port Ltd: holds 83 cr of Investments that were NOT netted from EV; set surplus_investments in the manifest for the genuinely surplus part
- Gujarat Pipavav Port Ltd: consolidated EV carries no minority interest — Screener does not export it; add minority_interest from the balance sheet if the subsidiaries are materially not wholly owned
- Container Corporation of India Ltd: holds 1,069 cr of Investments that were NOT netted from EV; set surplus_investments in the manifest for the genuinely surplus part
- Container Corporation of India Ltd: consolidated EV carries no minority interest — Screener does not export it; add minority_interest from the balance sheet if the subsidiaries are materially not wholly owned

## Relative-valuation bands (INR / share)

| Method | Low | Mid | High |
|---|---|---|---|
| Peer P/E (25th-75th) | 138 | 173 | 184 |
| Peer EV/EBITDA (25th-75th) | 165 | 196 | 218 |
| Peer P/B (25th-75th) | 239 | 277 | 299 |

Feed these to `charts.football_field` alongside the DCF scenario range and the 52-week range.

## Warnings

- the approved modeling strategy rules out ev_sales for this company, so no relative-valuation band is emitted for them. The multiples still appear in the comps table — what is withheld is the implication that they value the business.
- reporting basis not stated in the export header; using the declared 'consolidated' unverified
- currency unit not stated in the export; assuming Rs crore
- manifest name 'JSW Infrastructure Ltd' does not look like the export's 'Years' — check the file is the right company
- share count read from an absolute line and converted to crore (2,100,001,567 -> 210.00 Cr)
- reporting basis not stated in the export header; using the declared 'consolidated' unverified
- currency unit not stated in the export; assuming Rs crore
- manifest name 'Adani Ports and Special Economic Zone Ltd' does not look like the export's 'Years' — check the file is the right company
- share count read from an absolute line and converted to crore (2,303,959,098 -> 230.40 Cr)
- reporting basis not stated in the export header; using the declared 'consolidated' unverified
- currency unit not stated in the export; assuming Rs crore
- manifest name 'Gujarat Pipavav Port Ltd' does not look like the export's 'Years' — check the file is the right company
- share count read from an absolute line and converted to crore (483,439,910 -> 48.34 Cr)
- reporting basis not stated in the export header; using the declared 'consolidated' unverified
- currency unit not stated in the export; assuming Rs crore
- manifest name 'Container Corporation of India Ltd' does not look like the export's 'Years' — check the file is the right company
- share count read from an absolute line and converted to crore (609,294,348 -> 60.93 Cr)
