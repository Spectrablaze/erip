#!/usr/bin/env python3
"""
build_strategy.py — strategy_decisions.json -> model_strategy.json + model_strategy.md

    python3 build_strategy.py --in strategy_decisions.json --outdir reports/<T>/data/ \
                              --md reports/<T>/model_strategy.md \
                              --financials reports/<T>/data/financials.json

Expands the archetype library into a concrete driver requirement list, works out
what the existing financial-model can and cannot execute, runs the gate checks,
and writes both the machine artifact and the page the analyst approves.

It does not choose the architecture. The analyst (with Claude) writes
`strategy_decisions.json`; this turns that into something the rest of the
pipeline can consume and be bound by.

`strategy_decisions.json` is the file to edit and rebuild from. Never hand-edit
`model_strategy.json` — same discipline as decisions.json -> assumptions.json.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import archetypes as AR        # noqa: E402
import valuation as VAL        # noqa: E402
import check_strategy as CHK   # noqa: E402

SCHEMA_VERSION = "1.0"

# What financial-model can execute today, verified against rows.py: one revenue
# row, prev(revenue)*(1+rev_growth). Anything else is either translated in the
# assumptions layer or refused.
FM_CAPABILITY = "consolidated_growth_only"


def _drivers_for(S: dict) -> list[dict]:
    """Flatten every segment's archetype into the driver list fma must cover."""
    out = []
    for sg in S.get("segments") or []:
        res = AR.resolve(sg.get("economic_archetype"))
        if res is None:
            continue
        akey, spec = res
        declared = {d.get("id"): d for d in (sg.get("revenue_drivers") or [])}
        for d in AR.required_drivers(akey):
            rec = {
                "driver_id": d["id"],
                "segment": sg.get("name"),
                "archetype": akey,
                "label": d["label"],
                "unit": d["unit"],
                "fma_preset": d.get("fma_preset"),
                "optional": bool(d.get("optional")),
                "kind": ("revenue" if any(x["id"] == d["id"]
                                          for x in spec["revenue_drivers"]) else "common"),
            }
            ev = (declared.get(d["id"]) or {}).get("evidence")
            if ev:
                rec["evidence"] = ev
            out.append(rec)
    return out


def _execution_block(S: dict) -> dict:
    """Decide how the approved architecture reaches financial-model, or that it
    cannot. This is the Phase A contract, made explicit per company."""
    segs = S.get("segments") or []
    unsupported: list[str] = []
    pending: list[str] = []
    translations = {}
    for sg in segs:
        res = AR.resolve(sg.get("economic_archetype"))
        if res is None:
            # An unvalidated proposal is an ANALYST question (AMBER), not an
            # architectural dead end (RED). It cannot be executed until it is
            # validated, and segment_build.py / financial-model refuse it on
            # exactly that ground — but the decision of whether the architecture
            # is right belongs to a person, not to this check.
            if sg.get("proposed_archetype"):
                pending.append(
                    f"segment {sg.get('name')!r} uses proposed archetype "
                    f"{sg.get('proposed_archetype')!r}: no validated translation "
                    "exists, so nothing downstream can execute it until the "
                    "archetype is signed off and added to the library")
            continue
        akey, spec = res
        translations[sg.get("name")] = spec.get("translation", "unsupported")
        if spec.get("translation") == "unsupported":
            unsupported.append(
                f"segment {sg.get('name')!r} on archetype {akey!r} cannot be "
                "defensibly translated into a single consolidated growth rate")

    for extra in S.get("declared_unsupported") or []:
        unsupported.append(extra)

    multi = len([s for s in segs if (s.get("materiality_pct") or 0) >=
                 AR.SEGMENT_MATERIALITY_FLOOR_PCT]) > 1
    revenue_model = (S.get("model_architecture") or {}).get("revenue_model")
    if not revenue_model:
        revenue_model = "segment_buildup" if multi else (
            "consolidated_buildup"
            if segs and AR.resolve((segs[0] or {}).get("economic_archetype")) and
            AR.resolve(segs[0]["economic_archetype"])[0] != "generic_growth"
            else "consolidated_growth")

    derived = revenue_model in ("segment_buildup", "consolidated_buildup")
    return {
        "revenue_build_site": "assumptions_layer" if derived else "financial_model",
        "consolidated_growth_is_derived": derived,
        "financial_model_capability": FM_CAPABILITY,
        "segment_translations": translations,
        "unsupported_requirements": unsupported,
        "pending_validation": pending,
        "note": (
            "Phase A: financial-model has one revenue row, prev(revenue)*(1+"
            "rev_growth). The segment driver maths runs in the assumptions layer "
            "via segment_build.py and lands as an auditable per-year consolidated "
            "revenue_growth path, with the full build preserved in "
            "segment_build.json and segment_build.md. financial-model refuses "
            "anything it cannot execute rather than flattening it."
            if derived else
            "Revenue is a consolidated growth rate, which financial-model executes "
            "natively. No derivation."),
    }, revenue_model


def _facts(S: dict, fin: dict | None) -> dict:
    f = VAL._facts_from(fin, S.get("facts"))
    segs = S.get("segments") or []
    material = [s for s in segs
                if (s.get("materiality_pct") or 0) >= AR.SEGMENT_MATERIALITY_FLOOR_PCT]
    f.setdefault("single_segment", len(material) <= 1)
    npeers = S.get("peer_count")
    if isinstance(npeers, int):
        f.setdefault("no_peer_set", npeers < 3)
    if (S.get("sector") or "").lower() == "financials":
        f["financial_sector"] = True
    return f


def _methods(S: dict, facts: dict) -> tuple[list[dict], list[dict]]:
    """Normalise the analyst's method calls; attach owners and machine findings."""
    proposal = VAL.assess(facts)
    methods, rejected = [], []
    for m in S.get("valuation_methods") or []:
        res = VAL.resolve(m.get("method"))
        if res is None:
            methods.append(dict(m))          # check_strategy will block on it
            continue
        key, spec = res
        role = (m.get("role") or "").upper().replace("-", "_").replace(" ", "_")
        rec = {
            "method": key,
            "label": spec["label"],
            "applicability": (m.get("applicability") or "").upper() or None,
            "role": role or None,
            "rationale": m.get("rationale", ""),
            "execution_owner": m.get("execution_owner") or spec["execution_owner"],
            "requirements": m.get("requirements") or spec["requires"],
            "limitations": m.get("limitations") or spec["limitations"],
        }
        if m.get("manual_steps"):
            rec["manual_steps"] = m["manual_steps"]
        p = proposal.get(key) or {}
        if p.get("hard"):
            rec["machine_finding"] = p["reason"]
            if rec["applicability"] != "NOT_APPROPRIATE":
                rec["applicability"] = "NOT_APPROPRIATE"
        if role == "NOT_APPROPRIATE":
            rejected.append({"method": key, "label": spec["label"],
                             "reason": rec["rationale"] or p.get("reason", "")})
        else:
            methods.append(rec)

    for r in S.get("rejected_methods") or []:
        res = VAL.resolve(r.get("method"))
        rejected.append({"method": res[0] if res else r.get("method"),
                         "label": res[1]["label"] if res else r.get("method"),
                         "reason": r.get("reason", "")})

    # Anything the machine hard-disqualified that the analyst never mentioned is
    # surfaced anyway — silence is not a classification.
    named = {m.get("method") for m in methods} | {r.get("method") for r in rejected}
    for key, p in proposal.items():
        if key in named or not p.get("hard"):
            continue
        rejected.append({"method": key, "label": VAL.METHODS[key]["label"],
                         "reason": p["reason"] + " (raised automatically; the "
                                                 "strategy did not classify it)"})
    return methods, rejected


def build(S: dict, fin: dict | None = None) -> dict:
    execution, revenue_model = _execution_block(S)
    facts = _facts(S, fin)
    methods, rejected = _methods(S, facts)

    arch_in = S.get("model_architecture") or {}
    schedules = list(arch_in.get("required_schedules") or [])
    for sg in S.get("segments") or []:
        res = AR.resolve(sg.get("economic_archetype"))
        if res:
            for s in res[1]["schedules"]:
                tag = f"{sg.get('name')}: {s}"
                if tag not in schedules:
                    schedules.append(tag)

    out = {
        "schema_version": SCHEMA_VERSION,
        "company": S.get("company"),
        "ticker": S.get("ticker"),
        "as_of": S.get("as_of") or date.today().isoformat(),
        "scope_status": S.get("scope_status") or "IN_SCOPE",
        "sector": S.get("sector"),
        "business_description": S.get("business_description", ""),
        "segments": S.get("segments") or [],
        "model_architecture": {
            "revenue_model": revenue_model,
            "segment_modeling": arch_in.get("segment_modeling", ""),
            "required_schedules": schedules,
            "consolidation_method": arch_in.get(
                "consolidation_method",
                "sum of segment revenue; segment margins weighted to a consolidated "
                "EBIT margin; central/unallocated costs carried separately"),
            "execution": execution,
        },
        "required_drivers": _drivers_for(S),
        "valuation_methods": methods,
        "rejected_methods": rejected,
        "uncertainties": S.get("uncertainties") or [],
        "facts": facts,
        "modelability": {
            "status": (S.get("modelability") or {}).get("status"),
            "rationale": (S.get("modelability") or {}).get("rationale") or [],
        },
        "analyst_decision": S.get("analyst_decision") or {
            "status": "PENDING", "by": None, "date": None, "notes": []},
    }

    r = CHK.run(out)
    out["modelability"] = {
        "status": r["derived_modelability"],
        "declared": (S.get("modelability") or {}).get("status"),
        "rationale": ((S.get("modelability") or {}).get("rationale") or []) +
                     r["cap_reasons"],
    }
    out["checks"] = r["issues"]
    return out


# ------------------------------------------------------------------ markdown
def _md(S: dict) -> str:
    L = []
    A = L.append
    A(f"# Modeling strategy — {S.get('company') or S.get('ticker') or 'company'}")
    A("")
    A(f"*As of {S['as_of']} · sector `{S.get('sector')}` · schema v{S['schema_version']}*")
    A("")
    st = S["modelability"]["status"]
    banner = {"GREEN": "GREEN — proceed once approved",
              "AMBER": "AMBER — proceed only on explicit analyst resolution",
              "RED": "RED — STOP. Do not generate assumptions or a model."}[st]
    A(f"## Modelability: {banner}")
    A("")
    for r in S["modelability"]["rationale"]:
        A(f"- {r}")
    if not S["modelability"]["rationale"]:
        A("- No constraint found: the business economics and the modelling "
          "architecture are sufficiently evidenced.")
    A("")
    if st == "RED":
        A("> Nothing downstream may run. `financial-model-assumptions`, "
          "`financial-model`, `peer-comps` and `model.py` all check this file and "
          "will refuse.")
        A("")

    A("## 1. What this business is")
    A("")
    A(S.get("business_description") or "*not stated*")
    A("")

    A("## 2. Segment decomposition and economic architecture")
    A("")
    A("| Segment | % revenue | Archetype | Identity | Confidence |")
    A("|---|---:|---|---|---|")
    for sg in S["segments"]:
        res = AR.resolve(sg.get("economic_archetype"))
        ident = res[1]["identity"].split(";")[0] if res else "**unvalidated proposal**"
        label = res[1]["label"] if res else (sg.get("proposed_archetype") or "?")
        A(f"| {sg.get('name')} | {sg.get('materiality_pct','?')} | {label} | "
          f"{ident} | {sg.get('confidence','?')} |")
    A("")
    for sg in S["segments"]:
        A(f"### {sg.get('name')}")
        A("")
        for kind, title in (("revenue_drivers", "Revenue drivers"),
                            ("margin_drivers", "Margin drivers"),
                            ("capital_drivers", "Capital drivers"),
                            ("working_capital_drivers", "Working-capital drivers")):
            ds = sg.get(kind) or []
            if not ds:
                continue
            A(f"**{title}** — " + ", ".join(
                (d.get("id") or d.get("label") or "?") if isinstance(d, dict) else str(d)
                for d in ds))
            A("")
        ev = sg.get("evidence") or []
        if ev:
            A("**Evidence**")
            A("")
            for e in ev:
                pg = f", p. {e['page']}" if e.get("page") else ""
                A(f"- \"{e.get('quote','')}\" — `{e.get('source','?')}`{pg}")
            A("")
        else:
            A("**Evidence** — none recorded.")
            A("")
        res = AR.resolve(sg.get("economic_archetype"))
        if res:
            A(f"> Trap for this archetype: {res[1]['false_positive']}")
            A("")

    A("## 3. Model architecture")
    A("")
    ma = S["model_architecture"]
    A(f"- **Revenue model** — `{ma['revenue_model']}`")
    A(f"- **Consolidation** — {ma['consolidation_method']}")
    if ma.get("segment_modeling"):
        A(f"- **Segment modelling** — {ma['segment_modeling']}")
    A("")
    A("**Required schedules**")
    A("")
    for s in ma["required_schedules"] or ["(none beyond the standard set)"]:
        A(f"- {s}")
    A("")
    ex = ma["execution"]
    A("**Execution against the existing pipeline**")
    A("")
    A(f"- financial-model capability: `{ex['financial_model_capability']}`")
    A(f"- revenue build site: `{ex['revenue_build_site']}`")
    A(f"- consolidated growth is derived: `{ex['consolidated_growth_is_derived']}`")
    A("")
    A(ex["note"])
    A("")
    if ex["unsupported_requirements"]:
        A("**UNSUPPORTED — the pipeline must refuse:**")
        A("")
        for u in ex["unsupported_requirements"]:
            A(f"- {u}")
        A("")

    A("## 4. Required drivers (the contract with financial-model-assumptions)")
    A("")
    A("| Driver | Segment | Unit | Kind | Required |")
    A("|---|---|---|---|---|")
    for d in S["required_drivers"]:
        A(f"| `{d['driver_id']}` | {d['segment']} | {d['unit']} | {d['kind']} | "
          f"{'optional' if d['optional'] else '**yes**'} |")
    A("")
    A("`financial-model-assumptions` finds cited evidence and proposes values for "
      "each of these. A required driver with no entry is a check failure there, "
      "not a silent gap.")
    A("")

    A("## 5. Valuation methodology")
    A("")
    A("| Method | Applicability | Role | Who computes it |")
    A("|---|---|---|---|")
    for m in S["valuation_methods"]:
        A(f"| {m.get('label', m.get('method'))} | {m.get('applicability') or '?'} | "
          f"**{m.get('role') or '?'}** | `{m.get('execution_owner','?')}` |")
    A("")
    for m in S["valuation_methods"]:
        A(f"**{m.get('label', m.get('method'))} — {m.get('role')}**")
        A("")
        A(m.get("rationale") or "*no rationale recorded*")
        A("")
        if m.get("limitations"):
            A("Limitations: " + "; ".join(m["limitations"]))
            A("")
        if m.get("manual_steps"):
            A("**Must be completed by hand — this pipeline cannot compute it:**")
            A("")
            for s in m["manual_steps"]:
                A(f"- {s}")
            A("")

    A("## 6. Methods rejected as inappropriate")
    A("")
    if S["rejected_methods"]:
        A("| Method | Why not |")
        A("|---|---|")
        for r in S["rejected_methods"]:
            A(f"| {r.get('label', r.get('method'))} | {r.get('reason','')} |")
    else:
        A("*None recorded — which is itself unusual. A strategy that rejects "
          "nothing has probably not tested anything.*")
    A("")

    A("## 7. Uncertainties")
    A("")
    if S["uncertainties"]:
        A("| Issue | Impact | How to resolve |")
        A("|---|---|---|")
        for u in S["uncertainties"]:
            A(f"| {u.get('issue','')} | {u.get('impact','')} | "
              f"{u.get('required_resolution','')} |")
    else:
        A("*None recorded.*")
    A("")

    A("## 8. Checks")
    A("")
    if S.get("checks"):
        for c in S["checks"]:
            A(f"- `{c['level']}` **{c['code']}** — {c['message']}")
    else:
        A("- none raised")
    A("")

    A("## 9. Analyst decision")
    A("")
    ad = S["analyst_decision"]
    A(f"**Status: {ad.get('status','PENDING')}**")
    A("")
    A("The analyst must record one of `APPROVED`, `MODIFIED` or `REJECTED` in "
      "`strategy_decisions.json` and rebuild. Until then every downstream skill "
      "refuses to run.")
    A("")
    A("- **APPROVE** — the decomposition, the drivers and the valuation methods stand.")
    A("- **MODIFY** — change `strategy_decisions.json` and rebuild; the original is "
      "kept under `recommended`.")
    A("- **REJECT / STOP** — the strategy is not defensible; the report does not proceed.")
    A("")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--outdir", default="data")
    ap.add_argument("--md", help="also write the analyst page here")
    ap.add_argument("--financials", help="financials.json, for the applicability facts")
    ap.add_argument("--strict", action="store_true",
                    help="exit non-zero on a blocking check")
    a = ap.parse_args()

    S_in = json.load(open(a.inp, encoding="utf-8"))
    fin = json.load(open(a.financials, encoding="utf-8")) if a.financials else None
    out = build(S_in, fin)

    os.makedirs(a.outdir, exist_ok=True)
    p = os.path.join(a.outdir, "model_strategy.json")
    txt = json.dumps(out, indent=1, ensure_ascii=False)
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(txt)
    out["_hash"] = hashlib.sha256(txt.encode()).hexdigest()[:12]

    md_path = a.md or os.path.join(a.outdir, "model_strategy.md")
    with open(md_path, "w", encoding="utf-8") as fh:
        fh.write(_md(out))

    print(f"wrote {p}")
    print(f"wrote {md_path}")
    print(f"  modelability: {out['modelability']['status']}"
          + (f"  (declared {out['modelability']['declared']})"
             if out["modelability"].get("declared") else ""))
    print(f"  segments: {len(out['segments'])}   "
          f"required drivers: {len(out['required_drivers'])}")
    prim = [m["method"] for m in out["valuation_methods"] if m.get("role") == "PRIMARY"]
    print(f"  primary: {', '.join(prim) or 'NONE'}")
    for m in out["valuation_methods"]:
        if m.get("role") == "PRIMARY" and m.get("execution_owner") in (
                VAL.MANUAL, VAL.NOT_SUPPORTED):
            print(f"  ** {m['method']} is PRIMARY and must be computed by hand "
                  f"({m['execution_owner']}) **")
    for c in out["checks"]:
        print(f"  [{c['level']:<8}] {c['code']}: {c['message'][:110]}")
    print(f"  analyst decision: {out['analyst_decision'].get('status')}")

    if a.strict and any(c["level"] == "BLOCKING" for c in out["checks"]):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
