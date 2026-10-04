#!/usr/bin/env python3
"""
model.py — the valuation & analysis engine.

Everything the report needs computed rather than guessed: ratio pack, working
capital cycle, DuPont, ROIIC, forensic (accrual-quality) screens, a full FCFF DCF
with WACC build-up and a sensitivity grid, and relative valuation.

 python3 model.py data/financials.json data/assumptions.json -o data/model.json

Design rule: every number the report prints must come out of this file or out of a
source document. Nothing is invented in prose.
"""
from __future__ import annotations

import argparse
import json
import math

# ------------------------------------------------------------------ helpers
def _d(a, b):
	"""Safe divide."""
	try:
		return a / b if (a is not None and b not in (None, 0)) else None
	except (TypeError, ZeroDivisionError):
		return None


def _pct(a, b, dec=2):
	v = _d(a, b)
	return None if v is None else round(v * 100, dec)


def _growth(series, dec=2):
	out = [None]
	for prev, cur in zip(series, series[1:]):
		out.append(None if not prev else round((cur / prev - 1) * 100, dec))
	return out


def _cagr(series, dec=2):
	s = [v for v in series if v is not None]
	if len(s) < 2 or s[0] <= 0 or s[-1] <= 0:
		return None
	return round(((s[-1] / s[0]) ** (1 / (len(s) - 1)) - 1) * 100, dec)


def _avg2(series):
	"""Average of opening and closing balance — the correct denominator for turnover ratios."""
	return [None] + [None if (a is None or b is None) else (a + b) / 2
					 for a, b in zip(series, series[1:])]


def _get(block, key, n=None):
	v = (block or {}).get(key)
	if v is None:
		return [None] * (n or 0)
	return v


# ------------------------------------------------------------------ ratio pack
def ratios(fin: dict) -> dict:
	a, b, c = fin.get("annual", {}), fin.get("balance", {}), fin.get("cashflow", {})
	P = a.get("periods", [])
	n = len(P)

	sales = _get(a, "Sales", n)
	ebitda = _get(a, "Operating Profit", n)
	dep = _get(a, "Depreciation", n)
	interest = _get(a, "Interest", n)
	pbt = _get(a, "Profit before tax", n)
	tax = _get(a, "Tax", n)
	pat = _get(a, "Net profit", n)
	oi = _get(a, "Other Income", n)

	reserves = _get(b, "Reserves", n)
	equity = [None if (sc is None and r is None) else (sc or 0) + (r or 0)
			 for sc, r in zip(_get(b, "Equity Share Capital", n), reserves)]
	debt = _get(b, "Borrowings", n)
	inv = _get(b, "Inventory", n)
	rec = _get(b, "Receivables", n)
	cash = _get(b, "Cash & Bank", n)
	netblock = _get(b, "Net Block", n)
	cwip = _get(b, "Capital Work in Progress", n)
	othassets = _get(b, "Other Assets", n)
	othliab = _get(b, "Other Liabilities", n)
	shares = _get(b, "Adjusted Equity Shares in Cr", n) or _get(b, "No. of Equity Shares", n)

	total_assets = [None if all(x is None for x in row) else sum(x or 0 for x in row)
					for row in zip(netblock, cwip, _get(b, "Investments", n), othassets, inv, rec, cash)]
	# Screener's "Other Liabilities" already contains payables; approximate payables from it
	payables = _get(b, "Trade Payables", n)
	if not any(payables):
		payables = [None if x is None else x * 0.55 for x in othliab] # flagged in warnings

	ebit = [None if (e is None or d is None) else e - d for e, d in zip(ebitda, dep)]

	# True COGS needs the material line. Screener exports "Raw Material Cost" and
	# "Change in Inventory"; without them gross margin would just be EBITDA margin
	# rebadged, so we leave it None and say so rather than print a fake ratio.
	rm = _get(a, "Raw Material Cost", n)
	chg_inv = _get(a, "Change in Inventory", n)
	power = _get(a, "Power and Fuel", n)
	has_rm = any(v is not None for v in rm)
	if has_rm:
		cogs = [None if r is None else (r or 0) - (c or 0) + (p or 0)
				for r, c, p in zip(rm, chg_inv, power)]
	else:
		cogs = [None] * n
	# Cost of sales proxy used only for turnover-day denominators
	cos = cogs if has_rm else [None if (s is None or e is None) else s - e
							 for s, e in zip(sales, ebitda)]
	tax_rate = [_d(t, p) for t, p in zip(tax, pbt)]
	nopat = [None if (e is None or tr is None) else e * (1 - tr) for e, tr in zip(ebit, tax_rate)]
	ce = [None if (eq is None) else (eq or 0) + (d or 0) for eq, d in zip(equity, debt)]
	ic = [None if (eq is None) else (eq or 0) + (d or 0) - (ch or 0)
		 for eq, d, ch in zip(equity, debt, cash)]
	cfo = _get(c, "Cash from Operating Activity", n)
	capex_cf = _get(c, "Cash from Investing Activity", n)
	fcf = [None if (o is None or i is None) else o + i for o, i in zip(cfo, capex_cf)]

	avg_eq, avg_ta, avg_ce, avg_inv, avg_rec, avg_pay = (
		_avg2(equity), _avg2(total_assets), _avg2(ce), _avg2(inv), _avg2(rec), _avg2(payables))

	R = {
		"periods": P,
		"growth": {
			"Sales Growth %": _growth(sales),
			"EBITDA Growth %": _growth(ebitda),
			"PAT Growth %": _growth(pat),
		},
		"profitability": {
			# `cg or 0` would turn a MISSING cost line into a fabricated 100%
			# gross margin — which is exactly what happens for any company with
			# no material cost (services, financials). Absent COGS must stay null.
			"Gross Margin %": [None if cg is None else _pct(s - cg, s)
								 for s, cg in zip(sales, cogs)],
			"EBITDA Margin %": [_pct(e, s) for e, s in zip(ebitda, sales)],
			"EBIT Margin %": [_pct(e, s) for e, s in zip(ebit, sales)],
			"PBT Margin %": [_pct(p, s) for p, s in zip(pbt, sales)],
			"PAT Margin %": [_pct(p, s) for p, s in zip(pat, sales)],
			"Effective Tax %": [None if t is None else round(t * 100, 2) for t in tax_rate],
			"ROE %": [_pct(p, e) for p, e in zip(pat, avg_eq)],
			"ROA %": [_pct(p, t) for p, t in zip(pat, avg_ta)],
			"ROCE %": [_pct(e, t) for e, t in zip(ebit, avg_ce)],
			"ROIC %": [_pct(nl, i) for nl, i in zip(nopat, _avg2(ic))],
		},
		"leverage": {
			"Debt / Equity (x)": [_d(d, e) and round(_d(d, e), 2) for d, e in zip(debt, equity)],
			"Net Debt (INR Cr)": [None if d is None else round((d or 0) - (ch or 0)) for d, ch in zip(debt, cash)],
			"Net Debt / EBITDA (x)": [_d((d or 0) - (ch or 0), e) and round(_d((d or 0) - (ch or 0), e), 2)
									 for d, ch, e in zip(debt, cash, ebitda)],
			"Interest Coverage (x)": [_d(e, i) and round(_d(e, i), 1) for e, i in zip(ebit, interest)],
		},
		"efficiency": {
			"Asset Turnover (x)": [_d(s, t) and round(_d(s, t), 2) for s, t in zip(sales, avg_ta)],
			"Fixed Asset Turn (x)": [_d(s, f) and round(_d(s, f), 2) for s, f in zip(sales, _avg2(netblock))],
			"Inventory Days": [_d(i, cg) and round(_d(i, cg) * 365) for i, cg in zip(avg_inv, cos)],
			"Receivable Days": [_d(r, s) and round(_d(r, s) * 365) for r, s in zip(avg_rec, sales)],
			"Payable Days": [_d(p, cg) and round(_d(p, cg) * 365) for p, cg in zip(avg_pay, cos)],
		},
		"cash": {
			"CFO (INR Cr)": cfo,
			"FCF (INR Cr)": [None if f is None else round(f) for f in fcf],
			"CFO / EBITDA %": [_pct(o, e) for o, e in zip(cfo, ebitda)],
			"CFO / PAT %": [_pct(o, p) for o, p in zip(cfo, pat)],
			"FCF / Sales %": [_pct(f, s) for f, s in zip(fcf, sales)],
		},
		"per_share": {
			"EPS (INR)": [_d(p, s) and round(_d(p, s), 2) for p, s in zip(pat, shares)],
			"BVPS (INR)": [_d(e, s) and round(_d(e, s), 2) for e, s in zip(equity, shares)],
		},
		"_series": {
			"sales": sales, "ebitda": ebitda, "ebit": ebit, "dep": dep, "pat": pat,
			"cogs": cogs, "equity": equity, "debt": debt, "cash": cash, "ic": ic,
			"nopat": nopat, "cfo": cfo, "fcf": fcf, "shares": shares,
			"tax_rate": tax_rate, "total_assets": total_assets, "interest": interest,
			"inventory": inv, "receivables": rec, "payables": payables,
			"reserves": reserves,
			# Screener aggregates payables into "Other Liabilities", so this is a
			# current-liabilities PROXY. Altman and Piotroski both flag it.
			"current_liabilities": othliab,
		},
	}

	# Cash conversion cycle
	e = R["efficiency"]
	R["efficiency"]["Cash Conversion Cycle (days)"] = [
		None if None in (i, r, p) else i + r - p
		for i, r, p in zip(e["Inventory Days"], e["Receivable Days"], e["Payable Days"])]

	R["cagr"] = {
		"Sales CAGR %": _cagr(sales),
		"EBITDA CAGR %": _cagr(ebitda),
		"PAT CAGR %": _cagr(pat),
	}
	R["_warn"] = []
	if not any(_get(b, "Trade Payables", n)):
		R["_warn"].append("Trade Payables not in export — payable days estimated from Other Liabilities. "
						 "Replace with the annual-report figure before publishing.")
	if not has_rm:
		R["_warn"].append("Raw Material Cost not in export — Gross Margin is null. Pull the material "
						 "cost line from the annual report P&L, or drop the gross-margin section.")
	return R


# ------------------------------------------------------------------ DuPont
def dupont(R: dict) -> dict:
	s = R["_series"]
	P = R["periods"]
	avg_eq, avg_ta = _avg2(s["equity"]), _avg2(s["total_assets"])
	npm = [_d(p, sa) for p, sa in zip(s["pat"], s["sales"])]
	at = [_d(sa, t) for sa, t in zip(s["sales"], avg_ta)]
	em = [_d(t, e) for t, e in zip(avg_ta, avg_eq)]

	tax_burden = [_d(p, pb) for p, pb in zip(s["pat"], [None if None in (e, i) else e - i
														for e, i in zip(s["ebit"], s["interest"])])]
	int_burden = [_d(None if None in (e, i) else e - i, e) for e, i in zip(s["ebit"], s["interest"])]
	op_margin = [_d(e, sa) for e, sa in zip(s["ebit"], s["sales"])]

	return {
		"periods": P,
		"3_step": {
			"Net Profit Margin (%)": [None if v is None else round(v * 100, 2) for v in npm],
			"Asset Turnover (x)": [None if v is None else round(v, 2) for v in at],
			"Equity Multiplier (x)": [None if v is None else round(v, 2) for v in em],
			"ROE (%)": [None if None in (a, b_, c_) else round(a * b_ * c_ * 100, 2)
									 for a, b_, c_ in zip(npm, at, em)],
		},
		"5_step": {
			"Tax Burden (x)": [None if v is None else round(v, 3) for v in tax_burden],
			"Interest Burden (x)": [None if v is None else round(v, 3) for v in int_burden],
			"Operating Margin (%)": [None if v is None else round(v * 100, 2) for v in op_margin],
			"Asset Turnover (x)": [None if v is None else round(v, 2) for v in at],
			"Equity Multiplier (x)": [None if v is None else round(v, 2) for v in em],
		},
	}


# ------------------------------------------------------------------ ROIIC
def roiic(R: dict, lag: int = 1) -> dict:
	"""Return on Incremental Invested Capital: ΔNOPAT_t / ΔIC_(t-lag).
	Answers 'what did the last rupee of reinvestment actually earn?'"""
	s = R["_series"]
	P = R["periods"]
	d_nopat = [None] + [None if None in (a, b_) else b_ - a for a, b_ in zip(s["nopat"], s["nopat"][1:])]
	d_ic = [None] + [None if None in (a, b_) else b_ - a for a, b_ in zip(s["ic"], s["ic"][1:])]
	out = []
	for i in range(len(P)):
		j = i - lag
		out.append(None if (j < 0 or d_ic[j] in (None, 0) or d_nopat[i] is None)
				 else round(d_nopat[i] / d_ic[j] * 100, 1))
	# 3-yr rolling smooths out lumpy capex years — this is the number to quote
	roll = []
	for i in range(len(P)):
		if i < 3 or None in (s["nopat"][i], s["nopat"][i - 3], s["ic"][i - 1], s["ic"][i - 4] if i >= 4 else None):
			roll.append(None)
		else:
			dn, di = s["nopat"][i] - s["nopat"][i - 3], s["ic"][i - 1] - s["ic"][i - 4]
			roll.append(None if not di else round(dn / di * 100, 1))
	return {"periods": P, "NOPAT (INR Cr)": [None if v is None else round(v) for v in s["nopat"]],
			"Invested Capital (INR Cr)": [None if v is None else round(v) for v in s["ic"]],
			"Δ NOPAT": [None if v is None else round(v) for v in d_nopat],
			"Δ Invested Capital": [None if v is None else round(v) for v in d_ic],
			"ROIIC (%)": out, "ROIIC 3Y rolling (%)": roll}


# ------------------------------------------------------------------ forensic
def forensic(R: dict) -> dict:
	"""Accrual-quality and earnings-reality screens. Each returns a flag + reasoning
	hook the analyst writes prose around."""
	s = R["_series"]
	P = R["periods"]
	cfo_pat = [_pct(o, p) for o, p in zip(s["cfo"], s["pat"])]
	sales_g = _growth(s["sales"])
	rec_g = _growth(s["receivables"])
	inv_g = _growth(s["inventory"])
	# Sloan accruals: (PAT - CFO) / average total assets. Persistently high = low quality.
	accr = [None if None in (p, o, t) else round((p - o) / t * 100, 2)
			for p, o, t in zip(s["pat"], s["cfo"], _avg2(s["total_assets"]))]
	oi_share = [None if None in (e, p) else round(e / p * 100, 1) for e, p in zip(s["ebit"], s["pat"])]

	def _mean(x):
		v = [i for i in x if i is not None]
		return round(sum(v) / len(v), 1) if v else None

	flags = []
	m = _mean(cfo_pat)
	if m is not None:
		flags.append({
			"test": "CFO / PAT (10-yr mean)", "value": f"{m}%",
			"verdict": "PASS" if m >= 85 else ("WATCH" if m >= 70 else "FAIL"),
			"why": "Cash conversion of reported profit. Below ~80% sustained means earnings are "
				 "not turning into cash — check receivables, inventory and related-party balances."})
	lastn = 5
	rg = [g for g in rec_g[-lastn:] if g is not None]
	sg = [g for g in sales_g[-lastn:] if g is not None]
	if rg and sg:
		gap = round(sum(rg) / len(rg) - sum(sg) / len(sg), 1)
		flags.append({
			"test": "Receivables growth − Sales growth (5-yr avg)", "value": f"{gap:+.1f} pp",
			"verdict": "PASS" if gap <= 3 else ("WATCH" if gap <= 8 else "FAIL"),
			"why": "Receivables outrunning sales points to channel stuffing or loosening credit terms."})
	ig = [g for g in inv_g[-lastn:] if g is not None]
	if ig and sg:
		gap = round(sum(ig) / len(ig) - sum(sg) / len(sg), 1)
		flags.append({
			"test": "Inventory growth − Sales growth (5-yr avg)", "value": f"{gap:+.1f} pp",
			"verdict": "PASS" if gap <= 3 else ("WATCH" if gap <= 8 else "FAIL"),
			"why": "Inventory building faster than sales foreshadows write-downs or demand miss."})
	am = _mean(accr[-lastn:])
	if am is not None:
		flags.append({
			"test": "Sloan accrual ratio (5-yr mean)", "value": f"{am:+.1f}%",
			"verdict": "PASS" if am <= 3 else ("WATCH" if am <= 8 else "FAIL"),
			"why": "(PAT − CFO) / avg assets. High positive accruals predict lower future returns."})
	ic = R["leverage"]["Interest Coverage (x)"]
	last_ic = next((v for v in reversed(ic) if v is not None), None)
	if last_ic is not None:
		flags.append({
			"test": "Interest coverage (latest)", "value": f"{last_ic:.1f}x",
			"verdict": "PASS" if last_ic >= 5 else ("WATCH" if last_ic >= 2.5 else "FAIL"),
			"why": "EBIT / interest. Below 2.5x leaves no cushion for a demand or rate shock."})

	return {"periods": P, "CFO / PAT (%)": cfo_pat, "Accrual ratio (%)": accr,
			"Sales growth (%)": sales_g, "Receivables growth (%)": rec_g,
			"Inventory growth (%)": inv_g, "flags": flags,
			"manual_checks": [
				"Auditor name, tenure, and any qualification / emphasis of matter",
				"Change of auditor or CFO in the last 3 years",
				"Related-party transactions as % of revenue and of PAT",
				"Contingent liabilities as % of net worth",
				"Promoter pledging % and any change YoY",
				"Capitalised vs expensed R&D and interest",
				"Other income as % of PBT (is profit operating?)",
				"Subsidiary / JV losses not consolidated",
			]}


# ----------------------------------------------------- composite forensic scores
def _current_assets(s):
	return [None if all(x is None for x in row) else sum(x or 0 for x in row)
			for row in zip(s["inventory"], s["receivables"], s["cash"])]


def altman_z(R: dict, A: dict | None = None) -> dict:
	"""Altman Z-score — distress probability.

	Two published variants. The original Z uses the MARKET value of equity and is
	only valid for listed manufacturers; Z' substitutes book equity with its own
	re-estimated coefficients. Using market-value zone cut-offs on a book-value
	ratio is a common and material error, so the variant is chosen by what data
	is actually present and is always reported alongside the score.
	"""
	s, P = R["_series"], R["periods"]
	n = len(P)
	ca = _current_assets(s)
	cl = s.get("current_liabilities") or [None] * n
	ta = s["total_assets"]
	wc = [None if None in (a, l) else a - l for a, l in zip(ca, cl)]
	retained = s.get("reserves") or [None] * n
	tot_liab = [None if None in (t, e) else t - e for t, e in zip(ta, s["equity"])]

	Z_BOOK = ((0.717, 0.847, 3.107, 0.420, 0.998), (1.23, 2.90), "Z' (book equity)")
	Z_MKT = ((1.2, 1.4, 3.3, 0.6, 1.0), (1.81, 2.99), "Z (market equity)")
	notes = []

	def _zone(z, zones):
		if z is None:
			return None, None
		if z >= zones[1]:
			return "PASS", "safe"
		return ("WATCH", "grey") if z >= zones[0] else ("FAIL", "distress")

	def _compute(i, eq_val, co):
		x = [_d(wc[i], ta[i]), _d(retained[i], ta[i]), _d(s["ebit"][i], ta[i]),
			 _d(eq_val, tot_liab[i]), _d(s["sales"][i], ta[i])]
		if any(v is None for v in x):
			return None, None
		return sum(c * v for c, v in zip(co, x)), x

	# The historical series is ALWAYS book-equity Z'. Mixing a market-value final
	# year into a book-value history produces a fake step-change in the trend.
	co, zones, label = Z_BOOK
	rows, zs = [], []
	for i in range(n):
		z, x = _compute(i, s["equity"][i], co)
		zs.append(None if z is None else round(z, 2))
		rows.append(None if x is None else {
			"X1 WC/TA": round(x[0], 3), "X2 RE/TA": round(x[1], 3),
			"X3 EBIT/TA": round(x[2], 3), "X4 BookEq/TL": round(x[3], 3),
			"X5 Sales/TA": round(x[4], 3), "Z'": round(z, 2)})

	latest = next((v for v in reversed(zs) if v is not None), None)
	verdict, zone = _zone(latest, zones)
	notes.append(f"series variant: {label}; zone cut-offs {zones[0]} / {zones[1]}")

	# Market-value Z, latest period only, reported separately with its own cut-offs.
	market = None
	price = (A or {}).get("current_price")
	if price and s["shares"] and s["shares"][-1]:
		mve = float(price) * float(s["shares"][-1])
		co_m, zones_m, label_m = Z_MKT
		zm, xm = _compute(n - 1, mve, co_m)
		if zm is not None:
			vm, zn = _zone(zm, zones_m)
			market = {"variant": label_m, "score": round(zm, 2), "verdict": vm, "zone": zn,
					 "market_cap": round(mve), "X4 MktEq/TL": round(xm[3], 2),
					 "cut_offs": list(zones_m)}
			if xm[3] > 10:
				notes.append(
					f"X4 (market equity / total liabilities) is {xm[3]:.0f}x, so Z is "
					"dominated by one term. Altman's X4 is unbounded for a nearly "
					"debt-free company: the score confirms the absence of leverage, it "
					"does not measure operating risk. Quote the zone, not the number.")
	else:
		notes.append("no current_price in assumptions — market-value Z not computed.")

	notes.append("working capital and total liabilities are derived from the Screener "
				 "export's aggregated buckets — confirm against the annual report "
				 "balance sheet before quoting Z in the text.")
	return {"periods": P, "score": zs, "components": rows, "latest": latest,
			"zone": zone, "verdict": verdict, "variant": label,
			"market": market, "notes": notes}


def piotroski_f(R: dict) -> dict:
	"""Piotroski F-score — 9 binary fundamental-improvement tests, latest year.

	Scored out of however many tests have data; a test with a missing input is
	reported as null rather than silently counted as a fail, which would bias
	every score downward.
	"""
	s, P = R["_series"], R["periods"]
	n = len(P)
	if n < 2:
		return {"score": None, "tests": [], "notes": ["need at least two periods"]}

	ta_avg = _avg2(s["total_assets"])
	roa = [_d(p, t) for p, t in zip(s["pat"], ta_avg)]
	cfo_ta = [_d(o, t) for o, t in zip(s["cfo"], ta_avg)]
	lev = [_d(d, t) for d, t in zip(s["debt"], s["total_assets"])]
	ca = _current_assets(s)
	cl = s.get("current_liabilities") or [None] * n
	curr = [_d(a, l) for a, l in zip(ca, cl)]
	gm = [_d((sa or 0) - (cg or 0), sa) if cg is not None else None
		 for sa, cg in zip(s["sales"], s["cogs"])]
	at = [_d(sa, t) for sa, t in zip(s["sales"], ta_avg)]

	i, j = n - 1, n - 2

	def gt(a, b):
		return None if (a is None or b is None) else bool(a > b)

	tests = [
		("Profitability: ROA > 0", None if roa[i] is None else roa[i] > 0),
		("Profitability: CFO > 0", None if s["cfo"][i] is None else s["cfo"][i] > 0),
		("Profitability: ROA improving", gt(roa[i], roa[j])),
		("Profitability: CFO > ROA (accrual quality)", gt(cfo_ta[i], roa[i])),
		("Leverage: debt / assets falling", gt(lev[j], lev[i])),
		("Leverage: current ratio rising", gt(curr[i], curr[j])),
		("Leverage: no new shares issued",
		 None if None in (s["shares"][i], s["shares"][j]) else s["shares"][i] <= s["shares"][j] * 1.005),
		("Efficiency: gross margin rising", gt(gm[i], gm[j])),
		("Efficiency: asset turnover rising", gt(at[i], at[j])),
	]

	scored = [t for _, t in tests if t is not None]
	score = sum(1 for t in scored if t)
	out_of = len(scored)
	notes = []
	if out_of < 9:
		missing = [name for name, t in tests if t is None]
		notes.append(f"scored {score}/{out_of} — no data for: {'; '.join(missing)}")
	if out_of:
		verdict = "PASS" if score / out_of >= 7 / 9 else ("WATCH" if score / out_of >= 4 / 9 else "FAIL")
	else:
		verdict = None
	return {"period": P[i] if P else None, "score": score, "out_of": out_of,
			"verdict": verdict,
			"tests": [{"test": name, "pass": t} for name, t in tests], "notes": notes}


# -------------------------------------------------- three-statement hand-off
def _fm_bridge(A: dict, n: int, own_rows: list, own_fcff: list, tax: float):
	"""Read the `bridge` block emitted by the `financial-model` skill.

	Returns None when no model was supplied. Otherwise reports how far the
	three-statement FCFF sits from the DCF's own projection and, when
	`fcff_from_model` is set, replaces the stream being discounted.

	The comparison is the point even when the stream is not replaced: a DCF whose
	implied cash flow differs materially from a model with a balance sheet that
	ties is being run on drivers that do not fund themselves.
	"""
	bridge = A.get("_bridge")
	if not bridge or not bridge.get("fcff"):
		return None

	b_fcff = [float(x) for x in bridge["fcff"][:n] if x is not None]
	if not b_fcff:
		return None
	short = len(b_fcff) < n

	def _cmp(a, b):
		return None if not b else round((a / b - 1) * 100, 1)

	per_year = [{"year": i + 1,
				 "DCF own FCFF": round(own_fcff[i]),
				 "three-statement FCFF": round(b_fcff[i]),
				 "difference %": _cmp(own_fcff[i], b_fcff[i])}
				for i in range(min(n, len(b_fcff)))]

	own_tot, b_tot = sum(own_fcff[:len(b_fcff)]), sum(b_fcff)
	gap = _cmp(own_tot, b_tot)

	out = {"periods": bridge.get("periods"), "per_year": per_year,
		 "total_own": round(own_tot), "total_three_statement": round(b_tot),
		 "gap_%": gap, "used": bool(A.get("fcff_from_model")), "notes": []}

	if short:
		out["notes"].append(
			f"the three-statement model covers {len(b_fcff)} years against a "
			f"{n}-year DCF horizon — only the overlap is compared")
	if gap is not None and abs(gap) > 15:
		out["notes"].append(
			f"cumulative FCFF differs by {gap:+.0f}%. The DCF drivers do not fund the "
			"balance sheet the model builds. Reconcile capex, working capital and "
			"depreciation before publishing — do not average the two.")
	elif gap is not None:
		out["notes"].append(f"cumulative FCFF within {abs(gap):.0f}% of the "
							"three-statement model — the drivers are self-consistent.")

	if out["used"]:
		rev = bridge.get("revenue") or []
		ebit = bridge.get("ebit") or []
		dep = bridge.get("depreciation") or []
		capex = bridge.get("capex") or []
		dnwc = bridge.get("change_in_nwc") or []
		ebitda = bridge.get("ebitda") or []
		rows = []
		for i, f in enumerate(b_fcff):
			r = dict(own_rows[i]) if i < len(own_rows) else {"year": i + 1}
			r["year"] = i + 1
			if i < len(rev) and rev[i] is not None:
				r["Sales"] = round(float(rev[i]))
				if i and rev[i - 1]:
					r["Growth %"] = round((float(rev[i]) / float(rev[i - 1]) - 1) * 100, 1)
			if i < len(ebit) and ebit[i] is not None:
				r["EBIT"] = round(float(ebit[i]))
				r["NOPAT"] = round(float(ebit[i]) * (1 - tax))
				if r.get("Sales"):
					r["EBIT %"] = round(float(ebit[i]) / r["Sales"] * 100, 1)
			for key, src in (("D&A", dep), ("Capex", capex), ("Δ NWC", dnwc)):
				if i < len(src) and src[i] is not None:
					v = float(src[i])
					r[key] = round(v if key == "D&A" else -abs(v))
			r["FCFF"] = round(f)
			r["source"] = "three-statement model"
			rows.append(r)
		out["rows"] = rows
		out["fcff"] = b_fcff
		if ebitda and len(ebitda) > len(b_fcff) - 1 and ebitda[len(b_fcff) - 1] is not None:
			out["term_ebitda"] = float(ebitda[len(b_fcff) - 1])
	return out


# ------------------------------------------------------------------ DCF
def dcf(R: dict, A: dict) -> dict:
	"""FCFF DCF. `A` (assumptions) must supply:
	 rf, erp, beta, cost_of_debt, tax_rate, target_debt_weight,
	 forecast_years, revenue_growth[], ebit_margin[], capex_pct_sales[],
	 dep_pct_sales[], nwc_pct_sales[], terminal_growth,
	 net_debt, shares_out, current_price
	Any missing one is taken from the historical average and reported in `derived_from`."""
	s = R["_series"]
	hist_sales = [v for v in s["sales"] if v is not None]
	base_sales = hist_sales[-1]
	n = int(A.get("forecast_years", 5))
	derived = []

	def _series(key, default_fn):
		v = A.get(key)
		if isinstance(v, list):
			if len(v) >= n:
				return [float(x) for x in v[:n]]
			vals = [float(x) for x in v]
			if len(vals) < n:
				derived.append(f"{key} list shorter ({len(vals)}) than forecast horizon ({n}); last value {vals[-1]:.2f} repeated")
			vals.extend([vals[-1]] * (n - len(vals)))
			return vals
		if isinstance(v, (int, float)):
			return [float(v)] * n
		d = default_fn()
		derived.append(f"{key} defaulted to historical average ({d:.2f})")
		return [d] * n

	def _hist_avg(series, k=5):
		v = [x for x in series[-k:] if x is not None]
		return sum(v) / len(v) if v else 0.0

	g = _series("revenue_growth", lambda: _hist_avg([x for x in _growth(s["sales"]) if x is not None]) / 100)
	if max(g) > 1: # user gave percents
		g = [x / 100 for x in g]
	ebitm = _series("ebit_margin",
					lambda: _hist_avg([_d(e, sa) for e, sa in zip(s["ebit"], s["sales"])]))
	if max(ebitm) > 1:
		ebitm = [x / 100 for x in ebitm]
	capexp = _series("capex_pct_sales", lambda: 0.05)
	depp = _series("dep_pct_sales",
				 lambda: _hist_avg([_d(d, sa) for d, sa in zip(s["dep"], s["sales"])]))
	nwcp = _series("nwc_pct_sales", lambda: 0.02)
	for lst in (capexp, depp, nwcp):
		if max(lst) > 1:
			for i in range(len(lst)):
				lst[i] /= 100

	tax = float(A.get("tax_rate", _hist_avg([t for t in s["tax_rate"] if t is not None]) or 0.25))
	if tax > 1:
		tax /= 100

	rf = float(A["rf"]); erp = float(A["erp"]); beta = float(A["beta"])
	kd = float(A.get("cost_of_debt", rf + 0.015))
	wd = float(A.get("target_debt_weight", 0.0))
	for v in ("rf", "erp", "cost_of_debt"):
		if float(A.get(v, 0)) > 1:
			A[v] = float(A[v]) / 100
	rf, erp, kd = float(A["rf"]), float(A["erp"]), float(A.get("cost_of_debt", rf + 0.015))
	if wd > 1:
		wd /= 100

	# ---- beta ---------------------------------------------------------------
	# A single regression beta off one listing is noisy and reflects whatever
	# leverage the company happened to carry. Institutional practice: unlever
	# peer betas (Hamada), take the median, relever at the TARGET structure.
	beta_build = {"Input beta": round(beta, 3)}
	peer_betas = A.get("peer_betas")
	if peer_betas:
		de_target = _d(wd, 1 - wd) or 0.0
		unlevered = []
		for p in peer_betas:
			bl, de = p.get("beta"), p.get("debt_equity")
			if bl is None or de is None:
				continue
			unlevered.append(float(bl) / (1 + (1 - tax) * float(de)))
		if unlevered:
			u = sorted(unlevered)
			k = len(u) // 2
			bu = u[k] if len(u) % 2 else (u[k - 1] + u[k]) / 2
			beta = bu * (1 + (1 - tax) * de_target)
			beta_build.update({
				"Peer betas used": len(unlevered),
				"Median unlevered beta": round(bu, 3),
				"Target D/E": round(de_target, 3),
				"Relevered beta": round(beta, 3)})
		else:
			derived.append("peer_betas supplied but no entry had both beta and "
						 "debt_equity — fell back to the input beta.")
	if A.get("blume_adjust"):
		# Blume: betas revert toward 1 over time. Standard for a multi-year DCF.
		beta = 0.67 * beta + 0.33
		beta_build["Blume-adjusted beta"] = round(beta, 3)

	ke = rf + beta * erp
	wacc = ke * (1 - wd) + kd * (1 - tax) * wd
	gt = float(A["terminal_growth"])
	if gt > 1:
		gt /= 100
	if gt >= wacc:
		raise SystemExit(f"terminal growth ({gt:.2%}) must be below WACC ({wacc:.2%})")

	# Mid-year convention: cash flows accrue through the year rather than landing
	# on 31 March, so discounting at t+0.5 is the institutional default. Off by
	# default to keep prior outputs reproducible; set mid_year_convention: true.
	mid = bool(A.get("mid_year_convention", False))
	offset = 0.5 if mid else 1.0

	# ---- the forecast --------------------------------------------------------
	# Built from the drivers first, always — even when a three-statement model
	# supplies the cash flows, the internal projection is what the cross-check
	# below compares against.
	rows, sales, prev_sales = [], base_sales, base_sales
	fcff_raw = [] # unrounded — the rounded display value must never feed maths
	for i in range(n):
		sales = prev_sales * (1 + g[i])
		ebit = sales * ebitm[i]
		nopat_ = ebit * (1 - tax)
		dep_ = sales * depp[i]
		capex_ = sales * capexp[i]
		dnwc = (sales - prev_sales) * nwcp[i]
		fcff = nopat_ + dep_ - capex_ - dnwc
		fcff_raw.append(fcff)
		rows.append({"year": i + 1, "Sales": round(sales), "Growth %": round(g[i] * 100, 1),
					 "EBIT": round(ebit), "EBIT %": round(ebitm[i] * 100, 1),
					 "NOPAT": round(nopat_), "D&A": round(dep_), "Capex": round(-capex_),
					 "Δ NWC": round(-dnwc), "FCFF": round(fcff)})
		prev_sales = sales
	term_ebitda = sales * ebitm[-1] + sales * depp[-1] # terminal-year EBIT + D&A

	# ---- three-statement hand-off -------------------------------------------
	# `financial-model` projects a balance sheet and cash flow that tie; its
	# bridge.fcff therefore comes out of a company that funds itself, rather than
	# from a margin applied to a revenue line. Divergence between the two is the
	# signal: it means these drivers do not fund the balance sheet they imply.
	fm = _fm_bridge(A, n, rows, fcff_raw, tax)
	if fm and fm.get("used"):
		fcff_raw = fm["fcff"]
		rows = fm["rows"]
		if fm.get("term_ebitda"):
			term_ebitda = fm["term_ebitda"]
		# The model may project fewer years than the DCF horizon. Shortening the
		# horizon keeps the terminal-value discounting honest; silently padding
		# would invent cash flows the model never produced.
		if len(fcff_raw) != n:
			derived.append(f"horizon shortened from {n} to {len(fcff_raw)} years to "
						 "match the three-statement model")
			n = len(fcff_raw)

	pv_sum = 0.0
	for i, f in enumerate(fcff_raw):
		df = 1 / (1 + wacc) ** (i + offset)
		pv = f * df
		pv_sum += pv
		rows[i]["Discount factor"] = round(df, 4)
		rows[i]["PV of FCFF"] = round(pv)
	tv = fcff_raw[-1] * (1 + gt) / (wacc - gt)
	pv_tv = tv / (1 + wacc) ** (n - 1 + offset)
	ev = pv_sum + pv_tv
	net_debt = A.get("net_debt")
	if net_debt is None:
		net_debt = (s["debt"][-1] or 0) - (s["cash"][-1] or 0)
	net_debt = float(net_debt)
	# Treasury / strategic investments are not in the FCFF stream, so they must be
	# added back separately or the DCF understates equity value. Cash-rich Indian
	# industrials (Eicher, Maruti, ITC) all need this.
	nonop = float(A.get("non_operating_assets") or 0)
	if not nonop:
		derived.append("non_operating_assets = 0 — confirm the company has no surplus "
					 "treasury investments or stakes to add back")
	eq_val = ev - net_debt + nonop
	sh = float(A.get("shares_out") or s["shares"][-1] or 0)
	vps = _d(eq_val, sh)
	cmp_ = A.get("current_price")

	# Sensitivity: WACC (rows) x terminal growth (cols). Uses the unrounded FCFF
	# and the same discount offset as the headline, or the grid centre will not
	# reconcile to the intrinsic value printed above it.
	waccs = [round(wacc + d, 4) for d in (-0.01, -0.005, 0, 0.005, 0.01)]
	gts = [round(gt + d, 4) for d in (-0.01, -0.005, 0, 0.005, 0.01)]
	grid = []
	for w in waccs:
		row = []
		for gg in gts:
			if gg >= w:
				row.append(float("nan")); continue
			pv_ = sum(f / (1 + w) ** (k + offset) for k, f in enumerate(fcff_raw))
			tv_ = (fcff_raw[-1] * (1 + gg) / (w - gg)) / (1 + w) ** (n - 1 + offset)
			row.append(round(_d(pv_ + tv_ - net_debt + nonop, sh) or 0))
		grid.append(row)

	# ---- terminal-value cross-check ----------------------------------------
	# A Gordon-Growth terminal value implies an exit EV/EBITDA. If that implied
	# multiple sits far above where the sector actually trades, the perpetuity
	# assumption is doing the work, not the business.
	implied_exit = _d(tv, term_ebitda)
	cross = {"Terminal-year EBITDA": round(term_ebitda),
			 "Gordon-Growth terminal value": round(tv),
			 "Implied exit EV/EBITDA (x)": None if implied_exit is None else round(implied_exit, 1)}
	exit_mult = A.get("exit_multiple")
	if exit_mult:
		tv_x = float(exit_mult) * term_ebitda
		pv_tv_x = tv_x / (1 + wacc) ** (n - 1 + offset)
		ev_x = pv_sum + pv_tv_x
		vps_x = _d(ev_x - net_debt + nonop, sh)
		cross.update({
			"Exit multiple supplied (x)": float(exit_mult),
			"Terminal value at exit multiple": round(tv_x),
			"Value per share at exit multiple": None if vps_x is None else round(vps_x)})
		if implied_exit and float(exit_mult):
			gap = (implied_exit / float(exit_mult) - 1) * 100
			cross["Perpetuity vs exit-multiple gap %"] = round(gap, 1)
			if abs(gap) > 25:
				derived.append(
					f"perpetuity TV implies {implied_exit:.1f}x exit EBITDA against the "
					f"{float(exit_mult):.1f}x supplied ({gap:+.0f}%). Reconcile the two in "
					"the text rather than presenting one as the answer.")
	else:
		derived.append("no exit_multiple supplied — the terminal value rests on Gordon "
					 "Growth alone. Cross-check the implied exit multiple against "
					 "where the sector trades.")

	return {
		"wacc_build": {"Risk-free rate": round(rf * 100, 2), "Equity risk premium": round(erp * 100, 2),
					 "Beta": round(beta, 2), "Cost of equity (CAPM)": round(ke * 100, 2),
					 "Cost of debt (pre-tax)": round(kd * 100, 2), "Tax rate": round(tax * 100, 2),
					 "Cost of debt (post-tax)": round(kd * (1 - tax) * 100, 2),
					 "Target debt weight": round(wd * 100, 2), "WACC": round(wacc * 100, 2),
					 "Discounting": "mid-year" if mid else "end-year",
					 "Beta build": beta_build},
		"forecast": rows,
		"bridge": {"PV of explicit FCFF": round(pv_sum), "Terminal value": round(tv),
				 "PV of terminal value": round(pv_tv), "TV as % of EV": round(pv_tv / ev * 100, 1),
				 "Enterprise value": round(ev), "Less: net debt": round(-net_debt),
				 "Add: non-operating assets": round(nonop),
				 "Equity value": round(eq_val), "Shares outstanding (Cr)": round(sh, 2),
				 "Intrinsic value per share (INR)": None if vps is None else round(vps),
				 "Current market price (INR)": cmp_,
				 "Upside / (downside) %": None if (vps is None or not cmp_) else round((vps / cmp_ - 1) * 100, 1)},
		"sensitivity": {"wacc": [f"{w*100:.1f}%" for w in waccs],
						"terminal_growth": [f"{g_*100:.1f}%" for g_ in gts], "grid": grid},
		"terminal_cross_check": cross,
		"three_statement": fm,
		"derived_from": derived,
	}


def scenarios(R: dict, A: dict) -> dict:
	"""Bull / base / bear, each a full DCF re-run, then probability-weighted.

	A["scenarios"] = {"bull": {"probability": 0.25, "revenue_growth": [...],
							 "ebit_margin": [...], "terminal_growth": 0.055},
					 "base": {...}, "bear": {...}}
	Any driver absent from a scenario falls back to the base assumptions, so a
	scenario need only state what it changes. A sensitivity grid flexes the
	discount rate; this flexes the BUSINESS, which is where the real risk sits.
	"""
	spec = A.get("scenarios") or {}
	if not spec:
		return {}
	out, weights = {}, {}
	for name, over in spec.items():
		merged = dict(A)
		merged.pop("scenarios", None)
		prob = over.get("probability")
		merged.update({k: v for k, v in over.items() if k != "probability"})
		try:
			d = dcf(R, merged)
		except SystemExit as exc: # e.g. terminal growth >= WACC
			out[name] = {"error": str(exc)}
			continue
		b = d["bridge"]
		out[name] = {
			"probability": prob,
			"revenue_growth_y1_%": d["forecast"][0]["Growth %"],
			"exit_ebit_margin_%": d["forecast"][-1]["EBIT %"],
			"terminal_growth_%": merged.get("terminal_growth"),
			"WACC %": d["wacc_build"]["WACC"],
			"intrinsic_value_per_share": b["Intrinsic value per share (INR)"],
			"upside_%": b["Upside / (downside) %"],
			"TV_as_%_of_EV": b["TV as % of EV"],
		}
		if prob is not None and b["Intrinsic value per share (INR)"] is not None:
			weights[name] = (float(prob), b["Intrinsic value per share (INR)"])

	summary = {}
	if weights:
		tot = sum(p for p, _ in weights.values())
		summary["probability_total"] = round(tot, 3)
		if abs(tot - 1.0) > 0.001:
			summary["warning"] = (f"probabilities sum to {tot:.2f}, not 1.00 — "
								 "the weighted value below is normalised")
		summary["weighted_value_per_share"] = round(
			sum(p * v for p, v in weights.values()) / tot)
		vals = [v for _, v in weights.values()]
		summary["range"] = {"low": min(vals), "high": max(vals),
							"spread_x": round(max(vals) / min(vals), 2) if min(vals) else None}
		cmp_ = A.get("current_price")
		if cmp_:
			summary["weighted_upside_%"] = round(
				(summary["weighted_value_per_share"] / float(cmp_) - 1) * 100, 1)
	return {"cases": out, "summary": summary}


def relative(peers: list) -> dict:
	"""peers = [{"name","price","mcap","ev","sales","ebitda","pat","bv","roe"}...]
	First entry is treated as the subject company."""
	out = []
	for p in peers:
		out.append({
			"Company": p["name"],
			"Price (INR)": p.get("price"),
			"Mkt Cap (Cr)": p.get("mcap"),
			"EV (Cr)": p.get("ev"),
			"P/E (x)": _d(p.get("mcap"), p.get("pat")) and round(_d(p["mcap"], p["pat"]), 1),
			"EV/EBITDA (x)": _d(p.get("ev"), p.get("ebitda")) and round(_d(p["ev"], p["ebitda"]), 1),
			"EV/Sales (x)": _d(p.get("ev"), p.get("sales")) and round(_d(p["ev"], p["sales"]), 1),
			"P/B (x)": _d(p.get("mcap"), p.get("bv")) and round(_d(p["mcap"], p["bv"]), 1),
			"ROE (%)": p.get("roe"),
			"EBITDA Margin (%)": _pct(p.get("ebitda"), p.get("sales")),
		})
	def _med(k):
		v = sorted(x[k] for x in out[1:] if x[k] is not None)
		if not v:
			return None
		m = len(v) // 2
		return round(v[m] if len(v) % 2 else (v[m - 1] + v[m]) / 2, 1)
	med = {"Company": "Peer median", **{k: _med(k) for k in out[0] if k != "Company"}}
	prem = {"Company": f"{out[0]['Company']} premium / (discount)",
			**{k: (None if (out[0][k] is None or med[k] in (None, 0))
				 else f"{(out[0][k]/med[k]-1)*100:+.0f}%")
			 for k in out[0] if k != "Company"}}
	return {"table": out + [med, prem]}


# ------------------------------------------------------------------ CLI
def _load_gate():
	"""Import check_strategy.py from the `modeling-strategy` skill."""
	import os as _os
	import sys as _sys
	here = _os.path.dirname(_os.path.abspath(__file__))
	cands = []
	if _os.environ.get("MS_SKILL"):
		cands.append(_os.path.join(_os.environ["MS_SKILL"], "scripts"))
	cands += [
		_os.path.join(here, "..", "..", "modeling-strategy", "scripts"),
		_os.path.expanduser("~/.claude/skills/modeling-strategy/scripts"),
		_os.path.join(_os.getcwd(), ".claude", "skills", "modeling-strategy", "scripts"),
	]
	for c in cands:
		if _os.path.isfile(_os.path.join(c, "check_strategy.py")):
			_sys.path.insert(0, _os.path.abspath(c))
			import check_strategy
			return check_strategy
	raise SystemExit(
		"--strategy was given but the modeling-strategy skill could not be found.\n"
		"Install it beside this skill, or set MS_SKILL to its directory.")


def main():
	ap = argparse.ArgumentParser()
	ap.add_argument("financials")
	ap.add_argument("assumptions", nargs="?")
	ap.add_argument("-o", "--out", default="data/model.json")
	ap.add_argument("--sector", help="business model, e.g. 'IT services', 'FMCG', "
									 "'two-wheelers'. Overrides assumptions.sector.")
	ap.add_argument("--fm", help="model.json from the `financial-model` skill. Its "
								 "bridge.fcff is cross-checked against this DCF's own "
								 "projection.")
	ap.add_argument("--fcff-from-model", action="store_true",
					help="with --fm, discount the three-statement FCFF itself rather "
						 "than the driver-based projection")
	ap.add_argument("--strategy", help="model_strategy.json from the modeling-strategy "
									 "skill. Optional: without it this script "
									 "behaves exactly as before.")
	ap.add_argument("--force-dcf", action="store_true",
					help="with --strategy, compute the DCF even where the approved "
						 "strategy calls it inappropriate. Stamped into model.json.")
	args = ap.parse_args()

	fin = json.load(open(args.financials))
	A_early = {}
	if args.assumptions:
		A_early = json.load(open(args.assumptions))
	sector = args.sector or A_early.get("sector") or fin.get("sector")

	# ---- approved modeling strategy (optional) -------------------------------
	# It selects the methodology; this file still performs every calculation, so
	# there is still exactly one DCF in the pipeline.
	strategy, dcf_role, strategy_block = None, None, None
	if args.strategy:
		strategy = json.load(open(args.strategy, encoding="utf-8"))
		gate = _load_gate()
		ok, why = gate.gate_ok(strategy, require_approved=True)
		if not ok:
			raise SystemExit(f"refusing to value: {why}")
		roles = {m.get("method"): m for m in strategy.get("valuation_methods") or []}
		for r in strategy.get("rejected_methods") or []:
			roles.setdefault(r.get("method"), {"role": "NOT_APPROPRIATE",
											 "rationale": r.get("reason")})
		d = roles.get("fcff_dcf") or {}
		dcf_role = (d.get("role") or "").upper() or "UNCLASSIFIED"
		strategy_block = {
			"modelability": (strategy.get("modelability") or {}).get("status"),
			"analyst_decision": (strategy.get("analyst_decision") or {}).get("status"),
			"revenue_model": (strategy.get("model_architecture") or {}).get("revenue_model"),
			"method_roles": {k: {"role": v.get("role"),
								 "execution_owner": v.get("execution_owner"),
								 "rationale": v.get("rationale")}
							 for k, v in roles.items()},
			"primary": [k for k, v in roles.items() if (v.get("role") or "") == "PRIMARY"],
			"manual_completion_required": [
				{"method": k, "steps": v.get("manual_steps") or []}
				for k, v in roles.items()
				if (v.get("role") or "") == "PRIMARY"
				and v.get("execution_owner") in ("analyst_manual", "not_supported")],
			"dcf_role": dcf_role,
		}
		if sector and strategy.get("sector") and sector != strategy["sector"]:
			print(f"! sector disagrees: --sector/{sector!r} vs strategy "
				 f"{strategy['sector']!r}; using {sector!r}")

	R = ratios(fin)

	# Suppress metrics that do not apply to this business model BEFORE anything
	# downstream reads them, so a meaningless ratio cannot reach the page.
	prof = None
	try:
		import sectors as _sectors
	except ImportError:
		import os as _os, sys as _sys
		_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
		import sectors as _sectors
	prof = _sectors.apply(R, sector)

	out = {"ratios": {k: v for k, v in R.items() if not k.startswith("_")},
		 "sector_profile": prof,
		 "dupont": dupont(R), "roiic": roiic(R), "forensic": forensic(R),
		 "warnings": R.get("_warn", []) + fin.get("warnings", [])}

	if prof["blocked"]:
		out["warnings"].insert(0,
			f"SECTOR NOT MODELLED: {prof['label']}. This skill's ratio pack, forensic "
			"screens and FCFF DCF assume a non-financial company. Suppressed metrics are "
			"null; the remaining ones are not sufficient for a lender.")

	if args.assumptions:
		A = A_early
		# Attach the three-statement bridge, if one was built. `financial-model`
		# owns the projections; this file owns the valuation — the bridge is the
		# only thing that crosses, so there is never more than one DCF.
		if args.fm:
			try:
				fm_doc = json.load(open(args.fm, encoding="utf-8"))
			except (OSError, json.JSONDecodeError) as exc:
				raise SystemExit(f"could not read --fm {args.fm}: {exc}")
			br = fm_doc.get("bridge")
			if not br:
				raise SystemExit(f"{args.fm} has no 'bridge' block — is it the "
								 "model.json from the financial-model skill?")
			A["_bridge"] = br
			if args.fcff_from_model:
				A["fcff_from_model"] = True
		if prof["altman_applicable"]:
			out["altman_z"] = altman_z(R, A)
		else:
			out["altman_z"] = {"skipped": "Altman Z was estimated on non-financial "
										 "firms and is not applicable to " + prof["label"]}
		out["piotroski_f"] = piotroski_f(R)

		run_dcf, skip_why = True, None
		if dcf_role in ("NOT_APPROPRIATE", "LOW_RELIABILITY"):
			skip_why = (f"the approved modeling strategy classifies the FCFF DCF as "
						f"{dcf_role} for this company: "
						f"{(strategy_block['method_roles'].get('fcff_dcf') or {}).get('rationale') or 'no rationale recorded'}")
			if args.force_dcf:
				out["warnings"].insert(0, "DCF COMPUTED UNDER --force-dcf AGAINST THE "
										 "APPROVED STRATEGY: " + skip_why)
			else:
				run_dcf = False

		if run_dcf:
			out["dcf"] = dcf(R, A)
			sc = scenarios(R, A)
			if sc:
				out["scenarios"] = sc
		else:
			out["dcf"] = {"skipped": skip_why,
						 "note": "No DCF was computed. Re-run with --force-dcf only "
								 "if the strategy was wrong — and change the strategy "
								 "rather than the flag."}
			out["warnings"].insert(0, "DCF NOT COMPUTED — " + skip_why)
		if A.get("peers"):
			out["relative"] = relative(A["peers"])
		if strategy_block:
			out["valuation_strategy"] = strategy_block
	else:
		out["altman_z"] = altman_z(R, None) if prof["altman_applicable"] else \
			{"skipped": "Altman Z was estimated on non-financial firms and is not "
						"applicable to " + prof["label"]}
		out["piotroski_f"] = piotroski_f(R)

	import os
	os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
	json.dump(out, open(args.out, "w"), indent=1, default=str)

	print(f"wrote {args.out}")
	p = out["sector_profile"]
	print(f" sector: {p['label']}"
		 + (f" (from {p['input']!r})" if p["input"] else " — none given, unfiltered"))
	if p["suppressed"]:
		print(f" suppressed as not applicable: {', '.join(p['suppressed'])}")
	if p["focus"]:
		print(f" lead with: {', '.join(p['focus'][:5])}")
	if p["valuation"]:
		print(f" valuation: {p['valuation'].get('primary')}"
			 f" multiples: {', '.join(p['valuation'].get('multiples', []))}")
	for n in p["manual_inputs"][:3]:
		print(f" pull from the annual report: {n}")
	if p["blocked"]:
		print(" ** this archetype is NOT modelled by this skill — see warnings **")
	vs = out.get("valuation_strategy")
	if vs:
		print(f" strategy: {vs['modelability']} / {vs['analyst_decision']} "
			 f"primary: {', '.join(vs['primary']) or 'NONE'} "
			 f"DCF role: {vs['dcf_role']}")
		for m in vs["manual_completion_required"]:
			print(f" ** {m['method']} is PRIMARY and is NOT computed here — "
				 f"{len(m['steps'])} manual step(s) recorded in the strategy **")
	if "bridge" in (out.get("dcf") or {}):
		b = out["dcf"]["bridge"]
		print(f" WACC {out['dcf']['wacc_build']['WACC']}% | intrinsic "
			 f"INR {b['Intrinsic value per share (INR)']:,} vs CMP {b['Current market price (INR)']}"
			 f" -> {b['Upside / (downside) %']}%")
		print(f" TV = {b['TV as % of EV']}% of EV" +
			 (" ** >75% means the DCF is a terminal-value bet; say so in the report **"
			 if b["TV as % of EV"] > 75 else ""))
	fm = (out.get("dcf") or {}).get("three_statement")
	if fm:
		src = "DISCOUNTING the three-statement FCFF" if fm["used"] else "cross-check only"
		print(f" three-statement model ({src}):")
		print(f" cumulative FCFF own {fm['total_own']:,} vs model "
			 f"{fm['total_three_statement']:,} gap {fm['gap_%']:+}%")
		for note in fm["notes"]:
			print(f" {note}")

	if "scenarios" in out:
		print(" scenarios:")
		for name, c in out["scenarios"]["cases"].items():
			if "error" in c:
				print(f" {name:<6} ERROR {c['error']}")
				continue
			print(f" {name:<6} p={c['probability']} INR {c['intrinsic_value_per_share']:,}"
				 f" ({c['upside_%']:+}%) TV {c['TV_as_%_of_EV']}% of EV")
		sm = out["scenarios"]["summary"]
		if sm.get("weighted_value_per_share"):
			print(f" weighted INR {sm['weighted_value_per_share']:,}"
				 f" spread {sm['range']['spread_x']}x")
		if sm.get("warning"):
			print(f" ! {sm['warning']}")

	for f in out["forensic"]["flags"]:
		print(f" [{f['verdict']:<5}] {f['test']}: {f['value']}")
	z = out.get("altman_z") or {}
	if z.get("latest") is not None:
		print(f" [{z['verdict']:<5}] Altman {z['variant']}: {z['latest']} ({z['zone']})")
	pf = out.get("piotroski_f") or {}
	if pf.get("score") is not None:
		print(f" [{pf['verdict']:<5}] Piotroski F: {pf['score']}/{pf['out_of']}")
	for w in out["warnings"] + out.get("dcf", {}).get("derived_from", []):
		print(f" ! {w}")


if __name__ == "__main__":
	main()
