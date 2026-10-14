"""validate_report.py - one status for a report: is it fit to publish, and how current is it?

Runs or reads every check on a report and writes data/validation.json, which the showcase page
displays and the pre-push hook enforces.

  three-statement   the base model's blocking checks pass; failed advisory checks are explained in
                    data/exceptions.json
  workbook          the live Excel model reproduced every scenario in LibreOffice (data/workbook_check.json,
                    written by live_valuation.py --recalc); it must be newer than model.json
  citations         citation_check.py: no NOT_FOUND or UNRESOLVED evidence
  sources           source_register.py: every knowledge base built from the input on file
  typed numbers     number_lint.py: no model output typed into the report code
  stress            stress_test.py has run since the model last changed, with no invariant violations
  call              the standing call in reports/_knowledge/calls.json matches the model's target

Status is FAIL if any of these fail, PASS WITH NOTES if they pass but there are open notes (web
citations without a URL, explained exceptions, image citations), otherwise PASS.

    python validate_report.py --root reports/<T> [--paths scripts/build_report.py scripts/sections]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def _load(p, default=None):
    try:
        return json.load(open(p, encoding="utf-8"))
    except (OSError, ValueError):
        return default


def validate(root, paths=None):
    import citation_check
    import number_lint
    import source_register
    J = lambda *p: _load(os.path.join(root, *p))
    ticker = os.path.basename(os.path.normpath(root))
    M, A = J("data", "model.json") or {}, J("data", "assumptions.json") or {}
    checks, notes = {}, []

    # three-statement integrity
    ts = J("data", "three_statement", "scenarios", "base", "model.json") or J("data", "three_statement", "model.json") or {}
    items = (ts.get("checks") or {}).get("items", [])
    blocking = [i for i in items if not i["ok"] and i.get("severity") == "blocking"]
    exc = (J("data", "exceptions.json") or {}).get("exceptions", [])
    explained = {(e["check"], e["period"]) for e in exc}
    unexplained = [i for i in items if not i["ok"] and i.get("severity") != "blocking"
                   and (i["label"], i.get("period")) not in explained]
    checks["three_statement"] = {"status": "FAIL" if blocking or unexplained else "PASS",
                                 "detail": f"{len(items)} checks; {len(blocking)} blocking failures; "
                                           f"{len(exc)} explained exception(s); {len(unexplained)} unexplained"}
    if exc:
        notes.append(f"{len(exc)} explained check exception(s)")

    # workbook recalculation, and that it is not older than the model it reproduces
    wb = J("data", "workbook_check.json")
    m_time = os.path.getmtime(os.path.join(root, "data", "model.json")) if M else 0
    if not wb:
        checks["workbook"] = {"status": "FAIL", "detail": "no LibreOffice verification on record"}
    else:
        stale = datetime.fromisoformat(wb["run_at"]).timestamp() < m_time - 1
        checks["workbook"] = {"status": "FAIL" if stale or wb.get("status") != "PASS" else "PASS",
                              "detail": f"verified {wb['run_at']}" + (" but model.json is newer: re-run --recalc" if stale else ""),
                              "run_at": wb["run_at"]}

    # citations
    cc = citation_check.run(root)
    c = cc["counts"]
    checks["citations"] = {"status": cc["status"], "detail": ", ".join(f"{k} {v}" for k, v in sorted(c.items())),
                           "counts": c, "records": cc["records"]}
    ext_no_url = [r for r in cc["rows"] if r["grade"] == "EXTERNAL" and r.get("why")]
    if ext_no_url:
        notes.append(f"{len(ext_no_url)} web citation(s) without a URL")
    if c.get("NOT_HELD"):
        notes.append(f"{c['NOT_HELD']} citation(s) to documents not among the inputs")

    # sources
    sr = source_register.build(root)
    checks["sources"] = {"status": sr["status"], "detail": f"{len(sr['documents'])} input documents hashed; "
                         + ", ".join(f"{k['kb']} {k['status']}" for k in sr["knowledge_bases"])}

    # stress tests: on record, not older than the model, and no invariant violations
    ST = J("data", "stress.json")
    if not ST:
        checks["stress"] = {"status": "FAIL", "detail": "no stress tests on record (run stress_test.py)"}
    else:
        st_stale = datetime.fromisoformat(ST["run_at"]).timestamp() < m_time - 1
        viol = ST.get("invariant_violations") or []
        brk = [c["name"] for c in ST.get("cases", []) if any("revolver" not in b for b in c.get("breaches", []))]
        checks["stress"] = {"status": "FAIL" if (st_stale or viol) else "PASS",
                            "detail": f"{len(ST.get('cases', []))} cases, run {ST['run_at']}; "
                                      f"{len(viol)} invariant violation(s); {len(brk)} case(s) breach a reference level"
                                      + (" ; model.json is newer: re-run stress_test.py" if st_stale else "")}
        if brk:
            notes.append(f"stress breaches: {', '.join(brk)}")

    # typed numbers
    if paths is None:
        paths = (["scripts/build_report.py", "scripts/sections"]
                 if os.path.exists(os.path.join(root, "scripts", "build_report.py")) else ["build_report.py"])
    hits, n = number_lint.lint(root, paths)
    checks["typed_numbers"] = {"status": "FAIL" if hits else "PASS",
                               "detail": f"{len(hits)} model output(s) typed into {n} file(s)"}

    # the standing call agrees with the model
    tg = (M.get("dcf") or {}).get("target") or {}
    calls = _load(os.path.join(os.path.dirname(root), "_knowledge", "calls.json"), []) or []
    standing = [x for x in calls if x.get("ticker") == ticker and x.get("outcome") is None and not x.get("superseded_on")]
    st = standing[-1] if standing else None
    ok = bool(st and tg and float(st["target"]) == float(tg["target"]) and st["rating"] == tg["rating"])
    checks["call_ledger"] = {"status": "PASS" if ok else "FAIL",
                             "detail": (f"standing call v{st.get('version', 1)} {st['rating']} {st['target']:g}" if st else "no standing call")
                                       + ("" if ok else f" vs model {tg.get('rating')} {tg.get('target')}")}

    fails = [k for k, v in checks.items() if v["status"] != "PASS"]
    status = "FAIL" if fails else ("PASS WITH NOTES" if notes else "PASS")
    periods = (ts.get("periods") or {})
    out = {"ticker": ticker, "validated_at": datetime.now().isoformat(timespec="seconds"), "status": status,
           "failed": fails, "notes": notes, "checks": checks,
           "dates": {"cover_date": A.get("valuation_date"), "balance_sheet_date": A.get("balance_date"),
                     "last_actual_period": (periods.get("hist") or [None])[-1],
                     "forecast": f"{(periods.get('fcst') or ['?'])[0]} to {(periods.get('fcst') or ['?'])[-1]}",
                     "model_run": datetime.fromtimestamp(m_time).isoformat(timespec="seconds") if m_time else None},
           "call": {"rating": tg.get("rating"), "target": tg.get("target"),
                    "version": st.get("version") if st else None}}
    json.dump(out, open(os.path.join(root, "data", "validation.json"), "w", encoding="utf-8"), indent=1,
              ensure_ascii=False)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--root", required=True)
    ap.add_argument("--paths", nargs="+")
    a = ap.parse_args()
    out = validate(os.path.abspath(a.root), a.paths)
    for k, v in out["checks"].items():
        print(f"  {v['status']:5} {k:16} {v['detail']}"[:200])
    for nte in out["notes"]:
        print(f"  note  {nte}")
    print(f"{out['ticker']}: {out['status']}")
    sys.exit(1 if out["status"] == "FAIL" else 0)


if __name__ == "__main__":
    main()
