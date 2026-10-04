#!/usr/bin/env python3
"""
sectors.py — what a ratio pack means depends on the business model.

    python3 sectors.py --list
    python3 sectors.py --show services

The ratio pack in `model.py` is a manufacturer's ratio pack. Run a software firm
through it and you get "Inventory Days: 0" and a cash conversion cycle built on an
inventory line that does not exist; run a bank through it and you get an EV/EBITDA
and an interest coverage ratio that are not merely noisy but meaningless — interest
is a lender's revenue, not its financing cost.

A profile does four things:

  suppress       null out metrics that do not apply, so they cannot reach the page
  focus          the metrics that actually carry the argument for this business
  manual_inputs  figures no Screener export holds; pull them from the annual report
                 knowledge base and put them in assumptions.json
  valuation      which lens leads, and which multiples are admissible

`block: True` marks an archetype this skill does not model. It refuses rather than
producing confident nonsense.
"""
from __future__ import annotations

import argparse
import json

# Metric keys must match exactly what model.ratios() emits.
PROFILES: dict[str, dict] = {

    "manufacturing": {
        "label": "Manufacturing / auto / industrials",
        "aliases": ["auto", "industrial", "industrials", "engineering", "capital goods",
                    "two-wheelers", "four-wheelers", "components"],
        "suppress": [],
        "focus": ["Gross Margin %", "EBITDA Margin %", "Fixed Asset Turn (x)",
                  "Inventory Days", "Cash Conversion Cycle (days)", "ROCE %", "ROIC %"],
        "manual_inputs": [
            "installed capacity and utilisation % by plant (annual report / IP)",
            "volume and realisation split of revenue growth",
            "raw-material cost as % of sales, and the main input's price trend"],
        "valuation": {"primary": "FCFF DCF",
                      "multiples": ["P/E", "EV/EBITDA", "EV/Sales", "P/B"]},
        "notes": [
            "Decompose growth into volume, price and mix — a single percentage is not "
            "analysis for a manufacturer.",
            "Capacity utilisation sets the ceiling on the forecast: check the capex plan "
            "supports the revenue path before accepting the growth assumptions."],
    },

    "services": {
        "label": "Asset-light services (IT, consulting, platforms)",
        "aliases": ["it", "it services", "software", "technology", "consulting",
                    "asset-light", "internet", "platform", "staffing"],
        # No material cost and no stock. Printing these is noise at best; a computed
        # gross margin on an absent cost line is a fabricated number.
        "suppress": ["Gross Margin %", "Inventory Days"],
        "focus": ["EBITDA Margin %", "EBIT Margin %", "Receivable Days",
                  "CFO / PAT %", "ROIC %", "ROE %"],
        "manual_inputs": [
            "employee count, revenue per employee, utilisation %, attrition %",
            "deal wins / TCV and book-to-bill",
            "revenue by geography and by vertical, and client concentration",
            "onsite-offshore mix and its margin effect"],
        "valuation": {"primary": "FCFF DCF",
                      "multiples": ["P/E", "EV/EBITDA", "EV/Sales"]},
        "notes": [
            "The cost base is people, not materials. Margin analysis runs through "
            "utilisation, pyramid and wage inflation, not raw-material prices.",
            "ROIC is structurally very high because invested capital is small — the "
            "level is not the insight, the reinvestment rate is. Say where the cash goes.",
            "Working capital is the receivable cycle alone. DSO is the number to watch.",
            "Fixed asset turnover is high by construction and carries little signal."],
    },

    "consumer": {
        "label": "FMCG / retail / pharma (inventory-heavy consumer)",
        "aliases": ["fmcg", "retail", "pharma", "pharmaceuticals", "consumer",
                    "staples", "durables", "apparel", "qsr", "food"],
        "suppress": [],
        "focus": ["Gross Margin %", "EBITDA Margin %", "Inventory Days",
                  "Receivable Days", "Payable Days", "Cash Conversion Cycle (days)",
                  "ROCE %", "ROIC %"],
        "manual_inputs": [
            "advertising & promotion as % of sales (a discretionary margin lever)",
            "volume vs price/mix growth by category",
            "distribution reach — outlets, stockists, direct coverage",
            "for retail: store count, same-store sales growth, sales per sq ft",
            "for pharma: US vs domestic split, ANDA pipeline, USFDA observations"],
        "valuation": {"primary": "FCFF DCF",
                      "multiples": ["P/E", "EV/EBITDA", "EV/Sales", "P/B"]},
        "notes": [
            "Gross margin is the pricing-power signal; EBITDA margin nets off the A&P "
            "the company chose to spend. Discuss both or the margin story is incomplete.",
            "A negative cash conversion cycle is a competitive advantage here — it means "
            "the trade funds the working capital. Say so explicitly when it appears.",
            "Inventory growing faster than sales is the leading indicator of a "
            "write-down. The forensic screen flags it; do not bury the flag."],
    },

    "commodity": {
        "label": "Commodities / cement / metals / chemicals",
        "aliases": ["cement", "metals", "steel", "mining", "chemicals", "commodity",
                    "cyclical", "paper", "sugar", "fertiliser"],
        "suppress": [],
        "focus": ["EBITDA Margin %", "Fixed Asset Turn (x)", "Net Debt / EBITDA (x)",
                  "ROCE %", "Cash Conversion Cycle (days)"],
        "manual_inputs": [
            "realisation per tonne / unit, and the input-output spread",
            "capacity, utilisation % and the announced expansion pipeline",
            "EBITDA per tonne — the sector's true unit economic",
            "where the current price sits against the 10-year cycle"],
        "valuation": {"primary": "FCFF DCF on MID-CYCLE margins, cross-checked on EV/tonne",
                      "multiples": ["EV/EBITDA", "EV/tonne", "P/B", "replacement cost"]},
        "notes": [
            "Holding peak margins through the forecast is the classic error here. Fade "
            "the EBIT margin toward the 10-year median and say what cycle position you "
            "have assumed.",
            "P/E is close to useless at a cyclical trough or peak — earnings are the "
            "volatile term. Lead with EV/EBITDA and book value.",
            "Net debt / EBITDA is the survival metric through a downcycle: stress it in "
            "the bear case rather than the base."],
    },

    "realestate": {
        "label": "Real estate / infrastructure / EPC",
        "aliases": ["real estate", "realty", "property", "infrastructure", "infra",
                    "epc", "construction", "roads"],
        # "Inventory" is capitalised project cost, so a turnover ratio on it is not a
        # working-capital cycle and the CCC built from it is meaningless.
        "suppress": ["Inventory Days", "Cash Conversion Cycle (days)"],
        "focus": ["EBITDA Margin %", "Net Debt (INR Cr)", "Net Debt / EBITDA (x)",
                  "Interest Coverage (x)", "ROCE %"],
        "manual_inputs": [
            "pre-sales / bookings value and volume, and collections",
            "order book and book-to-bill, with execution timelines",
            "land bank and its carrying value",
            "project-level debt and completion status"],
        "valuation": {"primary": "NAV (project-by-project), DCF secondary",
                      "multiples": ["P/NAV", "P/B", "EV/EBITDA"]},
        "notes": [
            "Reported revenue lags cash: recognition follows completion while pre-sales "
            "and collections lead it. Lead the analysis with bookings and collections.",
            "'Inventory' here is capitalised project cost, not stock — the turnover "
            "ratios are suppressed for that reason."],
    },

    "financials": {
        "label": "Banks / NBFCs / insurance",
        "aliases": ["bank", "banks", "banking", "nbfc", "insurance", "insurer",
                    "financial services", "lender", "housing finance", "amc"],
        "block": True,
        # Everything below is either undefined or actively misleading for a lender.
        "suppress": ["Gross Margin %", "EBITDA Margin %", "Inventory Days",
                     "Payable Days", "Cash Conversion Cycle (days)",
                     "Interest Coverage (x)", "Net Debt (INR Cr)",
                     "Net Debt / EBITDA (x)", "Fixed Asset Turn (x)",
                     "Asset Turnover (x)", "CFO / EBITDA %", "FCF / Sales %"],
        "focus": ["ROE %", "ROA %"],
        "manual_inputs": [
            "NII, NIM, cost-to-income", "GNPA, NNPA, PCR, credit cost, slippage",
            "CASA ratio, deposit and loan growth", "CAR / CET1"],
        "valuation": {"primary": "Excess-return / residual income, or dividend discount",
                      "multiples": ["P/B", "P/E"]},
        "notes": [
            "Interest is a lender's REVENUE, not a financing cost — coverage ratios, "
            "EBITDA, net debt and every EV multiple are undefined here.",
            "FCFF is invalid for a bank: use FCFE, excess return or a dividend discount "
            "model.",
            "Altman Z was estimated on non-financial firms and is not applicable.",
            "This skill does not model financials. Do not force one through the "
            "manufacturing template — the numbers will be confident and wrong."],
    },
}

GENERIC = {
    "label": "Unclassified",
    "suppress": [],
    "focus": ["EBITDA Margin %", "ROCE %", "ROIC %", "CFO / PAT %"],
    "manual_inputs": ["identify the two or three unit economics this business "
                      "actually runs on, and source them from the annual report"],
    "valuation": {"primary": "FCFF DCF", "multiples": ["P/E", "EV/EBITDA", "P/B"]},
    "notes": ["No sector profile matched. Metrics are unfiltered — check each one is "
              "meaningful for this business model before it reaches the page."],
}

# Altman Z was fitted on non-financial firms; it must not be reported for lenders.
BLOCK_ALTMAN = {"financials"}


def resolve(sector: str | None) -> tuple[str, dict]:
    """Map free text ('Two-wheelers', 'IT Services') to a profile."""
    if not sector:
        return "generic", GENERIC
    s = sector.strip().lower()
    if s in PROFILES:
        return s, PROFILES[s]
    for key, p in PROFILES.items():
        if s == key or s in p.get("aliases", []):
            return key, p
    for key, p in PROFILES.items():          # substring match, longest alias first
        for a in sorted(p.get("aliases", []) + [key], key=len, reverse=True):
            if a in s or s in a:
                return key, p
    return "generic", GENERIC


def apply(R: dict, sector: str | None) -> dict:
    """Null out inapplicable metrics in a ratio pack; return the applicability report.

    Mutates R in place. Suppressed metrics become explicit nulls rather than being
    deleted, so a downstream template that expects the key still renders — as blank,
    not as a wrong number.
    """
    key, prof = resolve(sector)
    suppressed = []
    for group in ("profitability", "leverage", "efficiency", "cash", "per_share"):
        block = R.get(group) or {}
        for metric in prof.get("suppress", []):
            if metric in block:
                block[metric] = [None] * len(block[metric])
                suppressed.append(metric)
    return {
        "sector": key,
        "label": prof["label"],
        "input": sector,
        "blocked": bool(prof.get("block")),
        "suppressed": sorted(set(suppressed)),
        "focus": prof.get("focus", []),
        "manual_inputs": prof.get("manual_inputs", []),
        "valuation": prof.get("valuation", {}),
        "notes": prof.get("notes", []),
        "altman_applicable": key not in BLOCK_ALTMAN,
    }


def main():
    ap = argparse.ArgumentParser(description="inspect the sector profiles")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--show")
    ap.add_argument("--resolve", help="test what a free-text sector maps to")
    args = ap.parse_args()

    if args.list or not (args.show or args.resolve):
        print(f"{'key':<14} {'valuation lens':<52} blocked")
        print("-" * 76)
        for k, p in PROFILES.items():
            print(f"{k:<14} {p['valuation']['primary'][:50]:<52} "
                  f"{'YES' if p.get('block') else ''}")
        print("\nAnything unmatched falls back to 'generic' (nothing suppressed).")
        return
    if args.resolve:
        k, p = resolve(args.resolve)
        print(f"{args.resolve!r} -> {k}  ({p['label']})")
        return
    k, p = resolve(args.show)
    print(json.dumps({k: p}, indent=2))


if __name__ == "__main__":
    main()
