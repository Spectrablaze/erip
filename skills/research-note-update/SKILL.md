---
name: research-note-update
description: Write the short quarterly or event-driven update note that follows an initiating coverage report on a listed Indian company - a 4-page PDF in the same house style, a revised decisions.json, and a scored call written back to the calibration ledger. It pulls the standing rating, target and falsifiers, checks whether any falsifier has tripped, runs the quarter's actuals against the standing forecast as a variance table, decides whether the model needs a full re-forecast or only a re-strike, applies the house rating policy, and closes or re-opens the call in kb.py. This skill should be used when the user asks for an update note, a results update, a quarterly review of a covered stock, to check or close a standing call or target, to score past calls, to react to a company event on a name already covered, or says a review date has passed.
---

# Research note — update

## Orient

An initiating coverage note is 44–50 pages and answers "what is this company
worth?". This is the note that follows it, and it answers a narrower question:
**what changed, and is the call still right?**

Four pages. The knowledge base, the model, the assumptions and the comps already
exist — this computes a delta against them, which is why it is cheap per note.

The part that matters most is the last one. `kb.py` maintains a calibration
ledger of every published call, and it only pays off if calls actually get
followed and closed. Targets that sit open forever and `review_on` dates that
pass unnoticed produce no mean-error signal and no learning. **This skill is what
drives that loop.** A note that ships without touching the ledger correctly has
done the smaller half of the job.

**Prerequisite:** an open call on this ticker in `reports/_knowledge/calls.json`.
Without one there is nothing to update — run `equity-research-report` first. An
update note computes a delta; it cannot create a thesis.

## Read first

- `references/policy.md` — triggers, the rating policy, tolerances, ledger
  rules. **The judgement layer. Read it before Phase 5, every time.**
- `references/note-format.md` — the 4-page section list and what belongs where.
- `references/integration.md` — paths, the two different `model.json` files, and
  the exact command signatures (several differ from what looks natural).

## Scripts

| Script | Does |
|---|---|
| `scripts/standing.py` | Pulls the standing call, forecast and falsifier checklist into `standing.json`. Exits 2 if there is no open call. |
| `scripts/variance.py` | Quarter vs standing forecast → `variance.json` + `variance.md`, tolerance breaches, and the re-run depth verdict. |
| `scripts/rating.py` | Applies the house rating policy and prints the reason chain. Exits 1 when the divergence limit blocks the note. |
| `scripts/revise.py` | Patches `decisions.json` with an audited, cited revision and prints the exact rebuild chain. |

---

## How this runs — eight gated phases

Do not skip forward. Each phase writes a file the next one reads, and the gates
are where the note's honesty lives.

---

## Phase 0 — Recall and pull the standing position

```bash
ERR=<equity-research-report skill>
python3 $ERR/scripts/kb.py brief --ticker <T> --sector <sector>
python3 <this skill>/scripts/standing.py --ticker <T> --asof <YYYY-MM-DD> \
        --trigger quarterly_results --trigger-note "Q1FY27 results, 24 Jul 2026"
```

`kb.py brief` reports the whole book: due reviews, macro staleness, calibration.
`standing.py` narrows to this name and writes
`reports/<T>/updates/<date>/standing.json`.

**Read what it prints, do not skim it:**

- **`** REVIEW DUE **`** — this note is now obliged to close the call in Phase 7,
  whatever else it concludes.
- **The falsifiers.** These were written before the evidence arrived. They are
  the most valuable thing in the file, and every one gets adjudicated in Phase 3.
- **`CALIBRATION on <T>`** — the mean target error on this name. Carry it into
  the new target in Phase 5 explicitly.
- **`not in this model:`** — lines the standing forecast cannot support. Without
  the three-statement model the variance table is two lines and the EBITDA-margin
  check is impossible. Build it before continuing, or write the note knowing it.

**Gate:** exit 2 means no open call. Stop — this is initiating coverage, not an
update.

---

## Phase 1 — Confirm the trigger

Check the trigger against `references/policy.md` §1 before doing the work.

Quarterly results are the standing cadence. Event triggers — management change,
large capex or M&A, regulatory action, a guidance change, a tripped falsifier, a
passed review date — are equally valid and are dated and scored the same way.

**A price move is never a trigger on its own.** If the only new fact is that the
share price moved, there is no note to write. Say so and stop.

---

## Phase 2 — Actuals in, variance out

Write `reports/<T>/updates/<date>/actuals.json` from the results release. The
schema is in `variance.py`'s docstring; only `period`, `quarters_elapsed` and
`actual` are required.

**Get the seasonality block right — it is the difference between a real variance
and a misleading one:**

```json
"seasonality": {"q_share_of_fy": 0.226, "basis": "mean Q1 share FY22-FY26"}
```

Compute the share from the eight-quarter strip. Without it the script falls back
to flat ×4, marks every level line `(weak)`, and **suppresses all tolerance
breaches on those lines** — because a naive ×4 is not evidence strong enough to
move a rating. The EBITDA-margin check still counts, since a margin is a ratio
struck inside the quarter and needs no annualisation.

Units must match the model (Screener exports and the models are all INR cr).

```bash
python3 <this skill>/scripts/variance.py \
        --standing reports/<T>/updates/<date>/standing.json \
        --actuals  reports/<T>/updates/<date>/actuals.json
```

**Gate:** read `rerun.full_rerun_required`. It decides Phase 4.

---

## Phase 3 — Adjudicate every falsifier

Write `falsifiers.json` — one entry per falsifier from `standing.json`, each with
a status and **evidence with a source**:

```json
{"falsifiers": [
  {"text": "EBITDA margin below 21% for two consecutive quarters",
   "status": "intact",
   "evidence": "Q1FY27 margin 21.9%, Q4FY26 23.4% — one quarter below trend, not two"}
]}
```

Status is `intact`, `strained` (moving the wrong way, threshold not crossed — say
how much room is left) or `tripped` (crossed; this is a thesis reason).

This is judgement, not computation — no script can read a free-text falsifier
against a results release. It is also the phase most worth doing slowly. A
falsifier waved through as `intact` because the conclusion is already decided is
the failure mode this whole design exists to prevent.

**Gate:** no falsifier may remain `unassessed`. `rating.py` will warn, and a note
containing one must not ship.

---

## Phase 4 — Re-run the model to the depth the variance demands

**Variance-only** (`full_rerun_required: false`) — do not rebuild. Re-strike the
standing model against the current price and move on. Still refresh the comps:
they go stale in weeks even when nothing else does.

**Full re-forecast** (`full_rerun_required: true`) — a tolerance breached, it is
Q4/full-year, or the review date passed. Revise the drivers the evidence
actually moved:

```bash
python3 <this skill>/scripts/revise.py --report-dir reports/<T> --note-date <date> \
    --trigger quarterly_results \
    --set ebitda_margin=22.8 \
    --why ebitda_margin="Q1 margin 21.9% on input costs; guidance trimmed to 22-23%" \
    --evidence ebitda_margin="Q1FY27 results, 24 Jul 2026, p.4" \
    --confidence ebitda_margin=Medium
```

`revise.py` refuses an unsourced revision, refuses a driver the standing model
does not have, revises year 1 of a series by default, records the change in
`decisions.json`'s `revisions` array, and prints the exact rebuild chain for the
steps it made stale. Run that chain, then **re-run `standing.py`** so the note
scores against the rebuilt forecast.

Read the FCFF cross-check gap on the final `model.py` run. Above ~15% the drivers
no longer fund the balance sheet they imply — fix the drivers, never split the
difference.

---

## Phase 5 — Strike the rating

Read `references/policy.md` §2 before this step.

```bash
python3 <this skill>/scripts/rating.py \
        --standing reports/<T>/updates/<date>/standing.json \
        --variance reports/<T>/updates/<date>/variance.json \
        --falsifiers reports/<T>/updates/<date>/falsifiers.json \
        --new-target 5200 --cmp 4920
```

The policy in one line: **a rating change requires a thesis reason — a tripped
falsifier, a tolerance breach, or an explicit analyst reason naming a change in
the business — and given one, the letter falls out of the upside bands
mechanically.** Without a reason the note reiterates; price drift alone moves the
upside line and nothing else.

Before passing `--new-target`, apply the calibration from Phase 0. A persistent
positive mean error means the targets have run below outcomes — the DCF is too
conservative, so check terminal growth and exit margins. Say in the note that you
did this.

**Gate — exit 1 is a block, not a warning.** Three consecutive notes reiterating
against a band that disagrees means the rating has become unfalsifiable. Resolve
it by naming a thesis reason and re-rating, closing the call as wrong, or
re-striking the target on a stated model change. Do not work around it.

---

## Phase 6 — Write and render

Copy `assets/update-note.html` and `assets/update.css` into
`reports/<T>/updates/<date>/`, alongside `report.css` and the company
`brand.css`. Fill it per `references/note-format.md`.

The four pages: cover-lite (the call and what changed) · variance (the quarter
against forecast) · thesis check (falsifier adjudication and revisions) ·
valuation and verdict (the target bridge, comps, and the new falsifiers).

Charts via `$ERR/scripts/charts.py` — `bar_line_combo` for the quarterly strip,
`waterfall` for the target bridge. Pass no `title=`: the HTML `.fig-title` is the
title, and a baked-in SVG title prints it twice.

```bash
python3 $ERR/scripts/render.py reports/<T>/updates/<date>/note.html --check-only
python3 $ERR/scripts/render.py reports/<T>/updates/<date>/note.html \
        -o "reports/<T>/updates/<date>/<Company> - Update <Period>.pdf"
```

The gate hard-errors on unresolved `{{TOKEN}}` placeholders, missing images and
leftover TODOs — an unfilled slot cannot reach a PDF. Fix findings rather than
passing `--force`.

**Two things the note must contain, and usually would rather not:**

- **The target bridge must reconcile.** If the move from old target to new cannot
  be attributed to named drivers, it was reverse-engineered from the price.
  Rebuild it or reiterate the old target.
- **If the last forecast missed, say so in the note** — by how much and why — not
  only in the ledger.

---

## Phase 7 — Write back to the ledger

**This is the phase that makes the calibration loop real. Do not stop at the PDF.**

`calls.json` records calls, not notes. A reiteration is not a new call.

| Situation | Action |
|---|---|
| Reiterate, review not yet due | **Touch nothing.** The standing call stays open with its original target and horizon — that is what keeps the score honest. |
| Rating changed, or target re-struck | `kb.py close` with the current price and a note saying it was superseded, then `kb.py call` to open the new one. |
| `review_on` has passed | `kb.py close` with the current price, whatever the note concludes. Re-open only if there is a live view. |
| Dropping coverage | `kb.py close`, and do not re-open. |

```bash
python3 $ERR/scripts/kb.py close --ticker <T> --actual 4920 \
        --note "superseded by update note <date>; margin miss took FY27 EBITDA below plan"

python3 $ERR/scripts/kb.py call --ticker <T> --rating HOLD --target 5200 --cmp 4920 \
        --thesis "..." --review-months 6 \
        --falsifier "EBITDA margin below 21.5% for two consecutive quarters" \
        --falsifier "Capex above 8% of sales without a volume commitment" \
        --falsifier "Market share below 28%"
```

**Every re-opened call carries falsifiers** — three is a good number, each a
threshold with a number and a horizon, not a worry. A call logged without them is
one the next note cannot check, and the loop degrades into narrating the price.

**Choose `--review-months` deliberately.** It is the horizon you will be scored
over: 3 for a name mid-capex where the quarters decide something, 12 for a slow
structural thesis.

Then log what the note taught, if anything:

```bash
python3 $ERR/scripts/kb.py lesson --tag update \
        --text "Q1 margin miss was input-cost timing, not mix — the standing thesis
                over-weighted premiumisation in the near term"
python3 $ERR/scripts/kb.py review
```

Run `kb.py review` last and read it. It is the whole point of the exercise.
