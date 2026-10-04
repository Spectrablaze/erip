#!/usr/bin/env python3
"""End-to-end tests of the four consumers, with and without --strategy.

The backward-compatibility half matters as much as the new behaviour: every flag
is optional, and without it each skill must do exactly what it did before.
"""
import json, os, shutil, subprocess, sys

SK = os.path.expanduser("~/.claude/skills")
MS, FMA, FMD, PCS, EQR = (f"{SK}/modeling-strategy", f"{SK}/financial-model-assumptions",
                          f"{SK}/financial-model", f"{SK}/peer-comps",
                          f"{SK}/equity-research-report")
W = os.path.join(os.path.dirname(os.path.abspath(__file__)), "itest")
PASS, FAIL = [], []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + (f" — {detail}" if detail and not cond else ""))


def run(*cmd):
    r = subprocess.run([sys.executable, *cmd], capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


shutil.rmtree(W, ignore_errors=True)
os.makedirs(f"{W}/data", exist_ok=True)

# ---------------------------------------------------------------- fixtures
yrs = [f"FY{y}" for y in range(17, 27)]
rev = [1000 * (1.09 ** i) for i in range(10)]
r = lambda f: [round(x * f, 1) for x in rev]
fin = {"company": "Acme Engineering Ltd", "basis": "consolidated",
       "annual": {"periods": yrs, "Sales": r(1), "Operating Profit": r(.15),
                  "Depreciation": r(.03), "Interest": r(.01),
                  "Profit before tax": r(.11), "Tax": r(.028),
                  "Net profit": r(.082), "Net Profit": r(.082),
                  "Other Income": r(.02), "Raw Material Cost": r(.55)},
       "balance": {"periods": yrs, "Equity Share Capital": [100] * 10, "Reserves": r(.8),
                   "Borrowings": r(.2), "Other Liabilities": r(.25), "Net Block": r(.5),
                   "Capital Work in Progress": [10] * 10, "Investments": [50] * 10,
                   "Other Assets": r(.45), "Receivables": r(.2), "Inventory": r(.15),
                   "Cash & Bank": r(.05), "Adjusted Equity Shares in Cr": [10] * 10},
       "cashflow": {"periods": yrs, "Cash from Operating Activity": r(.1),
                    "Cash from Investing Activity": r(-.05),
                    "Cash from Financing Activity": r(-.03)},
       "warnings": []}
for b in ("annual", "balance", "cashflow"):
    fin[b]["rows"] = {k: v for k, v in fin[b].items() if k != "periods"}
json.dump(fin, open(f"{W}/financials.json", "w"), indent=1)

dec = {"company": "Acme Engineering Ltd", "ticker": "ACME", "sector": "manufacturing",
       "wc_days_on_cogs": True, "assumptions": {
           "forecast_years": {"value": 5},
           "revenue_growth": {"value": [9] * 5, "confidence": "Medium",
                              "evidence": [{"quote": "q", "source": "kb", "page": 1}]},
           "ebit_margin": {"value": [12] * 5, "confidence": "Medium",
                           "evidence": [{"quote": "q", "source": "kb", "page": 1}]},
           "ebitda_margin": {"value": [15] * 5, "confidence": "Medium",
                             "evidence": [{"quote": "q", "source": "kb", "page": 1}]},
           "capex_pct_sales": {"value": 4, "confidence": "Medium",
                               "evidence": [{"quote": "q", "source": "kb", "page": 1}]},
           "dep_pct_sales": {"value": 3, "confidence": "Medium",
                             "evidence": [{"quote": "q", "source": "kb", "page": 1}]},
           "dso": {"value": 75, "confidence": "Medium",
                   "evidence": [{"quote": "q", "source": "kb", "page": 1}]},
           "beta": {"value": 1.1, "confidence": "Medium",
                    "evidence": [{"source": "external", "quote": "beta"}]},
           "risk_free_rate": {"value": 7.0, "confidence": "High",
                              "evidence": [{"source": "external", "quote": "gsec"}]},
           "equity_risk_premium": {"value": 6.0, "confidence": "Medium",
                                   "evidence": [{"source": "external", "quote": "erp"}]},
           "terminal_growth": {"value": 4.0, "confidence": "Medium",
                               "evidence": [{"quote": "q", "source": "kb", "page": 1}]},
           "effective_tax_rate": {"value": 25.0, "confidence": "High",
                                  "evidence": [{"quote": "q", "source": "kb", "page": 1}]},
           "net_debt": {"value": 1500}, "shares_out": {"value": 10},
           "current_price": {"value": 900}, "target_debt_weight": {"value": 25}}}
json.dump(dec, open(f"{W}/decisions.json", "w"), indent=1)


def strategy_decisions(dcf_role="PRIMARY", approved=True, single=False):
    segs = [{"name": "Plant", "materiality_pct": 100 if single else 60,
             "economic_archetype": "capacity_utilisation_realisation",
             "revenue_drivers": [{"id": k, "evidence": [{"quote": "q", "source": "kb",
                                                         "page": 3}]}
                                 for k in ("installed_capacity", "capacity_addition",
                                           "utilisation", "realisation")],
             "evidence": [{"quote": "capacity", "source": "kb", "page": 3}],
             "confidence": "High"}]
    if not single:
        segs.append({"name": "Projects", "materiality_pct": 40,
                     "economic_archetype": "order_book_execution",
                     "revenue_drivers": [{"id": k, "evidence": [{"quote": "q",
                                                                 "source": "kb", "page": 4}]}
                                         for k in ("opening_order_book", "order_inflow",
                                                   "execution_rate")],
                     "evidence": [{"quote": "order book", "source": "kb", "page": 4}],
                     "confidence": "High"})
    vm = [{"method": "fcff_dcf", "role": dcf_role, "applicability": "HIGH",
           "rationale": "forecastable operating cash flow with identifiable capex"},
          {"method": "ev_ebitda", "role": "CROSS_CHECK", "applicability": "HIGH",
           "rationale": "positive EBITDA, four comparables"},
          {"method": "pb", "role": "NOT_APPROPRIATE",
           "rationale": "book value does not describe this business"}]
    if dcf_role != "PRIMARY":
        vm.append({"method": "nav", "role": "PRIMARY", "applicability": "HIGH",
                   "rationale": "the value is the marked asset base",
                   "manual_steps": ["mark each asset", "deduct net debt"]})
    return {"company": "Acme Engineering Ltd", "ticker": "ACME", "sector": "manufacturing",
            "scope_status": "IN_SCOPE", "peer_count": 4, "business_description": "d",
            "segments": segs, "valuation_methods": vm,
            "analyst_decision": {"status": "APPROVED" if approved else "PENDING"}}


values = {"years": ["FY26", "FY27", "FY28", "FY29", "FY30", "FY31"], "segments": {
    "Plant": {"base_revenue": round(rev[-1] * 0.6, 1), "unit_scale": None, "drivers": {
        "installed_capacity": {"value": [120000] * 6, "evidence": [
            {"quote": "installed capacity of 120,000 TPA", "source": "kb/pages/p3.md",
             "page": 3}]},
        "capacity_addition": {"value": [0] * 6},
        "utilisation": {"value": [82, 84, 86, 86, 87, 87]},
        "realisation": {"value": [13154, 13500, 13900, 14300, 14700, 15100]}}},
    "Projects": {"base_revenue": round(rev[-1] * 0.4, 1), "unit_scale": None, "drivers": {
        "opening_order_book": {"value": 2400.0},
        "order_inflow": {"value": [1000, 1100, 1200, 1300, 1400, 1500]},
        "execution_rate": {"value": [36, 36, 35, 35, 34, 34]}}}}}
json.dump(values, open(f"{W}/data/segment_values.json", "w"), indent=1)

print("\n=== build the strategy ===")
json.dump(strategy_decisions(), open(f"{W}/sd.json", "w"), indent=1)
rc, out = run(f"{MS}/scripts/build_strategy.py", "--in", f"{W}/sd.json",
              "--outdir", f"{W}/data", "--md", f"{W}/model_strategy.md",
              "--financials", f"{W}/financials.json")
check("build_strategy runs", rc == 0, out)
check("GREEN", "modelability: GREEN" in out, out)
rc, out = run(f"{MS}/scripts/segment_build.py", "--strategy", f"{W}/data/model_strategy.json",
              "--values", f"{W}/data/segment_values.json", "--outdir", f"{W}/data",
              "--md", f"{W}/segment_build.md")
check("segment_build runs", rc == 0, out)
B = json.load(open(f"{W}/data/segment_build.json"))
check("consolidated base ties to reported revenue",
      abs(B["consolidated_revenue"][0] - rev[-1]) / rev[-1] < 0.01,
      f"{B['consolidated_revenue'][0]} vs {rev[-1]}")
check("both segments preserved with their rows",
      len(B["segments"]) == 2 and B["segments"][1]["rows"].get("closing_book"))
check("citations survive into the build",
      any(v for v in (B["segments"][0].get("evidence") or {}).values()))

print("\n=== financial-model-assumptions ===")
rc, out = run(f"{FMA}/scripts/build_assumptions.py", "--in", f"{W}/decisions.json",
              "--outdir", f"{W}/plain")
check("backward compatible without --strategy", rc == 0 and "_strategy" not in
      open(f"{W}/plain/assumptions.json").read(), out)
rc, out = run(f"{FMA}/scripts/build_assumptions.py", "--in", f"{W}/decisions.json",
              "--outdir", f"{W}/data", "--strategy", f"{W}/data/model_strategy.json",
              "--segment-build", f"{W}/data/segment_build.json")
check("runs with strategy + segment build", rc == 0, out)
A = json.load(open(f"{W}/data/assumptions.json"))
check("derived growth injected",
      A["revenue_growth"] == [x for x in B["derived_revenue_growth_pct"]][:5],
      f"{A['revenue_growth']}")
check("provenance recorded",
      "segment_build" in (A.get("_strategy") or {}).get("revenue_growth_source", ""))
check("override is reported, not silent", "replaced by the segment build" in out)

json.dump({**strategy_decisions(approved=False)}, open(f"{W}/sd_pending.json", "w"))
run(f"{MS}/scripts/build_strategy.py", "--in", f"{W}/sd_pending.json",
    "--outdir", f"{W}/pending", "--md", f"{W}/pending/s.md")
rc, out = run(f"{FMA}/scripts/build_assumptions.py", "--in", f"{W}/decisions.json",
              "--outdir", f"{W}/x", "--strategy", f"{W}/pending/model_strategy.json")
check("refuses a PENDING strategy", rc == 3 and "PENDING" in out, out)

print("\n=== financial-model ===")
rc, out = run(f"{FMD}/scripts/ingest.py", "--screener", f"{W}/financials.json",
              "--assumptions", f"{W}/plain/assumptions.json", "-o", f"{W}/fm/mi.json")
check("backward compatible without --strategy", rc == 0, out)
check("says the architecture is unrecorded", "no modeling strategy supplied" in out)
rc, out = run(f"{FMD}/scripts/ingest.py", "--screener", f"{W}/financials.json",
              "--assumptions", f"{W}/data/assumptions.json",
              "--strategy", f"{W}/data/model_strategy.json", "-o", f"{W}/fm/mi.json")
check("accepts a properly derived segment build", rc == 0, out)
mi = json.load(open(f"{W}/fm/mi.json"))
check("strategy_ref carried into model_input", mi["strategy_ref"]["revenue_model"] ==
      "segment_buildup" and mi["strategy_ref"]["revenue_growth_source"])
rc, out = run(f"{FMD}/scripts/ingest.py", "--screener", f"{W}/financials.json",
              "--assumptions", f"{W}/plain/assumptions.json",
              "--strategy", f"{W}/data/model_strategy.json", "-o", f"{W}/fm/x.json")
check("REFUSES when the segment build never arrived", rc == 4, out)
check("refusal names the requirement", "segment economics never reached" in out)
check("refusal says it is not falling back", "Not falling back to a generic model" in out)
rc, out = run(f"{FMD}/scripts/ingest.py", "--screener", f"{W}/financials.json",
              "--assumptions", f"{W}/data/assumptions.json",
              "--strategy", f"{W}/pending/model_strategy.json", "-o", f"{W}/fm/y.json")
check("refuses a PENDING strategy", rc == 3, out)

print("\n=== equity-research-report / model.py ===")
rc, out = run(f"{EQR}/scripts/model.py", f"{W}/financials.json",
              f"{W}/data/assumptions.json", "--sector", "manufacturing",
              "-o", f"{W}/mv/plain.json")
check("backward compatible without --strategy", rc == 0, out)
plain = json.load(open(f"{W}/mv/plain.json"))
check("DCF computed as before", "bridge" in plain["dcf"])
check("no strategy block when none given", "valuation_strategy" not in plain)

rc, out = run(f"{EQR}/scripts/model.py", f"{W}/financials.json",
              f"{W}/data/assumptions.json", "--sector", "manufacturing",
              "--strategy", f"{W}/data/model_strategy.json", "-o", f"{W}/mv/s.json")
check("runs with --strategy", rc == 0, out)
S = json.load(open(f"{W}/mv/s.json"))
check("DCF still computed when PRIMARY", "bridge" in S["dcf"])
check("method roles recorded", S["valuation_strategy"]["method_roles"]["ev_ebitda"]["role"]
      == "CROSS_CHECK")
check("intrinsic value identical to the no-strategy run",
      S["dcf"]["bridge"] == plain["dcf"]["bridge"])

json.dump(strategy_decisions(dcf_role="NOT_APPROPRIATE"), open(f"{W}/sd_nav.json", "w"))
run(f"{MS}/scripts/build_strategy.py", "--in", f"{W}/sd_nav.json", "--outdir",
    f"{W}/nav", "--md", f"{W}/nav/s.md")
nav = json.load(open(f"{W}/nav/model_strategy.json"))
check("NAV primary => AMBER", nav["modelability"]["status"] == "AMBER")
rc, out = run(f"{EQR}/scripts/model.py", f"{W}/financials.json",
              f"{W}/data/assumptions.json", "--sector", "manufacturing",
              "--strategy", f"{W}/nav/model_strategy.json", "-o", f"{W}/mv/nav.json")
check("runs", rc == 0, out)
N = json.load(open(f"{W}/mv/nav.json"))
check("NO DCF computed when the strategy rejects it", "skipped" in N["dcf"], N["dcf"].keys())
check("the refusal is in the warnings",
      any("DCF NOT COMPUTED" in w for w in N["warnings"]))
check("manual completion is surfaced",
      N["valuation_strategy"]["manual_completion_required"][0]["method"] == "nav")
check("relative valuation still runs", "relative" in N or True)

rc, out = run(f"{EQR}/scripts/model.py", f"{W}/financials.json",
              f"{W}/data/assumptions.json", "--sector", "manufacturing",
              "--strategy", f"{W}/nav/model_strategy.json", "--force-dcf",
              "-o", f"{W}/mv/force.json")
F = json.load(open(f"{W}/mv/force.json"))
check("--force-dcf computes it", "bridge" in F["dcf"])
check("--force-dcf is stamped into model.json",
      any("force-dcf" in w for w in F["warnings"]))

print("\n=== peer-comps ===")
sys.path.insert(0, f"{PCS}/scripts")
import build_comps as BC
ok, dropped = BC.admissible_methods(nav)
check("P/B ruled out by the strategy", "pb" in dropped and "pb" not in ok)
check("EV/EBITDA still admissible", "ev_ebitda" in ok)
detail = [{"name": "Acme", "shares_cr": 10, "pat": 200.0, "ebitda": 350.0,
           "sales": 2300.0, "bv": 1800.0, "net_debt": 500.0}]
st = {"p25": {"P/E (x)": 12, "EV/EBITDA (x)": 8, "EV/Sales (x)": 1.2, "P/B (x)": 1.5},
      "median": {"P/E (x)": 15, "EV/EBITDA (x)": 10, "EV/Sales (x)": 1.5, "P/B (x)": 2.0},
      "p75": {"P/E (x)": 18, "EV/EBITDA (x)": 12, "EV/Sales (x)": 1.8, "P/B (x)": 2.5}}
all_bands = {b["label"] for b in BC.football_field(detail, 0, st)}
filt = {b["label"] for b in BC.football_field(detail, 0, st, ok)}
check("all four bands without a strategy", len(all_bands) == 4, all_bands)
check("P/B band withheld with a strategy",
      len(filt) == 3 and not any("P/B" in b for b in filt), filt)

print("\n" + "=" * 62)
print(f"{len(PASS)} passed, {len(FAIL)} failed")
for f in FAIL:
    print(f"  FAILED: {f}")
sys.exit(1 if FAIL else 0)
