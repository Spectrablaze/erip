# How to present the model

Follow this order. It puts the things that could invalidate the model before the
things that make it look impressive.

---

## 1. What was built, in four lines

> **{Company}** — three-statement model, {currency}.
> History {first} to {last} ({n} years) from {Screener export / annual report}.
> Forecast {first} to {last} ({n} years).
> Files: `model.xlsx` (live formulas), `model.json` (solved), `model_review.md`.

Then, once, the sentence that saves an afternoon later:

> Edits made by hand in Excel are lost on the next build. Change `overrides.json`
> and rebuild.

## 2. The checks — before anything else

State the blocking result plainly, and do not dress it up.

> All 9 blocking checks pass. The balance sheet ties to within {x} in every
> forecast year, and the circular solve converged in {n} passes.

If any blocking check failed, stop here. Report the check, what it means from
`references/checks.md`, and what you are going to do about it. Do not present
projections from a model that does not tie.

Then the advisory flags, each in one line — what fired, and whether it is a
finding or a known feature of the data:

> - Reserves roll (history): ₹{x} cr unexplained in {year}. The statement of
>   changes in equity shows {a buyback / OCI / a share issue}; not a modelling error.
> - Reconstructed CFO runs {x}% below reported CFO across the last three years.
>   {Explain, or say it is unexplained.}

## 3. Where the numbers came from

A short table, because the mix of sources determines how much weight the model
carries.

| | Source |
|---|---|
| Historical spine | Screener export, {n} years |
| Filled from the annual report | {payables (p. 198), capex (p. 176), ...} |
| Forecast drivers set from evidence | {n} of 21, via `financial-model-assumptions` |
| Forecast drivers held at the {n}y historical average | {list them} |

**Name the defaults.** A driver held at its historical average is a decision
that nobody made deliberately, and the user should get the chance to make it.

## 4. Drivers: history against forecast

Reproduce the driver table from `model_review.md`. Mark the ones that step
outside their own historical range and give the reason for each in one line:

> - Revenue growth 11.0% falling to 8.5%, against 8.8–11.6% historically —
>   management guided to low double digits (AR p. 43).
> - EBITDA margin 18.5% against a flat 18.0% history — {reason}. If there is no
>   reason, say so: this one is not supported by the documents.

## 5. What the model produces

The output table: revenue and growth, EBITDA and margin, EBIT, PAT, EPS, FCFF
and conversion, cash, debt, net debt, net debt/EBITDA, interest cover, ROCE,
ROE. Three historical years for context, then the forecast.

Then two or three sentences of what it actually says — not a restatement of the
numbers:

> The company funds its own capex from operating cash from {year} and the
> revolver is never drawn. Net debt turns negative in {year} and the cash pile
> reaches ₹{x} cr by {year}, which the model earns nothing on — if you want
> treasury income, set `interest_income_rate` and cut `other_income_pct` to match.

Say it if the model does **not** fund itself:

> The revolver is drawn from {year} and reaches ₹{x} cr by {year}. At this capex
> and this payout the plan requires external funding; that is a result, not a
> defect.

## 6. What would change the answer

Two or three drivers, with the direction and the rough size. Not a sensitivity
grid — this skill does not value the company — just the honest list of what the
model is most exposed to.

## 7. What to do next

> - Change a driver: edit `overrides.drivers` in `overrides.json`, re-run
>   `ingest.py` then `build_model.py`.
> - Improve the evidence: {the specific document that would resolve the weakest
>   driver}.
> - Value it: `model.json`'s `bridge` block feeds
>   `equity-research-report/scripts/model.py`.

---

## Tone

Plain and short. No adjectives on the numbers. If a driver is not supported by
the documents, say "not supported by the documents" rather than "conservative".
The user is going to defend this model to someone; give them the weak points
before someone else finds them.
