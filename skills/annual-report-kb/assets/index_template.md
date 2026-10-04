# <Company Name> - Annual Report <FY> Knowledge Base

<!--
Template for index.md, the main navigation file. Fill the counts from
manifest.json and drop rows for anything the report does not contain.
Delete this comment block in the generated file.
-->

Source: `report.pdf` (<N> pages) | Built <YYYY-MM-DD> | See
[parse_report.md](parse_report.md) for coverage and warnings.

**Start here:** the `context/` files summarise each topic with page citations.
Open `sections/` for full text, `tables/` for figures, `pages/` for a single page.

## Company context

| Topic | File | Covers |
|---|---|---|
| Company overview | [context/company_overview.md](context/company_overview.md) | What the company does, scale, history |
| Business model | [context/business_model.md](context/business_model.md) | How it makes money |
| Business segments | [context/business_segments.md](context/business_segments.md) | Segment structure and performance |
| Products | [context/products.md](context/products.md) | Product and brand portfolio |
| Manufacturing | [context/manufacturing.md](context/manufacturing.md) | Plants, capacity, utilisation, expansion |
| Management | [context/management.md](context/management.md) | Executive team |
| Directors | [context/directors.md](context/directors.md) | Board composition and governance |
| Subsidiaries | [context/subsidiaries.md](context/subsidiaries.md) | Group structure and ownership |
| Risks | [context/risks.md](context/risks.md) | Risk factors and mitigation |
| Sustainability | [context/sustainability.md](context/sustainability.md) | ESG / BRSR disclosures |
| Financial summary | [context/financial_summary.md](context/financial_summary.md) | Headline financials and ratios |
| Glossary | [context/glossary.md](context/glossary.md) | Company and industry terms |

## Sections

| # | Section | Pages | File |
|---|---|---|---|
| 01 | Letter to Shareholders | 8-13 | [sections/01_letter_to_shareholders.md](sections/01_letter_to_shareholders.md) |

## Data

| Resource | Count | Index |
|---|---|---|
| Tables | <N> | [metadata/table_index.json](metadata/table_index.json) |
| Images | <N> | [metadata/image_index.json](metadata/image_index.json) |
| Pages | <N> | [metadata/pages.json](metadata/pages.json) |
| Table of contents | - | [metadata/toc.json](metadata/toc.json) |

## Entities

| Type | Count | File |
|---|---|---|
| Directors | <N> | [entities/directors.json](entities/directors.json) |
| Executives | <N> | [entities/executives.json](entities/executives.json) |
| Subsidiaries | <N> | [entities/subsidiaries.json](entities/subsidiaries.json) |
| Plants | <N> | [entities/plants.json](entities/plants.json) |
| Products | <N> | [entities/products.json](entities/products.json) |
| Brands | <N> | [entities/brands.json](entities/brands.json) |
| Locations | <N> | [entities/locations.json](entities/locations.json) |

## Images by category

| Category | Count |
|---|---|
| plants | <N> |
| directors | <N> |
| charts | <N> |

## Conventions

- Page numbers in filenames and JSON are **0-based**; `pdf_page` and citations
  written as "(p. N)" are **1-based**, matching the PDF reader.
- Every table and image record carries the page it came from and the page file
  that contains its surrounding text.
