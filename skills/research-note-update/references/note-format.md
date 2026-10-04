# The 4-page update note — section list and fill rules

The initiating note is 66 blueprint rows across 44–50 pages. This is the cut-down
that follows it. Four pages, fixed order, same house style: `report.css` supplies
the type and grid, `brand.css` the company palette, `assets/update.css` the few
components an update note needs and the initiating note has no equivalent for.

Start from `assets/update-note.html`. It is a placeholder skeleton using
`{{TOKEN}}` markers — and `render.py`'s pre-flight gate **hard-errors on any
unresolved `{{ }}`**, so an unfilled slot cannot reach a PDF. That is deliberate:
leave a token in and the render fails loudly rather than shipping a gap.

Delete slots that do not apply (a note with two "what changed" points deletes
`{{CHANGE_3}}` and `{{CHANGE_4}}`); never leave the token behind, and never fill
one with "N/A".

---

## Page 1 — Cover-lite

**Job:** a reader who stops here still knows the call, the target, the direction
of travel, and why the note exists.

| Block | Content | Rule |
|---|---|---|
| Verdict band | `REITERATE`/`CHANGE`, rating, target, upside | First ink on the page. Add `buy`/`hold`/`sell` to its class by hand — see the note below. |
| Why this note exists | 2–3 sentences | Name the trigger. For an event note, what happened and when. |
| What changed | 2–4 bullets, each number-led | Each opens with the figure that moved. Bold it. |
| What did not change | 1 short paragraph | The load-bearing part of the thesis that survived. Skipping this is how a note becomes a list of news. |
| Rating policy sentence | 1 sentence | Which policy branch produced this rating — see below. |
| Sidebar: Recommendation | rating now/prev, CMP, target old/new/Δ, upside | Straight from `rating.json`. |
| Sidebar: The standing call | opened, CMP then, return since, falsifiers intact, next review | From `standing.json`. |
| Sidebar: Quarter at a glance | revenue, YoY, EBITDA, margin, vs forecast, PAT | From `variance.json`. |
| Sidebar: Calibration | closed calls, mean target error, bias | From `standing.json`'s `closed_call_history`. Print it even when it is unflattering — especially then. |

**The verdict band's colour is a hand edit, not a token.** Change
`class="verdict-band"` to `class="verdict-band hold"` (or `buy`/`sell`).
`render.py`'s pre-flight scans element *text*, not attributes, so a `{{TOKEN}}`
inside `class=""` would be the one placeholder able to slip past the gate — the
template avoids putting one there. Unedited, the band renders in the house brand
colour: neutral, never misleading.

**The policy sentence** is one of these, and it is not optional:

- *Reiterated: no falsifier tripped and every tracked line held inside tolerance, so the rating is unchanged on a thesis that still stands.*
- *Reiterated despite the target band implying {LETTER}: the thesis runs to {HORIZON}, which the price has not yet discounted. Divergence {N} of 3.*
- *Changed to {LETTER}: {thesis reason}, and the re-struck target puts upside at {X}%, inside the {LETTER} band.*

---

## Page 2 — Variance

**Job:** the quarter against what was forecast, and whether the gap is noise or a
revision.

- **The variance table** is `variance.md` converted to HTML — do not retype the
  numbers. Mark breached cells `class="breach"`; mark suppressed weak-evidence
  cells `class="weak"`.
- **State the run-rate method under the heading.** A reader must be able to see
  whether the implied full year came off a seasonal share or a flat ×4.
- **The margin sentence gets its own line under the table**, not a cell inside
  it. From `variance.json`'s `margin` block: quarter margin, forecast FY margin,
  the delta in bps, and whether it breached. This is deliberately prominent —
  on a note with no seasonal share it is the *only* hard evidence the quarter
  gives, because a margin is a ratio struck inside the quarter and needs no
  annualisation. It is also, more often than not, the number that moves the
  rating.
- **What drove the variance** — two paragraphs, mix and price/volume where the
  disclosure supports it. Do not attribute a margin miss to "input costs" unless
  management or the segment data says so.
- **Management's account, and whether it holds.** Their explanation, then yours.
  This paragraph is where an update note earns its keep — anyone can reprint
  guidance.
- **Re-run depth box** — `variance.json`'s `rerun` block, verbatim. It tells the
  reader whether the target on page 1 came from a rebuilt model or a re-struck
  one.
- **Eight-quarter strip** — revenue, EBITDA, margin, PAT across eight quarters.
  This is also where next quarter's seasonal share comes from, so keep it current.

**Chart:** `charts/update_quarterly.svg` — `charts.py bar_line_combo`, revenue
bars with EBITDA margin as the line, eight quarters. No `title=` argument: the
HTML `.fig-title` is the title, and baking one into the SVG prints it twice
(`render.py` warns about this).

---

## Page 3 — Thesis check

**Job:** adjudicate what was written down before the evidence arrived.

- **The standing thesis** reproduced verbatim from `calls.json` in a `.thesis`
  block. Verbatim matters — paraphrasing it is how a thesis quietly becomes
  whatever the quarter supports.
- **Falsifier status table.** One row per logged falsifier. Status is one of:

  | Status | Meaning |
  |---|---|
  | `intact` | The evidence this quarter is consistent with the thesis. |
  | `strained` | Moving the wrong way but not yet through the threshold. Say how much room is left. |
  | `tripped` | The threshold was crossed. This is a thesis reason and forces the rating gate open. |

  Every row needs evidence with a source — a figure and where it came from.
  `unassessed` renders as a hatched warning pill; a note containing one must not
  ship.
- **What changed / what is unchanged** — two columns, business facts not price.
- **Assumptions revised this quarter** — from `decisions.json`'s `revisions`
  array: driver, was, now, why, citation. If nothing was revised, say so in one
  line and delete the table.

---

## Page 4 — Valuation and verdict

**Job:** reconcile the old target to the new one, and leave the next note
something to check.

- **Target price bridge.** The move from old target to new, attributed to named
  drivers. **If it does not reconcile, the target was reverse-engineered from
  the price** — rebuild it or reiterate the old one.
- **Four KPIs:** WACC, TV as % of EV, implied forward P/E, peer median P/E. TV
  above 75% of EV means the target is a bet on terminal assumptions; say so on
  the page.
- **Relative valuation** — the subject, three to five peers, the median, and the
  premium/discount line. Refresh peer prices even on a variance-only note; comps
  go stale in weeks. Use the `peer-comps` skill's output rather than retyping.
- **Verdict** — one paragraph, then the boxed call.
- **What would change my mind** — three falsifiers, each a threshold with a
  number and a horizon, not a worry. These are logged with `kb.py call
  --falsifier` and are exactly what the next note adjudicates on page 3.
- **Next review date** — the `review_on` you are choosing, not a default you
  accepted without thinking.

**Chart:** `charts/update_tp_bridge.svg` — `charts.py waterfall`, old target →
driver contributions → new target.

---

## Style

The initiating note's voice carries over unchanged (`equity-research-report`'s
`reference/research-and-writing.md`), with two additions specific to updates:

- **Lead with the delta.** The reader has the initiating note. Do not re-describe
  the business, the industry or the management. Every sentence that could have
  appeared in the initiating note unchanged is a sentence to cut.
- **Be explicit about being wrong.** If the last note's forecast missed, say by
  how much and why, in the note, not only in the ledger. A four-page note that
  never admits a miss across eight quarters is not being read by anyone who
  checks.

## Length discipline

Four pages is the format, not a target to fill. If page 2 is thin because the
quarter was uneventful, tighten pages 1–2 into a single page and ship three. Do
not pad; `render.py` counts `<section class="page">` blocks and will report the
page count, but it cannot tell padding from substance.

**Expect one warning on every update note.** `render.py`'s gate emits
`only 4 .page sections — the reference reports run 32-45 pages`. That check was
written for initiating notes. It is a warning, not an error, it does not block
the render, and on an update note it is correct to ignore. Do not add pages to
silence it, and do not pass `--force` — nothing is being forced.
