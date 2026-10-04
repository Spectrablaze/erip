#!/usr/bin/env python3
"""Adversarial tests for the modeling-strategy layer.

Asserts on BEHAVIOUR — does it choose a sensible architecture, identify
inappropriate valuation methods, recognise uncertainty, ask for intervention,
and refuse — not on a particular archetype string.
"""
import json, os, sys, subprocess

MS = os.path.expanduser("~/.claude/skills/modeling-strategy/scripts")
sys.path.insert(0, MS)
import archetypes as AR
import valuation as VAL
import build_strategy as BS
import check_strategy as CHK
import segment_build as SB

PASS, FAIL = [], []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + (f" — {detail}" if detail and not cond else ""))


def seg(name, mat, arch, drivers=None, conf="High", ev=True, proposed=None):
    spec = AR.ARCHETYPES.get(arch)
    ds = drivers if drivers is not None else (
        [{"id": d["id"], "evidence": [{"quote": "q", "source": "kb", "page": 1}]}
         for d in spec["revenue_drivers"] if not d.get("optional")] if spec else [])
    return {"name": name, "materiality_pct": mat, "economic_archetype": arch,
            "proposed_archetype": proposed, "revenue_drivers": ds,
            "margin_drivers": [{"id": "segment_margin"}],
            "capital_drivers": [{"id": "segment_capex_intensity"}],
            "working_capital_drivers": [{"id": "segment_wc_days"}],
            "evidence": ([{"quote": "how it earns revenue", "source": "kb", "page": 9}]
                         if ev else []),
            "confidence": conf, "status": "recommended"}


def m(method, role, appl="HIGH", why="because", **kw):
    d = {"method": method, "role": role, "applicability": appl, "rationale": why}
    d.update(kw)
    return d


def build(**kw):
    base = {"company": "Test Co", "ticker": "TEST", "scope_status": "IN_SCOPE",
            "sector": "manufacturing", "peer_count": 4,
            "business_description": "d", "segments": [], "valuation_methods": [],
            "analyst_decision": {"status": "APPROVED"}}
    base.update(kw)
    return BS.build(base, None)


def roles(S):
    r = {x["method"]: x.get("role") for x in S["valuation_methods"]}
    r.update({x["method"]: "NOT_APPROPRIATE" for x in S["rejected_methods"]})
    return r


def codes(S):
    return {c["code"] for c in S["checks"]}


print("\n=== 1. Conventional manufacturing ===")
S = build(segments=[seg("Plant", 100, "capacity_utilisation_realisation")],
          valuation_methods=[m("fcff_dcf", "PRIMARY"), m("ev_ebitda", "CROSS_CHECK"),
                             m("pe", "SECONDARY", "MEDIUM")])
check("GREEN", S["modelability"]["status"] == "GREEN", S["modelability"]["rationale"])
check("capacity architecture kept", S["segments"][0]["economic_archetype"] ==
      "capacity_utilisation_realisation")
check("FCFF primary, EV/EBITDA cross-check",
      roles(S)["fcff_dcf"] == "PRIMARY" and roles(S)["ev_ebitda"] == "CROSS_CHECK")
check("capacity schedules required", any("commissioning" in s for s in
      S["model_architecture"]["required_schedules"]))
check("utilisation is a required driver",
      "utilisation" in {d["driver_id"] for d in S["required_drivers"]})

print("\n=== 2. EPC / order book ===")
S = build(sector="realestate",
          segments=[seg("EPC", 100, "order_book_execution")],
          valuation_methods=[m("fcff_dcf", "PRIMARY"), m("ev_ebitda", "CROSS_CHECK"),
                             m("nav", "NOT_APPROPRIATE",
                               why="the balance sheet does not carry the order book")])
check("GREEN", S["modelability"]["status"] == "GREEN")
check("order-book drivers required",
      {"opening_order_book", "order_inflow", "execution_rate"} <=
      {d["driver_id"] for d in S["required_drivers"]})
check("order book roll-forward scheduled",
      any("roll-forward" in s for s in S["model_architecture"]["required_schedules"]))
check("NAV explicitly rejected with a reason",
      any(r["method"] == "nav" and r["reason"] for r in S["rejected_methods"]))

print("\n=== 3. IT services ===")
S = build(sector="services",
          segments=[seg("Services", 100, "headcount_utilisation_realisation")],
          valuation_methods=[m("fcff_dcf", "PRIMARY"), m("pe", "SECONDARY"),
                             m("ev_ebitda", "CROSS_CHECK"),
                             m("pb", "NOT_APPROPRIATE",
                               why="value sits in people, not on the balance sheet")])
check("GREEN", S["modelability"]["status"] == "GREEN")
check("headcount/utilisation/realisation required",
      {"headcount", "utilisation", "realisation"} <=
      {d["driver_id"] for d in S["required_drivers"]})
check("P/B rejected", roles(S).get("pb") == "NOT_APPROPRIATE")

print("\n=== 4. Consumer / retail ===")
S = build(sector="consumer",
          segments=[seg("Retail", 60, "stores_sales_per_store"),
                    seg("Wholesale", 40, "volume_price")],
          valuation_methods=[m("fcff_dcf", "PRIMARY"), m("ev_ebitda", "CROSS_CHECK"),
                             m("pe", "SECONDARY")])
check("GREEN", S["modelability"]["status"] == "GREEN")
check("two different architectures kept",
      len({s["economic_archetype"] for s in S["segments"]}) == 2)
check("volume and price are separate drivers",
      {"volume", "price"} <= {d["driver_id"] for d in S["required_drivers"]})
check("store maturity ramp scheduled",
      any("maturity" in s for s in S["model_architecture"]["required_schedules"]))

print("\n=== 5. Hotels ===")
S = build(segments=[seg("Owned hotels", 100, "rooms_occupancy_arr")],
          valuation_methods=[m("fcff_dcf", "PRIMARY"), m("ev_ebitda", "SECONDARY"),
                             m("pe", "LOW_RELIABILITY", "LOW",
                               why="D&A intensity makes earnings a poor comparator"),
                             m("ev_per_unit", "CROSS_CHECK", why="EV per key")])
check("GREEN", S["modelability"]["status"] == "GREEN")
check("rooms/occupancy/ARR required", {"keys", "occupancy", "arr"} <=
      {d["driver_id"] for d in S["required_drivers"]})
check("P/E demoted, not silently used", roles(S)["pe"] == "LOW_RELIABILITY")
check("EV per key flagged as manual",
      [x for x in S["valuation_methods"] if x["method"] == "ev_per_unit"
       ][0]["execution_owner"] == "analyst_manual")

print("\n=== 6. Commodity producer ===")
S = build(sector="commodity",
          segments=[seg("Mining", 100, "production_realisation")],
          valuation_methods=[m("fcff_dcf", "PRIMARY",
                               why="on mid-cycle realisation, cycle window stated"),
                             m("ev_ebitda", "CROSS_CHECK"),
                             m("ev_per_unit", "CROSS_CHECK",
                               why="cycle-independent"),
                             m("pe", "LOW_RELIABILITY", "LOW",
                               why="earnings are the volatile term at a cycle extreme")],
          uncertainties=[{"issue": "cycle position", "impact": "terminal margin",
                          "required_resolution": "10y realisation history"}])
check("GREEN", S["modelability"]["status"] == "GREEN")
check("benchmark price is a driver", "reference_price" in
      {d["driver_id"] for d in S["required_drivers"]})
check("mid-cycle scheduled", any("mid-cycle" in s for s in
      S["model_architecture"]["required_schedules"]))
check("P/E marked low reliability at the cycle", roles(S)["pe"] == "LOW_RELIABILITY")

print("\n=== 7. Multi-segment conglomerate — SOTP primary, unexecutable ===")
S = build(segments=[seg("Engineering", 45, "order_book_execution"),
                    seg("Cement", 35, "capacity_utilisation_realisation"),
                    seg("Digital", 20, "subscribers_arpu")],
          valuation_methods=[
              m("sotp", "PRIMARY", why="three segments with unrelated economics",
                manual_steps=["value each segment on its own basis",
                              "allocate or separately value central cost",
                              "state the holding-company discount and why"]),
              m("fcff_dcf", "SECONDARY", why="valid for the engineering segment alone"),
              m("ev_ebitda", "CROSS_CHECK")])
check("AMBER, not GREEN", S["modelability"]["status"] == "AMBER")
check("SOTP stays PRIMARY (not downgraded)", roles(S)["sotp"] == "PRIMARY")
check("execution_owner is analyst_manual",
      [x for x in S["valuation_methods"] if x["method"] == "sotp"
       ][0]["execution_owner"] == "analyst_manual")
check("manual completion is spelled out", "manual_primary" in codes(S))
check("three architectures preserved",
      len({s["economic_archetype"] for s in S["segments"]}) == 3)

print("\n=== 8a. Loss-making — correctly classified ===")
fin = {"pl": {"Operating Profit": [-50.0], "Net Profit": [-120.0], "Depreciation": [30.0]}}
S = BS.build({"company": "LossCo", "scope_status": "IN_SCOPE", "sector": "services",
              "peer_count": 4, "segments": [seg("Core", 100, "subscribers_arpu")],
              "valuation_methods": [
                  m("fcff_dcf", "PRIMARY", "MEDIUM",
                    why="cash flow turns positive in year 3 on disclosed unit economics"),
                  m("ev_sales", "SECONDARY", why="the only defensible multiple")],
              "analyst_decision": {"status": "APPROVED"}}, fin)
r = roles(S)
check("EV/EBITDA auto-rejected on negative EBITDA", r.get("ev_ebitda") == "NOT_APPROPRIATE")
check("P/E auto-rejected on negative earnings", r.get("pe") == "NOT_APPROPRIATE")
check("EV/Sales survives as secondary", r.get("ev_sales") == "SECONDARY")
check("rejections were raised without being asked",
      any("raised automatically" in x["reason"] for x in S["rejected_methods"]))

print("\n=== 8b. Loss-making — analyst tries to use P/E anyway ===")
S = BS.build({"company": "LossCo", "scope_status": "IN_SCOPE", "sector": "services",
              "peer_count": 4, "segments": [seg("Core", 100, "subscribers_arpu")],
              "valuation_methods": [m("pe", "PRIMARY", why="peers trade on P/E")],
              "analyst_decision": {"status": "APPROVED"}}, fin)
check("BLOCKING disqualified_method", "disqualified_method" in codes(S))
check("RED", S["modelability"]["status"] == "RED")
ok, why = CHK.gate_ok(S)
check("gate refuses", not ok, why)

print("\n=== 9. Insufficient disclosure ===")
S = build(segments=[{"name": "Whole company", "materiality_pct": 100,
                     "economic_archetype": "generic_growth", "revenue_drivers":
                     [{"id": "revenue_growth"}], "evidence": [], "confidence": "Low"}],
          valuation_methods=[m("fcff_dcf", "PRIMARY", "LOW",
                               why="no driver disclosure; growth-rate forecast only"),
                             m("ev_ebitda", "CROSS_CHECK")],
          uncertainties=[{"issue": "no segment note", "impact": "cannot decompose",
                          "required_resolution": "FY26 annual report segment note"}])
check("AMBER", S["modelability"]["status"] == "AMBER")
check("generic dominance flagged", "generic_dominates" in codes(S))
check("missing evidence named", "segment_unevidenced" in codes(S))
check("uncertainty carries a resolution path",
      all(u.get("required_resolution") for u in S["uncertainties"]))

print("\n=== 10. Bank / NBFC / insurer — MUST REFUSE ===")
S = build(sector="financials",
          segments=[seg("Lending", 100, "generic_growth",
                        drivers=[{"id": "revenue_growth"}])],
          valuation_methods=[m("pb", "PRIMARY", why="standard for a lender")])
check("RED", S["modelability"]["status"] == "RED")
check("out_of_scope raised", "out_of_scope" in codes(S))
ok, why = CHK.gate_ok(S)
check("gate refuses", not ok, why)
S2 = build(scope_status="OUT_OF_SCOPE", sector="manufacturing",
           segments=[seg("X", 100, "volume_price")],
           valuation_methods=[m("fcff_dcf", "PRIMARY")])
check("explicit OUT_OF_SCOPE also RED", S2["modelability"]["status"] == "RED")

print("\n--- pre-existing financial-sector refusals still fire independently ---")
sys.path.insert(0, os.path.expanduser("~/.claude/skills/equity-research-report/scripts"))
import sectors as SEC
k, prof = SEC.resolve("NBFC")
check("sectors.py still blocks financials", k == "financials" and prof.get("block"))
rep = SEC.apply({"profitability": {"EBITDA Margin %": [10, 11]}}, "bank")
check("sectors.py still suppresses EBITDA for a lender",
      "EBITDA Margin %" in rep["suppressed"] and rep["blocked"])
for f, txt in [("financial-model-assumptions/SKILL.md", "banks, NBFCs and insurers"),
               ("financial-model/SKILL.md", "banks, NBFCs and insurers"),
               ("equity-research-report/SKILL.md", "banks, NBFCs and insurers")]:
    body = open(os.path.expanduser(f"~/.claude/skills/{f}"), encoding="utf-8").read()
    check(f"{f.split('/')[0]} refusal text intact", txt in body)

print("\n=== N1. Invented architecture is rejected ===")
check("resolve() returns None for an invented key",
      AR.resolve("cohort contribution ramp") is None)
S = build(segments=[{"name": "X", "materiality_pct": 100,
                     "economic_archetype": "cohort_contribution_ramp",
                     "revenue_drivers": [], "evidence": [], "confidence": "High"}],
          valuation_methods=[m("fcff_dcf", "PRIMARY")])
check("unknown archetype is BLOCKING", "unknown_archetype" in codes(S))
check("RED", S["modelability"]["status"] == "RED")
S = build(segments=[{"name": "X", "materiality_pct": 100, "economic_archetype": None,
                     "proposed_archetype": "cohort contribution ramp",
                     "revenue_drivers": [], "evidence": [{"quote": "q", "source": "k"}],
                     "confidence": "High"}],
          valuation_methods=[m("fcff_dcf", "PRIMARY")])
check("a declared PROPOSAL is AMBER, not RED", S["modelability"]["status"] == "AMBER")
check("proposal is surfaced for sign-off", "proposed_archetype" in codes(S))
check("proposal is recorded as unexecutable until validated",
      S["model_architecture"]["execution"]["pending_validation"] != [])
check("but it is not treated as a dead end",
      S["model_architecture"]["execution"]["unsupported_requirements"] == [])
try:
    SB.build(S, {"years": ["FY26", "FY27"],
                 "segments": {"X": {"base_revenue": 100.0, "drivers": {}}}})
    check("segment build refuses a proposed archetype", False, "it built anyway")
except SB.BuildError as e:
    check("segment build refuses a proposed archetype",
          "no validated archetype" in str(e), str(e))

print("\n=== N2. PRIMARY manual method with no manual plan ===")
S = build(segments=[seg("A", 55, "volume_price"), seg("B", 45, "customers_arpu")],
          valuation_methods=[m("sotp", "PRIMARY", why="two economics")])
check("BLOCKING manual_primary_unspecified", "manual_primary_unspecified" in codes(S))
check("RED", S["modelability"]["status"] == "RED")

print("\n=== N3. Declared-unsupported architecture forces a refusal ===")
S = build(segments=[seg("A", 100, "volume_price")],
          valuation_methods=[m("fcff_dcf", "PRIMARY")],
          declared_unsupported=["needs a per-project revenue schedule with "
                                "independent completion timing"])
check("unsupported_architecture is BLOCKING", "unsupported_architecture" in codes(S))
check("RED", S["modelability"]["status"] == "RED")
ok, _ = CHK.gate_ok(S)
check("gate refuses", not ok)

print("\n=== N4. Segment build base-year tie-out ===")
S = build(segments=[seg("Plant", 100, "capacity_utilisation_realisation")],
          valuation_methods=[m("fcff_dcf", "PRIMARY")])
good = {"years": ["FY26", "FY27"], "segments": {"Plant": {
    "base_revenue": 2900.0, "unit_scale": None, "drivers": {
        "installed_capacity": {"value": [120000, 120000]},
        "capacity_addition": {"value": [0, 0]},
        "utilisation": {"value": [82, 84]},
        "realisation": {"value": [29471, 30500]}}}}}
B = SB.build(S, good)
check("clean unit conversion recognised",
      "clean power of ten" in B["segments"][0]["tie_out"]["note"])
check("derived growth produced", B["derived_revenue_growth_pct"][0] is not None)

bad = json.loads(json.dumps(good))
bad["segments"]["Plant"]["unit_scale"] = 1e-6
bad["segments"]["Plant"]["base_revenue"] = 2400.0     # drivers rebuild ~2900
try:
    SB.build(S, bad)
    check("tie-out mismatch refuses", False, "it built anyway")
except SB.BuildError as e:
    check("tie-out mismatch refuses", "does not describe this segment" in str(e))

unexplained = json.loads(json.dumps(good))
unexplained["segments"]["Plant"]["base_revenue"] = 4200.0   # 1.45x, not a unit scale
B2 = SB.build(S, unexplained)
check("unexplained revenue is warned, not absorbed",
      any("unexplained" in w for w in B2["warnings"]))

pending = json.loads(json.dumps(S))
pending["analyst_decision"] = {"status": "PENDING"}
try:
    SB.build(pending, good)
    check("segment build refuses before approval", False, "built while PENDING")
except SB.BuildError as e:
    check("segment build refuses before approval", "PENDING" in str(e))

print("\n=== N5. No PRIMARY method at all ===")
S = build(segments=[seg("A", 100, "volume_price")],
          valuation_methods=[m("ev_ebitda", "CROSS_CHECK")])
check("no_primary is BLOCKING", "no_primary" in codes(S))
check("RED", S["modelability"]["status"] == "RED")

print("\n=== N6. Fake granularity is flagged ===")
S = build(segments=[seg("Main", 96, "volume_price"), seg("Tiny", 4, "customers_arpu")],
          valuation_methods=[m("fcff_dcf", "PRIMARY")])
check("sub-floor segment flagged", "fake_granularity" in codes(S))

print("\n=== N7. A declared GREEN cannot survive a real constraint ===")
S = build(segments=[seg("A", 100, "volume_price", conf="Low")],
          valuation_methods=[m("fcff_dcf", "PRIMARY")],
          modelability={"status": "GREEN", "rationale": ["looks fine"]})
check("declared GREEN downgraded to AMBER", S["modelability"]["status"] == "AMBER")
check("the downgrade is reported", "modelability_adjusted" in codes(S))

print("\n" + "=" * 62)
print(f"{len(PASS)} passed, {len(FAIL)} failed")
if FAIL:
    for f in FAIL:
        print(f"  FAILED: {f}")
sys.exit(1 if FAIL else 0)
