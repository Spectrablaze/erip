# Contract, artifacts and the gate

## Position in the pipeline

```
PDFs ──annual-report-kb──► kb/                                          Phase 2
Screener ──parse_screener.py──► data/financials.json                    Phase 3a
                    │
                    ▼
              THIS SKILL              strategy_probe → strategy_decisions.json
                    │                 → build_strategy → check_strategy
                    ▼
   data/model_strategy.json  +  model_strategy.md                       Phase 3b
                    │
        ═══════ ANALYST APPROVAL GATE ═══════
                    │
    ┌───────────────┼────────────────┬──────────────────┐
    ▼               ▼                ▼                  ▼
financial-model  peer-comps    financial-model      model.py
-assumptions     (multiple      (capability          (method roles,
(driver coverage) filter)        check, refuses)      one DCF)         Phase 3c–3f
    │
    └─► segment_build.py ─► segment_build.json → derived revenue_growth
```

`modeling-strategy` decides **what** is modelled.
`financial-model-assumptions` decides **what values**.
`financial-model` does the arithmetic. `model.py` does the valuation.

Nothing in this skill computes a valuation. That is not a style preference — the
pipeline's one-DCF property is what makes its numbers reconcilable, and a second
discounting site anywhere would destroy it.

## Artifacts

| File | Written by | Consumed by |
|---|---|---|
| `strategy_decisions.json` | the analyst (with Claude) | `build_strategy.py` |
| `data/model_strategy.json` | `build_strategy.py` | all four downstream skills |
| `model_strategy.md` | `build_strategy.py` | the analyst, at the gate |
| `data/segment_values.json` | the analyst, post-gate, with `fma` evidence | `segment_build.py` |
| `data/segment_build.json` | `segment_build.py` | `build_assumptions.py`, the report |
| `segment_build.md` | `segment_build.py` | the report, as an exhibit |

Edit `strategy_decisions.json` and rebuild. Never hand-edit `model_strategy.json`
— the same discipline as `decisions.json` → `assumptions.json`.

## The gate

`check_strategy.gate_ok(strategy, require_approved=True)` is the single function
all four consumers call, so the gate is enforced identically everywhere. It
returns `(False, reason)` when:

- modelability derives to **RED**
- any **BLOCKING** check is raised
- `analyst_decision.status` is not `APPROVED` or `MODIFIED`

Modelability is **derived**, never taken from the document. Checks can only cap
it downward. A strategy that claims GREEN while carrying an unexecutable primary
method is downgraded to AMBER and told so.

| Status | Meaning |
|---|---|
| GREEN | economics and architecture sufficiently evidenced; proceed on approval |
| AMBER | partially understood, unusual, or the correct method is unexecutable here; the analyst resolves each named item |
| RED | out of scope, no defensible architecture, or disclosure so thin that proceeding would manufacture precision — **stop** |

Banks, NBFCs and insurers are automatic RED. That check is additive: the four
pre-existing refusals (`sectors.py` `block: True`, `financial-model-assumptions`
non-negotiable 6, `financial-model` non-negotiable 6, orchestrator Phase 0) are
untouched and still fire on their own.

## Downstream flags — all optional, all backward-compatible

Absent `--strategy`, every consumer behaves exactly as it did before and prints
one line saying it ran without a modeling strategy.

| Skill | Flag | Behaviour with it |
|---|---|---|
| `financial-model-assumptions` | `build_assumptions.py --strategy F` | gate check; every `required_drivers` entry must appear in `decisions.json` or `_analyst`, else a check failure. Writes `strategy_ref` into `assumptions.json`. |
| | `build_assumptions.py --segment-build F` | injects the derived `revenue_growth` path with `source: segment_build`, preserving the trace |
| `financial-model` | `ingest.py --strategy F` | gate check; refuses an architecture it cannot execute; **disables the silent historical-average fallback for strategy-required drivers** |
| `peer-comps` | `build_comps.py --strategy F` | restricts emitted multiples and football-field bands to methods not `NOT_APPROPRIATE` |
| `equity-research-report` | `model.py --strategy F` | gate check; labels each valuation output with its approved role; refuses to emit a headline DCF whose role is `NOT_APPROPRIATE`/`LOW_RELIABILITY` without `--force-dcf` |

## `model_strategy.json` schema (v1.0)

```jsonc
{
  "schema_version": "1.0",
  "company": "...", "ticker": "...", "as_of": "2026-08-06",
  "scope_status": "IN_SCOPE",              // or OUT_OF_SCOPE -> RED
  "sector": "manufacturing",               // a sectors.py key; context, not architecture
  "business_description": "...",

  "segments": [{
    "name": "Projects", "materiality_pct": 62.0,
    "economic_archetype": "order_book_execution",   // an archetypes.py key
    "proposed_archetype": null,                     // set instead -> AMBER
    "revenue_drivers": [{"id": "...", "evidence": [{"quote","source","page"}]}],
    "margin_drivers": [], "capital_drivers": [], "working_capital_drivers": [],
    "evidence": [{"quote","source","page"}],
    "confidence": "High|Medium|Low",
    "status": "recommended|user_modified|insufficient"
  }],

  "model_architecture": {
    "revenue_model": "segment_buildup|consolidated_buildup|consolidated_growth",
    "segment_modeling": "...", "required_schedules": [...],
    "consolidation_method": "...",
    "execution": {
      "revenue_build_site": "assumptions_layer",
      "consolidated_growth_is_derived": true,
      "financial_model_capability": "consolidated_growth_only",
      "segment_translations": {"Projects": "derived_growth"},
      "unsupported_requirements": []        // non-empty -> RED, pipeline refuses
    }
  },

  "required_drivers": [{"driver_id","segment","archetype","label","unit",
                        "fma_preset","optional","kind"}],

  "valuation_methods": [{"method","label","applicability","role","rationale",
                         "execution_owner","requirements","limitations",
                         "manual_steps"}],
  "rejected_methods": [{"method","label","reason"}],
  "uncertainties": [{"issue","impact","required_resolution"}],
  "facts": {...},                            // what disqualified what
  "modelability": {"status","declared","rationale":[...]},
  "analyst_decision": {"status":"PENDING|APPROVED|MODIFIED|REJECTED","by","date","notes"},
  "checks": [{"level":"BLOCKING|WARN|INFO","code","message"}]
}
```

Conventions are borrowed deliberately, not reinvented: evidence objects match
`decisions.json`'s `{quote, source, page}`; confidence is `High/Medium/Low`;
status is `recommended/user_modified/insufficient`; sector keys are `sectors.py`'s.
Citations therefore flow into `assumptions_evidence.md` unchanged.

## Phase A: how a segment architecture reaches `financial-model`

`financial-model/scripts/rows.py` defines one revenue row:

```
Row("revenue", ..., fcst="prev(revenue)*(1+rev_growth)")
```

There are no segment rows and no driver build-up rows. So:

1. `segment_build.py` runs the approved archetypes on approved, cited values.
2. Each segment's build must reproduce the **base year** within 1% of reported
   segment revenue, or it refuses.
3. Segment revenue is summed to consolidated revenue, from which a per-year
   growth path is derived.
4. `build_assumptions.py --segment-build` injects that path as `revenue_growth`,
   tagged with its source.
5. `financial-model` executes one growth rate, as it always has.

Nothing is lost: `segment_build.json` carries every segment, every intermediate
row and every citation, and `segment_build.md` is an exhibit in the report. The
consolidated growth rate is *derived*, and it can always be walked back.

Where an archetype has `translation: "unsupported"`, or a proposed archetype has
no validated builder, `unsupported_requirements` is populated, modelability is
RED, and `financial-model` refuses. It does not flatten and it does not
approximate.

## Feeding the report

- `model_strategy.md` — the methodology section, and the audit trail for why the
  valuation uses the lens it uses.
- `segment_build.md` — an exhibit alongside `model_review.md`.
- `valuation_methods` roles — the valuation pages are written to the approved
  roles, so a company whose primary method is NAV does not get a page headed
  "DCF valuation".
- `rejected_methods` — one or two sentences in the valuation section. Saying why
  a method was *not* used is what distinguishes a methodology from a habit.

## Phase 8 write-back

```bash
python3 <eqr>/scripts/kb.py --root reports sector --sector "capital goods" \
    --archetype "order_book_execution" \
    --note "segment EBIT split was in the segment note, not the MD&A"
```

The next company in the sector starts from the architecture that worked, and
adjusts — the same loop the peer set already uses.
