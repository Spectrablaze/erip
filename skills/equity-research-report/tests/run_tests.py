"""run_tests.py - tests anyone can run, with no source documents.

The two sample reports rest on third-party filings that cannot be published, so they cannot be
re-run outside this machine. These tests can. They use a synthetic company and expected answers
that come from closed-form arithmetic, not from the engine being tested:

  DCF engine (model.dcf)
    1  a constant-growth FCFF stream valued with Gordon on FCFF equals the closed form
       C x (1 + WACC)^0.5 / (WACC - g)              (mid-year, no stub)
    2  with RONIC = WACC the terminal value is NOPAT(N+1) / WACC whatever the growth rate
    3  a first-year stub weights and times the first cash flow exactly as stated
    4  the equity bridge: (EV - net debt - leases - minority + non-operating) x roll-forward / shares
    5  the target: value x (1 + ke)^(h/12) - DPS x h/12, rounded; rating from the bands
  Three-statement engine (financial-model ingest + build_model) on the synthetic company
    6  balance sheet ties, cash ties, reserves roll forward, every forecast year
    7  revenue, EBITDA, tax, PAT and capex follow their drivers exactly
    8  FCFF re-derived from the rows equals the model's FCFF
  Inputs
    9  rate parsing judges a path as a whole (0.36 in a percent path is 0.36%, not 36%)
  End to end
   10  the synthetic company's value per share matches tests/expected.json (a golden file: catches
       any change in behaviour; regenerate it deliberately with --update-golden)

    python run_tests.py [--update-golden]
Exit 1 on any failure.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
SKILLS = os.path.dirname(SKILL)
sys.path.insert(0, os.path.join(SKILL, "scripts"))
sys.path.insert(0, os.path.join(SKILLS, "financial-model", "scripts"))
import model  # noqa: E402

PY = sys.executable
RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append((name, bool(ok), detail))
    print(f"  {'PASS' if ok else 'FAIL'}  {name}  {detail}")


def close(a, b, rel=1e-9, abs_=1e-6):
    return abs(a - b) <= max(abs_, rel * max(abs(a), abs(b)))


# ---------------------------------------------------------------------------------- DCF engine
def base_inputs(fcff, ebit, tax=0.25, **extra):
    """A minimal R and A for model.dcf with the three-statement bridge supplying the cash flows."""
    n = len(fcff)
    R = {"_series": {"sales": [100.0] * 5, "ebit": [20.0] * 5, "dep": [5.0] * 5, "tax_rate": [25.0] * 5,
                     "debt": [50.0] * 5, "cash": [10.0] * 5, "shares": [10.0] * 5}}
    A = {"rf": 7.0, "erp": 5.0, "beta": 1.0, "cost_of_debt": 8.0, "tax_rate": tax * 100, "target_debt_weight": 0.0,
         "forecast_years": n, "terminal_growth": 4.0, "net_debt": 40.0, "shares_out": 10.0, "current_price": 100.0,
         "mid_year_convention": True, "fcff_from_model": True, "non_operating_assets": 0.0,
         "_bridge": {"periods": [f"Y{i + 1}" for i in range(n)], "fcff": fcff, "ebit": ebit,
                     "ebitda": [e + 5 for e in ebit], "revenue": [100.0 * (i + 1) for i in range(n)],
                     "depreciation": [5.0] * n, "capex": [5.0] * n, "change_in_nwc": [0.0] * n,
                     "tax_rate": [tax] * n}}
    A.update(extra)
    return R, A


def test_dcf():
    W = 0.07 + 1.0 * 0.05                                   # ke = rf + beta x erp, no debt weight
    g, C, n = 0.04, 100.0, 10
    fcff = [C * (1 + g) ** t for t in range(n)]
    R, A = base_inputs(fcff, [50.0] * n)
    d = model.dcf(R, A)
    ev = d["timing"]["pv_explicit"] + d["bridge"]["PV of terminal value"]
    ev_exact = d["timing"]["pv_explicit"] + (fcff[-1] * (1 + g) / (W - g)) / (1 + W) ** (n - 0.5)
    closed = C * (1 + W) ** 0.5 / (W - g)
    check("1 Gordon on FCFF = closed form", close(ev_exact, closed, rel=1e-9),
          f"engine {ev_exact:.6f} vs closed form {closed:.6f} (bridge rounds to {ev:.0f})")

    # 2: RONIC = WACC -> TV = NOPAT(N+1) / WACC for any g
    nopat = 60.0 * (1 - 0.25)
    tvs = []
    for gg in (2.0, 5.0):
        R, A = base_inputs([10.0] * n, [60.0] * n, terminal_ronic=W * 100, terminal_growth=gg)
        tvs.append(model.dcf(R, A)["bridge"]["Terminal value"])
    expect = nopat * (1 + 0.02) / W     # NOPAT(N+1) at g=2%; at g=5% it is NOPAT x 1.05 / W
    check("2 RONIC = WACC: TV = NOPAT(N+1) / WACC", close(tvs[0], round(expect), abs_=1) and
          close(tvs[1], round(nopat * 1.05 / W), abs_=1), f"TV {tvs} vs {round(expect)}, {round(nopat * 1.05 / W)}")

    # 3: stub - balance date 30 Jun, first FY ends 31 Mar next year -> 0.75 of year 1 at t = 0.375
    R, A = base_inputs([100.0] * 3, [50.0] * 3, balance_date="2026-06-30", first_fy_end="2027-03-31")
    t = model.dcf(R, A)["timing"]
    f = (date(2027, 3, 31) - date(2026, 6, 30)).days / 365.25
    pv = 100 * f / (1 + W) ** (f / 2) + 100 / (1 + W) ** (f + 0.5) + 100 / (1 + W) ** (f + 1.5)
    check("3 stub weighting and timing", close(t["first_year_share"], f) and close(t["pv_explicit"], pv),
          f"share {t['first_year_share']:.4f} vs {f:.4f}; PV {t['pv_explicit']:.4f} vs {pv:.4f}")

    # 4: equity bridge with every claim and a roll-forward
    R, A = base_inputs([100.0] * 3, [50.0] * 3, balance_date="2026-03-31", first_fy_end="2027-03-31",
                       valuation_date="2026-08-07", lease_liabilities=30.0, minority_interest=20.0,
                       non_operating_assets=15.0)
    d = model.dcf(R, A)
    tm = d["timing"]
    ev = tm["pv_explicit"] + (100 * 1.04 / (W - 0.04)) / (1 + W) ** tm["terminal_period"]
    roll = (1 + W) ** ((date(2026, 8, 7) - date(2026, 3, 31)).days / 365.25)
    vps = (ev - 40 - 30 - 20 + 15) * roll / 10
    check("4 equity bridge and roll-forward", close(tm["roll_forward"], roll) and
          abs(d["bridge"]["Intrinsic value per share (INR)"] - round(vps)) <= 0,
          f"value {d['bridge']['Intrinsic value per share (INR)']} vs {vps:.4f}")

    # 5: target policy
    A["target_policy"] = {"method": "dcf", "horizon_months": 12, "round": 5, "buy_above": 15, "sell_below": 10}
    A["_bridge"]["dividends"] = [20.0, 20.0, 20.0]
    A["_bridge"]["shares"] = [10.0, 10.0, 10.0]
    tg = model.dcf(R, A)["target"]
    fwd = vps * (1 + W) - 2.0
    exp_t = round(fwd / 5) * 5
    exp_r = "BUY" if exp_t / 100 - 1 > 0.15 else ("SELL" if exp_t / 100 - 1 < -0.10 else "HOLD")
    check("5 target and rating", tg["target"] == exp_t and tg["rating"] == exp_r,
          f"target {tg['target']} {tg['rating']} vs {exp_t} {exp_r}")


# ------------------------------------------------------------------ synthetic three-statement
def synthetic_financials():
    """A made-up company whose history is internally consistent. Nothing here is real."""
    years = [f"Mar-{y}" for y in range(19, 27)]
    n = len(years)
    sales = [1000 * 1.10 ** i for i in range(n)]
    opex = [s * 0.70 for s in sales]
    dep = [s * 0.05 for s in sales]
    intr = [20.0] * n
    oi = [s * 0.01 for s in sales]
    pbt = [s - o - d - i + x for s, o, d, i, x in zip(sales, opex, dep, intr, oi)]
    tax = [p * 0.25 for p in pbt]
    np_ = [p - t for p, t in zip(pbt, tax)]
    div = [p * 0.20 for p in np_]
    eq_cap = [100.0] * n
    reserves, r = [], 900.0
    for i in range(n):
        r = r + (np_[i] - div[i] if i else 0)
        reserves.append(r)
    borrow = [250.0] * n
    recv = [s * 60 / 365 for s in sales]
    invn = [s * 0.30 * 20 / 365 for s in sales]
    payables = [s * 0.30 * 30 / 365 for s in sales]
    other_liab = [p + s * 0.05 for p, s in zip(payables, sales)]
    net_block = [600 * 1.10 ** i for i in range(n)]
    cwip = [s * 0.05 for s in sales]
    invest = [50.0] * n
    total = [a + b + c + d for a, b, c, d in zip(eq_cap, reserves, borrow, other_liab)]
    other_assets = [t - nb - cw - iv for t, nb, cw, iv in zip(total, net_block, cwip, invest)]
    cash = [oa - rv - iv - s * 0.04 for oa, rv, iv, s in zip(other_assets, recv, invn, sales)]
    rnd = lambda xs: [round(x, 2) for x in xs]
    return {
        "company": "SynthCo Ltd (synthetic test company)", "meta": {"face_value": 10.0, "current_price": 100.0},
        "annual": {"periods": years, "Sales": rnd(sales), "Power and Fuel": [0.0] * n, "Other Mfr. Exp": rnd(opex),
                   "Employee Cost": [0.0] * n, "Selling and admin": [0.0] * n, "Other Expenses": [0.0] * n,
                   "Other Income": rnd(oi), "Depreciation": rnd(dep), "Interest": rnd(intr),
                   "Profit before tax": rnd(pbt), "Tax": rnd(tax), "Net profit": rnd(np_), "Dividend Amount": rnd(div),
                   "Expenses": rnd(opex), "Operating Profit": rnd([s - o for s, o in zip(sales, opex)])},
        "balance": {"periods": years, "Equity Share Capital": eq_cap, "Reserves": rnd(reserves), "Borrowings": borrow,
                    "Other Liabilities": rnd(other_liab), "Total": rnd(total), "Net Block": rnd(net_block),
                    "Capital Work in Progress": rnd(cwip), "Investments": invest, "Other Assets": rnd(other_assets),
                    "Receivables": rnd(recv), "Inventory": rnd(invn), "Cash & Bank": rnd(cash),
                    "No. of Equity Shares": [10.0e7] * n, "Face value": [10.0] * n, "Trade Payables": rnd(payables)},
        "cashflow": {"periods": years, "Cash from Operating Activity": [None] * n, "Cash from Investing Activity": [None] * n,
                     "Cash from Financing Activity": [None] * n, "Net Cash Flow": [None] * n},
        "quarterly": {"periods": [], "Sales": []},
    }


SYN_ASSUMPTIONS = {
    "company": "SynthCo Ltd", "sector": "industrials", "forecast_years": 5,
    "revenue_growth": [12.0, 10.0, 8.0, 6.36, 5.0], "ebit_margin": [25.0] * 5, "dep_pct_sales": [5.0] * 5,
    "capex_pct_sales": [8.0] * 5, "tax_rate": 25.0, "dso": 60, "dio": 20, "dpo": 30, "dividend_payout": 20.0,
    "cost_of_debt": 8.0, "rf": 7.0, "erp": 5.0, "beta": 1.0, "target_debt_weight": 10.0, "terminal_growth": 4.0,
    "net_debt": 50.0, "shares_out": 10.0, "current_price": 100.0, "mid_year_convention": True,
    "terminal_ronic": 14.0, "balance_date": "2026-03-31", "first_fy_end": "2027-03-31", "valuation_date": "2026-06-30",
    "target_policy": {"method": "dcf", "horizon_months": 12, "round": 5, "buy_above": 15, "sell_below": 10},
}


def run_synthetic(td):
    fin = os.path.join(td, "financials.json")
    json.dump(synthetic_financials(), open(fin, "w"))
    ap = os.path.join(td, "assumptions.json")
    json.dump(SYN_ASSUMPTIONS, open(ap, "w"))
    fm = os.path.join(SKILLS, "financial-model", "scripts")
    mi, outdir = os.path.join(td, "model_input.json"), os.path.join(td, "ts")
    for cmd in ([PY, os.path.join(fm, "ingest.py"), "--screener", fin, "--assumptions", ap, "-o", mi],
                [PY, os.path.join(fm, "build_model.py"), "--in", mi, "--outdir", outdir, "--no-xlsx"],
                [PY, os.path.join(SKILL, "scripts", "model.py"), fin, ap, "--sector", "industrials",
                 "--fm", os.path.join(outdir, "model.json"), "--fcff-from-model", "-o", os.path.join(td, "m.json")]):
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode:
            raise SystemExit(f"synthetic run failed: {' '.join(cmd[:2])}\n{r.stdout[-800:]}\n{r.stderr[-800:]}")
    return json.load(open(os.path.join(outdir, "model.json"))), json.load(open(os.path.join(td, "m.json")))


def test_three_statement(ts):
    r, n = ts["rows"], len(ts["bridge"]["periods"])
    v = lambda k: (r[k]["values"] if isinstance(r[k], dict) else r[k])
    f = lambda k: v(k)[-n:]
    h = lambda k: v(k)[-n - 1]                     # last actual
    ta, tle = f("total_assets") if "total_assets" in r else None, None
    blocking = [i for i in ts["checks"]["items"] if not i["ok"] and i.get("severity") == "blocking"]
    check("6 balance sheet, cash and reserves tie (engine checks)", not blocking,
          "; ".join(i["label"] for i in blocking) or f"{len(ts['checks']['items'])} checks")
    g = [x / 100 for x in SYN_ASSUMPTIONS["revenue_growth"]]
    rev = f("revenue")
    prev = [h("revenue")] + rev[:-1]
    ok_rev = all(close(rev[i], prev[i] * (1 + g[i]), rel=1e-9) for i in range(n))
    ebitda_m = [(e + d) / 100 for e, d in zip(SYN_ASSUMPTIONS["ebit_margin"], SYN_ASSUMPTIONS["dep_pct_sales"])]
    ok_ebitda = all(close(f("ebitda")[i], rev[i] * ebitda_m[i], rel=1e-9) for i in range(n))
    ok_capex = all(close(f("capex")[i], rev[i] * 0.08, rel=1e-9) for i in range(n))
    pbt, tax, pat = f("pbt"), f("tax"), f("pat")
    ok_tax = all(close(tax[i], pbt[i] * 0.25, rel=1e-9) and close(pat[i], pbt[i] - tax[i], rel=1e-9) for i in range(n))
    check("7 revenue, EBITDA, capex, tax and PAT follow their drivers", ok_rev and ok_ebitda and ok_capex and ok_tax,
          f"revenue {ok_rev}, EBITDA {ok_ebitda}, capex {ok_capex}, tax/PAT {ok_tax}")
    ebit, dep, capex, dnwc = f("ebit"), f("dep_charge"), f("capex"), f("d_nwc")
    fcff = [ebit[i] * (1 - 0.25) + dep[i] - capex[i] - dnwc[i] for i in range(n)]
    check("8 FCFF re-derived from the rows", all(close(fcff[i], ts["bridge"]["fcff"][i], rel=1e-6, abs_=1e-3) for i in range(n)),
          f"Y1 {fcff[0]:.3f} vs model {ts['bridge']['fcff'][0]:.3f}")


def test_rate_parsing():
    import ingest
    a = ingest._rate([13.0, 6.4, 0.36])
    b = ingest._rate([0.12, 0.10])
    c = ingest._rate(12.0), ingest._rate(0.5)
    ok = close(a[2], 0.0036) and close(a[0], 0.13) and close(b[0], 0.12) and close(c[0], 0.12) and close(c[1], 0.5)
    check("9 rate parsing judges the whole path", ok, f"[13, 6.4, 0.36] -> {[round(x, 4) for x in a]}")


def main():
    update = "--update-golden" in sys.argv
    print("ERIP engine tests (synthetic data only)")
    test_dcf()
    test_rate_parsing()
    with tempfile.TemporaryDirectory() as td:
        ts, m = run_synthetic(td)
    test_three_statement(ts)
    got = {"value_per_share": m["dcf"]["bridge"]["Intrinsic value per share (INR)"], "target": m["dcf"]["target"]["target"],
           "rating": m["dcf"]["target"]["rating"], "tv_pct_ev": m["dcf"]["bridge"]["TV as % of EV"],
           "fcff": [round(x, 3) for x in ts["bridge"]["fcff"]]}
    gp = os.path.join(HERE, "expected.json")
    if update or not os.path.exists(gp):
        json.dump(got, open(gp, "w"), indent=1)
        print(f"  golden file written: {got['value_per_share']} / target {got['target']} {got['rating']}")
    exp = json.load(open(gp))
    check("10 end to end matches the golden file", got == exp,
          f"value {got['value_per_share']} target {got['target']} {got['rating']}" + ("" if got == exp else f" vs {exp}"))
    fails = [n for n, ok, _ in RESULTS if not ok]
    print(f"\n{len(RESULTS) - len(fails)}/{len(RESULTS)} passed" + (f"; FAILED: {', '.join(fails)}" if fails else ""))
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
