#!/usr/bin/env python3
"""build_audit_book.py — produce an audit book from model.json and assumptions.json.

Usage:
 python scripts/build_audit_book.py \
 --model data/three_statement/model.json \
 --assumptions data/assumptions.json \
 --source-registry data/source_registry.json \
 --citations-dir data/citations \
 --outdir data/three_statement/
"""

import argparse, json, os, sys
from pathlib import Path
from datetime import datetime

try:
	from jinja2 import Environment, FileSystemLoader, select_autoescape
except ImportError:
	print("jinja2 required: pip install jinja2")
	sys.exit(1)

PROVENANCE_TYPES = ["REPORTED", "DERIVED", "ASSUMPTION", "MARKET", "MODEL_DERIVED"]
CONFIDENCE_LEVELS = {"HIGH": "Audited / regulatory filing", "MEDIUM": "Estimated / management guidance", "LOW": "Analyst judgment / no external source"}
APPROVAL_STATUSES = ["PENDING", "APPROVED", "CHALLENGED"]

def load_json(path):
	if Path(path).exists():
		with open(path, encoding="utf-8") as f:
			return json.load(f)
	return {}

def get_source_registry(source_registry_path):
	if source_registry_path and Path(source_registry_path).exists():
		with open(source_registry_path, encoding="utf-8") as f:
			return json.load(f)
	return {}

def collect_citations(citations_dir, row_keys):
	"""Collect all citations for the given row keys from citations_dir."""
	citations = {}
	if not citations_dir:
		return citations
	cit_dir = Path(citations_dir)
	if not cit_dir.exists():
		return citations
	for row_key in row_keys:
		cit_file = cit_dir / f"{row_key}.json"
		if cit_file.exists():
			with open(cit_file, encoding="utf-8") as f:
				citations[row_key] = json.load(f)
	return citations

def classify_source(source_name):
	"""Classify a source name into a provenance type."""
	name_lower = source_name.lower()
	if any(k in name_lower for k in ["annual report", "ar ", " standalone", " consolidated",
									 "audit report", "regulatory", "sebi", "nse", "bse",
									 "filing", "schedule", "financial statement"]):
		return "REPORTED"
	if any(k in name_lower for k in ["market data", "bloomberg", "reuters", "cap IQ",
									 "pacer", "cmie", "imf", "world bank", "market"]):
		return "MARKET"
	if any(k in name_lower for k in ["management", "guidance", "estimate", "projection"]):
		return "DERIVED"
	if any(k in name_lower for k in ["assumption", "judgment", "scenario", "analyst"]):
		return "ASSUMPTION"
	return "REPORTED"

def build_source_register(model, assumptions, source_registry, citations):
	"""Build the source register from model.json, assumptions.json, and citations."""
	register = []
	seen = set()

	# From citations in model.json
	for row_key, cit in model.get("citations", {}).items():
		src = cit.get("source", "") if isinstance(cit, dict) else str(cit)
		page = cit.get("page", "") if isinstance(cit, dict) else ""
		key = (src, page, row_key)
		if key not in seen:
			seen.add(key)
			register.append({
				"row_key": row_key,
				"source": src,
				"page": page,
				"provenance_type": classify_source(src),
				"confidence": "HIGH",
				"period": model.get("periods", {}).get("hist", [""])[-1] if model.get("periods", {}).get("hist") else "",
				"notes": "Cited in model.json",
			})

	# From source_registry.json
	for entry in source_registry.get("sources", []):
		key = (entry.get("source", ""), entry.get("page", ""), entry.get("row_key", ""))
		if key not in seen:
			seen.add(key)
			register.append({
				"row_key": entry.get("row_key", ""),
				"source": entry.get("source", ""),
				"page": entry.get("page", ""),
				"provenance_type": entry.get("provenance_type", classify_source(entry.get("source", ""))),
				"confidence": entry.get("confidence", "MEDIUM"),
				"period": entry.get("period", ""),
				"notes": entry.get("notes", ""),
			})

	# From citations directory
	for row_key, cit in citations.items():
		if isinstance(cit, dict):
			key = (cit.get("source", ""), cit.get("page", ""), row_key)
			if key not in seen:
				seen.add(key)
				register.append({
					"row_key": row_key,
					"source": cit.get("source", ""),
					"page": cit.get("page", ""),
					"provenance_type": cit.get("provenance_type", classify_source(cit.get("source", ""))),
					"confidence": cit.get("confidence", "MEDIUM"),
					"period": cit.get("period", ""),
					"notes": cit.get("notes", ""),
				})

	# Add derived assumptions from assumptions.json
	flat_assumptions = {
		"rf": "Risk-free rate",
		"erp": "Equity risk premium",
		"beta": "Equity beta",
		"cost_of_debt": "Cost of debt",
		"tax_rate": "Effective tax rate",
		"terminal_growth": "Terminal growth rate",
	}
	for key, label in flat_assumptions.items():
		if key in assumptions:
			register.append({
				"row_key": key,
				"source": f"assumptions.json > {key}",
				"page": "",
				"provenance_type": "ASSUMPTION",
				"confidence": "MEDIUM",
				"period": "",
				"notes": f"Analyst-assumed {label}: {assumptions[key]}",
			})

	# Sort: REPORTED first, then DERIVED, ASSUMPTION, MARKET, MODEL_DERIVED
	type_order = {t: i for i, t in enumerate(PROVENANCE_TYPES)}
	register.sort(key=lambda x: type_order.get(x.get("provenance_type", "DERIVED"), 99))
	return register

def build_assumption_register(assumptions):
	"""Build the assumption register from assumptions.json."""
	register = []
	scenarios = assumptions.get("scenarios", {})

	for key, value in assumptions.items():
		if key.startswith("_") or key in ["company", "currency", "sector", "built"]:
			continue
		if isinstance(value, (int, float)):
			register.append({
				"key": key,
				"label": key.replace("_", " ").title(),
				"value": value,
				"unit": "%" if "rate" in key.lower() or "margin" in key.lower() or "growth" in key.lower() else "",
				"provenance_type": "ASSUMPTION" if key in ["rf", "erp", "beta", "cost_of_debt", "tax_rate", "terminal_growth"] else "DERIVED",
				"rationale": f"Set in assumptions.json for {assumptions.get('company', 'model')}",
				"range": "",
				"approval_status": "APPROVED" if key in ["rf", "erp", "beta", "cost_of_debt", "tax_rate"] else "PENDING",
				"downstream": ["model.json", "model-workbook.xlsx", "audit_book.md"],
			})

	# Add scenario-specific assumptions
	for sc_name, sc_data in scenarios.items():
		if sc_name.startswith("_"):
			continue
		for key in ["revenue_growth", "ebitda_margin", "capex_pct_sales", "terminal_growth"]:
			if key in sc_data:
				register.append({
					"key": f"{sc_name}.{key}",
					"label": f"{sc_name.title()} — {key.replace('_', ' ').title()}",
					"value": sc_data[key] if not isinstance(sc_data[key], list) else f"[{len(sc_data[key])} values]",
					"unit": "%" if "growth" in key.lower() or "margin" in key.lower() else "",
					"provenance_type": "ASSUMPTION",
					"rationale": sc_data.get("_why", f"{sc_name.title()} scenario assumption"),
					"range": "",
					"approval_status": "PENDING",
					"downstream": [f"Scenario analysis ({sc_name})"],
				})
		if "intrinsic_value_per_share" in sc_data:
			register.append({
				"key": f"{sc_name}.intrinsic_value",
				"label": f"{sc_name.title()} — Intrinsic value per share",
				"value": sc_data["intrinsic_value_per_share"],
				"unit": "INR",
				"provenance_type": "MODEL_DERIVED",
				"rationale": "DCF output under " + sc_name.title() + " scenario",
				"range": "",
				"approval_status": "PENDING",
				"downstream": ["Valuation sheet", "Research note"],
			})

	return register

def build_lineage(model, assumptions):
	"""Build data lineage from model.json inputs to outputs."""
	lineage = {
		"stage_1_sources": {
			"description": "Raw inputs from source documents",
			"inputs": list(model.get("citations", {}).keys()),
		},
		"stage_2_assumptions": {
			"description": "Analyst assumptions from assumptions.json",
			"inputs": [k for k in assumptions.keys() if not k.startswith("_")],
		},
		"stage_3_calculations": {
			"description": "Model-generated values (model-derived)",
			"inputs": [k for k, v in model.get("rows", {}).items() if v.get("kind") == "calc"],
		},
		"stage_4_outputs": {
			"description": "Final model outputs",
			"inputs": ["model.json", "Company_ERIP_Model.xlsx", "Company_ERIP_Audit_Book"],
		},
	}
	return lineage

def build_valuation_inputs(model, assumptions):
	"""Extract material valuation inputs from model and assumptions."""
	inputs = []
	dcf = assumptions.get("dcf", {})

	# WACC build
	wb = dcf.get("wacc_build", {})
	for k, v in wb.items():
		if isinstance(v, (int, float)):
			inputs.append({
				"name": k.replace("_", " ").title(),
				"value": v,
				"format": "0.00%" if "rate" in k or "premium" in k or "growth" in k else "0.00",
				"source": "assumptions.json > dcf > wacc_build",
				"provenance_type": "MARKET" if k in ["risk_free_rate", "equity_risk_premium", "beta"] else "ASSUMPTION",
				"rationale": f"Input to WACC calculation",
			})
		elif isinstance(v, dict):
			for kk, vv in v.items():
				inputs.append({
					"name": f"{k} > {kk}",
					"value": vv,
					"format": "0.00%" if isinstance(vv, float) else "0.00",
					"source": "assumptions.json > dcf > wacc_build",
					"provenance_type": "MARKET",
					"rationale": f"WACC sub-component",
				})

	# Bridge
	bridge = dcf.get("bridge", {})
	for k, v in bridge.items():
		if isinstance(v, (int, float)):
			inputs.append({
				"name": k.replace("_", " ").title(),
				"value": v,
				"format": "#,##0.00",
				"source": "model.json > bridge",
				"provenance_type": "MODEL_DERIVED",
				"rationale": f"DCF bridge output",
			})

	# Terminal growth (from assumptions if not in dcf)
	if "terminal_growth" in assumptions and not dcf:
		inputs.append({
			"name": "Terminal Growth",
			"value": assumptions["terminal_growth"],
			"format": "0.00%",
			"source": "assumptions.json",
			"provenance_type": "ASSUMPTION",
			"rationale": "Long-run GDP-equivalent growth rate for terminal value",
		})

	return inputs

def build_checks_summary(model):
	"""Build a summary of model checks."""
	checks = model.get("checks", {})
	items = checks.get("items", [])
	blocking = [it for it in items if it.get("severity") == "blocking"]
	warning = [it for it in items if it.get("severity") == "warning"]
	passed = [it for it in items if it.get("ok", False)]
	failed = [it for it in items if not it.get("ok", False)]
	return {
		"total": len(items),
		"passed": len(passed),
		"failed": len(failed),
		"blocking": len(blocking),
		"warning": len(warning),
		"all_pass": checks.get("pass", True),
		"items": items,
	}

def build_audit_book(model_path, assumptions_path, source_registry_path, citations_dir, out_dir):
	model = load_json(model_path)
	assumptions = load_json(assumptions_path)
	source_registry = get_source_registry(source_registry_path)

	company = model.get("company", "Company")
	safe_name = company.replace(" ", "_").replace("/", "_").replace("&", "")
	out_filename = safe_name + "_ERIP_Audit_Book.md"
	out_path = os.path.join(out_dir, out_filename)

	# Collect all row keys
	row_keys = list(model.get("rows", {}).keys())
	citations = collect_citations(citations_dir, row_keys)

	# Build sections
	source_register = build_source_register(model, assumptions, source_registry, citations)
	assumption_register = build_assumption_register(assumptions)
	lineage = build_lineage(model, assumptions)
	valuation_inputs = build_valuation_inputs(model, assumptions)
	checks = build_checks_summary(model)

	# Render template
	template_dir = Path(__file__).parent / "templates"
	env = Environment(
		loader=FileSystemLoader(str(template_dir)),
		autoescape=select_autoescape(["html", "xml"]),
		trim_blocks=True,
		lstrip_blocks=True,
	)
	template = env.get_template("audit_book.md.j2")
	rendered = template.render(
		company=company,
		sector=model.get("sector", "N/A"),
		currency=model.get("currency", ""),
		built=model.get("built", ""),
		generated_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
		periods=model.get("periods", {}),
		options=model.get("options", {}),
		source_register=source_register,
		assumption_register=assumption_register,
		lineage=lineage,
		valuation_inputs=valuation_inputs,
		checks=checks,
		provenance_types=PROVENANCE_TYPES,
		confidence_levels=CONFIDENCE_LEVELS,
		approval_statuses=APPROVAL_STATUSES,
		reconciliation=model.get("reconciliation", []),
		citations=model.get("citations", {}),
		notes=model.get("notes", []),
		model_json_path=model_path,
		assumptions_json_path=assumptions_path,
	)

	with open(out_path, "w", encoding="utf-8") as f:
		f.write(rendered)

	return {
		"path": out_path,
		"filename": out_filename,
		"n_sources": len(source_register),
		"n_assumptions": len(assumption_register),
		"checks_pass": checks["all_pass"],
	}

def main():
	ap = argparse.ArgumentParser(
		description="Build audit book from model.json and assumptions.json",
		formatter_class=argparse.RawDescriptionHelpFormatter)
	ap.add_argument("--model", required=True, help="Path to model.json")
	ap.add_argument("--assumptions", required=True, help="Path to assumptions.json")
	ap.add_argument("--source-registry", default=None, help="Path to source_registry.json")
	ap.add_argument("--citations-dir", default=None, help="Directory with citation JSON files")
	ap.add_argument("--outdir", required=True, help="Output directory")
	args = ap.parse_args()

	result = build_audit_book(
		args.model, args.assumptions,
		args.source_registry, args.citations_dir,
		args.outdir)
	print("Wrote " + result["path"])
	print(f" Sources: {result['n_sources']} entries")
	print(f" Assumptions: {result['n_assumptions']} entries")
	chk_str = "ALL PASS" if result["checks_pass"] else "REVIEW REQUIRED"
	print(f" Checks: {chk_str}")

if __name__ == "__main__":
	raise SystemExit(main())
