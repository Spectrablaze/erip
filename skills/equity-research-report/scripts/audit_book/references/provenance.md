# Provenance classification rules

Every line item in the model must carry a provenance type. This document
explains how to classify each kind of row.

## REPORTED

The figure comes directly from a source document. No calculation.

**Examples:**
- Revenue from the annual report P&L
- EBITDA from the annual report
- Net fixed assets from the balance sheet
- Trade payables from the annual report notes
- Cash and bank from the balance sheet

**Source citation required.** Page number, table description, and where
available a verbatim quote of the line item label from the document.

## DERIVED

The figure is calculated from reported figures but not by the model engine.
It is back-solved from historical actuals.

**Examples:**
- Driver values back-solved from reported financials (e.g. DSO, DPO, DIO
 back-solved from receivables, payables, inventory and revenue/COGS)
- Gross margin derived from revenue minus COGS
- EBIT derived from EBITDA minus depreciation

**Source citation:** cite the formula and the reported figures it uses.

## ASSUMPTION

The figure is set by the analyst based on evidence. It is not reported and
not derived from reported figures alone.

**Examples:**
- Forecast revenue growth rates
- Forecast EBITDA margins
- Terminal growth rate
- WACC components (risk-free rate, ERP, beta, cost of debt)
- Target capital structure
- Exit multiple
- Capex intensity

**Source citation:** cite the evidence (concall guidance, industry report,
historical CAGR, peer median, etc.) and the analyst's reasoning.

## MARKET

The figure comes from observable market data at a point in time.

**Examples:**
- Current share price
- 10-year government bond yield
- Peer multiples (if from a live market data feed)

**Source citation:** cite the data source and the date the data was pulled.

## MODEL_DERIVED

The figure is produced by the financial model's calculation engine. It is
not reported and not assumed.

**Examples:**
- FCFF, FCFE
- EPS, BVPS
- Net debt
- Cash flow statement lines (CFO, CFI, CFF)
- Schedule lines (fixed asset roll, debt schedule, NWC)
- Check residuals

**Source citation:** cite the formula in rows.py that produces it.

## Classification rules

1. If the figure appears in the annual report or Screener export exactly as
 reported, it is REPORTED.
2. If the figure is computed from reported figures to produce a driver
 value, it is DERIVED.
3. If the figure is an analyst judgment about the future, it is ASSUMPTION.
4. If the figure is a market observable, it is MARKET.
5. If the figure is produced by the model engine's formulas, it is
 MODEL_DERIVED.

## When in doubt

Prefer the more specific type. If a figure is both reported and market
(e.g., a share price from the annual report), use MARKET. If it is both
reported and derived (e.g., gross margin computed from reported revenue and
COGS), use DERIVED.
