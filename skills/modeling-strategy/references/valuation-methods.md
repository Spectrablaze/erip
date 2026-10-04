# Choosing the valuation methodology

`scripts/valuation.py` holds the method library, the hard disqualifiers and the
execution owners. This file is the reasoning, and the cases that are easy to get
wrong.

## Two questions, kept apart

1. **Is this method economically appropriate for this business?**
2. **Can anything in this pipeline compute it?**

Conflating them is how a pipeline ends up running an FCFF DCF on a portfolio of
assets: the DCF was never chosen, it was the only thing available. So the
strategy answers (1) with no reference to (2), and records (2) separately as
`execution_owner`.

When the right method has no owner, the output is: method **PRIMARY**,
`execution_owner: analyst_manual`, modelability **AMBER**, and an explicit list of
what a human has to finish. Never a downgrade to whatever the pipeline can run.

## What this pipeline can actually compute

Verified against the code, not assumed:

| Method | Owner | Where |
|---|---|---|
| FCFF DCF, WACC build-up, sensitivity, scenarios | `model.py` | `dcf()`, `scenarios()` |
| P/E, EV/EBITDA, EV/Sales, P/B | `peer-comps`, `model.py` | `build_comps.py`, `relative()` |
| Everything else | `analyst_manual` | — |

"Everything else" includes FCFE, EV/EBIT, SOTP, NAV, FFO/AFFO, EV per tonne,
replacement cost and DDM. Several of them are the *correct* primary method for
whole classes of company, which is the reason `analyst_manual` is a first-class
answer rather than an error state.

## The default is not a default

FCFF DCF leads most reports in this pipeline, and that is usually right. It is
also the single most likely way for the layer to fail quietly: nobody objects to
a DCF, so it survives by not being argued with.

So the rule is a **positive argument each time**. "No objection" is not a
rationale. The argument has to name the operating cash flow, its forecastability
and the capital requirement behind it. If that sentence cannot be written, the
DCF is not the primary method, whatever the pipeline is convenient for.

## Hard disqualifiers

Arithmetic, not taste. `check_strategy.py` will not let an analyst assert these
away, and `build_strategy.py` raises them even when the strategy never mentioned
the method:

| Fact | Disqualifies |
|---|---|
| negative EBITDA | EV/EBITDA |
| negative EBIT | EV/EBIT |
| negative PAT | P/E |
| fewer than 3 comparable peers | every multiple-based method |
| bank / NBFC / insurer | everything — out of scope, RED |
| a single segment | SOTP |

A negative-denominator multiple has no interpretation. It is not "low
reliability", it is undefined, and printing `nm` next to a peer median that
excludes it is the correct behaviour — which `peer-comps` already does.

## The cases worth thinking about

**Loss-making.** P/E and EV/EBITDA are out by arithmetic. What is left is
EV/Sales (which ignores profitability entirely, so the margin assumption has to
sit next to it in writing) and a DCF whose value is almost all terminal. Both are
weak; say which you anchored on and why, and report TV as % of EV. A
loss-making company where the losses are structural rather than cyclical is a
candidate for RED — not because the arithmetic fails but because a forecast that
turns positive by assumption is false precision.

**Cyclical at a peak or trough.** P/E is close to useless — earnings are the
volatile term. Lead with EV/EBITDA on a mid-cycle margin, and cross-check on
book value and EV per unit of capacity, which are cycle-independent. State the
cycle position you assumed; a forecast that holds peak realisation is the single
most common way a commodity valuation becomes fiction.

**Conglomerate.** SOTP is the correct primary method once segments have genuinely
different economics, and nothing here computes it. The honest configuration is
SOTP PRIMARY / `analyst_manual` / AMBER, with the parts valued individually — the
pipeline can still produce the DCF for the operating segment and the multiples
for the rest, and the analyst aggregates. Watch two things: central costs
double-count unless allocated or valued as a separate negative, and a
holding-company discount needs a reason, in either direction.

**Real estate developer.** NAV project-by-project is primary; revenue is an
accounting consequence of completion. A DCF struck on reported revenue is
modelling the accounting, not the business.

**REIT / InvIT.** Depreciation makes P/E meaningless, which is why FFO exists.
AFFO depends on a maintenance-capex judgement that is not a disclosure — state it.

**Asset-light, high ROIC.** P/B says nothing because the assets are not on the
balance sheet. The level of ROIC is not the insight either; the reinvestment rate
is. Lead with the DCF and cross-check on P/E.

**Heavy leverage as the story.** FCFE is the right lens when the debt path moves
value more than the operating forecast does — infrastructure, project SPVs.
`financial-model`'s bridge already carries an FCFE line, so the manual step is a
discount at the cost of equity rather than a rebuild.

## Roles

| Role | Means |
|---|---|
| `PRIMARY` | the valuation is anchored here; the target price comes from it |
| `SECONDARY` | a genuine second opinion, reported with its own number |
| `CROSS_CHECK` | a sanity test, not a value; used to say whether PRIMARY is odd |
| `LOW_RELIABILITY` | computable, reported, explicitly not leaned on |
| `NOT_APPROPRIATE` | rejected, with the economic reason |

One PRIMARY is normal, two is defensible for a genuine SOTP. More than two is
flagged: anchoring on everything is anchoring on nothing.

**Rejections are the informative half.** A strategy that rejects nothing has not
tested anything, and `build_strategy.py` surfaces any hard-disqualified method
the analyst never mentioned — silence is not a classification.

## What this layer must never do

- Compute a valuation. It selects; `model.py` calculates. There is one DCF in
  this pipeline and it lives in `model.py`.
- Downgrade a correct method because it is inconvenient.
- Promote EV/EBITDA because EBITDA happens to be positive. Availability is not
  applicability — for a business whose capital consumption *is* the economics,
  EV/EBIT is the fairer lens, and it is the one the pipeline does not compute.
