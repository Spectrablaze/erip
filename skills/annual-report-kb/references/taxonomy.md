# Taxonomy - sections, images, entities

## Canonical sections

Map the report's own headings onto these names where they exist. Do not invent
a section that is not in the document, and do not force an odd one in - an
`<Company>-specific` section (e.g. "Mining Services Review") is better than
mislabelling it.

| Canonical name | Also appears as |
|---|---|
| Letter to Shareholders | Chairman's Message, Chairman's Letter, MD's Message, CEO Message |
| Company Profile | About Us, Who We Are, Company Overview, At a Glance |
| Business Operations | Operational Review, Business Review, Performance Review |
| Business Segments | Segment Review, Our Businesses, Portfolio |
| Products | Product Portfolio, Our Brands, Offerings |
| Manufacturing | Manufacturing Facilities, Plants, Operations Footprint, Capacity |
| Management Discussion & Analysis | MD&A, MDA |
| Risk Factors | Risk Management, Key Risks, Risk & Mitigation |
| Corporate Governance | Governance Report, Board Report |
| Directors' Report | Board's Report, Report of the Directors |
| Sustainability | ESG, BRSR, CSR, Business Responsibility Report |
| Financial Statements | Standalone/Consolidated Financials, Balance Sheet |
| Notes to Accounts | Notes to Financial Statements |
| Auditor's Report | Independent Auditor's Report |
| Shareholder Information | General Shareholder Information, Notice |

Practical guidance for the section plan:

- In Indian annual reports, statutory content (Directors' Report, Corporate
  Governance, Auditor's Report, Financial Statements, Notes) usually occupies
  the back half and is far longer than the narrative front half. Keep
  **Financial Statements** and **Notes to Accounts** as separate sections - they
  are the two most-read files downstream.
- Standalone and consolidated financials are separate sections when both exist.
- One section per topic, not per page. A 300-page financials block is one file.

## Image categories

`apply_plan.py` accepts exactly these; anything else falls back to `other`.

| Category | Use for |
|---|---|
| `directors` | Board member portraits |
| `executives` | KMP / leadership portraits |
| `plants` | Manufacturing plants, refineries, process units |
| `factories` | Assembly or fabrication sites, when distinguished from plants |
| `products` | Product photography, SKUs |
| `brands` | Brand marks and product logos |
| `maps` | Footprint maps, geographic presence |
| `charts` | Bar/line/pie charts of financial or operating data |
| `diagrams` | Process flows, value chains, org structures |
| `logos` | Corporate logo and repeated decorative marks |
| `other` | Anything unclassified, including decoration |

Classification hints, in order of reliability: the `caption` field, then
`section`, then `page_text_snippet`. A portrait-aspect crop near a person's name
and designation is a director or executive; a wide crop on a page whose text
mentions capacity in MT/MW/GW is usually a plant; repeated identical crops
across many pages are `logos`.

Leaving genuinely decorative images in `other` is correct and expected. Spend
classification effort on plants, products, directors and charts - those are what
a research agent later looks for.

## Entity schemas

Write these to `entities/`. Every record carries `page` (0-based) so any claim
can be traced back. Use `null` for unknown fields rather than omitting them, and
never guess a value that is not in the document.

`directors.json`
```json
[{"name": "...", "position": "Chairman / Independent Director",
  "background": "one-line bio as stated", "since": "2019 or null",
  "committees": ["Audit"], "page": 42}]
```

`executives.json`
```json
[{"name": "...", "role": "Chief Financial Officer",
  "responsibilities": "as stated in the report", "page": 46}]
```

`subsidiaries.json`
```json
[{"name": "...", "ownership_pct": 74.0, "geography": "India",
  "type": "subsidiary | associate | joint venture", "page": 310}]
```

`plants.json`
```json
[{"name": "Dahej", "location": "Gujarat", "country": "India",
  "capacity": "2.0 MTPA", "products": ["..."], "page": 123}]
```

`products.json`
```json
[{"name": "...", "segment": "...", "description": "...", "page": 88}]
```

`brands.json`
```json
[{"name": "...", "segment": "...", "description": "...", "page": 90}]
```

`locations.json`
```json
[{"name": "...", "type": "office | plant | warehouse | mine | port",
  "region": "...", "country": "India", "page": 15}]
```

Ownership percentages belong in `subsidiaries.json` as numbers, not strings -
the downstream valuation work does arithmetic on them.
