#!/usr/bin/env python3
"""
rows.py - the model definition. One row, defined once.

This is the only place the structure of the model lives. `build_model.py` turns
this list into both the computed grid and the Excel workbook, so a change here
changes both and they cannot disagree.

Row kinds
  head    a section label, no data
  actual  history comes from the source financials; the forecast is a formula
  input   a driver: history is back-solved by `hist`; the forecast is a
          hardcoded number the user is meant to edit (blue in the workbook)
  calc    a formula in every column

`hist` overrides `fcst` in the historical columns. Where a row has neither an
actual nor a `hist`, the historical column uses `fcst`.

Units: whatever the source financials use (Screener exports ₹ crore, with share
counts in crore, so EPS and BVPS come out in ₹ per share without conversion).
"""
from __future__ import annotations

from dataclasses import dataclass, field

# Excel number formats
FMT = {
    "cur": "#,##0.0;(#,##0.0);\"-\"",
    "pct": "0.0%;(0.0%)",
    "days": "#,##0.0",
    "x": "0.00\"x\"",
    "sh": "#,##0.00",
    "chk": "#,##0.000;(#,##0.000)",
    "n": "#,##0.00",
}

DRIVERS = "Drivers"
IS = "Income Statement"
BS = "Balance Sheet"
CF = "Cash Flow"
SCH = "Schedules"
CHK = "Checks"
SUM = "Summary"

SHEETS = [DRIVERS, IS, BS, CF, SCH, CHK, SUM]


@dataclass
class Row:
    key: str
    label: str
    sheet: str
    kind: str = "calc"          # head | actual | input | calc
    fcst: str | None = None     # formula used in forecast columns
    hist: str | None = None     # formula used in historical columns
    fmt: str = "cur"
    indent: int = 0
    bold: bool = False
    rule: str = ""              # "top" | "bottom" | ""
    note: str = ""
    meta: dict = field(default_factory=dict)


def H(label, sheet):
    return Row(key=f"_h{abs(hash((label, sheet))) % 10**8}", label=label,
               sheet=sheet, kind="head")


# --------------------------------------------------------------------- MODEL
ROWS: list[Row] = [
    # =================================================================== DRIVERS
    H("Growth and margins", DRIVERS),
    Row("rev_growth", "Revenue growth", DRIVERS, "input", fmt="pct",
        hist="revenue/prev(revenue)-1", indent=1,
        note="Forecast growth. Historical cells back-solve from reported revenue."),
    Row("gross_margin", "Gross margin", DRIVERS, "input", fmt="pct",
        hist="gross_profit/revenue", indent=1,
        note="Where the source has no expense detail this equals the EBITDA margin "
             "and the opex line is zero; see references/checks.md."),
    Row("ebitda_margin", "EBITDA margin", DRIVERS, "input", fmt="pct",
        hist="ebitda/revenue", indent=1),
    Row("other_income_pct", "Other income (% sales)", DRIVERS, "input", fmt="pct",
        hist="other_income/revenue", indent=1,
        note="Reported other income already contains treasury income. Only raise "
             "interest_income_rate above zero if you cut this to match."),

    H("Capital expenditure and depreciation", DRIVERS),
    Row("capex_pct_sales", "Capex (% sales)", DRIVERS, "input", fmt="pct",
        hist="capex/revenue", indent=1),
    Row("dep_pct_nb", "Depreciation (% opening net block)", DRIVERS, "input", fmt="pct",
        hist="dep_charge/prev(net_block)", indent=1),
    Row("dep_pct_sales", "Depreciation (% sales)", DRIVERS, "input", fmt="pct",
        hist="dep_charge/revenue", indent=1,
        note="Only used when dep_basis is 'sales'."),
    Row("cwip_pct_sales", "CWIP (% sales)", DRIVERS, "input", fmt="pct",
        hist="cwip/revenue", indent=1),

    H("Working capital", DRIVERS),
    Row("dso", "Receivable days", DRIVERS, "input", fmt="days",
        hist="receivables/revenue*365", indent=1),
    Row("dio", "Inventory days", DRIVERS, "input", fmt="days",
        hist="inventory/cogs*365", indent=1),
    Row("dpo", "Payable days", DRIVERS, "input", fmt="days",
        hist="payables/cogs*365", indent=1,
        note="Zero until trade payables are supplied from the annual report; "
             "Screener's export does not carry them."),
    Row("other_ca_pct", "Other current assets (% sales)", DRIVERS, "input", fmt="pct",
        hist="other_ca/revenue", indent=1),
    Row("other_liab_pct", "Other liabilities (% sales)", DRIVERS, "input", fmt="pct",
        hist="other_liab/revenue", indent=1),

    H("Financing, tax and distribution", DRIVERS),
    Row("tax_rate", "Effective tax rate", DRIVERS, "input", fmt="pct",
        hist="tax/pbt", indent=1),
    Row("cost_of_debt", "Interest rate on debt", DRIVERS, "input", fmt="pct",
        hist="interest_expense/AVG(prev(debt_total),debt_total)", indent=1),
    Row("interest_income_rate", "Yield on cash and investments", DRIVERS, "input",
        fmt="pct", hist="0", indent=1),
    Row("debt_growth", "Term debt growth", DRIVERS, "input", fmt="pct",
        hist="term_debt/prev(term_debt)-1", indent=1,
        note="Back-solved from history, so a company that has been deleveraging "
             "keeps deleveraging unless you say otherwise."),
    Row("term_debt_repay", "Scheduled debt repayment", DRIVERS, "input", fmt="cur",
        hist="0", indent=1),
    Row("equity_issued", "Equity issued", DRIVERS, "input", fmt="cur",
        hist="0", indent=1),
    Row("payout_ratio", "Dividend payout", DRIVERS, "input", fmt="pct",
        hist="dividends/pat", indent=1),
    Row("min_cash", "Minimum cash balance", DRIVERS, "input", fmt="cur",
        hist="0", indent=1,
        note="The revolver is drawn to hold cash at or above this level."),

    # ========================================================= INCOME STATEMENT
    H("Income statement", IS),
    Row("revenue", "Revenue", IS, "actual", fcst="prev(revenue)*(1+rev_growth)",
        bold=True),
    Row("cogs", "Cost of goods sold", IS, "actual", fcst="revenue*(1-gross_margin)",
        indent=1),
    Row("gross_profit", "Gross profit", IS, fcst="revenue-cogs", rule="top"),
    Row("opex", "Operating expenses", IS, fcst="gross_profit-ebitda", indent=1),
    Row("ebitda", "EBITDA", IS, "actual", fcst="revenue*ebitda_margin",
        bold=True, rule="top"),
    Row("dep_charge", "Depreciation and amortisation", IS, "actual",
        fcst="MIN(dep_pct_nb*prev(net_block),prev(net_block)+capex)", indent=1,
        note="Capped at opening net block plus capex so the asset base cannot go "
             "negative. Swapped for revenue*dep_pct_sales when dep_basis='sales'."),
    Row("ebit", "EBIT", IS, fcst="ebitda-dep_charge", bold=True, rule="top"),
    Row("other_income", "Other income", IS, "actual",
        fcst="revenue*other_income_pct+interest_income_rate*AVG(prev(cash),cash)",
        indent=1),
    Row("interest_expense", "Interest expense", IS, "actual",
        fcst="cost_of_debt*AVG(prev(debt_total),debt_total)", indent=1,
        note="On the average debt balance - this is the intended circular reference."),
    Row("exceptional", "Exceptional items", IS, "actual", fcst="0", indent=1),
    Row("pbt", "Profit before tax", IS, "actual",
        fcst="ebit+other_income-interest_expense+exceptional", bold=True, rule="top"),
    Row("tax", "Tax", IS, "actual", fcst="pbt*tax_rate", indent=1),
    Row("pat", "Profit after tax", IS, "actual", fcst="pbt-tax",
        bold=True, rule="top"),
    Row("eps", "Earnings per share", IS, fcst="pat/shares", fmt="sh"),

    # ============================================================ BALANCE SHEET
    H("Assets", BS),
    Row("cash", "Cash and bank", BS, "actual", fcst="prev(cash)+net_change_cash",
        indent=1),
    Row("receivables", "Trade receivables", BS, "actual",
        fcst="dso/365*revenue", indent=1),
    Row("inventory", "Inventories", BS, "actual", fcst="dio/365*cogs", indent=1),
    Row("other_ca", "Other current assets", BS, "actual",
        fcst="revenue*other_ca_pct", indent=1),
    Row("net_block", "Net fixed assets", BS, "actual",
        fcst="prev(net_block)+capex-dep_charge", indent=1),
    Row("cwip", "Capital work in progress", BS, "actual",
        fcst="revenue*cwip_pct_sales", indent=1),
    Row("investments", "Investments", BS, "actual", fcst="prev(investments)", indent=1),
    Row("total_assets", "Total assets", BS,
        fcst="cash+receivables+inventory+other_ca+net_block+cwip+investments",
        bold=True, rule="top"),

    H("Liabilities and equity", BS),
    Row("share_capital", "Share capital", BS, "actual",
        fcst="prev(share_capital)", indent=1),
    Row("reserves", "Reserves and surplus", BS, "actual",
        fcst="prev(reserves)+pat-dividends+equity_issued", indent=1),
    Row("term_debt", "Term borrowings", BS, "actual",
        fcst="MAX(prev(term_debt)*(1+debt_growth)-term_debt_repay,0)", indent=1),
    Row("revolver", "Revolver / short-term plug", BS, "actual",
        fcst="prev(revolver)+revolver_draw-revolver_repay", indent=1),
    Row("debt_total", "Total debt", BS, fcst="term_debt+revolver", indent=1),
    Row("payables", "Trade payables", BS, "actual", fcst="dpo/365*cogs", indent=1),
    Row("other_liab", "Other liabilities", BS, "actual",
        fcst="revenue*other_liab_pct", indent=1),
    Row("total_liab_eq", "Total liabilities and equity", BS,
        fcst="share_capital+reserves+debt_total+payables+other_liab",
        bold=True, rule="top"),

    # =============================================================== CASH FLOW
    H("Operating", CF),
    Row("cf_pat", "Profit after tax", CF, fcst="pat", indent=1),
    Row("cf_dep", "Depreciation and amortisation", CF, fcst="dep_charge", indent=1),
    Row("cf_wc", "(Increase)/decrease in net operating assets", CF,
        fcst="-d_nwc", indent=1),
    Row("cfo", "Cash from operations", CF, fcst="cf_pat+cf_dep+cf_wc",
        bold=True, rule="top"),

    H("Investing", CF),
    Row("cf_capex", "Capital expenditure", CF, fcst="-capex-(cwip-prev(cwip))",
        indent=1),
    Row("cf_invest", "Investments", CF, fcst="-(investments-prev(investments))",
        indent=1),
    Row("cfi", "Cash from investing", CF, fcst="cf_capex+cf_invest",
        bold=True, rule="top"),

    H("Financing", CF),
    Row("cf_debt", "Term debt drawn/(repaid)", CF,
        fcst="term_debt-prev(term_debt)", indent=1),
    Row("cf_revolver", "Revolver drawn/(repaid)", CF,
        fcst="revolver-prev(revolver)", indent=1),
    Row("cf_div", "Dividends paid", CF, fcst="-dividends", indent=1),
    Row("cf_equity", "Equity issued", CF, fcst="equity_issued", indent=1),
    Row("cff", "Cash from financing", CF,
        fcst="cf_debt+cf_revolver+cf_div+cf_equity", bold=True, rule="top"),

    H("Cash reconciliation", CF),
    Row("net_change_cash", "Net change in cash", CF, fcst="cfo+cfi+cff", bold=True),
    Row("cash_open", "Opening cash", CF, fcst="prev(cash)", indent=1),
    Row("cash_close", "Closing cash", CF, fcst="cash_open+net_change_cash",
        bold=True, rule="top"),

    H("Reported cash flow (history only)", CF),
    Row("rep_cfo", "Reported cash from operations", CF, "actual", fcst="0", indent=1),
    Row("rep_cfi", "Reported cash from investing", CF, "actual", fcst="0", indent=1),
    Row("rep_cff", "Reported cash from financing", CF, "actual", fcst="0", indent=1),
    Row("cfo_gap", "Reconstructed less reported CFO", CF, fcst="cfo-rep_cfo",
        fmt="chk", indent=1,
        note="History only. A large gap is an accrual-quality signal, not a bug."),

    # =============================================================== SCHEDULES
    H("Fixed assets", SCH),
    Row("nb_open", "Opening net block", SCH, fcst="prev(net_block)", indent=1),
    Row("capex", "Capital expenditure", SCH, "actual",
        fcst="revenue*capex_pct_sales", indent=1),
    Row("sch_dep", "Depreciation charge", SCH, fcst="dep_charge", indent=1),
    Row("nb_close", "Closing net block", SCH, fcst="nb_open+capex-sch_dep",
        bold=True, rule="top"),

    H("Working capital", SCH),
    Row("nwc", "Net operating assets", SCH,
        fcst="receivables+inventory+other_ca-payables-other_liab", bold=True),
    Row("d_nwc", "Change in net operating assets", SCH, fcst="nwc-prev(nwc)", indent=1),
    Row("wc_days", "Net operating assets (days of sales)", SCH,
        fcst="nwc/revenue*365", fmt="days", indent=1),

    H("Debt, revolver and interest", SCH),
    Row("td_open", "Opening term debt", SCH, fcst="prev(term_debt)", indent=1),
    Row("cff_ex_rev", "Financing flows before the revolver", SCH,
        fcst="cf_debt+cf_div+cf_equity", indent=1),
    Row("cash_pre_rev", "Cash before the revolver", SCH,
        fcst="prev(cash)+cfo+cfi+cff_ex_rev", indent=1),
    Row("revolver_draw", "Revolver drawn", SCH,
        fcst="MAX(min_cash-cash_pre_rev,0)", indent=1),
    Row("revolver_repay", "Revolver repaid", SCH,
        fcst="MIN(prev(revolver),MAX(cash_pre_rev-min_cash,0))", indent=1),
    Row("avg_debt", "Average total debt", SCH,
        fcst="AVG(prev(debt_total),debt_total)", indent=1),

    H("Equity and shareholders", SCH),
    Row("dividends", "Dividends declared", SCH, "actual",
        fcst="pat*payout_ratio", indent=1),
    Row("shares", "Shares outstanding", SCH, "actual", fcst="prev(shares)",
        fmt="sh", indent=1),
    Row("equity", "Shareholders' equity", SCH, fcst="share_capital+reserves",
        bold=True),
    Row("bvps", "Book value per share", SCH, fcst="equity/shares", fmt="sh", indent=1),

    # =================================================================== CHECKS
    H("Integrity checks - every one of these must read zero", CHK),
    Row("chk_balance", "Total assets less total liabilities and equity", CHK,
        fcst="total_assets-total_liab_eq", fmt="chk"),
    Row("chk_cash_tie", "Balance sheet cash less cash flow closing cash", CHK,
        fcst="cash-cash_close", fmt="chk"),
    Row("chk_reserves", "Reserves roll-forward residual", CHK,
        fcst="reserves-(prev(reserves)+pat-dividends+equity_issued)", fmt="chk"),
    Row("chk_fa_roll", "Net block roll-forward residual", CHK,
        fcst="net_block-nb_close", fmt="chk"),
    H("Sanity checks - these must not go negative", CHK),
    Row("chk_min_cash", "Cash less the minimum cash balance", CHK,
        fcst="cash-min_cash", fmt="chk"),
    Row("chk_revolver_pos", "Revolver balance", CHK, fcst="revolver", fmt="chk"),
    Row("chk_nb_pos", "Net block", CHK, fcst="net_block", fmt="chk"),
    Row("chk_equity_pos", "Shareholders' equity", CHK, fcst="equity", fmt="chk"),

    # ================================================================== SUMMARY
    H("Operating performance", SUM),
    Row("s_revenue", "Revenue", SUM, fcst="revenue", bold=True),
    Row("s_rev_growth", "Revenue growth", SUM, fcst="revenue/prev(revenue)-1",
        fmt="pct", indent=1),
    Row("s_ebitda", "EBITDA", SUM, fcst="ebitda"),
    Row("s_ebitda_margin", "EBITDA margin", SUM, fcst="ebitda/revenue",
        fmt="pct", indent=1),
    Row("s_ebit", "EBIT", SUM, fcst="ebit"),
    Row("s_pat", "Profit after tax", SUM, fcst="pat"),
    Row("s_eps", "Earnings per share", SUM, fcst="eps", fmt="sh"),

    H("Cash generation", SUM),
    Row("s_fcff", "Free cash flow to the firm", SUM,
        fcst="ebit*(1-tax_rate)+dep_charge-capex-d_nwc", bold=True,
        note="NOPAT + D&A - capex - change in net operating assets. This is the "
             "line the DCF in equity-research-report discounts."),
    Row("s_fcfe", "Free cash flow to equity", SUM,
        fcst="pat+dep_charge-capex-d_nwc+(debt_total-prev(debt_total))"),
    Row("s_cash_conv", "EBITDA to FCFF conversion", SUM,
        fcst="s_fcff/ebitda", fmt="pct", indent=1),

    H("Leverage and returns", SUM),
    Row("s_net_debt", "Net debt", SUM, fcst="debt_total-cash-investments"),
    Row("s_nd_ebitda", "Net debt / EBITDA", SUM, fcst="s_net_debt/ebitda",
        fmt="x", indent=1),
    Row("s_int_cover", "EBIT / interest expense", SUM,
        fcst="ebit/interest_expense", fmt="x", indent=1),
    Row("s_capemp", "Capital employed", SUM,
        fcst="share_capital+reserves+debt_total-cash"),
    Row("s_roce", "Post-tax ROCE", SUM,
        fcst="ebit*(1-tax_rate)/AVG(prev(s_capemp),s_capemp)", fmt="pct", indent=1),
    Row("s_roe", "Return on equity", SUM,
        fcst="pat/AVG(prev(equity),equity)", fmt="pct", indent=1),
]

BY_KEY = {r.key: r for r in ROWS if r.kind != "head"}

# Drivers, in the order they appear, for ingest and reporting.
DRIVER_KEYS = [r.key for r in ROWS if r.kind == "input"]

# Rows whose historical columns must be supplied by the source financials.
ACTUAL_KEYS = [r.key for r in ROWS if r.kind == "actual"]

# Checks that must read zero, and checks that must not go negative.
ZERO_CHECKS = ["chk_balance", "chk_cash_tie", "chk_reserves", "chk_fa_roll"]
NONNEG_CHECKS = ["chk_min_cash", "chk_revolver_pos", "chk_nb_pos", "chk_equity_pos"]


def depreciation_formula(basis: str) -> str:
    """The forecast depreciation formula for the chosen basis."""
    if basis == "sales":
        return "revenue*dep_pct_sales"
    return "MIN(dep_pct_nb*prev(net_block),prev(net_block)+capex)"


def apply_options(dep_basis: str = "net_block") -> None:
    """Mutate the row set for the build options that change a formula."""
    BY_KEY["dep_charge"].fcst = depreciation_formula(dep_basis)
