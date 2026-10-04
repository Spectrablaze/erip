---
name: modeling-strategy
description: "Decides what a company should actually be modelled as before any assumptions or forecasts are built - segment-level economic driver architecture (order book x execution, capacity x utilisation x realisation, rooms x occupancy x ARR, customers x ARPU and the rest), the model schedules that architecture requires, and which valuation methodologies (FCFF DCF, FCFE, EV/EBITDA, EV/EBIT, P/E, EV/Sales, SOTP, NAV, FFO/AFFO) are economically appropriate versus inappropriate - then puts it to the analyst as an explicit approval gate. This skill should be used before financial-model-assumptions whenever a forecast, financial model, DCF or equity research report is being built, or when the user asks how a business should be modelled, what drives its economics, which valuation method fits, or whether a company can be modelled at all."
---

# Modeling strategy

Answer one question, before any number is forecast:

> **What business am I actually modelling, what drives its economics, what model
> architecture is appropriate, and which valuation methodologies make economic
> sense?**

This skill decides **what** should be modelled. `financial-model-assumptions`
decides **what values**. `financial-model` does the arithmetic. `model.py` does
the valuation. Those boundaries are the point — keep them.

It never computes a valuation. The pipeline has exactly one DCF and it lives in
`equity-research-report/scripts/model.py`.

## Why this exists

A pipeline that runs from "understand the company" straight into assumptions
assumes every business shares a financial architecture. It does not. An EPC arm
runs on order book × execution; a plant runs on capacity × utilisation ×
realisation; a hotel runs on rooms × occupancy × ARR — and one company can
contain all three. Valuation is the same story: a DCF is not always right, EBITDA
is not always the profitability metric that matters, and a method being
*available* is not a reason to use it.

Two failure modes are being designed against, and they pull in the same
direction: **confident invention** (a fluent architecture no disclosure supports)
and **false precision** (a five-year forecast off a business nobody understood).
The system prefers abstention to either.

## Scope

Banks, NBFCs and insurers are **out of scope** and refused — interest is revenue
for a lender, so EBITDA, net debt, the revolver plug and FCFF are undefined. This
check is additive: the four pre-existing refusals elsewhere in the pipeline are
untouched and still fire independently.

## Where it runs

`equity-research-report` **Phase 3b** — after the knowledge base (Phase 2) and
the Screener parse (Phase 3a), before `financial-model-assumptions` (Phase 3c).

## Workflow

### 1. Probe the evidence

```bash
python3 scripts/strategy_probe.py --kb reports/<T>/kb/annual_report \
        --kb reports/<T>/kb/investor_presentation \
        --financials reports/<T>/data/financials.json \
        -o reports/<T>/data/strategy_probe.json
```

Returns ranked archetype candidates with page citations, whether segment
disclosure exists, and the arithmetic facts that disqualify valuation methods
(negative EBITDA, negative PAT, thin peer set). If it reports lender disclosures
— NIM, GNPA, CASA, CRAR — **stop and confirm the sector**.

It proposes; it does not decide. A low score on the archetype you were about to
choose is the finding worth acting on.

### 2. Choose the architecture

Read `references/archetypes.md` before choosing, and `references/evidence.md`
when the probe comes back thin.

```bash
python3 scripts/archetypes.py --list
python3 scripts/archetypes.py --show order_book_execution
python3 scripts/archetypes.py --drivers rooms_occupancy_arr
```

The library is **closed**. `resolve()` matches exactly or returns nothing —
there is no fuzzy fallback, because a near-miss that silently lands on the wrong
architecture is worse than an honest unknown. If a business fits nothing, leave
`economic_archetype` null and write the candidate into `proposed_archetype`: that
caps modelability at AMBER and asks the analyst to sign it off. **Never invent a
key.**

Work at segment level where disclosure supports it, and only there. Below 10% of
revenue a segment does not get its own architecture — that is fake granularity.
`generic_growth` is the honest fallback when drivers are not disclosed; above 40%
of revenue it caps modelability at AMBER, because at that share the model is a
growth rate wearing a decomposition.

### 3. Select the valuation methods

Read `references/valuation-methods.md`. Classify every plausible method
`PRIMARY` / `SECONDARY` / `CROSS_CHECK` / `LOW_RELIABILITY` / `NOT_APPROPRIATE`,
each with an economic justification.

Two rules that carry most of the value:

- **A DCF needs a positive argument every time.** Nobody objects to a DCF, so it
  survives by not being argued with. Name the operating cash flow, its
  forecastability and the capital requirement, or it is not primary.
- **Never downgrade a correct method because the pipeline cannot compute it.** If
  SOTP, NAV, FCFE or FFO/AFFO is right, mark it PRIMARY with
  `execution_owner: analyst_manual`, list what a human must finish, and accept
  AMBER. Substituting a computable method for the correct one is the exact
  failure this layer exists to prevent.

### 4. Build the artifact

Fill `assets/strategy_decisions_template.json`, then:

```bash
python3 scripts/build_strategy.py --in reports/<T>/strategy_decisions.json \
        --outdir reports/<T>/data/ --md reports/<T>/model_strategy.md \
        --financials reports/<T>/data/financials.json
```

Emits `model_strategy.json` (the contract) and `model_strategy.md` (the page the
analyst approves). It expands each archetype into the concrete driver list
`financial-model-assumptions` must evidence, works out what `financial-model` can
and cannot execute, and runs the gate checks.

Edit `strategy_decisions.json` and rebuild. **Never hand-edit
`model_strategy.json`** — the same discipline as `decisions.json` →
`assumptions.json`.

### 5. The analyst gate — stop here

```bash
python3 scripts/check_strategy.py --in reports/<T>/data/model_strategy.json
```

Modelability is **derived**, never taken from the document, and checks can only
cap it downward:

| | |
|---|---|
| **GREEN** | economics and architecture sufficiently evidenced — proceed on approval |
| **AMBER** | partially understood, unusual, or the correct method is unexecutable here — the analyst resolves each named item |
| **RED** | out of scope, no defensible architecture, or disclosure so thin that proceeding would manufacture precision — **stop the pipeline** |

Present it using `assets/output_template.md`: lead with the classification and
its cause, then the segments, the required drivers, the accepted **and rejected**
methods, and the uncertainties. Force `APPROVE` / `MODIFY` / `REJECT`, record it
in `strategy_decisions.json`, rebuild.

**Nothing downstream runs until this is resolved.** All four consumers call
`check_strategy.gate_ok()`, so the gate is enforced identically in every one.

### 6. After approval — derive the consolidated growth path

Only for a segment or driver build-up. `financial-model` has one revenue row,
`prev(revenue)*(1+rev_growth)`, so the segment mathematics runs here and lands as
a derived growth path rather than being flattened silently.

Fill `assets/segment_values_template.json` with the values
`financial-model-assumptions` evidenced, then:

```bash
python3 scripts/segment_build.py --strategy reports/<T>/data/model_strategy.json \
        --values reports/<T>/data/segment_values.json \
        --outdir reports/<T>/data/ --md reports/<T>/segment_build.md
```

Every driver series starts at the **base year**, so the build must reproduce the
last reported year within 1% of reported segment revenue. Above that it refuses:
an architecture that cannot rebuild the year it can see has no business
forecasting five it cannot. Do not scale the gap away — fix the drivers or change
the architecture.

`segment_build.json` preserves every segment, every intermediate row and every
citation, so the consolidated growth rate can always be walked back to the
segment economics it came from.

### 7. Hand off

All flags are optional and backward-compatible — without them each skill behaves
exactly as before.

```bash
build_assumptions.py --strategy <f> --segment-build <f>   # driver coverage + growth
ingest.py            --strategy <f>                       # capability check, refuses
build_comps.py       --strategy <f>                       # admissible multiples only
model.py             --strategy <f>                       # method roles, one DCF
```

`references/integration.md` has the full schema and the hand-off detail.

## Non-negotiables

1. **Never invent an architecture.** Unmatched → `proposed_archetype` → AMBER →
   analyst sign-off. There is no fuzzy match, on purpose.
2. **Never fabricate a driver or a KPI.** Not disclosed is `Not enough evidence`,
   not a plausible number. A sector's usual KPI is not this company's disclosure.
3. **Never compute a valuation.** Select the method; `model.py` calculates it.
4. **Never force a DCF, and never lead with EBITDA by default.** Both need a
   positive argument for this company.
5. **Never downgrade the correct method to a computable one.** PRIMARY +
   `analyst_manual` + AMBER + explicit manual steps.
6. **Never proceed past the gate.** `PENDING` blocks everything.
7. **Never silently flatten or approximate.** An architecture the pipeline cannot
   execute populates `unsupported_requirements`, goes RED, and is refused.
8. **Stop on banks, NBFCs and insurers.**

## Bundled resources

| File | Use |
|---|---|
| `scripts/archetypes.py` | the closed archetype library; drivers, identities, traps |
| `scripts/valuation.py` | method library, hard disqualifiers, execution owners |
| `scripts/strategy_probe.py` | KB + financials → cited archetype candidates and facts |
| `scripts/build_strategy.py` | decisions → `model_strategy.json` + `.md` |
| `scripts/check_strategy.py` | the gate: derives modelability; `gate_ok()` for consumers |
| `scripts/segment_build.py` | approved segment economics → derived consolidated growth |
| `references/archetypes.md` | choosing between near-neighbour archetypes; granularity |
| `references/valuation-methods.md` | method selection reasoning; the hard cases |
| `references/evidence.md` | where each operating disclosure actually lives |
| `references/integration.md` | contract, schema, gate, downstream flags |
| `assets/strategy_decisions_template.json` | the file the analyst edits |
| `assets/segment_values_template.json` | post-gate values for the segment build |
| `assets/output_template.md` | how to present the gate |
| `tests/test_modeling_strategy.py` | 72 behavioural tests across ten company types |
| `tests/test_integration.py` | 39 end-to-end tests of the four consumers, with and without `--strategy` |

All scripts are standard library only. Run both suites after changing any of
them — the backward-compatibility half matters as much as the new behaviour.

## Tone

Concise, analytical, and willing to say the business is not well enough
understood. An AMBER with three named gaps is a better deliverable than a GREEN
that was reached by not looking. Do not argue with the analyst's modifications —
record them, carry them through, and say once where they make something else
inconsistent.
