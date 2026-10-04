# Where the operating disclosures actually live

Grounding rule: every material conclusion in the strategy cites the knowledge
base. **Do not invent a KPI because it is common in the sector.** A cement
company that does not disclose EBITDA per tonne is a company whose strategy says
so, not a company whose strategy assumes it.

`strategy_probe.py` searches for these automatically and returns page citations.
This file is where to look when the probe comes back thin, and what each source
can and cannot settle.

## By document

| Source | Settles |
|---|---|
| `context/business_overview.md` | what the company sells, to whom; the first pass at segmentation |
| `context/management_discussion.md` | order book, capacity, volumes, realisation, the drivers management itself talks about — the single richest source |
| segment note (annual report) | segment revenue, results, assets. The materiality split comes from here, not from a slide |
| `metadata/table_index.json` → `tables/` | capacity tables, plant lists, product-wise volumes |
| `entities/` | `plants` carry `capacity`; `products` and `brands` carry `segment` |
| investor presentation | the operating KPI deck: utilisation, SSSG, RevPAR, ARPU, book-to-bill. Usually the only place a quarterly KPI series exists |
| concall transcript | execution period, ramp timing, guidance — the qualifiers that turn a disclosed number into a forecastable one |
| notes to accounts | revenue-recognition policy, which decides whether reported revenue leads or lags the economics |

## By archetype — what must be found before claiming it

| Archetype | Minimum disclosure |
|---|---|
| `capacity_utilisation_realisation` | installed capacity; utilisation % or volume; the commissioning date of anything in the forecast |
| `order_book_execution` | order book / unexecuted order value; inflow; an execution period or book-to-bill |
| `project_pipeline_completion` | pipeline or saleable area; pre-sales; collections; a completion schedule |
| `volume_price` / `units_asp` | volume or units **disclosed** — not derived as revenue ÷ price |
| `production_realisation` | production volume; an identifiable benchmark price; unit cash cost or a spread |
| `stores_sales_per_store` | store count; SSSG or sales per store/sq ft |
| `rooms_occupancy_arr` | keys; occupancy and ARR (or RevPAR); the owned vs managed split |
| `headcount_utilisation_realisation` | headcount; utilisation or revenue per employee; onsite/offshore mix where material |
| `customers_arpu` / `subscribers_arpu` | customer or subscriber count; ARPU or per-customer revenue; churn or retention |

If the minimum is absent, the honest options are a different archetype,
`generic_growth` with the limitation stated, or AMBER with the missing disclosure
named. Not a plausible number.

## Traps that produce a confident wrong answer

- **Circular derivation.** Deriving volume as revenue ÷ price when price was
  itself derived as revenue ÷ volume. The bridge then always ties and never
  informs. One of the two must be independently disclosed.
- **Order book basis.** Order books are usually stated ex-GST and ex-escalation;
  revenue is not. Check before dividing one by the other.
- **Wholesale vs retail.** Despatches (SIAM) and registrations (FADA) are
  different numbers for the same market. Never mix them in one series.
- **Capacity as at year end vs average.** Year-end capacity against full-year
  revenue overstates utilisation whenever anything was commissioned mid-year.
- **Closing vs average counts.** Closing customers, subscribers or stores against
  a full year of revenue overstates the per-unit metric by roughly half the
  year's growth. `segment_build.py` uses averages for exactly this reason.
- **Managed vs owned keys.** A management contract earns a fee on somebody else's
  revenue and carries almost no capital. Running managed keys through an ARR
  build inflates revenue and capex together.
- **Segment revenue including inter-segment sales.** The segment note usually
  discloses both; the eliminations line is what reconciles to consolidated
  revenue, and it belongs in `unallocated`.

## Recording evidence

Use `decisions.json`'s object shape so citations flow downstream unchanged:

```json
{"quote": "unexecuted order book of INR 12,480 cr as at 31 March 2026",
 "source": "context/management_discussion.md", "page": 41}
```

`source: "external"` for anything genuinely outside the knowledge base — a
benchmark commodity price, an industry-body volume. Never dress external data as
a knowledge-base finding.

A segment with no `evidence` array caps modelability at AMBER. That is
deliberate: an unevidenced architecture is an assertion, and this layer exists to
stop assertions travelling as analysis.
