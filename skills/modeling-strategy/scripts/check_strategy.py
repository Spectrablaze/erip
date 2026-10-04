#!/usr/bin/env python3
"""
check_strategy.py — the gate. Validates a model_strategy.json and derives its
modelability classification independently of what the document claims.

    python3 check_strategy.py --in data/model_strategy.json
    python3 check_strategy.py --in data/model_strategy.json --strict
    python3 check_strategy.py --in data/model_strategy.json --require-approved

`--strict` exits non-zero on any BLOCKING check, so it can gate a pipeline.
`--require-approved` additionally exits non-zero unless a human has recorded
APPROVED or MODIFIED in analyst_decision — this is the flag every downstream
consumer uses.

The modelability status is DERIVED here and compared against the declared one. A
document that claims GREEN while carrying an unsupported primary method is
downgraded, and the downgrade is reported. The declared value never wins: the
whole point of this layer is that it cannot talk itself into confidence.

Deriving is one-directional. Checks can only ever cap modelability DOWNWARD
(GREEN -> AMBER -> RED). Nothing here can promote a document.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import archetypes as AR      # noqa: E402
import valuation as VAL      # noqa: E402

BLOCKING, WARN, INFO = "BLOCKING", "WARN", "INFO"
RANK = {"GREEN": 2, "AMBER": 1, "RED": 0}
UNRANK = {v: k for k, v in RANK.items()}


def _issue(level, code, message):
    return {"level": level, "code": code, "message": message}


def run(S: dict) -> dict:
    """Validate. Returns {issues, derived_modelability, cap_reasons}."""
    issues: list[dict] = []
    cap = "GREEN"
    caps: list[str] = []

    def _cap(to: str, why: str):
        nonlocal cap
        if RANK[to] < RANK[cap]:
            cap = to
        caps.append(f"{to}: {why}")

    # ---------------------------------------------------------------- scope
    scope = (S.get("scope_status") or "").upper()
    sector = (S.get("sector") or "").strip().lower()
    if scope == "OUT_OF_SCOPE" or sector == "financials":
        issues.append(_issue(
            BLOCKING, "out_of_scope",
            "Banks, NBFCs and insurers are not modelled by this pipeline. Interest "
            "is revenue for a lender, so EBITDA, net debt, the revolver plug and "
            "FCFF are undefined. Stop here."))
        _cap("RED", "out of scope (financial sector)")
        return {"issues": issues, "derived_modelability": "RED",
                "cap_reasons": caps, "blocking": 1}
    if not scope:
        issues.append(_issue(WARN, "scope_missing",
                             "scope_status not set; expected IN_SCOPE or OUT_OF_SCOPE"))

    # ------------------------------------------------------------- segments
    segs = S.get("segments") or []
    if not segs:
        issues.append(_issue(BLOCKING, "no_segments",
                             "No segments declared. A consolidated-only view is still "
                             "one segment — declare it explicitly with its archetype."))
        _cap("RED", "no business decomposition at all")

    total_mat = 0.0
    generic_share = 0.0
    unknown_archetypes = []
    for i, sg in enumerate(segs):
        name = sg.get("name") or f"segment[{i}]"
        mat = sg.get("materiality_pct")
        if isinstance(mat, (int, float)):
            total_mat += float(mat)
        else:
            issues.append(_issue(WARN, "materiality_missing",
                                 f"{name}: no materiality_pct — cannot weight the build"))
            mat = 0.0

        key = sg.get("economic_archetype")
        res = AR.resolve(key) if key else None
        if res is None:
            proposed = sg.get("proposed_archetype")
            if proposed:
                unknown_archetypes.append(name)
                issues.append(_issue(
                    WARN, "proposed_archetype",
                    f"{name}: '{proposed}' is not in the validated library. It needs "
                    "explicit analyst sign-off before anything downstream runs."))
                _cap("AMBER", f"{name} uses an unvalidated proposed archetype")
            else:
                issues.append(_issue(
                    BLOCKING, "unknown_archetype",
                    f"{name}: economic_archetype {key!r} is not in the validated "
                    "library and no proposed_archetype was recorded. Pick a "
                    "validated archetype or raise a proposal — do not invent one."))
                _cap("RED", f"{name} has no defensible architecture")
                continue
        else:
            akey = res[0]
            if akey == "generic_growth":
                generic_share += float(mat or 0)
            # every non-optional revenue driver must be present on the segment
            declared = {d.get("id") for d in (sg.get("revenue_drivers") or [])}
            missing = [d["id"] for d in res[1]["revenue_drivers"]
                       if not d.get("optional") and d["id"] not in declared]
            if missing:
                issues.append(_issue(
                    BLOCKING, "drivers_incomplete",
                    f"{name}: archetype '{akey}' requires {', '.join(missing)} — "
                    "absent from revenue_drivers. An architecture missing its own "
                    "identity variables is not an architecture."))
                _cap("RED", f"{name} declares an archetype it does not populate")

        conf = (sg.get("confidence") or "").title()
        if conf == "Low":
            _cap("AMBER", f"{name} segment confidence is Low")
        if not sg.get("evidence"):
            issues.append(_issue(
                WARN, "segment_unevidenced",
                f"{name}: no evidence recorded. Every material conclusion should "
                "cite the knowledge base."))
            _cap("AMBER", f"{name} carries no source evidence")

        if isinstance(mat, (int, float)) and 0 < mat < AR.SEGMENT_MATERIALITY_FLOOR_PCT \
                and res is not None and res[0] != "generic_growth":
            issues.append(_issue(
                WARN, "fake_granularity",
                f"{name}: {mat}% of revenue carries its own driver architecture. "
                f"Below the {AR.SEGMENT_MATERIALITY_FLOOR_PCT}% floor this is "
                "granularity the disclosure probably does not support — consider "
                "folding it into the consolidated build."))

    if segs and abs(total_mat - 100.0) > 5.0:
        issues.append(_issue(
            WARN, "materiality_unbalanced",
            f"segment materiality sums to {total_mat:.1f}%, not ~100%. The "
            "decomposition does not account for the whole company."))

    if generic_share > AR.GENERIC_MATERIALITY_CAP_PCT:
        issues.append(_issue(
            WARN, "generic_dominates",
            f"{generic_share:.0f}% of revenue is on generic_growth, above the "
            f"{AR.GENERIC_MATERIALITY_CAP_PCT:.0f}% cap. At that share the 'model' "
            "is a single growth rate wearing a decomposition. Say so plainly."))
        _cap("AMBER", f"generic_growth covers {generic_share:.0f}% of revenue")

    # ---------------------------------------------------- valuation methods
    methods = S.get("valuation_methods") or []
    facts = S.get("facts") or {}
    roles = {}
    for m in methods:
        mk = m.get("method")
        res = VAL.resolve(mk)
        if res is None:
            issues.append(_issue(
                BLOCKING, "unknown_method",
                f"valuation method {mk!r} is not in the library."))
            _cap("RED", f"unknown valuation method {mk!r}")
            continue
        key, spec = res
        role = (m.get("role") or "").upper().replace("-", "_").replace(" ", "_")
        if role and role not in VAL.ROLES:
            issues.append(_issue(WARN, "bad_role",
                                 f"{key}: role {role!r} is not one of {VAL.ROLES}"))
        roles.setdefault(role, []).append(key)

        if not (m.get("rationale") or "").strip():
            issues.append(_issue(
                WARN, "unjustified_method",
                f"{key}: classified {role or 'unclassified'} with no rationale. "
                "Every classification needs an economic justification."))

        # hard disqualifiers cannot be asserted away
        if role in ("PRIMARY", "SECONDARY", "CROSS_CHECK"):
            for d in spec["disqualify"]:
                if d in VAL.HARD and facts.get(d):
                    issues.append(_issue(
                        BLOCKING, "disqualified_method",
                        f"{key} is marked {role} but {VAL.HARD[d]}. This is "
                        "arithmetic, not judgement — it cannot be overridden."))
                    _cap("RED", f"{key} marked {role} while disqualified")

        # execution reality
        own = m.get("execution_owner") or spec["execution_owner"]
        if role == "PRIMARY" and own in (VAL.MANUAL, VAL.NOT_SUPPORTED):
            if not (m.get("manual_steps") or []):
                issues.append(_issue(
                    BLOCKING, "manual_primary_unspecified",
                    f"{key} is PRIMARY with execution_owner '{own}' but no "
                    "manual_steps. The strategy must state exactly what a human "
                    "has to complete outside the pipeline."))
                _cap("RED", f"{key} is PRIMARY and unexecutable with no manual plan")
            else:
                issues.append(_issue(
                    INFO, "manual_primary",
                    f"{key} is the correct PRIMARY method and this pipeline cannot "
                    f"compute it (owner: {own}). Modelability is capped at AMBER and "
                    "the manual steps are recorded."))
                _cap("AMBER", f"PRIMARY method {key} must be completed by hand")

    if not roles.get("PRIMARY"):
        issues.append(_issue(
            BLOCKING, "no_primary",
            "No method is marked PRIMARY. A strategy that does not name the lens "
            "the valuation is anchored on has not made the decision it exists to "
            "make."))
        _cap("RED", "no primary valuation method selected")
    elif len(roles["PRIMARY"]) > 2:
        issues.append(_issue(WARN, "many_primaries",
                             f"{len(roles['PRIMARY'])} methods marked PRIMARY. "
                             "Anchoring on everything is anchoring on nothing."))

    # ------------------------------------------------------ execution reality
    arch = S.get("model_architecture") or {}
    ex = arch.get("execution") or {}
    unsupported = ex.get("unsupported_requirements") or []
    if unsupported:
        issues.append(_issue(
            BLOCKING, "unsupported_architecture",
            "The approved architecture requires something the existing "
            "financial-model cannot execute or defensibly translate: "
            + "; ".join(unsupported)
            + ". It must refuse rather than flatten. Resolve the requirement or "
              "revise the architecture."))
        _cap("RED", "architecture cannot be executed")

    for p in ex.get("pending_validation") or []:
        issues.append(_issue(
            WARN, "pending_validation",
            p + ". Sign the archetype off and add it to the library, or choose a "
                "validated one — the downstream skills will refuse it as it stands."))
        _cap("AMBER", "an archetype is awaiting validation")

    if arch.get("revenue_model") == "segment_buildup":
        if not ex.get("consolidated_growth_is_derived"):
            issues.append(_issue(
                WARN, "derivation_undeclared",
                "revenue_model is segment_buildup but execution does not declare "
                "consolidated_growth_is_derived. Phase A runs the segment maths in "
                "the assumptions layer and lands a DERIVED consolidated growth "
                "path — that has to be stated, not implied."))

    # ------------------------------------------------------- uncertainties
    for u in S.get("uncertainties") or []:
        if not u.get("required_resolution"):
            issues.append(_issue(
                WARN, "uncertainty_unresolved",
                f"uncertainty {u.get('issue','?')!r} has no required_resolution — "
                "an uncertainty without a way to close it is just a disclaimer."))

    declared = (S.get("modelability") or {}).get("status")
    derived = cap
    if declared and declared.upper() != derived:
        lvl = INFO if RANK.get(declared.upper(), 9) > RANK[derived] else WARN
        issues.append(_issue(
            lvl, "modelability_adjusted",
            f"declared modelability {declared.upper()} -> derived {derived}. "
            "The derived value governs."))

    return {"issues": issues, "derived_modelability": derived, "cap_reasons": caps,
            "blocking": sum(1 for i in issues if i["level"] == BLOCKING)}


def gate_ok(S: dict, require_approved: bool = True) -> tuple[bool, str]:
    """The single question every downstream consumer asks.

    Returns (ok, reason). Used by financial-model-assumptions, financial-model,
    peer-comps and model.py so the gate is enforced identically in all four.
    """
    r = run(S)
    if r["derived_modelability"] == "RED":
        return False, ("modeling strategy is RED — " +
                       "; ".join(r["cap_reasons"][:3] or ["no defensible architecture"]))
    if r["blocking"]:
        codes = [i["code"] for i in r["issues"] if i["level"] == BLOCKING]
        return False, f"modeling strategy has blocking checks: {', '.join(codes)}"
    if require_approved:
        st = ((S.get("analyst_decision") or {}).get("status") or "PENDING").upper()
        if st == "REJECTED":
            return False, "the analyst rejected this modeling strategy"
        if st not in ("APPROVED", "MODIFIED"):
            return False, (f"modeling strategy is {st} — the analyst approval gate "
                           "has not been resolved")
    return True, "ok"


def main():
    ap = argparse.ArgumentParser(description="validate a model_strategy.json")
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--strict", action="store_true",
                    help="exit non-zero on any BLOCKING check")
    ap.add_argument("--require-approved", action="store_true",
                    help="also exit non-zero unless the analyst gate is resolved")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    S = json.load(open(a.inp, encoding="utf-8"))
    r = run(S)

    if a.json:
        print(json.dumps(r, indent=2))
    else:
        print(f"modelability: {r['derived_modelability']}"
              + (f"   (declared {(S.get('modelability') or {}).get('status')})"
                 if (S.get("modelability") or {}).get("status") else ""))
        for c in r["cap_reasons"]:
            print(f"  capped -> {c}")
        if not r["issues"]:
            print("  no checks raised")
        for i in r["issues"]:
            print(f"  [{i['level']:<8}] {i['code']}: {i['message']}")
        ok, why = gate_ok(S, require_approved=a.require_approved)
        print(f"\ngate: {'PASS' if ok else 'BLOCKED'} — {why}")

    if a.strict and r["blocking"]:
        raise SystemExit(1)
    if a.require_approved:
        ok, _ = gate_ok(S, require_approved=True)
        if not ok:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
