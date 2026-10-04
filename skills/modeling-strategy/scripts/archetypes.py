#!/usr/bin/env python3
"""
archetypes.py — the controlled library of economic driver architectures.

    python3 archetypes.py --list
    python3 archetypes.py --show order_book_execution
    python3 archetypes.py --resolve "order book x execution"
    python3 archetypes.py --drivers capacity_utilisation_realisation

A sector label says what industry a company is filed under. An ARCHETYPE says how
its revenue is actually produced — which is the thing a model has to reproduce.
The two are related but not the same, and the mapping is many-to-many: a cement
company that also runs an EPC arm has two archetypes and one sector.

This library is deliberately CLOSED. `resolve()` returns None for anything not in
it, and the caller is expected to raise that to the analyst as a proposal rather
than inventing an architecture. That asymmetry is the whole point: the failure
mode being designed against is a confident, fluent, made-up revenue build.

Each archetype declares:

  revenue_drivers      the variables the revenue line is actually built from
  identity             the arithmetic, written out, so it can be checked by eye
  requires             disclosures that must exist for the archetype to be claimed
  schedules            model schedules this architecture implies beyond the default
  false_positive       the trap — why this archetype gets claimed when it is wrong
  translation          how it reaches the existing financial-model (see PHASE A)

PHASE A translation contract
----------------------------
`financial-model` has ONE revenue row: prev(revenue)*(1+rev_growth). No segment
rows, no driver build-up. So every archetype here must state how it reaches that
row. Three possibilities:

  derived_growth   the driver maths runs in the assumptions layer and lands as an
                   auditable per-year consolidated revenue_growth path
  native           the archetype already IS a growth rate (generic_growth only)
  unsupported      cannot be defensibly translated — the pipeline must REFUSE

Nothing here is `unsupported` today, but the field exists so that adding one is a
one-line declaration rather than a silent flattening.
"""
from __future__ import annotations

import argparse
import json

# --------------------------------------------------------------------------
# Drivers every material segment needs regardless of how its revenue is built.
# Kept separate so an archetype declares only what is distinctive about it.
# --------------------------------------------------------------------------
SEGMENT_COMMON: list[dict] = [
    {"id": "segment_margin", "label": "Segment EBIT or EBITDA margin", "unit": "%",
     "fma_preset": "ebit_margin",
     "note": "Segment-level margin. Where only a consolidated margin is disclosed, "
             "say so — a segment build on a consolidated margin is a weighted "
             "average pretending to be a decomposition."},
    {"id": "segment_capex_intensity", "label": "Capex to support the revenue path",
     "unit": "% of segment revenue", "fma_preset": "capex",
     "note": "The check that the growth path is funded. A capacity-led archetype "
             "whose capex does not rise with capacity is asserting free growth."},
    {"id": "segment_wc_days", "label": "Working-capital days for the segment",
     "unit": "days", "fma_preset": "dso",
     "note": "DSO always; DIO/DPO where the segment holds stock."},
]

ARCHETYPES: dict[str, dict] = {

    # ---------------------------------------------------------------- volume
    "volume_price": {
        "label": "Volume x Price",
        "aliases": ["volume x price", "volume and price", "volume-price",
                    "price volume", "volume x realisation"],
        "identity": "revenue = volume x average price",
        "revenue_drivers": [
            {"id": "volume", "label": "Units sold", "unit": "units",
             "fma_preset": "volume_growth"},
            {"id": "price", "label": "Average selling price / realisation",
             "unit": "INR per unit", "fma_preset": "pricing_growth"},
            {"id": "mix_effect", "label": "Mix shift", "unit": "% of revenue growth",
             "fma_preset": "pricing_growth", "optional": True},
        ],
        "requires": ["volume disclosed in units, tonnes or an equivalent physical measure",
                     "realisation or ASP disclosed, or derivable as revenue / volume"],
        "schedules": ["volume-price-mix bridge on revenue growth"],
        "false_positive":
            "Claimed for any company that sells a physical thing. It is only right "
            "when volume is DISCLOSED. Deriving volume as revenue/price when price "
            "was itself derived as revenue/volume is circular and produces a bridge "
            "that always ties and never informs.",
        "translation": "derived_growth",
    },

    "capacity_utilisation_realisation": {
        "label": "Capacity x Utilisation x Realisation",
        "aliases": ["capacity x utilisation", "capacity utilization",
                    "capacity x utilization x realization",
                    "capacity utilisation realisation"],
        "identity": "revenue = installed capacity x utilisation % x realisation per unit",
        "revenue_drivers": [
            {"id": "installed_capacity", "label": "Installed capacity",
             "unit": "physical units p.a.", "fma_preset": "capex"},
            {"id": "capacity_addition", "label": "Announced capacity additions and "
             "commissioning dates", "unit": "physical units p.a.", "fma_preset": "capex"},
            {"id": "utilisation", "label": "Capacity utilisation", "unit": "%",
             "fma_preset": "volume_growth"},
            {"id": "realisation", "label": "Realisation per unit",
             "unit": "INR per unit", "fma_preset": "pricing_growth"},
        ],
        "requires": ["installed capacity by plant or in total",
                     "utilisation %, or volume from which it can be computed",
                     "commissioning timeline for any capacity in the forecast"],
        "schedules": ["capacity roll-forward with commissioning lag",
                      "capex tied to the capacity additions being modelled"],
        "false_positive":
            "Utilisation above 100% in the forecast, or capacity appearing in the "
            "revenue line the same year the capex is spent. Capacity commissions "
            "with a lag and ramps; a step change is almost always wrong. This "
            "archetype's whole value is that it puts a CEILING on the forecast — "
            "if the model can exceed capacity, the archetype is decorative.",
        "translation": "derived_growth",
    },

    "units_asp": {
        "label": "Units x ASP",
        "aliases": ["units x asp", "units and asp", "unit x average selling price"],
        "identity": "revenue = units shipped x average selling price",
        "revenue_drivers": [
            {"id": "units", "label": "Units shipped", "unit": "units",
             "fma_preset": "volume_growth"},
            {"id": "asp", "label": "Average selling price", "unit": "INR per unit",
             "fma_preset": "pricing_growth"},
        ],
        "requires": ["unit shipments disclosed", "ASP disclosed or derivable"],
        "schedules": ["ASP trend against input cost, to test pricing power"],
        "false_positive":
            "Indistinguishable from volume_price for most businesses. Use this only "
            "where the unit is a discrete product with a quoted ASP (vehicles, "
            "handsets, appliances); use volume_price where the unit is a quantity "
            "(tonnes, litres, kWh).",
        "translation": "derived_growth",
    },

    "production_realisation": {
        "label": "Production volume x Commodity realisation",
        "aliases": ["production x realisation", "commodity", "production volume",
                    "production x realization"],
        "identity": "revenue = saleable production x realisation, where realisation "
                    "is set by an external reference price the company does not control",
        "revenue_drivers": [
            {"id": "production_volume", "label": "Saleable production",
             "unit": "physical units p.a.", "fma_preset": "volume_growth"},
            {"id": "reference_price", "label": "Reference / benchmark commodity price",
             "unit": "INR or USD per unit", "fma_preset": "pricing_growth"},
            {"id": "realisation_spread", "label": "Realisation vs the benchmark "
             "(premium, discount, hedges)", "unit": "%", "fma_preset": "pricing_growth"},
            {"id": "cost_curve_position", "label": "Unit cash cost / cost-curve position",
             "unit": "INR per unit", "fma_preset": "gross_margin"},
        ],
        "requires": ["production volume disclosed",
                     "an identifiable benchmark price for the output",
                     "unit cost, or a spread over the key input"],
        "schedules": ["mid-cycle realisation and margin, with the cycle window stated",
                      "spread over the key input cost"],
        "false_positive":
            "Holding the spot price flat, or worse, growing it. The company does not "
            "set this price. Extrapolating a peak realisation across a forecast is "
            "the single most common way a commodity model becomes fiction — anchor "
            "to mid-cycle and SAY which years were treated as the cycle.",
        "translation": "derived_growth",
    },

    # ------------------------------------------------------------ order book
    "order_book_execution": {
        "label": "Order Book x Execution",
        "aliases": ["order book", "order book x execution", "orderbook",
                    "order inflow", "epc", "book to bill"],
        "identity": "revenue = opening order book x execution rate + inflow executed "
                    "within the year;  closing book = opening + inflow - revenue",
        "revenue_drivers": [
            {"id": "opening_order_book", "label": "Opening order book",
             "unit": "INR cr", "fma_preset": "guidance"},
            {"id": "order_inflow", "label": "Order inflow / new order wins",
             "unit": "INR cr p.a.", "fma_preset": "guidance"},
            {"id": "execution_rate", "label": "Execution rate (share of the book "
             "converted to revenue in the year)", "unit": "%",
             "fma_preset": "guidance"},
            {"id": "book_to_bill", "label": "Book-to-bill", "unit": "x",
             "fma_preset": "guidance", "optional": True},
        ],
        "requires": ["order book or unexecuted order value disclosed",
                     "order inflow, or enough history to infer it",
                     "an execution period or book-to-bill from management"],
        "schedules": ["order book roll-forward: opening + inflow - executed = closing",
                      "execution timeline by project vintage where disclosed"],
        "false_positive":
            "Modelling revenue growth and back-filling an order book that ties. The "
            "book is the CONSTRAINT, not the output. Two hard checks: the closing "
            "book must never go negative, and an execution rate that rises while the "
            "book ages is a claim about project mix that has to be argued, not "
            "assumed. Also: order book is usually disclosed ex-GST and ex-escalation "
            "while revenue is not — check the basis before dividing one by the other.",
        "translation": "derived_growth",
    },

    "project_pipeline_completion": {
        "label": "Project Pipeline x Completion / Execution",
        "aliases": ["project pipeline", "pipeline x completion", "projects",
                    "pre-sales", "bookings"],
        "identity": "revenue recognised = f(project completion), which is decoupled "
                    "from pre-sales bookings and from collections",
        "revenue_drivers": [
            {"id": "pipeline_value", "label": "Launched + planned project value",
             "unit": "INR cr", "fma_preset": "guidance"},
            {"id": "presales_bookings", "label": "Pre-sales / bookings",
             "unit": "INR cr p.a.", "fma_preset": "guidance"},
            {"id": "collection_efficiency", "label": "Collections as % of bookings",
             "unit": "%", "fma_preset": "dso"},
            {"id": "completion_schedule", "label": "Completion / handover schedule",
             "unit": "% per year", "fma_preset": "guidance"},
        ],
        "requires": ["project-wise or aggregate pipeline value",
                     "pre-sales and collections disclosed",
                     "a completion or handover timeline"],
        "schedules": ["pipeline roll-forward", "bookings-to-collections-to-revenue bridge",
                      "project-level debt against project cash flows"],
        "false_positive":
            "Treating reported revenue as the business. Revenue here is an accounting "
            "consequence of completion; the ECONOMICS are bookings and collections, "
            "and they lead revenue by years. A working-capital assumption struck off "
            "reported revenue is wrong for this archetype — strike it off collections. "
            "'Inventory' is capitalised project cost, so inventory days are meaningless.",
        "translation": "derived_growth",
    },

    # ------------------------------------------------------------- recurring
    "customers_arpu": {
        "label": "Customers x ARPU",
        "aliases": ["customers x arpu", "accounts x arpu", "users x arpu"],
        "identity": "revenue = average customers x ARPU;  customers = opening + adds "
                    "- churn",
        "revenue_drivers": [
            {"id": "opening_customers", "label": "Opening customer count",
             "unit": "count", "fma_preset": "new_customers"},
            {"id": "customer_adds", "label": "Gross additions", "unit": "count p.a.",
             "fma_preset": "new_customers"},
            {"id": "churn", "label": "Churn / attrition", "unit": "% p.a.",
             "fma_preset": "customer_retention"},
            {"id": "arpu", "label": "Average revenue per customer", "unit": "INR p.a.",
             "fma_preset": "pricing_growth"},
        ],
        "requires": ["customer or account count disclosed",
                     "ARPU disclosed or derivable as revenue / average customers",
                     "churn or retention disclosed"],
        "schedules": ["customer roll-forward: opening + adds - churn = closing",
                      "cohort or vintage ARPU where disclosed"],
        "false_positive":
            "Using closing rather than average customers against a full year of "
            "revenue — that overstates ARPU by roughly half the year's growth. And "
            "adds without churn is not a roll-forward, it is a ratchet.",
        "translation": "derived_growth",
    },

    "subscribers_arpu": {
        "label": "Subscribers x ARPU",
        "aliases": ["subscribers x arpu", "subs x arpu", "subscription",
                    "saas", "arpu"],
        "identity": "revenue = average subscribers x ARPU x (billing periods per year)",
        "revenue_drivers": [
            {"id": "opening_subscribers", "label": "Opening subscribers", "unit": "count",
             "fma_preset": "new_customers"},
            {"id": "net_adds", "label": "Net subscriber additions", "unit": "count p.a.",
             "fma_preset": "new_customers"},
            {"id": "churn", "label": "Subscriber churn", "unit": "% p.a.",
             "fma_preset": "customer_retention"},
            {"id": "arpu", "label": "ARPU", "unit": "INR per subscriber per period",
             "fma_preset": "pricing_growth"},
            {"id": "net_revenue_retention", "label": "Net revenue retention", "unit": "%",
             "fma_preset": "customer_retention", "optional": True},
        ],
        "requires": ["subscriber count disclosed",
                     "ARPU or an equivalent per-subscriber revenue measure",
                     "churn, or net revenue retention"],
        "schedules": ["subscriber roll-forward",
                      "deferred revenue where billing leads recognition"],
        "false_positive":
            "Mixing an ARPU quoted per month with an annual subscriber count. Also: "
            "for a subscription business, deferred revenue and billings can diverge "
            "from recognised revenue for years — if the disclosure supports billings, "
            "model billings and derive revenue, not the reverse.",
        "translation": "derived_growth",
    },

    "stores_sales_per_store": {
        "label": "Stores x Sales per Store",
        "aliases": ["stores x sales per store", "store count", "retail",
                    "sss", "same store sales"],
        "identity": "revenue = average store count x sales per store, decomposed into "
                    "new-store contribution and same-store sales growth",
        "revenue_drivers": [
            {"id": "opening_stores", "label": "Opening store count", "unit": "count",
             "fma_preset": "new_customers"},
            {"id": "store_adds", "label": "Store openings, net of closures",
             "unit": "count p.a.", "fma_preset": "capex"},
            {"id": "sales_per_store", "label": "Sales per store (or per sq ft)",
             "unit": "INR cr p.a.", "fma_preset": "revenue_growth"},
            {"id": "sss_growth", "label": "Same-store sales growth", "unit": "%",
             "fma_preset": "revenue_growth"},
            {"id": "maturity_curve", "label": "New-store maturity ramp", "unit": "%",
             "fma_preset": "revenue_growth", "optional": True},
        ],
        "requires": ["store count disclosed",
                     "same-store sales growth, or sales per store / per sq ft"],
        "schedules": ["store roll-forward with the maturity ramp",
                      "capex per new store, tied to the store additions modelled",
                      "lease liability where stores are leased"],
        "false_positive":
            "Applying full-format sales to a store opened in month eleven. New stores "
            "ramp; a store-count model without a maturity assumption systematically "
            "overstates the first two forecast years. And SSS plus new stores is not "
            "additive with store-count growth — pick one decomposition and hold it.",
        "translation": "derived_growth",
    },

    "rooms_occupancy_arr": {
        "label": "Rooms x Occupancy x ARR",
        "aliases": ["rooms x occupancy", "revpar", "hotels", "hospitality",
                    "rooms x occupancy x arr"],
        "identity": "room revenue = available room nights x occupancy % x ARR "
                    "(= room nights x RevPAR); total revenue adds F&B and other",
        "revenue_drivers": [
            {"id": "keys", "label": "Room keys (owned, leased, managed separately)",
             "unit": "count", "fma_preset": "capex"},
            {"id": "occupancy", "label": "Occupancy", "unit": "%",
             "fma_preset": "volume_growth"},
            {"id": "arr", "label": "Average room rate", "unit": "INR per night",
             "fma_preset": "pricing_growth"},
            {"id": "non_room_revenue", "label": "F&B and other revenue",
             "unit": "% of room revenue", "fma_preset": "revenue_growth"},
        ],
        "requires": ["room inventory disclosed",
                     "occupancy and ARR, or RevPAR",
                     "owned vs managed split — the economics differ completely"],
        "schedules": ["key roll-forward with pipeline and ramp",
                      "owned vs managed revenue split (managed is a fee stream, "
                      "not a room-night stream)"],
        "false_positive":
            "Applying owned-hotel economics to managed keys. A management contract "
            "earns a fee on the OWNER's revenue and carries almost no capital — "
            "putting managed keys through an ARR build inflates both revenue and "
            "capex. If the split is not disclosed, that is a segmentation limitation, "
            "not a detail.",
        "translation": "derived_growth",
    },

    "headcount_utilisation_realisation": {
        "label": "Headcount x Utilisation x Billing rate",
        "aliases": ["headcount x utilisation", "it services", "billable headcount",
                    "headcount x utilization x realization", "pyramid"],
        "identity": "revenue = billable headcount x utilisation % x realisation per "
                    "billable person",
        "revenue_drivers": [
            {"id": "headcount", "label": "Billable headcount", "unit": "count",
             "fma_preset": "employee_cost"},
            {"id": "utilisation", "label": "Utilisation", "unit": "%",
             "fma_preset": "employee_cost"},
            {"id": "realisation", "label": "Revenue per billable employee / billing rate",
             "unit": "INR p.a.", "fma_preset": "pricing_growth"},
            {"id": "attrition", "label": "Attrition", "unit": "%",
             "fma_preset": "employee_cost"},
            {"id": "tcv_conversion", "label": "Deal TCV and its conversion period",
             "unit": "USD mn / months", "fma_preset": "guidance", "optional": True},
        ],
        "requires": ["headcount disclosed",
                     "utilisation, or revenue per employee",
                     "onsite-offshore mix where it is material to realisation"],
        "schedules": ["headcount roll-forward with attrition",
                      "wage inflation against the pyramid and utilisation offsets"],
        "false_positive":
            "Growing revenue per employee indefinitely to make a margin work. Wage "
            "inflation is the dominant cost lever and it is not optional; a forecast "
            "that holds employee cost flat as a % of sales while growing realisation "
            "is asserting a productivity gain that has to be named (pyramid, "
            "automation, mix) and defended.",
        "translation": "derived_growth",
    },

    # ---------------------------------------------------------------- fallback
    "generic_growth": {
        "label": "Generic revenue growth (no validated driver architecture)",
        "aliases": ["generic", "growth", "top-down growth", "consolidated growth"],
        "identity": "revenue = prior revenue x (1 + growth)",
        "revenue_drivers": [
            {"id": "revenue_growth", "label": "Revenue growth", "unit": "%",
             "fma_preset": "revenue_growth"},
        ],
        "requires": [],
        "schedules": [],
        "false_positive":
            "This is the HONEST fallback, not a default. It says the disclosure does "
            "not support a driver build. Using it where drivers ARE disclosed throws "
            "away the analysis; using it silently for most of the revenue is the "
            "false-precision failure this whole layer exists to prevent — hence the "
            "materiality cap in check_strategy.py.",
        "translation": "native",
        "fallback": True,
    },
}

# A segment on generic_growth is a stated limitation. Above this share of total
# revenue it stops being a limitation and becomes the model, which caps
# modelability at AMBER. See check_strategy.py.
GENERIC_MATERIALITY_CAP_PCT = 40.0

# Below this share of revenue a segment does not get its own architecture — that
# is fake granularity. It is folded into the consolidated build and said so.
SEGMENT_MATERIALITY_FLOOR_PCT = 10.0


def resolve(name: str | None) -> tuple[str, dict] | None:
    """Free text -> archetype. Returns None when nothing matches.

    None is a RESULT, not an error: the caller must surface it to the analyst as
    a proposed archetype rather than inventing one. Matching is exact-then-alias
    only. There is deliberately no fuzzy fallback — a near-miss that silently
    lands on the wrong architecture is worse than an explicit unknown.
    """
    if not name:
        return None
    s = str(name).strip().lower().replace("_", " ").replace("×", "x")
    s = " ".join(s.split())
    for key, spec in ARCHETYPES.items():
        if s == key.replace("_", " ") or s == key:
            return key, spec
        if s == spec["label"].lower():
            return key, spec
        for a in spec.get("aliases", []):
            if s == a.lower():
                return key, spec
    return None


def required_drivers(key: str, include_common: bool = True) -> list[dict]:
    """Every driver a segment on this archetype must have an assumption for.

    Optional drivers are included with their `optional` flag intact — the
    coverage check in financial-model-assumptions treats them as nice-to-have.
    """
    spec = ARCHETYPES.get(key)
    if spec is None:
        raise KeyError(f"unknown archetype {key!r}")
    out = [dict(d) for d in spec["revenue_drivers"]]
    if include_common:
        out += [dict(d) for d in SEGMENT_COMMON]
    return out


def keys() -> list[str]:
    return list(ARCHETYPES)


def main():
    ap = argparse.ArgumentParser(description="the validated archetype library")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--show", help="full spec for one archetype")
    ap.add_argument("--resolve", help="test what free text maps to")
    ap.add_argument("--drivers", help="required drivers for one archetype")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    a = ap.parse_args()

    if a.resolve:
        r = resolve(a.resolve)
        if r is None:
            print(f"{a.resolve!r} -> NO MATCH")
            print("  Not in the validated library. Raise it to the analyst as a "
                  "proposed archetype; do not invent an architecture.")
            raise SystemExit(2)
        print(f"{a.resolve!r} -> {r[0]}  ({r[1]['label']})")
        return

    if a.drivers:
        r = resolve(a.drivers)
        if r is None:
            raise SystemExit(f"unknown archetype {a.drivers!r}")
        ds = required_drivers(r[0])
        if a.json:
            print(json.dumps(ds, indent=2))
            return
        print(f"{r[1]['label']}\n  {r[1]['identity']}\n")
        for d in ds:
            opt = "  (optional)" if d.get("optional") else ""
            print(f"  {d['id']:<26} {d['label']} [{d['unit']}]{opt}")
        return

    if a.show:
        r = resolve(a.show)
        if r is None:
            raise SystemExit(f"unknown archetype {a.show!r}")
        print(json.dumps({r[0]: r[1]}, indent=2))
        return

    if a.json:
        print(json.dumps(ARCHETYPES, indent=2))
        return

    print(f"{'key':<36} {'identity':<40}")
    print("-" * 78)
    for k, s in ARCHETYPES.items():
        ident = s["identity"].split(";")[0]
        print(f"{k:<36} {ident[:40]}")
    print(f"\n{len(ARCHETYPES)} validated archetypes. Anything else is a PROPOSAL "
          "requiring analyst sign-off.")


if __name__ == "__main__":
    main()
