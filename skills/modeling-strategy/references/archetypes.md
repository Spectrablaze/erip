# Economic driver archetypes — the reasoning

`scripts/archetypes.py` is the machine-readable library. This file is why it is
shaped the way it is, and how to choose between entries that look similar.

## The premise

A sector label tells you what an industry association calls the company. An
archetype tells you what the revenue line is made of. They are related and they
are not the same thing:

- Two "capital goods" companies, one selling standard pumps off a line and one
  building turnkey plants, share a sector and share nothing else. One is
  capacity × utilisation × realisation; the other is order book × execution.
- One "hotel" company can be both rooms × occupancy × ARR (owned) and a fee
  stream on somebody else's revenue (managed).
- A cement company that also runs a ready-mix retail network has two.

So the library is keyed on the economics, and the sector key from
`equity-research-report/scripts/sectors.py` travels alongside as context. Sector
still decides which *ratios* are meaningful — that is its job and it does it well.
Archetype decides what the *revenue build* is.

## Why the library is closed

The realistic failure mode of a language model asked "what drives this business?"
is not silence. It is a fluent, plausible, invented architecture — "subscriber
cohorts × contribution margin ramp" — that no disclosure supports and no analyst
asked for. Confident invention is the specific risk, so `resolve()` matches
exactly or returns `None`, and `None` becomes a proposal for a human to sign off
rather than a soft landing.

Matching is exact-or-alias. There is deliberately no fuzzy fallback: a near-miss
that quietly lands on the wrong architecture is worse than an honest unknown,
because it comes with all the apparatus of rigour attached.

The cost of the closed list is that a genuinely novel business is friction. That
is the correct trade. Promoting a repeated proposal into the library is a
deliberate act by a person, in a commit, with the false-positive trap written
down — not something that happens at runtime.

## Choosing between the near-neighbours

These are the pairs that actually get confused.

**`volume_price` vs `units_asp`** — use `units_asp` where the unit is a discrete
product with a quoted average selling price (vehicles, handsets, appliances) and
`volume_price` where the unit is a quantity (tonnes, litres, kWh, cases). If the
company reports "ASP", use `units_asp`; the disclosure vocabulary is the tell.

**`volume_price` vs `production_realisation`** — the question is who sets the
price. If the company posts a price list and defends it, `volume_price`. If the
price is an external benchmark the company takes (LME, coal index, spot cement in
a region), `production_realisation`, and then the mid-cycle discipline applies.
The distinction matters far more than it looks: extrapolating a peak realisation
across a forecast is how a commodity model becomes fiction, and only one of these
two archetypes carries the machinery to prevent it.

**`capacity_utilisation_realisation` vs `volume_price`** — use capacity where
capacity is disclosed and binding. Its whole value is the ceiling it puts on the
forecast. If the model can produce revenue above installed capacity, the
archetype is decoration and `volume_price` was the honest choice.

**`order_book_execution` vs `project_pipeline_completion`** — an order book is a
contracted claim on the company's future revenue. A project pipeline is the
company's own inventory of things it hopes to sell. EPC and defence are the
former; residential real estate is the latter, where revenue is an accounting
consequence of completion and the economics are pre-sales and collections. Where
both exist, they are two segments.

**`customers_arpu` vs `subscribers_arpu`** — subscription implies a recurring
billing period, deferred revenue, and a churn number the company discloses. Use
`customers_arpu` for a transactional customer base where "churn" is inferred
rather than reported.

**Anything vs `generic_growth`** — `generic_growth` is the honest fallback when
the disclosure does not carry drivers. It is not the default and it is not a
failure. What it must never be is silent: `check_strategy.py` caps modelability
at AMBER once it covers more than 40% of revenue, because at that share the
"model" is a growth rate wearing a decomposition.

## Segment granularity

Two opposite errors, and the floor sits between them.

*Too coarse* — running a conglomerate through one archetype. The consolidated
growth rate is then a weighted average of things that move for unrelated reasons,
and no assumption in the model can be argued.

*Too fine* — giving a 4%-of-revenue segment its own driver architecture because
the segment note has a line for it. The drivers will not be disclosed, the
assumptions will be invented, and the apparent precision is entirely artificial.

`SEGMENT_MATERIALITY_FLOOR_PCT` is 10%. Below it, fold the segment into the
consolidated build and say so. The test is not "is there a segment note" but
"does the disclosure carry this segment's drivers".

Where segment disclosure is absent altogether, that is a stated limitation, and
the question becomes whether consolidated modelling remains defensible. Sometimes
it does — a single-product manufacturer needs no segments. Sometimes it does not,
and that is an AMBER with a named missing disclosure.

## The base-year tie-out

Every archetype in the library is arithmetic that must reproduce the last
reported year before it forecasts anything. `segment_build.py` enforces this: the
driver series starts at the base year, the build is compared to reported segment
revenue, and a gap above 1% is a refusal rather than a warning.

This is the single most useful check in the layer. An architecture that cannot
rebuild the year it can see is not describing the business, and the gap is
usually informative — a missing revenue stream, a unit error, or a driver taken
from a segment that is not the one being modelled.

## Adding an archetype

Only after the same proposal has come up more than once. Each entry needs:

1. `identity` — the arithmetic, written out, checkable by eye.
2. `revenue_drivers` — with units, and an `fma_preset` so the assumption engine
   knows where to search for evidence.
3. `requires` — the disclosures without which the archetype cannot be claimed.
4. `schedules` — what the model has to carry beyond the standard set.
5. `false_positive` — **the mandatory field.** Why this archetype gets claimed
   when it is wrong. An entry without a real one is not ready.
6. `translation` — how it reaches `financial-model`'s single revenue row, and a
   builder in `segment_build.py`. `unsupported` is a legitimate answer; it makes
   the pipeline refuse, which is the point.
