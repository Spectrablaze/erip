# House policy — triggers, ratings, tolerances, and the ledger

This is the judgement layer. The scripts enforce the mechanical half; this file
carries the reasoning, and it is what to re-read when a note feels like it wants
an exception. Exceptions are allowed. Unrecorded exceptions are not.

---

## 1. What triggers an update note

Two standing triggers.

**Quarterly results — the cadence.** One note per reported quarter, written from
the results release and the concall. This is the note that keeps the forecast
honest and the calibration ledger accumulating.

**Events — between quarters.** An event note is warranted when something occurs
that a reader holding the standing call would want to hear about before the next
quarter. In practice:

| Event | Write a note when |
|---|---|
| Management change | MD/CEO/CFO departs, or a promoter-family succession is announced. A divisional head leaving is not a note. |
| Large capex or M&A | Announced capex above ~15% of the standing capex plan, or any acquisition above ~5% of market cap. |
| Regulatory action | A ruling, tax change, tariff, ban or licence decision that touches a line in the model. A show-cause notice is not yet a note; a penalty is. |
| Guidance change | Management revises volume, margin or capex guidance outside the standing assumption. |
| Falsifier trip | Any logged falsifier trips on evidence, at any time. This one is mandatory — a tripped falsifier that waits for the quarter defeats the point of logging it. |
| Review date passed | `review_on` has elapsed. Mandatory. Close the call, then decide whether to re-open. |

A price move is **never** a trigger on its own. If the only new fact is that the
share price moved, there is no note to write — the upside line changes and the
thesis does not.

**When the trigger is ambiguous, write the note.** The cost of an unnecessary
2-page note is small; the cost of a silent quarter is that the ledger stops
telling the truth about how the calls are doing.

---

## 2. The rating policy: falsifier gates, band sets the letter

Encoded in `scripts/rating.py`. Stated plainly:

### A rating change requires a thesis reason

There are exactly three admissible reasons, and `rating.py` will not change a
rating without one:

1. **A logged falsifier tripped.** The strongest reason, because it was written
   down before the evidence arrived.
2. **A tracked line breached tolerance** in `variance.py` — the business is
   running outside the band the forecast assumed.
3. **An explicit analyst reason**, passed as `--thesis-reason`. It must name a
   change in the business. "The stock has run" is not a thesis reason. "Capacity
   commissioning slipped two quarters, so the FY28 volume ramp moves out" is.

### Given a reason, the letter is mechanical

Upside to the re-struck target, against the current price:

| Upside | Rating |
|---|---|
| above **+15%** | BUY |
| **−10%** to **+15%** | HOLD |
| below **−10%** | SELL |

Override per company with a top-level `rating_bands` block in `decisions.json`
(`{"buy_above": 20.0, "sell_below": -5.0}`). Override it for a *reason* — a
high-beta name deserves a wider band — and record the reason in the note.

The letter being mechanical is the point. It stops the rating from being argued
into place after the target has been struck.

### Without a reason, reiterate

Price drift alone changes the upside line and nothing else. A BUY whose upside
has compressed from 22% to 6% because the market repriced it is **still a BUY**
until something in the business changes or the target is re-struck on evidence.

### The divergence rule — why the above is not a licence to never downgrade

Reiterating has an obvious abuse: hold BUY forever, never be wrong, never learn
anything. So every time the band letter disagrees with the reiterated rating,
the note records a **divergence**, and `rating.py` counts consecutive ones.

- **One divergence is legitimate.** The thesis has a horizon the price has not
  run yet. Say so in the note, in one sentence, and name the horizon.
- **Three consecutive divergences blocks the note** (`rating.py` exits 1). At
  that point the position is that the market has disagreed for three quarters
  and the thesis has produced no reason to change. That is not conviction, it is
  an unfalsifiable rating. Resolve it one of three ways:
  1. name a thesis reason and re-rate;
  2. close the call as wrong (`kb.py close`), and re-initiate if the name still
     deserves coverage;
  3. re-strike the target so band and rating agree — and say in the note what in
     the model changed to justify it. If nothing changed, this option is not open.

Tune the limit by editing `DIVERGENCE_LIMIT` in `rating.py`; do not work around
it per note.

---

## 3. Re-run depth: variance-first, full re-forecast on trigger

The default is a **variance check against the standing model**. Annualise the
quarter, compare to the forecast row, table it. The model is not rebuilt.

Escalate to a **full re-forecast** when any of these hold — `variance.py`
decides this and writes it into `variance.json` under `rerun`:

- any tracked line breached tolerance;
- it is Q4 or full-year results — the base year is now history, so the whole
  curve must be re-struck;
- the standing call is past its `review_on`;
- a falsifier tripped (pass it in yourself: `variance.py` cannot read a
  falsifier adjudication that has not been written yet).

### Default tolerances

| Check | Tolerance |
|---|---|
| Implied FY revenue vs forecast | ±5% |
| Implied FY EBITDA / EBIT / PAT / EPS | ±10% |
| EBITDA margin, quarter vs forecast FY | ±150 bps |

Override with a top-level `tolerances` block in `decisions.json`. Widen them for
a genuinely lumpy business — project revenue, a commodity, an order-book name —
and record why in the note. Tolerances tightened to make a note escalate, or
loosened to make it not, are a way of lying to the ledger.

### The seasonality trap

Annualising one quarter by ×4 is wrong for most Indian names. `variance.py`
handles it like this:

- Supply `seasonality.q_share_of_fy` in `actuals.json` — this quarter's
  historical share of full-year revenue, from the eight-quarter strip — and the
  run-rate is grossed up on that share.
- Without it, the script falls back to flat ×4, marks every level line
  `(weak)`, and **suppresses all tolerance breaches on those lines**. A naive ×4
  is not evidence strong enough to move a rating.
- The **EBITDA margin check still counts** in that case, because a margin is a
  ratio struck inside the quarter and needs no annualisation at all. When there
  is no seasonal share, the margin is the only hard evidence the quarter gives.

Compute the share from the strip — mean share of that quarter over the last
three to five years — and record the basis in `seasonality.basis`.

---

## 4. Ledger rules — what touches `calls.json` and when

`reports/_knowledge/calls.json` is the calibration ledger. It is scored, so what
goes into it must mean one thing consistently.

**One rule: `calls.json` records calls, not notes.** A reiteration is not a new
call. The note history lives in `reports/<T>/updates/`.

| Situation | Action |
|---|---|
| Reiterate, review not yet due | **Do not touch `calls.json`.** The standing call stays open, with its original target and its original `review_on`. This is what keeps the score honest: you are graded on the target you set, over the horizon you set. |
| Rating changed, or target re-struck | `kb.py close` the standing call with the current price as `--actual` and a note saying it was superseded, then `kb.py call` to open the new one. The old target gets scored at the point you abandoned it. |
| `review_on` has passed | `kb.py close` with the current price, regardless of what the note concludes. Then open a new call only if the note actually has a live view. |
| Dropping coverage | `kb.py close`, and do not re-open. |

**Every re-opened call must carry falsifiers.** `kb.py call --falsifier` is
repeatable; three is a good number. A call logged without falsifiers is a call
the next update note cannot check, and the whole loop degrades into narrating
the share price.

**`--review-months` sets the next horizon.** Default 6. Use 3 for a name in the
middle of a capex or turnaround where the quarters actually decide something,
12 for a slow structural thesis. Choose it deliberately: it is the horizon you
will be scored over.

**Read the calibration before striking the target.** `standing.py` prints the
mean target error on this name, and `kb.py review` prints it across the book. A
persistent positive mean means the targets have run below outcomes — the DCF is
too conservative, so check terminal growth and exit margins. A persistent
negative mean is the opposite. Carry that number into the new target explicitly
and say in the note that you did. Calibration you look at and do not act on is
decoration.

---

## 5. Revising assumptions

Edit `decisions.json`, never `assumptions.json` — the latter is generated and a
rebuild destroys hand edits. Use `scripts/revise.py`, which enforces the parts
that are easy to get wrong:

- **Every revised driver needs a citation** (`--evidence`). An unsourced
  revision is the mechanism by which a forecast quietly drifts to fit the share
  price, and it is the single most common way a research process rots.
- **A per-year series is revised in year 1 by default**, holding the rest of the
  curve. One quarter is evidence about this year; it is rarely evidence about
  FY30. Pass `--whole-series` only when the change is genuinely structural, and
  justify it in the note.
- **New drivers are not an update.** Introducing a driver the standing model did
  not have is a re-initiation — go back through `financial-model-assumptions`.
- Revisions are appended to a top-level `revisions` array with from/to values,
  reason and citation. That array is what page 3's revision table prints, and
  what the next note reads to see what this one moved.

---

## 6. When the note should not ship

Stop and resolve, rather than writing around it:

- **A falsifier is still `unassessed`.** Every one gets adjudicated with
  evidence, or the thesis check on page 3 is theatre.
- **`rating.py` exited 1** on the divergence limit. See §2.
- **The variance table has no forecast to compare against** — the model was
  never built, or was built into the wrong directory. Fix the model.
- **A full re-forecast was triggered but not run.** Shipping a variance-only
  note when the trigger says re-forecast means the target on page 1 came from a
  model that the quarter has already contradicted.
- **The target moved but the bridge does not reconcile.** If the move from old
  target to new cannot be attributed to named drivers, the target was reverse-
  engineered from the price. Rebuild it or reiterate the old one.
