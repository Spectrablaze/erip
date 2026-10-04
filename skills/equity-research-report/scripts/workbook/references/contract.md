# Shared artifact contract

The three-model pipeline communicates through files. Each skill owns its
output; downstream skills read, never write upstream files.

## File ownership

| File | Produced by | Consumed by |
|---|---|---|
| `data/model_input.json` | `financial-model/scripts/ingest.py` | `financial-model/scripts/build_model.py` |
| `data/model.json` | `financial-model/scripts/build_model.py` | `model-workbook`, `model-audit`, `equity-research-report/scripts/model.py` |
| `data/three_statement/model.xlsx` | `financial-model/scripts/build_model.py` | human review |
| `data/assumptions.json` | `financial-model-assumptions` | `model-workbook`, `model-audit`, `equity-research-report/scripts/model.py` |
| `<Company>_ERIP_Model.xlsx` | `model-workbook` | human review, report exhibit |
| `<Company>_ERIP_Audit_Book.xlsx` | `model-audit` | human review, report exhibit |
| `data/model_review.md` | `financial-model/scripts/check_model.py` | `equity-research-report` Phase 3e |

## model.json contract

This is the single authoritative model state. Both companion skills read it.

Key structure (abbreviated):

```json
{
 "company": "string",
 "currency": "INR cr",
 "sector": "string",
 "built": "ISO date",
 "periods": {
 "all": ["Mar-17", ..., "Mar-31E"],
 "hist": ["Mar-17", ..., "Mar-26"],
 "fcst": ["Mar-27E", ..., "Mar-31E"],
 "n_hist": 10
 },
 "options": {
 "dep_basis": "net_block",
 "avg_years": 3
 },
 "solve": {
 "iterations": 5,
 "residual": 0.0
 },
 "rows": {
 "<row_key>": {
 "label": "Human-readable name",
 "sheet": "Income Statement",
 "kind": "actual | calc | input",
 "unit": "cur | pct | days | chk",
 "note": "Human-readable constraint or caveat",
 "values": [float, ...] // len = n_hist + n_fcst
 }
 },
 "drivers": {
 "<driver_key>": {
 "values": [float, ...],
 "source": "assumptions | overrides | historical average"
 }
 },
 "checks": {
 "pass": true,
 "items": [
 {
 "check": "chk_balance",
 "label": "Balance sheet ties",
 "ok": true,
 "worst": 0.0,
 "period": "Mar-27E",
 "severity": "blocking | advisory",
 "detail": "explanation"
 }
 ]
 },
 "reconciliation": [
 {
 "row": "payables",
 "period": "Mar-24",
 "screener": 461.6,
 "annual_report": 470.0,
 "diff_pct": 1.82
 }
 ],
 "citations": {
 "payables": {
 "source": "tables/table_p0198_1.md",
 "page": 198,
 "quote": "Trade payables - total outstanding dues"
 }
 },
 "notes": ["string"],
 "bridge": {
 "periods": ["Mar-27E", ...],
 "revenue": [float, ...],
 "ebitda": [float, ...],
 "ebit": [float, ...],
 "depreciation": [float, ...],
 "capex": [float, ...],
 "change_in_nwc": [float, ...],
 "tax_rate": [float, ...],
 "fcff": [float, ...],
 "fcfe": [float, ...],
 "net_debt_close": [float, ...],
 "shares": [float, ...],
 "eps": [float, ...],
 "bvps": [float, ...]
 }
}
```

## assumptions.json contract

Produced by `financial-model-assumptions`. Carries the forecast drivers plus
metadata the companion skills display.

Key structure:

```json
{
 "_comment": "provenance note",
 "_generated": "ISO date",
 "forecast_years": 5,
 "sector": "realestate",
 "revenue_growth": [21.39, 13.02, ...],
 "ebitda_margin": [44.0, 43.5, ...],
 "capex_pct_sales": [31.0, 30.0, ...],
 "dep_pct_sales": [14.5, 14.5, ...],
 "nwc_pct_sales": [11.1, 10.82, ...],
 "tax_rate": 18.5,
 "terminal_growth": 5.0,
 "cost_of_debt": 8.0,
 "rf": 6.78,
 "erp": 5.5,
 "beta": 1.3,
 "target_debt_weight": 12.0,
 "net_debt": 42910.0,
 "shares_out": 230.396,
 "current_price": 1695.0,
 "exit_multiple": 14.0,
 "mid_year_convention": true,
 "blume_adjust": true,
 "non_operating_assets": 3340.86,
 "_analyst": {
 "ebitda_margin": [...],
 "dso": 58,
 "dio": 6.5,
 "dpo": 26
 },
 "peers": [...],
 "scenarios": {
 "bull": {
 "probability": 0.25,
 "revenue_growth": [24.0, 16.0, ...],
 "_why": "string"
 },
 "base": { "probability": 0.5, "_why": "..." },
 "bear": { "probability": 0.25, "_why": "..." }
 },
 "dcf": {
 "wacc_build": { ... },
 "forecast": [...],
 "bridge": { ... },
 "sensitivity": { "wacc": [...], "terminal_growth": [...], "grid": [[...]] },
 "three_statement": { ... }
 },
 "_strategy": {
 "revenue_model": "segment_buildup",
 "modelability": "AMBER",
 "analyst_decision": "APPROVED",
 "primary_methods": ["fcff_dcf"]
 }
}
```

## Provenance types (used by model-audit)

| Type | Meaning |
|---|---|
| `REPORTED` | Taken directly from a source document (annual report, Screener) |
| `DERIVED` | Calculated from reported figures (back-solved drivers) |
| `ASSUMPTION` | Set by the analyst based on evidence |
| `MARKET` | Taken from market data (prices, yields) |
| `MODEL_DERIVED` | Produced by the financial model (FCFF, EPS, etc.) |

## Ground truth rule

`model.json` is the ground truth for numbers. If `model.xlsx` (written by
`financial-model`) disagrees with `model.json`, `model.json` wins. The workbook
is a human-readable view; the JSON is the source of truth.
