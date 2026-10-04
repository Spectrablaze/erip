# Evidence, confidence and conflict rules

## What counts as evidence

Only material that is in the knowledge base, cited to a locatable place:

| Type | Cite as |
|---|---|
| Annual report / MD&A | quote + `(p. N)` + the KB file it came from |
| Earnings call | quote + speaker + quarter |
| Investor presentation | slide title or number |
| Regulatory filing | filing type + date |
| Industry report | publisher + the specific figure |
| Historical financials | the computed ratio and the periods it covers |

Market data that is genuinely not in the knowledge base - risk-free rate, equity
risk premium, beta, current price - is marked `"source": "external"` in the
evidence field. Labelling it external is not a weakness; presenting it as a
knowledge-base finding is a fabrication.

## Quoting

Quote the shortest span that carries the claim, verbatim. Never paraphrase into
quotation marks, and never merge two sentences from different pages into one
quote. If the source states a range, carry the range through - "26-27%" does not
become "27%" without a stated reason for picking the top.

Page numbers cited to the reader are 1-based. `kb_search.py` already converts
from the 0-based filenames the knowledge base uses.

## Confidence rubric

| Level | Requires |
|---|---|
| **High** | Explicit management guidance or a disclosed contracted fact, **and** a consistent 3-5 year history. The two agree. |
| **Medium** | One of the two: guidance without a supporting history, or a stable history without forward guidance. |
| **Low** | Indirect inference, a single data point, an external estimate, or sources that disagree materially. |

Do not report High confidence on any assumption whose only support is the
historical average. A stable history is Medium - the past is evidence about the
past.

An assumption resting on external market data is capped at Medium.

## When sources disagree

Do not average them silently. Write out:

1. What each source says, with its citation.
2. Why they differ - different period, different scope (standalone vs
   consolidated), guidance issued before an event, segment vs company level.
3. Which one is recommended and on what basis.
4. The confidence, lowered to reflect the disagreement.

The most common causes of apparent conflict, worth checking before calling it a
conflict at all: standalone vs consolidated figures; reported vs
like-for-like growth; a restated prior year; the deck quoting a segment while
the P&L reports the total.

## Insufficient evidence

When the knowledge base cannot support an assumption, use exactly this form and
do not substitute an industry rule of thumb:

```
### Suggested Value
Not enough evidence

### Why
The knowledge base does not contain sufficient information to estimate this
assumption reliably. [State precisely what is missing and which document would
carry it.]

### Confidence
Low

### User Confirmation
Would you like to enter this assumption manually?
```

Record it in `decisions.json` with `"status": "insufficient"` so it stays
visible in the audit trail rather than disappearing.

Naming the document that would resolve the gap is what makes this useful - "no
volume disclosure; the quarterly investor presentation would carry it" is
actionable, "not enough evidence" alone is not.

## Handling the user's changes

1. Accept the new value without argument.
2. Record it with `"status": "user_modified"` and keep the original under
   `"recommended"` so the audit trail shows both.
3. Use it in every downstream assumption from that point on - a raised revenue
   growth changes the capex needed to support it and the working capital
   absorbed by it. State that linkage rather than leaving the model inconsistent.
4. If it is materially outside the evidence, note the implication once, plainly,
   and move on:

   > The knowledge base supports 18%; at 25% the model implies capacity above
   > the disclosed nameplate by FY29. I'll use 25% and flag the capacity
   > constraint in the capex assumption.

Never re-litigate a value the user has already set.

## Standing rules

- Every recommendation carries evidence or is marked insufficient. There is no
  third category.
- Prefer a range where the evidence gives a range; pick the point estimate
  inside it and say why that point.
- Conservative means "defensible from the evidence", not "the lowest number".
  Understating growth to look prudent is as much an error as overstating it.
- State the units and the basis every time: percent of sales, days on COGS,
  consolidated, in the reporting currency.
- A forecast year is only as good as its base. Confirm the base year is not
  itself abnormal before anchoring anything to it.
