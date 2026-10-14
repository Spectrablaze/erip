"""selftest.py - one command that says whether this skill is safe to ship.

Run it before packaging, after any edit to scripts/, and after anything that rewrites files in
bulk. Every check writes only to a temp directory; no report folder is modified.

    python selftest.py [--reports <dir with the fixture reports>] [--quick]

  1  syntax       every bundled .py parses (compile(), not py_compile: py_compile writes)
  2  indentation  tab-indented files are listed. They were the tell-tale of the Aug 2026 damage.
                  This is a warning, because some files were always tab-indented.
  3  regression   model.py on APSEZ's frozen three-statement model reproduces its saved valuation exactly
  4  three-stmt   the JSW base case rebuilt from scratch gives the same FCFF and value as
                  data/model.json (financial-model ingest -> build -> model.py --fcff-from-model)
  5  workbook     the JSW live workbook rebuilds and, in LibreOffice, reproduces every
                  scenario's Python value with no formula errors (skipped with --quick or if
                  LibreOffice/UNO is unavailable)
  6  typed-nums   no current model output is typed as a literal in the fixture reports' build code
                  (number_lint.py)
  7  package      package_skill.py output has no node_modules/__pycache__ and fits the 10 MB
                  browser-upload limit
  8  copies       the project and public-repo copies match this one (ENGINE.md exempt: the
                  public copy has local paths removed on purpose)

Exit code 0 only if no check FAILs.
"""
from __future__ import annotations

import argparse
import filecmp
import json
import os
import subprocess
import sys
import tempfile
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
SKILLS = os.path.dirname(SKILL)
PY = sys.executable
SKIP_DIRS = {"node_modules", "__pycache__", ".git", "reports"}
# Machine-specific paths live outside the skill, in ~/.claude/erip_selftest.json:
#   {"reports": "<dir holding ADANIPORTS/ and JSWINFRA/>", "copies": ["<other copy of this skill>", ...]}
_CFG_P = os.path.join(os.path.expanduser("~"), ".claude", "erip_selftest.json")
CFG = json.load(open(_CFG_P, encoding="utf-8")) if os.path.exists(_CFG_P) else {}
COPIES = CFG.get("copies", [])
COPY_EXEMPT = {"ENGINE.md"}

results = []


def report(name, status, detail=""):
    results.append((name, status, detail))
    print(f"  {status:4}  {name:12} {detail}")


def _pyfiles(root):
    for r, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            if f.endswith(".py"):
                yield os.path.join(r, f)


def check_syntax():
    bad = []
    for p in _pyfiles(SKILL):
        try:
            compile(open(p, "rb").read(), p, "exec")
        except SyntaxError as e:
            bad.append(f"{os.path.relpath(p, SKILL)}:{e.lineno} {e.msg}")
    report("syntax", "FAIL" if bad else "PASS", "; ".join(bad) or f"{sum(1 for _ in _pyfiles(SKILL))} files parse")


def check_indent():
    tabbed = [os.path.relpath(p, SKILL) for p in _pyfiles(SKILL)
              if any(line.startswith("\t") for line in open(p, encoding="utf-8", errors="replace"))]
    report("indentation", "WARN" if tabbed else "PASS",
           ("tab-indented: " + ", ".join(sorted(tabbed))) if tabbed else "all space-indented")


def _walk_diff(a, b, path="", out=None):
    out = [] if out is None else out
    if isinstance(a, dict) and isinstance(b, dict):
        for k in set(a) | set(b):
            _walk_diff(a.get(k), b.get(k), f"{path}/{k}", out)
    elif isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        for i, (x, y) in enumerate(zip(a, b)):
            _walk_diff(x, y, f"{path}[{i}]", out)
    elif a != b:
        out.append(path)
    return out


def check_regression(reports):
    """model.py, on a frozen three-statement model, must reproduce the saved APSEZ valuation exactly.

    The fixture is built by scenario_runs.py: base case, three-statement FCFF, scenarios attached
    afterwards. So the run strips the scenarios and compares everything except that block."""
    root = os.path.join(reports, "ADANIPORTS")
    ts = os.path.join(root, "data", "three_statement", "scenarios", "base", "model.json")
    if not (os.path.exists(os.path.join(root, "data", "model.json")) and os.path.exists(ts)):
        return report("regression", "SKIP", "no APSEZ fixture")
    saved = json.load(open(os.path.join(root, "data", "model.json"), encoding="utf-8"))
    sector = saved.get("sector_profile", {}).get("input", "realestate")
    A = json.load(open(os.path.join(root, "data", "assumptions.json"), encoding="utf-8"))
    A.pop("scenarios", None)
    with tempfile.TemporaryDirectory() as td:
        ap, out = os.path.join(td, "a.json"), os.path.join(td, "m.json")
        json.dump(A, open(ap, "w"))
        d = lambda *p: os.path.join(root, "data", *p)
        r = subprocess.run([PY, os.path.join(HERE, "model.py"), d("financials.json"), ap,
                            "--sector", sector, "--strategy", d("model_strategy.json"),
                            "--fm", ts, "--fcff-from-model", "-o", out], capture_output=True, text=True)
        if r.returncode:
            return report("regression", "FAIL", "model.py crashed: " + r.stderr.strip().splitlines()[-1][:200])
        new = json.load(open(out, encoding="utf-8"))
    saved.pop("scenarios", None)
    new.pop("scenarios", None)
    diffs = _walk_diff(saved, new)
    report("regression", "FAIL" if diffs else "PASS",
           f"{len(diffs)} diffs, e.g. {diffs[:3]}" if diffs else
           f"APSEZ valuation reproduced exactly (INR {saved['dcf']['bridge']['Intrinsic value per share (INR)']})")


def check_three_statement(reports):
    root = os.path.join(reports, "JSWINFRA")
    if not os.path.exists(os.path.join(root, "data", "scenarios_3s.json")):
        return report("three-stmt", "SKIP", "no JSW fixture")
    sys.path.insert(0, HERE)
    from scenario_runs import value_case
    A = json.load(open(os.path.join(root, "data", "assumptions.json"), encoding="utf-8"))
    saved = json.load(open(os.path.join(root, "data", "model.json"), encoding="utf-8"))
    strat = os.path.join(root, "data", "model_strategy.json")
    try:
        m = value_case(root, A, "selftest", "realestate", strat if os.path.exists(strat) else None)
    except SystemExit as e:
        return report("three-stmt", "FAIL", str(e)[:200])
    v_new = m["dcf"]["bridge"]["Intrinsic value per share (INR)"]
    v_old = saved["dcf"]["bridge"]["Intrinsic value per share (INR)"]
    f_new = [r["FCFF"] for r in m["dcf"]["forecast"]]
    f_old = [r["FCFF"] for r in saved["dcf"]["forecast"]]
    ok = v_new == v_old and f_new == f_old
    report("three-stmt", "PASS" if ok else "FAIL",
           f"JSW base INR {v_new} (saved {v_old}); FCFF {'identical' if f_new == f_old else 'DIFFERS'}")


def _uno_available():
    cmd = (["wsl", "-d", os.environ.get("ERIP_WSL_DISTRO", "Ubuntu"), "--"] if os.name == "nt" else []) + \
          ["python3", "-c", "import uno"]
    try:
        return subprocess.run(cmd, capture_output=True, timeout=60).returncode == 0
    except Exception:
        return False


def check_workbook(reports, quick):
    root = os.path.join(reports, "JSWINFRA")
    if quick:
        return report("workbook", "SKIP", "--quick")
    if not os.path.isdir(os.path.join(root, "data", "three_statement", "scenarios")):
        return report("workbook", "SKIP", "no JSW scenario fixture")
    if not _uno_available():
        return report("workbook", "SKIP", "LibreOffice + python3-uno not available")
    sys.path.insert(0, os.path.join(HERE, "workbook"))
    import live_valuation as lv
    # lo_recalc runs inside WSL, which only sees the Windows drive, so the temp dir must be on it
    with tempfile.TemporaryDirectory(dir=os.path.join(root, "data")) as td:
        raw, out = os.path.join(td, "raw.xlsx"), os.path.join(td, "out.xlsx")
        try:
            info = lv.build(root, raw)
            res = lv.recalc_and_verify(raw, out, info)
        except SystemExit as e:
            return report("workbook", "FAIL", str(e)[:300])
    report("workbook", "PASS", "; ".join(f"{k} {v['value']} ({v['rating']})" for k, v in res.items())
           + " - each equals its Python value, 0 formula errors")


def check_engine_tests():
    """The synthetic-company engine tests (tests/run_tests.py): closed-form DCF checks, three-statement
    identities re-derived from the rows, and a golden end-to-end value. Needs no source documents."""
    t = os.path.join(SKILL, "tests", "run_tests.py")
    if not os.path.exists(t):
        return report("engine", "SKIP", "tests/run_tests.py missing")
    r = subprocess.run([PY, t], capture_output=True, text=True)
    last = (r.stdout.strip().splitlines() or ["no output"])[-1]
    report("engine", "PASS" if r.returncode == 0 else "FAIL", last)


def check_number_lint(reports):
    """No current model output may be typed into a fixture report's build code."""
    import number_lint
    for t in ("JSWINFRA", "ADANIPORTS"):
        root = os.path.join(reports, t)
        if not os.path.exists(os.path.join(root, "data", "model.json")):
            report("typed-nums", "SKIP", f"no {t} fixture")
            continue
        paths = (["scripts/build_report.py", "scripts/sections"]
                 if os.path.exists(os.path.join(root, "scripts", "build_report.py")) else ["build_report.py"])
        hits, n = number_lint.lint(root, paths)
        report("typed-nums", "FAIL" if hits else "PASS",
               f"{t}: " + ("; ".join(f"{f}:{ln} {num}" for f, ln, num, _, _ in hits[:4]) if hits
                           else f"no model output typed into {n} file(s)"))


def check_package():
    pk = os.path.join(SKILLS, "skill-creator", "scripts", "package_skill.py")
    if not os.path.exists(pk):
        return report("package", "SKIP", "skill-creator not installed")
    with tempfile.TemporaryDirectory() as td:
        r = subprocess.run([PY, pk, SKILL, td], capture_output=True, text=True, cwd=os.path.dirname(pk))
        z = os.path.join(td, "equity-research-report.zip")
        if r.returncode or not os.path.exists(z):
            return report("package", "FAIL", (r.stdout + r.stderr).strip().splitlines()[-1][:200])
        names = zipfile.ZipFile(z).namelist()
        junk = [n for n in names if "node_modules" in n or "__pycache__" in n]
        mb = os.path.getsize(z) / 1e6
    bad = junk or mb >= 10
    report("package", "FAIL" if bad else "PASS",
           f"{len(names)} entries, {mb:.2f} MB" + (f", {len(junk)} build-output entries" if junk else ""))


def check_copies():
    if not COPIES:
        return report("copies", "SKIP", "no copies listed in ~/.claude/erip_selftest.json")
    for dst in COPIES:
        if not os.path.isdir(dst):
            report("copies", "SKIP", f"missing {dst}")
            continue
        diff = []

        def walk(cmp, rel=""):
            diff.extend(os.path.join(rel, f) for f in cmp.left_only + cmp.right_only + cmp.diff_files
                         if f not in SKIP_DIRS and f not in COPY_EXEMPT and not f.endswith(".pyc"))
            for name, sub in cmp.subdirs.items():
                if name not in SKIP_DIRS:
                    walk(sub, os.path.join(rel, name))
        walk(filecmp.dircmp(SKILL, dst, ignore=list(SKIP_DIRS)))
        # dircmp compares by stat; confirm reported differences with a byte compare
        diff = [f for f in diff if not (os.path.isfile(os.path.join(SKILL, f)) and os.path.isfile(os.path.join(dst, f))
                                        and filecmp.cmp(os.path.join(SKILL, f), os.path.join(dst, f), shallow=False))]
        label = "project" if "Equity Report" in dst else "public repo"
        report("copies", "FAIL" if diff else "PASS", f"{label}: " + (", ".join(diff[:8]) if diff else "in sync"))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--reports", default=CFG.get("reports", "reports"))
    ap.add_argument("--quick", action="store_true", help="skip the LibreOffice workbook check")
    a = ap.parse_args()
    print(f"selftest  {SKILL}")
    check_syntax()
    check_indent()
    check_regression(a.reports)
    check_three_statement(a.reports)
    check_workbook(a.reports, a.quick)
    check_engine_tests()
    check_number_lint(a.reports)
    check_package()
    check_copies()
    fails = [n for n, s, _ in results if s == "FAIL"]
    print(f"\n{'FAIL: ' + ', '.join(fails) if fails else 'ALL PASS'}  "
          f"({sum(s == 'PASS' for _, s, _ in results)} pass, {sum(s == 'WARN' for _, s, _ in results)} warn, "
          f"{sum(s == 'SKIP' for _, s, _ in results)} skip)")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
