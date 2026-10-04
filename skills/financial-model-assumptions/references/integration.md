# Files, schemas and how this fits the surrounding skills

## Position in the pipeline

```
annual report PDF
      |  annual-report-kb skill
      v
<Company> Annual Report/          knowledge base: context/, sections/, pages/,
      |                           tables/, entities/, metadata/
      |  THIS SKILL
      v
decisions.json  ->  assumptions.json + assumptions_evidence.md
      |
      |  equity-research-report skill: model.py
      v
model.json  ->  DCF, relative valuation, forensic screens, the report
```

If the user has a PDF and no knowledge base, build one first with
`annual-report-kb`. If they have only a financials export and no narrative
documents, this skill still runs - the historical anchors work - but every
forward-looking assumption will be Medium confidence at best, and that must be
stated up front rather than discovered at the end.

## decisions.json

The working record. It is the file the user edits to change an assumption, and
the only input to `build_assumptions.py`.

```json
{
  "company": "Acme Chemicals Ltd",
  "ticker": "ACME",
  "kb": "Acme Chemicals Annual Report",
  "sector": "manufacturing",
  "as_of": "2026-08-01",
  "currency": "INR cr",
  "wc_days_on_cogs": true,

  "assumptions": {
    "revenue_growth": {
      "value": [13.0, 12.0, 11.0, 10.0, 9.5],
      "unit": "%",
      "confidence": "High",
      "status": "recommended",
      "why": [
        "Management guided to low-teens growth over the medium term",
        "5y revenue CAGR 14.4%, decelerating to 11.1% over the last 3y"
      ],
      "evidence": [
        {"quote": "sustain low-teens revenue growth over the medium term",
         "source": "context/management_discussion.md", "page": 43}
      ]
    },

    "customer_retention": {
      "value": "Not enough evidence",
      "confidence": "Low",
      "status": "insufficient",
      "why": ["The knowledge base does not disclose retention or churn"],
      "evidence": []
    }
  },

  "peers": [{"name": "Acme", "price": null, "mcap": null, "ev": null,
             "sales": null, "ebitda": null, "pat": null, "bv": null, "roe": null}]
}
```

Field notes:

- `value` — a number, or a per-year list (one entry per forecast year), or the
  string `"Not enough evidence"`.
- `status` — `recommended` (default), `user_modified`, or `insufficient`.
  When the user changes a value, set `user_modified` and keep the original
  under `recommended` so the audit trail carries both.
- `confidence` — `High` / `Medium` / `Low`, per `evidence-rules.md`.
- `why` — a list of short reasons, most important first.
- `evidence` — objects with `quote`, `source` and `page`. Use
  `"source": "external"` for market data that is not in the knowledge base.
- `wc_days_on_cogs` — `true` when DIO and DPO were struck on COGS (the usual
  case). This changes the working-capital conversion materially; set it
  correctly.
- `peers`, `peer_betas`, `scenarios`, `mid_year_convention`, `blume_adjust`,
  `non_operating_assets` at the top level pass straight through to
  `assumptions.json`.

## Key mapping into model.py

| decisions.json | assumptions.json | Notes |
|---|---|---|
| `revenue_growth` | `revenue_growth` | list or scalar |
| `ebit_margin` | `ebit_margin` | **the margin the DCF actually uses** |
| `ebitda_margin` | — | used to derive `ebit_margin` if it is absent |
| `capex_pct_sales` | `capex_pct_sales` | |
| `dep_pct_sales` | `dep_pct_sales` | |
| `dso` / `dio` / `dpo` | `nwc_pct_sales` | derived; see the formula below |
| `effective_tax_rate` | `tax_rate` | |
| `interest_rate` | `cost_of_debt` | |
| `risk_free_rate` | `rf` | |
| `equity_risk_premium` | `erp` | |
| `beta` | `beta` | |
| `target_debt_weight` | `target_debt_weight` | |
| `terminal_growth` | `terminal_growth` | must be < WACC |
| `net_debt`, `shares_out`, `current_price` | same | per-share bridge |

Everything else — volume, pricing, retention, gross margin, the expense ratios,
the day-counts — is written to `_analyst` in `assumptions.json`. `model.py`
ignores unknown keys, so they travel with the file for the forecast sheet and
the report narrative without breaking anything.

Rates may be percent (`12.0`) or decimal (`0.12`); `model.py` normalises both.
The builder emits percent, matching the template `new_company.py` scaffolds.

## Working-capital conversion

```
NWC/Sales = DSO/365 + (DIO - DPO)/365 x (COGS/Sales)
```

with `COGS/Sales = 1 - gross_margin`. Set `wc_days_on_cogs: false` to treat all
three as sales-based. On the worked example this reproduces the historical
NWC/sales to within 0.1pp — if the derived figure is far from the historical
`nwc_pct_sales` anchor, the day-count basis is usually wrong.

## Checks the builder raises

- `BLOCKING: terminal growth >= WACC` — `model.py` exits on this, so fix it
  before running the model. `--strict` makes the builder exit too.
- Terminal growth within 2pp of WACC — terminal value will dominate.
- Per-year list shorter than the horizon — held flat, and reported.
- A value outside its plausibility band — flagged, never changed.
- An assumption with no evidence and no `insufficient` status.
- `model.py` inputs still unset.

## What the user gets

- `assumptions_evidence.md` — the audit trail: value, why, quoted evidence with
  page citations, confidence, and whether the analyst or the user set it.
- `assumptions.json` — feeds `model.py` directly.
- `decisions.json` — the file to edit and rebuild from.
