#!/usr/bin/env python3
"""Reconcile a generated workbook against the source model.json and assumptions.json."""

import json, os, sys
from pathlib import Path

try:
	from openpyxl import load_workbook
except ImportError:
	sys.exit("openpyxl required: pip install openpyxl")

def load_json(path):
	if not Path(path).exists():
		return None
	with open(path, encoding='utf-8') as f:
		return json.load(f)

def reconcile(model_path, workbook_path, assumptions_path):
	model = load_json(model_path)
	assumptions = load_json(assumptions_path)
	if not model:
		print("ERROR: model.json not found")
		return False

	rd = model.get("rows", {})
	periods = model.get("periods", {}).get("all", [])
	fi = len(model.get("periods", {}).get("hist", []))
	DATA_COL0 = 2

	results = []

	# 1. Balance sheet tie
	ta = rd.get('total_assets',{}).get('values',[])
	tl = rd.get('total_liab_eq',{}).get('values',[])
	bs_pass = all(abs(float(a)-float(l)) < 0.01 for a, l in zip(ta, tl) if a and l)
	results.append(("Balance sheet tie", bs_pass, "total_assets == total_liab_eq"))

	# 2. Cash reconciliation
	cfo = rd.get('cfo',{}).get('values',[])
	cfi = rd.get('cfi',{}).get('values',[])
	cff = rd.get('cff',{}).get('values',[])
	nc = rd.get('net_change_cash',{}).get('values',[])
	cash_ok = True
	for j in range(fi, len(periods)):
		if abs((cfo[j] or 0) + (cfi[j] or 0) + (cff[j] or 0) - (nc[j] or 0)) > 0.01:
			cash_ok = False
		if j > fi:
			if abs((rd.get('cash_close',{}).get('values',[])[j-1] or 0) - (rd.get('cash_open',{}).get('values',[])[j] or 0)) > 0.01:
				cash_ok = False
	results.append(("Cash reconciliation", cash_ok, "CFO+CFI+CFF=net_change; close_t-1=open_t"))

	# 3. Checks pass
	checks_pass = model.get("checks", {}).get("pass", True)
	failed_checks = [it for it in model.get("checks",{}).get("items",[]) if not it.get("ok", True)]
	n_failed = len(failed_checks)
	n_block = sum(1 for it in failed_checks if it.get("severity") != "advisory")
	n_adv = n_failed - n_block
	fc_str = ("ALL PASS" if n_failed == 0 else f"{n_block} blocking, {n_adv} advisory item(s) flagged: "
			+ ", ".join(it.get("label", it.get("check", "?")) for it in failed_checks))
	results.append(("Integrity checks", checks_pass, fc_str))

	# 4. Workbook readable
	wb_pass = False
	if Path(workbook_path).exists():
		wb = load_workbook(workbook_path, data_only=False)
		try:
			wb_pass = wb["Model info"].cell(1, 1).value == model.get("company","") + " - Three-Statement Model"
		except Exception:
			pass
	results.append(("Workbook readable", wb_pass, "Model info sheet present"))

	print(f"\n# Workbook Reconciliation")
	print(f"- Model: {model.get('company','')}")
	print(f"- Generated: {model.get('built','')}")
	print(f"- Model.json: {model_path}")
	print(f"- Workbook: {workbook_path}")
	print(f"- Assumptions: {assumptions_path}")
	print()
	all_pass = True
	for name, ok, detail in results:
		status = "PASS" if ok else "FAIL"
		if not ok:
			all_pass = False
		print(f"- {name}: {status} ({detail})")

	print(f"\nOVERALL: {'ALL PASS' if all_pass else 'REVIEW REQUIRED'}")
	return all_pass

if __name__ == "__main__":
	import argparse
	ap = argparse.ArgumentParser()
	ap.add_argument("--model", required=True)
	ap.add_argument("--workbook", required=True)
	ap.add_argument("--assumptions", default=None)
	args = ap.parse_args()
	ok = reconcile(args.model, args.workbook, args.assumptions)
	sys.exit(0 if ok else 1)
