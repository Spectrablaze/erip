# Artifact Contract

This document defines the JSON contracts between `financial-model` and the two
companion presentation skills (`model-workbook` and `model-audit`).

## Shared Principle

`financial-model` is the sole computational authority. Both companion skills
consume its outputs. Neither companion recalculates the model.

---

## model.json (authoritative model state)

Written by: `financial-model`
Consumed by: `model-workbook`, `model-audit`

Top-level keys:

```
{
 "company": "Adani Ports & SEZ Ltd",
 "currency": "INR cr",
 "sector": "Infrastructure / Ports",
 "built": "2026-08-12",
 "fy_anchor": "Mar",
 "reporting_basis": "Ind AS",
 "options": {
 "dep_basis": "net_block"
 },
 "periods": {
 "hist": ["FY23", "FY24", "FY25"],
 "fcst": ["FY26E", ..., "FY35E"],
 "all": ["FY23", ..., "FY35E"]
 },
 "rows": {
 "<row_key>": {
 "label": "Human-readable name",
 "sheet": "Income Statement",
 "kind": "actual | calc | input",
 "values": [float, float, ...],
 "unit": "INR cr",
 "source": "screener | direct_input | derived",
 "confidence": 0.95,
 "citation": "AR2025 p.45",
 "rationale": "..."
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
 "severity": "error",
 "period": "FY26E"
 }
 ]
 },
 "reconciliation": [
 {
 "row": "Revenue",
 "period": "FY24",
 "screener": 1234.5,
 "annual_report": 1234.5,
 "diff_pct": 0.0,
 "resolution": "MATCH"
 }
 ],
 "citations": {
 "revenue_fy24": {
 "source": "AR2024",
 "page": 45
 }
 },
 "notes": ["Build note text"],
 "solve": {
 "iterations": 7,
 "residual": 1.2e-8,
 "circular": true
 }
}
```

### Row keys convention

Use snake_case. `model-workbook` maps keys to sheet rows. `model-audit` uses
keys to join with source_registry.

Standard row keys:
- `revenue`, `cogs`, `gross_profit`, `opex`, `ebitda`, `dep_charge`, `ebit`,
 `pbt`, `pat`, `eps`
- `cash`, `receivables`, `inventory`, `other_ca`, `net_block`, `cwip`,
 `investments`, `payables`, `other_liab`
- `term_debt`, `revolver`, `share_capital`, `reserves`
- `cfo`, `cfi`, `cff`, `net_change_cash`, `cash_open`, `cash_close`
- `d_nwc`, `nwc`, `capex`, `nb_open`, `nb_close`
- `s_fcff`, `s_wacc`, `s_net_debt`, `s_terminal_value`

---

## assumptions.json (driver assumptions and scenario metadata)

Written by: `financial-model` (as part of the model solve)
Consumed by: `model-workbook`, `model-audit`

```
{
 "company": "Adani Ports & SEZ Ltd",
 "built": "2026-08-12",
 "scenarios": {
 "base": {
 "probability": 0.50,
 "revenue_growth": [0.08, 0.07, 0.06, 0.05],
 "ebitda_margin": [0.72, 0.73, 0.73, 0.74],
 "capex_pct_sales": [0.18, 0.16, 0.14, 0.12],
 "terminal_growth": 0.025,
 "_why": "Management guidance, PBJV volume growth"
 },
 "bear": { ... },
 "bull": { ... }
 },
 "dcf": {
 "wacc_build": {
 "risk_free_rate": 0.0698,
 "equity_risk_premium": 0.06,
 "beta": 1.15,
 "cost_of_equity": 0.1387,
 "market_debt_weight": 0.25,
 "cost_of_debt": 0.075,
 "tax_rate": 0.25,
 "wacc": 0.1175
 },
 "bridge": {
 "fcf_fy35": 28934.5,
 "terminal_value": 450000.0,
 "pv_fcf_sum": 127000.0,
 "pv_terminal": 320000.0,
 "enterprise_value": 447000.0,
 "net_debt": -89000.0,
 "equity_value": 536000.0,
 "shares_outstanding": 234.5,
 "intrinsic_value_per_share": 2285.0
 },
 "sensitivity": {
 "wacc": [0.10, 0.105, 0.11, 0.115, 0.12],
 "terminal_growth": [0.015, 0.02, 0.025, 0.03, 0.035],
 "grid": [
 [3850, 4120, 4420, 4770, 5170],
 ...
 ]
 }
 },
 "sensitivity": { ... }
}
```

---

## source_registry.json (source register)

Written by: `model-audit`
Consumed by: `model-audit` (lineage)

```
{
 "company": "Adani Ports & SEZ Ltd",
 "generated": "2026-08-12",
 "sources": {
 "revenue_fy24": {
 "type": "REPORTED",
 "document": "AR2024",
 "page": 45,
 "table": "Standalone P&L",
 "value_raw": 1234.5,
 "confidence": 0.99,
 "approved": true,
 "transformations": ["INR cr", "crores_to_crores"],
 "downstream": ["model.json:revenue", "checks:recon_revenue"]
 }
 }
}
```

### Provenance types

| Type | Meaning |
|------|---------|
| REPORTED | Stated in a source document (AR, concall, filing) |
| DERIVED | Calculated from other REPORTED figures |
| ASSUMPTION | Explicit model assumption |
| MARKET | Observable market data (beta, yield, FX) |
| MODEL_DERIVED | Produced by the model solver |

---

## lineage.json (data lineage)

Written by: `model-audit`
Consumed by: `model-audit` (output generation)

Maps each material model output back through its calculation chain to sources.

```
{
 "lineage": {
 "model.json:pat_fy27": {
 "path": [
 "source_registry:revenue_fy27",
 "source_registry:cogs_fy27",
 "source_registry:tax_fy27"
 ],
 "calculation": "revenue - cogs - opex - dep - interest - tax",
 "confidence": 0.85,
 "bottleneck": "cogs_fy27 is ASSUMPTION"
 }
 }
}
```

---

## checks.json (validation results)

Written by: `financial-model`
Consumed by: `model-workbook`, `model-audit`

Same schema as `model.json > checks`. Embedded in model.json but can also
exist standalone for incremental validation.

---

## Reconciliation Standard

For every company, `financial-model` must produce a `reconciliation` array
covering all historical periods and key P&L/BS lines:

| Row | FY23 screener | FY23 AR | FY24 screener | FY24 AR | Diff% |
|-----|--------------|---------|--------------|---------|-------|
| Revenue | | | | | |
| PAT | | | | | |
| Cash | | | | | |
| Debt | | | | | |

Resolution codes: `MATCH` | `ROUNDING` | `DIFFERS` | `NOT_FOUND`

The reconciliation block appears in:
- `model.json > reconciliation` (authoritative)
- `model-workbook` Model info sheet
- `model-audit` source register
