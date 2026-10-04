# Shared Contract — ERIP Skills

This file defines the artifact contract between the three companion skills in the ERIP architecture.

## Skills

| Skill | Responsibility | Output |
|-------|---------------|--------|
| `financial-model` | Financial modelling logic, forecast calculations, three-statement mechanics, DCF, valuation mathematics, model state | `model.json`, `assumptions.json`, `checks.json`, `source_registry.json` |
| `model-workbook` | Convert authoritative model state into professional Excel workbook | `<Company>_ERIP_Model.xlsx` |
| `model-audit` | Build source register, assumption register, data lineage, audit book | `<Company>_ERIP_Audit_Book.md` |

## Contract: Inputs to model-workbook

| Input | Produced by | Description |
|-------|------------|-------------|
| `model.json` | `financial-model` | Authoritative solved model state (rows, periods, checks, bridge) |
| `assumptions.json` | `financial-model` | Driver values, scenarios, DCF parameters |
| `source_registry.json` | `financial-model` | Source document registry with confidence levels |

## Contract: Inputs to model-audit

| Input | Produced by | Description |
|-------|------------|-------------|
| `model.json` | `financial-model` | Model state (for lineage tracing) |
| `assumptions.json` | `financial-model` | Assumptions with provenance metadata |
| `citations/*.json` | `financial-model` | Source citations per model line |
| `source_registry.json` | `financial-model` | Source document registry |

## model.json Schema

```json
{
 "company": "string",
 "currency": "INR",
 "built": "2026-08-07",
 "sector": "Infrastructure",
 "periods": {
 "hist": ["Mar-16", "Mar-17", ...],
 "fcst": ["Mar-27E", ...],
 "all": ["Mar-16", ...]
 },
 "rows": {
 "revenue": {"values": [float, ...], "label": "string", "kind": "actual"},
 "ebitda": {"values": [float, ...], "label": "string", "kind": "actual"},
 "pat": {"values": [float, ...], "label": "string", "kind": "calc"},
 "total_assets": {"values": [float, ...], "label": "string", "kind": "calc"},
 ...
 },
 "checks": {
 "pass": true,
 "items": [
 {"check": "chk_balance", "label": "...", "ok": true, "worst": 0.0, "severity": "blocking"}
 ]
 },
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
 },
 "solve": {
 "iterations": 12,
 "residual": 0.001
 },
 "options": {
 "dep_basis": "net_block"
 },
 "citations": {
 "revenue": {"source": "Annual Report 2024-25", "page": 42}
 },
 "reconciliation": [
 {"row": "revenue", "period": "Mar-25A", "screener": 78286.82, "annual_report": 78286.82, "diff_pct": "0.0%"}
 ],
 "notes": ["Build note 1", "Build note 2"]
}
```

## assumptions.json Schema

```json
{
 "company": "string",
 "currency": "INR",
 "built": "2026-08-07",
 "sector": "Infrastructure",
 "rf": 7.0,
 "erp": 5.5,
 "beta": 0.85,
 "cost_of_debt": 8.5,
 "tax_rate": 25.0,
 "terminal_growth": 3.5,
 "scenarios": {
 "base": {
 "rev_growth": [0.12, 0.10, ...],
 "ebitda_margin": [0.55, 0.54, ...],
 "capex_pct_sales": [0.25, ...],
 "terminal_growth": 0.035,
 "probability": 0.6,
 "_why": "Base case reflects consensus analyst views",
 "intrinsic_value_per_share": 850.0
 },
 "bull": {...},
 "bear": {...}
 },
 "dcf": {
 "wacc_build": {
 "risk_free_rate": 0.07,
 "equity_risk_premium": 0.055,
 "beta": 0.85,
 "cost_of_equity": 0.11675,
 "cost_of_debt": 0.085,
 "tax_rate": 0.25,
 "terminal_growth": 0.035
 },
 "bridge": {
 "fcff_5yr": [7166.14, 10227.98, ...],
 "terminal_value": 250000.0,
 "enterprise_value": 350000.0,
 "net_debt": 32798.16,
 "equity_value": 317201.84,
 "shares": 230.4,
 "intrinsic_value_per_share": 1376.75
 },
 "sensitivity": {
 "wacc": [0.09, 0.10, 0.11, 0.12],
 "terminal_growth": [0.025, 0.03, 0.035, 0.04],
 "grid": [[1200, 1300, 1400, 1500], ...]
 }
 }
}
```

## Provenance Types

| Type | Definition |
|------|-----------|
| REPORTED | Directly from audited financial statements or regulatory filings |
| DERIVED | Calculated from reported figures (e.g., margin %) |
| ASSUMPTION | Analyst judgment not directly observable |
| MARKET | External market data (beta, WACC inputs, comps) |
| MODEL_DERIVED | Output of the model's own calculations |

## Row Kind Enumeration

| Kind | Display |
|------|---------|
| `actual` | Reported historical figure |
| `calc` | Model-derived value |
| `input` | Analyst-assumed driver |
| `head` | Section header (no data) |
| `chk` | Integrity check item |

## Governing Principle

One authoritative model state (model.json) → multiple presentation/audit outputs.

Neither companion skill independently recalculates the financial model.
