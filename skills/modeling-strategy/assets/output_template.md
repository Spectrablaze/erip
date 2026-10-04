# How to present the strategy to the analyst

`build_strategy.py` writes `model_strategy.md`, which is the document the analyst
reads. This file is how to *frame* it in the conversation — what to lead with,
what to force a decision on, and what not to bury.

Present in this order. It is the order of consequence, not the order of the file.

---

## 1. Lead with the modelability classification and what caused it

Not "here is the strategy". Start with:

> **AMBER.** The business decomposes cleanly into two segments with disclosed
> drivers, but the correct primary valuation method is SOTP and nothing in this
> pipeline computes it. The DCF can value the Projects segment; the Products
> stake has to be marked by hand.

GREEN, AMBER and RED are decisions about whether to spend the next four hours,
so they go first. For AMBER, the *specific* cause always travels with the label.

## 2. The business, in the company's own terms

Two or three sentences on how revenue is actually earned, each traceable to the
knowledge base. If this paragraph could describe three companies in the sector,
it has not been written from the filings.

## 3. Segment decomposition, with the archetype and why

One line per segment: share of revenue, archetype, the identity, and the single
piece of evidence that makes the archetype the right one. Then say what was
*considered and rejected* — an EPC business that also sells products is not
"an EPC business", and the reason for splitting or not splitting is the decision
being approved.

Where a segment is on `generic_growth`, say so as a limitation in plain words:
"we cannot build this 22% of revenue from drivers; it is a growth rate."

## 4. The drivers the assumption engine will now have to evidence

Show the required-driver table. This is the concrete consequence of the
architecture, and it is what the analyst is really approving — every one of
these becomes a cited assumption in the next phase, and a driver with no
evidence becomes a `Not enough evidence` entry rather than a number.

Flag any driver you already know the knowledge base does not carry. It is far
cheaper to change the architecture now than to discover the gap mid-assumptions.

## 5. Valuation methods — including the ones being rejected

Both tables, together. The rejected list is the more informative one, and it is
the part most likely to be skipped. Never present the accepted methods alone.

For a PRIMARY method the pipeline cannot compute, state plainly:

> FCFF DCF is not the right lens here. NAV is, and this pipeline does not compute
> a NAV. Marked PRIMARY with `execution_owner: analyst_manual`; the manual steps
> are listed. Modelability is AMBER because of it, and the report's headline
> valuation will not come out of `model.py`.

**Do not** substitute a computable method for the correct one and mention the
correct one in passing. That is the exact failure this layer exists to prevent.

## 6. Uncertainties, each with the thing that would resolve it

An uncertainty with no resolution path is a disclaimer. If it cannot be closed,
say what it means for the model instead.

## 7. Force the decision

Close with the three options, explicitly, and stop:

> **APPROVE** as it stands · **MODIFY** (say what, and I will rebuild) ·
> **REJECT / STOP** (the strategy is not defensible).
>
> Nothing downstream runs until this is recorded — `financial-model-assumptions`,
> `financial-model`, `peer-comps` and `model.py` all check the gate and refuse.

Record the answer in `strategy_decisions.json` under `analyst_decision`, keep the
original recommendation, and rebuild. Never edit `model_strategy.json` by hand.

---

## Tone

The same as the rest of the pipeline: concise, analytical, no advocacy. Two
specific things to avoid.

- **Do not argue the analyst out of a modification.** Record it, carry it
  through, and say once — plainly — where it makes something else inconsistent.
- **Do not soften a RED.** A RED is a refusal to produce false precision, not a
  setback. Say what would have to become true for it to change.
