#!/usr/bin/env python3
"""
valuation.py — which valuation methods are admissible, and who can compute them.

    python3 valuation.py --list
    python3 valuation.py --show fcff_dcf
    python3 valuation.py --assess facts.json

Two separate questions, deliberately kept apart:

  1. Is this method ECONOMICALLY appropriate for this business?
  2. Can anything in this pipeline actually COMPUTE it?

Conflating them is how a pipeline ends up doing an FCFF DCF on a company whose
value is a portfolio of assets — the DCF was not chosen, it was the only thing
available. So `assess()` answers (1) with no reference to (2), and
`execution_owner` answers (2) with no reference to (1).

When the right method has no owner, the honest output is: method PRIMARY,
execution_owner analyst_manual, modelability AMBER, and an explicit statement of
what a human has to finish. Never a downgrade to whatever the pipeline can run.

WHAT THIS PIPELINE CAN COMPUTE (verified against the code, not assumed)

  model.py      FCFF DCF (dcf()), WACC build-up, sensitivity, scenarios,
                and P/E, EV/EBITDA, EV/Sales, P/B via relative()
  peer-comps    the same four trailing multiples, with medians, quartiles and
                football-field bands
  everything else   analyst_manual

`assess()` returns a PROPOSAL. Every applicability call is editable by the
analyst in strategy_decisions.json, and the hard disqualifiers below are the only
things it will not let an analyst assert away silently.
"""
from __future__ import annotations

import argparse
import json

MODEL_PY = "model.py"
PEER_COMPS = "peer-comps"
MANUAL = "analyst_manual"
NOT_SUPPORTED = "not_supported"

ROLES = ["PRIMARY", "SECONDARY", "CROSS_CHECK", "LOW_RELIABILITY", "NOT_APPROPRIATE"]
APPLICABILITY = ["HIGH", "MEDIUM", "LOW", "NOT_APPROPRIATE"]

METHODS: dict[str, dict] = {

    "fcff_dcf": {
        "label": "FCFF DCF",
        "execution_owner": MODEL_PY,
        "measures": "enterprise value from unlevered operating cash flow",
        "requires": [
            "operating cash flows that are positive, or credibly turn positive "
            "inside the forecast horizon",
            "identifiable capital requirements (capex and working capital)",
            "a capital structure stable enough for a single WACC",
        ],
        "limitations": [
            "terminal value dominates when the horizon is short relative to the "
            "growth runway — report TV as % of EV",
            "invalid where interest is revenue (lenders)",
        ],
        "disqualify": ["financial_sector"],
        "note": "The pipeline's default. That is exactly why it needs a positive "
                "argument each time rather than an absence of objection.",
    },

    "fcfe": {
        "label": "FCFE / equity DCF",
        "execution_owner": MANUAL,
        "measures": "equity value directly, after debt service",
        "requires": [
            "a debt schedule with forecastable drawdowns and repayments",
            "leverage that is stable or explicitly modelled through the forecast",
        ],
        "limitations": [
            "very sensitive to the debt path; a changing capital structure moves "
            "value more than the operating forecast does",
        ],
        "disqualify": [],
        "note": "The right lens when leverage is the story rather than a parameter "
                "— highly levered infrastructure, project SPVs. model.py computes "
                "FCFF only; financial-model's bridge carries an FCFE line that an "
                "analyst can discount by hand at the cost of equity.",
    },

    "ev_ebitda": {
        "label": "EV/EBITDA",
        "execution_owner": PEER_COMPS,
        "measures": "enterprise value against pre-D&A operating profit",
        "requires": [
            "positive EBITDA",
            "a peer set of at least three comparable companies",
            "broadly comparable capital intensity across the set",
        ],
        "limitations": [
            "blind to depreciation, so it flatters capital-intensive businesses "
            "against asset-light ones",
            "blind to differences in lease accounting",
        ],
        "disqualify": ["negative_ebitda", "financial_sector", "no_peer_set"],
        "note": "Availability is not a reason to use it. For a business whose "
                "capital consumption IS the economics, EV/EBIT is the fairer lens.",
    },

    "ev_ebit": {
        "label": "EV/EBIT",
        "execution_owner": MANUAL,
        "measures": "enterprise value against post-depreciation operating profit",
        "requires": ["positive EBIT", "a comparable peer set"],
        "limitations": [
            "depreciation policy differences across peers feed straight through",
        ],
        "disqualify": ["negative_ebit", "financial_sector", "no_peer_set"],
        "note": "Preferred over EV/EBITDA where capital intensity differs widely "
                "across the peer set. peer-comps does not emit it today; it is "
                "computable by hand from the peers.json EV and EBIT figures.",
    },

    "pe": {
        "label": "P/E",
        "execution_owner": PEER_COMPS,
        "measures": "equity value against net earnings",
        "requires": ["positive and reasonably sustainable earnings",
                     "a comparable peer set"],
        "limitations": [
            "differences in leverage and in the effective tax rate reduce "
            "comparability directly",
            "near-useless at a cyclical trough or peak, when earnings are the "
            "volatile term",
        ],
        "disqualify": ["negative_pat", "financial_sector_ok", "no_peer_set"],
        "note": "The `financial_sector_ok` marker means P/E is not disqualified "
                "for a lender on economic grounds — but this pipeline does not "
                "model lenders at all, so the point is moot here.",
    },

    "ev_sales": {
        "label": "EV/Sales",
        "execution_owner": PEER_COMPS,
        "measures": "enterprise value against revenue",
        "requires": ["a peer set with comparable margin structure"],
        "limitations": [
            "ignores profitability entirely — only defensible when margins across "
            "the set are similar, or when the thesis is an explicit margin-recovery "
            "argument stated as such",
        ],
        "disqualify": ["financial_sector", "no_peer_set"],
        "note": "The standard fallback for a loss-making company, and the one that "
                "most needs its margin assumption written down next to it.",
    },

    "pb": {
        "label": "P/B",
        "execution_owner": PEER_COMPS,
        "measures": "equity value against book equity",
        "requires": ["book value that approximates the economic asset base"],
        "limitations": [
            "meaningless where value sits in intangibles the balance sheet does "
            "not carry",
            "distorted by historical-cost land and by revaluation reserves",
        ],
        "disqualify": [],
        "note": "Informative for asset-heavy and cyclical businesses, weak for "
                "asset-light ones. Pair it with ROE or it says nothing.",
    },

    "sotp": {
        "label": "Sum of the parts",
        "execution_owner": MANUAL,
        "measures": "each business valued on its own basis, then aggregated",
        "requires": [
            "two or more segments with genuinely different economics",
            "segment-level financials sufficient to value each part",
            "a defensible holding-company discount, or a reason there is none",
        ],
        "limitations": [
            "the aggregate is only as good as the weakest part's valuation",
            "double-counts central costs unless they are explicitly allocated or "
            "valued as a separate negative",
        ],
        "disqualify": ["single_segment"],
        "note": "The correct primary method for a genuine conglomerate. Nothing in "
                "this pipeline computes it — the parts can be valued individually "
                "and aggregated by the analyst, and the strategy must say so.",
    },

    "nav": {
        "label": "NAV / asset-based",
        "execution_owner": MANUAL,
        "measures": "the marked value of assets less liabilities",
        "requires": [
            "assets that are separately marketable and markable",
            "an observable market or an appraisal basis for those assets",
        ],
        "limitations": [
            "captures no going-concern or franchise value",
            "for a developer, entirely dependent on the assumed realisation and "
            "timing of each project",
        ],
        "disqualify": ["operating_business_no_markable_assets"],
        "note": "Primary for real-estate developers and holding companies. It is a "
                "floor, not a fair value, for an operating business.",
    },

    "ffo_affo": {
        "label": "FFO / AFFO multiple or yield",
        "execution_owner": MANUAL,
        "measures": "distributable cash flow of a rent-yielding asset pool",
        "requires": [
            "a stabilised, rent-yielding asset base",
            "a REIT/InvIT-like distribution structure, or economics close to one",
        ],
        "limitations": [
            "AFFO depends on a maintenance-capex assumption that is a judgement, "
            "not a disclosure",
        ],
        "disqualify": ["not_yield_asset"],
        "note": "For REITs and InvITs. Depreciation makes P/E meaningless for "
                "these, which is the reason the measure exists.",
    },

    "ev_per_unit": {
        "label": "EV per tonne / per unit of capacity",
        "execution_owner": MANUAL,
        "measures": "enterprise value against physical capacity",
        "requires": ["a homogeneous physical output", "disclosed capacity"],
        "limitations": [
            "ignores cost position entirely — two identical-capacity plants at "
            "opposite ends of the cost curve are not worth the same",
        ],
        "disqualify": ["no_physical_capacity"],
        "note": "A cycle-independent cross-check for commodities, which is exactly "
                "when the earnings-based multiples stop working.",
    },

    "replacement_cost": {
        "label": "Replacement cost",
        "execution_owner": MANUAL,
        "measures": "the cost of rebuilding the asset base today",
        "requires": ["capital cost per unit of capacity, currently observable"],
        "limitations": ["a ceiling on a cyclical peak and a floor at a trough, "
                        "rarely a fair value in between"],
        "disqualify": ["no_physical_capacity"],
        "note": "Most useful stated as a ratio to EV, alongside EV per unit.",
    },

    "ddm": {
        "label": "Dividend discount",
        "execution_owner": MANUAL,
        "measures": "equity value from the dividend stream",
        "requires": ["a stable, policy-driven payout with a long history"],
        "limitations": ["says nothing about a company that retains its cash"],
        "disqualify": ["no_dividend_history"],
        "note": "Mostly relevant to lenders and utilities. Out of scope here for "
                "the former; occasionally a cross-check for the latter.",
    },
}

# Hard disqualifiers: an analyst may not mark a method PRIMARY or SECONDARY while
# the fact that disqualifies it holds. These are arithmetic, not taste.
HARD = {
    "negative_ebitda": "EBITDA is negative — the multiple has no interpretation",
    "negative_ebit": "EBIT is negative — the multiple has no interpretation",
    "negative_pat": "earnings are negative — the multiple has no interpretation",
    "financial_sector": "banks, NBFCs and insurers are out of scope for this pipeline",
    "no_peer_set": "fewer than three comparable peers — a median is not meaningful",
    "single_segment": "SOTP needs two or more segments with different economics",
}


def _facts_from(fin: dict | None, strategy_facts: dict | None = None) -> dict:
    """Derive the applicability facts from a parsed financials.json.

    Only reads what it can verify. A fact it cannot establish is absent, and an
    absent fact never disqualifies anything — the analyst is asked instead.
    """
    f: dict = {}
    if strategy_facts:
        f.update(strategy_facts)
    if not fin:
        return f

    def _last(*names):
        blocks = [fin.get(k) for k in ("pl", "profit_loss", "annual", "income_statement")]
        for b in blocks:
            if not isinstance(b, dict):
                continue
            for n in names:
                for k, v in b.items():
                    if k.strip().lower() == n.lower() and isinstance(v, list):
                        vals = [x for x in v if isinstance(x, (int, float))]
                        if vals:
                            return vals[-1]
        return None

    ebitda = _last("Operating Profit", "EBITDA")
    pat = _last("Net Profit", "PAT", "Profit after tax")
    dep = _last("Depreciation")
    if ebitda is not None:
        f.setdefault("ebitda", ebitda)
        f.setdefault("negative_ebitda", ebitda <= 0)
        if dep is not None:
            f.setdefault("negative_ebit", (ebitda - dep) <= 0)
    if pat is not None:
        f.setdefault("pat", pat)
        f.setdefault("negative_pat", pat <= 0)
    return f


def assess(facts: dict) -> dict:
    """Propose an applicability for every method from the facts available.

    HIGH / MEDIUM / LOW / NOT_APPROPRIATE, each with a reason. This is a starting
    point for the analyst, not a verdict — except NOT_APPROPRIATE arising from a
    HARD disqualifier, which check_strategy.py will not let a role override.
    """
    out = {}
    for key, m in METHODS.items():
        hard_hit = [d for d in m["disqualify"] if d in HARD and facts.get(d)]
        if hard_hit:
            out[key] = {
                "applicability": "NOT_APPROPRIATE",
                "reason": HARD[hard_hit[0]],
                "hard": True,
                "execution_owner": m["execution_owner"],
            }
            continue
        soft_hit = [d for d in m["disqualify"] if d not in HARD and facts.get(d)]
        if soft_hit:
            out[key] = {
                "applicability": "LOW",
                "reason": f"condition '{soft_hit[0]}' holds — argue the method or drop it",
                "hard": False,
                "execution_owner": m["execution_owner"],
            }
            continue
        out[key] = {
            "applicability": None,
            "reason": "no disqualifying fact established — the analyst must argue "
                      "applicability from the business economics",
            "hard": False,
            "execution_owner": m["execution_owner"],
        }
    return out


def owner(method_key: str) -> str:
    m = METHODS.get(method_key)
    return m["execution_owner"] if m else NOT_SUPPORTED


def resolve(name: str | None) -> tuple[str, dict] | None:
    if not name:
        return None
    s = str(name).strip().lower().replace(" ", "_").replace("/", "_").replace("-", "_")
    s = s.replace("__", "_")
    if s in METHODS:
        return s, METHODS[s]
    for k, m in METHODS.items():
        if s == m["label"].lower().replace(" ", "_").replace("/", "_"):
            return k, m
    aliases = {
        "dcf": "fcff_dcf", "fcff": "fcff_dcf", "fcff_dcf": "fcff_dcf",
        "ev_ebitda": "ev_ebitda", "evebitda": "ev_ebitda",
        "p_e": "pe", "price_earnings": "pe",
        "p_b": "pb", "price_book": "pb",
        "ev_sales": "ev_sales", "ev_revenue": "ev_sales",
        "sum_of_the_parts": "sotp", "sum_of_parts": "sotp",
        "net_asset_value": "nav", "p_nav": "nav",
        "ffo": "ffo_affo", "affo": "ffo_affo", "ffo_affo": "ffo_affo",
        "ev_tonne": "ev_per_unit", "ev_per_tonne": "ev_per_unit",
        "dividend_discount": "ddm", "ddm": "ddm",
    }
    if s in aliases:
        k = aliases[s]
        return k, METHODS[k]
    return None


def main():
    ap = argparse.ArgumentParser(description="valuation method applicability")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--show")
    ap.add_argument("--resolve")
    ap.add_argument("--assess", help="a JSON file of facts, or '-' for stdin")
    a = ap.parse_args()

    if a.resolve:
        r = resolve(a.resolve)
        print(f"{a.resolve!r} -> {r[0] if r else 'NO MATCH'}")
        raise SystemExit(0 if r else 2)

    if a.show:
        r = resolve(a.show)
        if not r:
            raise SystemExit(f"unknown method {a.show!r}")
        print(json.dumps({r[0]: r[1]}, indent=2))
        return

    if a.assess:
        import sys
        facts = json.load(sys.stdin if a.assess == "-" else open(a.assess))
        print(json.dumps(assess(facts), indent=2))
        return

    print(f"{'key':<18} {'owner':<14} {'label'}")
    print("-" * 70)
    for k, m in METHODS.items():
        print(f"{k:<18} {m['execution_owner']:<14} {m['label']}")
    print("\nowner = who can actually compute it. `analyst_manual` is a legitimate "
          "answer for a PRIMARY method; it caps modelability at AMBER.")


if __name__ == "__main__":
    main()
