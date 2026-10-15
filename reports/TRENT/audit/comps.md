# Peer comparables — Trent Ltd

Basis **consolidated** · priced **2026-10-14** · 5 peers · trailing multiples computed from Screener exports.

| Company | Price | Mkt Cap (Cr) | EV (Cr) | P/E (x) | EV/EBITDA (x) | EV/Sales (x) | P/B (x) | ROE (%) | EBITDA Mgn (%) |
|---|---|---|---|---|---|---|---|---|---|
| Trent Ltd | 2,971.0 | 158,423.3 | 160,177.3 | 87.6 | 40.8 | 7.6 | 22.7 | 29.1 | 18.8 |
| Avenue Supermarts Ltd | 3,415.0 | 222,644.0 | 224,765.3 | 71.4 | 40.4 | 3.0 | 9.1 | 13.6 | 7.5 |
| V-Mart Retail Ltd | 827.6 | 6,576.4 | 7,514.4 | 47.8 | 13.7 | 1.9 | 6.9 | 15.6 | 13.7 |
| V2 Retail Ltd | 170.6 | 6,222.2 | 7,210.5 | 35.1 | 14.0 | 2.1 | 6.9 | 28.5 | 15.0 |
| Aditya Birla Fashion and Retail Ltd | 45.3 | 5,526.6 | 11,235.2 | nm | 17.0 | 1.3 | 0.9 | -12.3 | 7.9 |
| Shoppers Stop Ltd | 373.2 | 4,110.1 | 7,414.1 | nm | 9.8 | 1.4 | 14.1 | -11.3 | 14.7 |
| **Peer median** |  |  |  | 47.8 | 14.0 | 1.9 | 6.9 | 13.6 |  |
| **Trent Ltd prem / (disc)** |  |  |  | +83% | +191% | +300% | +229% | +114% |  |

Peer interquartile range: P/E (x) 41.5-59.6; EV/EBITDA (x) 13.7-17.0; EV/Sales (x) 1.4-2.1; P/B (x) 6.9-9.1; ROE (%) -11.3-15.6

## Comparability

- **MEDIUM** (trailing_window_misalignment): trailing P&L windows end at different dates: Jun-26 (Trent Ltd, V-Mart Retail Ltd, V2 Retail Ltd, Aditya Birla Fashion and Retail Ltd, Shoppers Stop Ltd); Sep-26 (Avenue Supermarts Ltd). Earnings are compared over non-identical twelve-month periods.
- **MEDIUM** (unverified_basis): Trent Ltd: reporting basis was declared in the manifest, not read from the export header.
- **MEDIUM** (unverified_basis): Avenue Supermarts Ltd: reporting basis was declared in the manifest, not read from the export header.
- **MEDIUM** (unverified_basis): V-Mart Retail Ltd: reporting basis was declared in the manifest, not read from the export header.
- **MEDIUM** (unverified_basis): V2 Retail Ltd: reporting basis was declared in the manifest, not read from the export header.
- **MEDIUM** (unverified_basis): Aditya Birla Fashion and Retail Ltd: reporting basis was declared in the manifest, not read from the export header.
- **MEDIUM** (not_meaningful): Aditya Birla Fashion and Retail Ltd: P/E is not meaningful (denominator <= 0).
- **MEDIUM** (unverified_basis): Shoppers Stop Ltd: reporting basis was declared in the manifest, not read from the export header.
- **MEDIUM** (not_meaningful): Shoppers Stop Ltd: P/E is not meaningful (denominator <= 0).
- **MEDIUM** (outlier): Aditya Birla Fashion and Retail Ltd: P/B (x) of 0.9 is more than 3x away from the peer median of 6.9. It is included in the median as it stands — drop the peer from the manifest if it is not genuinely comparable.

## Provenance

| Company | Basis | FY end | Trailing window | Balance sheet | Price |
|---|---|---|---|---|---|
| Trent Ltd | consolidated (declared) | Mar-26 | TTM to Jun-26 | Mar-26 | NSE close 2026-10-14 (Screener export) |
| Avenue Supermarts Ltd | consolidated (declared) | Mar-26 | TTM to Sep-26 | Mar-26 | NSE close 2026-10-14 (Screener export, downloaded 15 Oct) |
| V-Mart Retail Ltd | consolidated (declared) | Mar-26 | TTM to Jun-26 | Mar-26 | NSE close 2026-10-14 (Screener export, downloaded 15 Oct) |
| V2 Retail Ltd | consolidated (declared) | Mar-26 | TTM to Jun-26 | Mar-26 | NSE close 2026-10-14 (Screener export, downloaded 15 Oct) |
| Aditya Birla Fashion and Retail Ltd | consolidated (declared) | Mar-26 | TTM to Jun-26 | Mar-26 | NSE close 2026-10-14 (Screener export, downloaded 15 Oct) |
| Shoppers Stop Ltd | consolidated (declared) | Mar-26 | TTM to Jun-26 | Mar-26 | NSE close 2026-10-14 (Screener export, downloaded 15 Oct) |

ROE is computed as PAT / average net worth for every company, so it is internally consistent but will not tie to a screen using a different convention.

## Enterprise value bridge

| Company | market cap | + borrowings | - cash & bank | - surplus investments | + minority interest | + preference capital | EV |
|---|---|---|---|---|---|---|---|
| Trent Ltd | 158,423.3 | 2,561.2 | -283.0 | -647.5 | 123.3 | 0.0 | 160,177.3 |
| Avenue Supermarts Ltd | 222,644.0 | 2,425.0 | -303.8 | -0.0 | 0.0 | 0.0 | 224,765.3 |
| V-Mart Retail Ltd | 6,576.4 | 957.6 | -19.5 | -0.0 | 0.0 | 0.0 | 7,514.4 |
| V2 Retail Ltd | 6,222.2 | 994.6 | -6.2 | -0.0 | 0.0 | 0.0 | 7,210.5 |
| Aditya Birla Fashion and Retail Ltd | 5,526.6 | 6,189.1 | -480.5 | -0.0 | 0.0 | 0.0 | 11,235.2 |
| Shoppers Stop Ltd | 4,110.1 | 3,316.7 | -12.7 | -0.0 | 0.0 | 0.0 | 7,414.1 |

### Bridge notes

- Avenue Supermarts Ltd: holds 4 cr of Investments that were NOT netted from EV; set surplus_investments in the manifest for the genuinely surplus part
- Avenue Supermarts Ltd: consolidated EV carries no minority interest — Screener does not export it; add minority_interest from the balance sheet if the subsidiaries are materially not wholly owned
- V-Mart Retail Ltd: holds 18 cr of Investments that were NOT netted from EV; set surplus_investments in the manifest for the genuinely surplus part
- V-Mart Retail Ltd: consolidated EV carries no minority interest — Screener does not export it; add minority_interest from the balance sheet if the subsidiaries are materially not wholly owned
- V2 Retail Ltd: holds 5 cr of Investments that were NOT netted from EV; set surplus_investments in the manifest for the genuinely surplus part
- V2 Retail Ltd: consolidated EV carries no minority interest — Screener does not export it; add minority_interest from the balance sheet if the subsidiaries are materially not wholly owned
- Aditya Birla Fashion and Retail Ltd: holds 1,240 cr of Investments that were NOT netted from EV; set surplus_investments in the manifest for the genuinely surplus part
- Aditya Birla Fashion and Retail Ltd: consolidated EV carries no minority interest — Screener does not export it; add minority_interest from the balance sheet if the subsidiaries are materially not wholly owned
- Shoppers Stop Ltd: holds 0 cr of Investments that were NOT netted from EV; set surplus_investments in the manifest for the genuinely surplus part
- Shoppers Stop Ltd: consolidated EV carries no minority interest — Screener does not export it; add minority_interest from the balance sheet if the subsidiaries are materially not wholly owned

## Relative-valuation bands (INR / share)

| Method | Low | Mid | High |
|---|---|---|---|
| Peer P/E (25th-75th) | 1,408 | 1,622 | 2,022 |
| Peer EV/EBITDA (25th-75th) | 978 | 1,001 | 1,222 |
| Peer EV/Sales (25th-75th) | 519 | 716 | 794 |

Feed these to `charts.football_field` alongside the DCF scenario range and the 52-week range.

## Warnings

- the approved modeling strategy rules out pb for this company, so no relative-valuation band is emitted for them. The multiples still appear in the comps table — what is withheld is the implication that they value the business.
- reporting basis not stated in the export header; using the declared 'consolidated' unverified
- currency unit not stated in the export; assuming Rs crore
- share count read from an absolute line and converted to crore (355,487,461 -> 35.55 Cr)
- share count overridden by the manifest: 35.5487461 -> 53.3232 Cr (BSE shareholding pattern 30-09-2026 (533,232,301 shares) after the 1:2 bonus, record date 4 June 2026)
- reporting basis not stated in the export header; using the declared 'consolidated' unverified
- currency unit not stated in the export; assuming Rs crore
- share count read from an absolute line and converted to crore (651,959,123 -> 65.20 Cr)
- reporting basis not stated in the export header; using the declared 'consolidated' unverified
- currency unit not stated in the export; assuming Rs crore
- share count read from an absolute line and converted to crore (79,458,289 -> 7.95 Cr)
- reporting basis not stated in the export header; using the declared 'consolidated' unverified
- currency unit not stated in the export; assuming Rs crore
- share count read from an absolute line and converted to crore (364,637,550 -> 36.46 Cr)
- reporting basis not stated in the export header; using the declared 'consolidated' unverified
- currency unit not stated in the export; assuming Rs crore
- share count read from an absolute line and converted to crore (1,220,538,192 -> 122.05 Cr)
- reporting basis not stated in the export header; using the declared 'consolidated' unverified
- currency unit not stated in the export; assuming Rs crore
- share count read from an absolute line and converted to crore (110,117,329 -> 11.01 Cr)
