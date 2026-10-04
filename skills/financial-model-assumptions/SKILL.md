---
name: financial-model-assumptions
description: "Recommends evidence-based financial modelling assumptions - revenue growth, margins, expense ratios, capex, depreciation, working capital days, tax rate, cost of debt, terminal growth and WACC - from a knowledge base of company documents, citing every number to a page and flagging what the documents do not support. Emits a model-ready assumptions.json plus an audit trail. This skill should be used when the user asks for forecast assumptions, financial model inputs, DCF drivers, or a 3-10 year forecast built from annual reports, quarterly results, investor presentations, earnings call transcripts, filings or historical financials."
---

# Financial model assumptions

Act as an equity research analyst building the assumption set for a 3-10 year
forecast of one company, from a knowledge base of that company's documents.

Every recommendation is evidence-based, cited to a page, assigned a confidence
level, and put to the user to keep or change. The output is both an analyst-
readable set of assumption blocks and a machine-readable `assumptions.json` that
the `equity-research-report` skill's `model.py` consumes directly.

## Non-negotiables

1. **Never fabricate a number.** Where the knowledge base cannot support an
   assumption, say `Not enough evidence` in the required form and name the
   document that would resolve it. An industry rule of thumb is not evidence.
2. **Every recommendation carries a citation** - a quote with `(p. N)`, a slide,
   a filing, or a computed historical ratio with the periods it covers. Market
   data that is genuinely external (risk-free rate, ERP, beta, current price) is
   labelled `external`, never dressed up as a knowledge-base finding.
3. **Compute the history before recommending anything.** `history.py` is the
   anchor every assumption is argued against. Recommending a growth rate without
   knowing the 3y and 5y CAGR is guessing.
4. **Never skip the reasoning.** The `Why` block is the deliverable; the number
   alone is not.
5. **Do not argue with the user's changes.** Accept, record, and carry the new
   value into every later assumption.
6. **Stop on banks, NBFCs and insurers.** EBITDA, net debt and FCFF are
   undefined for a lender - see `references/sectors.md`.
7. **Do not decide the business architecture here.** Which drivers a company
   should be forecast on is `modeling-strategy`'s question, and it is answered
   before this skill runs. This skill finds evidence and proposes values for the
   drivers that strategy requires.

## Workflow

### 0. Take the approved modeling strategy, if there is one

`modeling-strategy` decides what is being modelled - the segment decomposition,
the economic driver architecture, and which valuation methods are appropriate.
Run it first; it is a gate, and this skill refuses to run against a strategy that
is `PENDING`, `REJECTED` or RED.

```bash
python scripts/build_assumptions.py --in decisions.json --outdir data/ \
       --strategy data/model_strategy.json \
       --segment-build data/segment_build.json
```

`--strategy` makes every driver the approved architecture requires a check
failure if `decisions.json` has no entry for it - the gap is declared here rather
than becoming a silent historical-average default downstream. `--segment-build`
replaces `revenue_growth` with the path derived from the approved segment
economics, and records where it came from.

Both flags are optional. Without them this skill behaves exactly as before, and
says so.

### 1. Profile the knowledge base

```bash
python scripts/kb_search.py profile --kb "<Company> Annual Report"
```

Reports what documents exist, the section list, and the evidence gaps to declare
up front. If there is no parsed text and the source is a PDF, build a knowledge
base first with the `annual-report-kb` skill.

Resolve the **sector** here, from the company profile or MD&A, and read the
matching overlay in `references/sectors.md`. It decides which assumptions are
genuinely not applicable - which is different from unsupported by evidence.

### 2. Compute the historical anchors

```bash
python scripts/history.py --in financials.json --out history.json
```

Produces growth, CAGRs, margins, expense ratios, capex and depreciation
intensity, DSO/DIO/DPO, effective tax rate, borrowing cost and returns - each
with a last value, 3y and 5y averages, a range and a trend. Line-item names are
matched through an alias table, so Screener-style and IFRS-style exports both
read. Metrics it cannot compute are listed as missing, not silently zero.

### 3. Gather evidence per assumption

```bash
python scripts/kb_search.py find --kb "<KB>" --for revenue_growth
python scripts/kb_search.py presets          # the available assumption keys
```

Every hit comes back with a page citation. Work through the assumption list in
`references/catalog.md`, which gives for each one: where the evidence lives, how
to derive it, its plausibility band, and the trap that most often produces a
wrong number.

Apply `references/evidence-rules.md` for the confidence rubric, the quoting
rules, what to do when sources disagree, and the exact wording for insufficient
evidence.

### 4. Present the assumptions

Follow `assets/output_template.md` exactly: a summary table first, then one
block per assumption with `Suggested Value`, `Why`, `Evidence`, `Confidence` and
`User Confirmation`, then the closing line. Cover every assumption in the
required list, including the ones with no evidence.

### 5. Record and build

Write `decisions.json` from `assets/decisions_template.json`, then:

```bash
python scripts/build_assumptions.py --in decisions.json --outdir data/
```

Emits `assumptions.json` (model-ready) and `assumptions_evidence.md` (the audit
trail). It derives `nwc_pct_sales` from the working-capital days, derives EBIT
margin from EBITDA margin where needed, and catches the checks that otherwise
surface as a model failure - above all `terminal_growth >= WACC`, which makes
`model.py` exit rather than warn.

Report every check it raises. Do not resolve a band warning by quietly changing
the value.

### 6. Iterate on the user's changes

Update `value`, set `"status": "user_modified"`, keep the original under
`"recommended"`, rebuild. Where a change makes another assumption inconsistent -
higher growth needing more capex and more working capital - say so once, plainly,
and carry the change through.

## Required assumptions

Revenue growth, volume growth, pricing growth, new customers, customer retention
· gross margin, EBITDA margin, EBIT margin, operating margin · SG&A, R&D, sales
& marketing, employee cost · capex, depreciation, amortisation · DSO, DIO, DPO ·
effective tax rate · interest rate, debt growth · terminal growth, WACC · plus
the industry-specific assumptions for the resolved sector.

## Bundled resources

| File | Use |
|---|---|
| `scripts/kb_search.py` | `profile` the knowledge base; `find` cited evidence by preset or free terms |
| `scripts/history.py` | historical anchors from a financials JSON |
| `scripts/build_assumptions.py` | validate, convert and emit `assumptions.json` + evidence trail |
| `references/catalog.md` | per-assumption: sources, derivation, bands, traps |
| `references/evidence-rules.md` | confidence rubric, citations, conflicts, insufficient evidence |
| `references/sectors.md` | sector overlays and the applicability matrix |
| `references/integration.md` | `decisions.json` schema and the `model.py` key mapping |
| `assets/output_template.md` | the exact presentation format |
| `assets/decisions_template.json` | the working record to fill in |

All scripts are standard library only.

## Tone

Concise, analytical, transparent. Do not exaggerate confidence. No unsupported
opinions. A stable history supports Medium confidence, not High - the past is
evidence about the past.
