# Peer comparables — Adani Ports and Special Economic Zone Ltd

Basis **consolidated** · priced **2026-08-07** · 3 peers · trailing multiples computed from Screener exports.

| Company | Price | Mkt Cap (Cr) | EV (Cr) | P/E (x) | EV/EBITDA (x) | EV/Sales (x) | P/B (x) | ROE (%) | EBITDA Mgn (%) |
|---|---|---|---|---|---|---|---|---|---|
| Adani Ports and Special Economic Zone Ltd | 1,695.0 | 390,521.1 | 448,459.2 | 29.8 | 19.2 | 11.1 | 4.1 | 16.6 | 57.9 |
| JSW Infrastructure Ltd | 327.5 | 68,775.1 | 73,356.3 | 46.3 | 27.2 | 13.1 | 6.3 | 14.4 | 48.3 |
| Gujarat Pipavav Port Ltd | 151.3 | 7,312.5 | 6,673.5 | 14.6 | 9.4 | 5.8 | 3.4 | 23.4 | 61.2 |
| Container Corporation of India Ltd | 512.0 | 31,195.9 | 28,673.1 | 25.1 | 14.6 | 3.2 | 2.4 | 9.8 | 21.6 |
| **Peer median** |  |  |  | 25.1 | 14.6 | 5.8 | 3.4 | 14.4 |  |
| **Adani Ports and Special Economic Zone Ltd prem / (disc)** |  |  |  | +19% | +32% | +91% | +21% | +15% |  |

Peer interquartile range: P/E (x) 19.9-35.7; EV/EBITDA (x) 12.0-20.9; EV/Sales (x) 4.5-9.4; P/B (x) 2.9-4.8; ROE (%) 12.1-18.9

## Comparability

- **MEDIUM** (trailing_window_misalignment): trailing P&L windows end at different dates: Jun-26 (Adani Ports and Special Economic Zone Ltd, JSW Infrastructure Ltd, Container Corporation of India Ltd); Mar-26 (Gujarat Pipavav Port Ltd). Earnings are compared over non-identical twelve-month periods.
- **MEDIUM** (unverified_basis): Adani Ports and Special Economic Zone Ltd: reporting basis was declared in the manifest, not read from the export header.
- **MEDIUM** (unverified_basis): JSW Infrastructure Ltd: reporting basis was declared in the manifest, not read from the export header.
- **MEDIUM** (unverified_basis): Gujarat Pipavav Port Ltd: reporting basis was declared in the manifest, not read from the export header.
- **MEDIUM** (unverified_basis): Container Corporation of India Ltd: reporting basis was declared in the manifest, not read from the export header.

## Provenance

| Company | Basis | FY end | Trailing window | Balance sheet | Price |
|---|---|---|---|---|---|
| Adani Ports and Special Economic Zone Ltd | consolidated (declared) | Mar-26 | TTM to Jun-26 | Mar-26 | Screener export close, 2026-08-07 cover date |
| JSW Infrastructure Ltd | consolidated (declared) | Mar-26 | TTM to Jun-26 | Mar-26 | Screener export close, same day as subject |
| Gujarat Pipavav Port Ltd | consolidated (declared) | Mar-26 | TTM to Mar-26 | Mar-26 | Screener export close, same day as subject |
| Container Corporation of India Ltd | consolidated (declared) | Mar-26 | TTM to Jun-26 | Mar-26 | Screener export close, same day as subject |

ROE is computed as PAT / average net worth for every company, so it is internally consistent but will not tie to a screen using a different convention.

## Enterprise value bridge

| Company | market cap | + borrowings | - cash & bank | - surplus investments | + minority interest | + preference capital | EV |
|---|---|---|---|---|---|---|---|
| Adani Ports and Special Economic Zone Ltd | 390,521.1 | 63,565.5 | -8,483.5 | -0.0 | 2,856.2 | 0.0 | 448,459.2 |
| JSW Infrastructure Ltd | 68,775.1 | 6,898.9 | -2,317.7 | -0.0 | 0.0 | 0.0 | 73,356.3 |
| Gujarat Pipavav Port Ltd | 7,312.5 | 36.9 | -675.9 | -0.0 | 0.0 | 0.0 | 6,673.5 |
| Container Corporation of India Ltd | 31,195.9 | 964.6 | -3,487.3 | -0.0 | 0.0 | 0.0 | 28,673.1 |

### Bridge notes

- Adani Ports and Special Economic Zone Ltd: holds 5,449 cr of Investments that were NOT netted from EV; set surplus_investments in the manifest for the genuinely surplus part
- JSW Infrastructure Ltd: holds 25 cr of Investments that were NOT netted from EV; set surplus_investments in the manifest for the genuinely surplus part
- JSW Infrastructure Ltd: consolidated EV carries no minority interest — Screener does not export it; add minority_interest from the balance sheet if the subsidiaries are materially not wholly owned
- Gujarat Pipavav Port Ltd: holds 83 cr of Investments that were NOT netted from EV; set surplus_investments in the manifest for the genuinely surplus part
- Gujarat Pipavav Port Ltd: consolidated EV carries no minority interest — Screener does not export it; add minority_interest from the balance sheet if the subsidiaries are materially not wholly owned
- Container Corporation of India Ltd: holds 1,069 cr of Investments that were NOT netted from EV; set surplus_investments in the manifest for the genuinely surplus part
- Container Corporation of India Ltd: consolidated EV carries no minority interest — Screener does not export it; add minority_interest from the balance sheet if the subsidiaries are materially not wholly owned

## Relative-valuation bands (INR / share)

| Method | Low | Mid | High |
|---|---|---|---|
| Peer P/E (25th-75th) | 1,133 | 1,428 | 2,032 |
| Peer EV/EBITDA (25th-75th) | 980 | 1,244 | 1,884 |
| Peer P/B (25th-75th) | 1,208 | 1,416 | 1,999 |

Feed these to `charts.football_field` alongside the DCF scenario range and the 52-week range.

## Warnings

- the approved modeling strategy rules out ev_sales for this company, so no relative-valuation band is emitted for them. The multiples still appear in the comps table — what is withheld is the implication that they value the business.
- reporting basis not stated in the export header; using the declared 'consolidated' unverified
- currency unit not stated in the export; assuming Rs crore
- manifest name 'Adani Ports and Special Economic Zone Ltd' does not look like the export's 'Years' — check the file is the right company
- reporting basis not stated in the export header; using the declared 'consolidated' unverified
- currency unit not stated in the export; assuming Rs crore
- manifest name 'JSW Infrastructure Ltd' does not look like the export's 'Years' — check the file is the right company
- reporting basis not stated in the export header; using the declared 'consolidated' unverified
- currency unit not stated in the export; assuming Rs crore
- manifest name 'Gujarat Pipavav Port Ltd' does not look like the export's 'Years' — check the file is the right company
- reporting basis not stated in the export header; using the declared 'consolidated' unverified
- currency unit not stated in the export; assuming Rs crore
- manifest name 'Container Corporation of India Ltd' does not look like the export's 'Years' — check the file is the right company
