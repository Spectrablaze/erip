"""number_lint.py - find model outputs typed into report code as literals.

A figure typed into a string goes stale the moment the model is re-run: the August APSEZ prose
kept quoting INR 641 and a "INR 375 capex swing" after the model said otherwise. This reads every
string literal in the report's build scripts (f-string text included, its {expressions} excluded)
and flags numbers equal to a current model output: valuation bridge, terminal cross-check,
scenario values, sensitivity grid, tornado bars and the three-statement forecast lines.

    python number_lint.py --root reports/<T> [--paths build_report.py scripts/sections]

Exit 1 when anything is flagged. A literal that is a coincidence (a capacity of 563 MMT that
equals a per-share value) is silenced with a trailing comment on its line: # lint: not-model
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import re
import sys

NUM = re.compile(r"(?<![\w.\-])(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)(?![\w])")
# a number followed by one of these is a quantity or a date, not a valuation output
UNIT = re.compile(r"\s*(?:%?\s*)?(?:MT|MMT|MTPA|km|years?|yrs?|months?|days?|bp|bps|TEU|rakes?|ports?|"
                  r"Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\b")

RANGE = re.compile(r"\s*(?:to|-|–)\s*[\d,.]+")
# accounting standards and legal references: "Ind AS 116", "Section 135", "Rule 11"
REF = re.compile(r"(?:\bAS|\bIFRS|\bSection|\bRule|\bSchedule|\bReg\.?)\s*$")
# page references: "p.107", "pp.70, 107", "pp.103-107"
PAGE = re.compile(r"\bpp?\.\s?(?:[\d,\s\-\u2013]|to\b)*$")


def outputs(root):
    """Current model outputs worth guarding, as {normalised value: where it comes from}."""
    J = lambda p: json.load(open(os.path.join(root, p), encoding="utf-8"))
    M = J("data/model.json")
    out = {}

    def add(v, where):
        if isinstance(v, bool) or not isinstance(v, (int, float)) or v != v:
            return
        if abs(v) >= 100 and not (1990 <= abs(v) <= 2100 and float(v).is_integer()):
            out.setdefault(("i", round(abs(v))), where)
        if 1 <= abs(v) < 100 and not float(v).is_integer():
            out.setdefault(("f", round(abs(v), 1)), where)

    d = M.get("dcf") or {}
    INPUTS = ("net debt", "market price", "Shares", "non-operating", "lease", "minority")   # sourced inputs, not outputs
    for k, v in (d.get("bridge") or {}).items():
        if not any(t in k for t in INPUTS):
            add(v, f"dcf.bridge.{k}")
    for k, v in (d.get("terminal_cross_check") or {}).items():
        if "supplied" not in k:                    # the exit multiple is an input
            add(v, f"dcf.terminal_cross_check.{k}")
    for row in (d.get("sensitivity") or {}).get("grid", []):
        for v in row:
            add(v, "dcf.sensitivity.grid")
    for r in d.get("forecast") or []:
        for k in ("Sales", "EBIT", "NOPAT", "FCFF", "PV of FCFF"):
            add(r.get(k), f"dcf.forecast.{k}")
    sc = M.get("scenarios") or {}
    for c, v in (sc.get("cases") or {}).items():
        add(v.get("intrinsic_value_per_share"), f"scenarios.{c}")
    add(sc.get("probability_weighted") or (sc.get("summary") or {}).get("weighted_value_per_share"), "scenarios.weighted")
    tp = os.path.join(root, "data", "tornado.json")
    if os.path.exists(tp):
        for dr in J("data/tornado.json").get("drivers", []):
            add(dr.get("low"), f"tornado.{dr['label']}")
            add(dr.get("high"), f"tornado.{dr['label']}")
            add(abs((dr.get("high") or 0) - (dr.get("low") or 0)), f"tornado swing.{dr['label']}")
    return out


def _strings(tree):
    """(lineno, text) for every literal piece of text, f-string text parts included."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            yield node.lineno, getattr(node, "end_lineno", node.lineno), node.value


def lint(root, paths):
    guard = outputs(root)
    hits = []
    files = []
    for p in paths:
        p = os.path.join(root, p)
        if os.path.isdir(p):
            files += [os.path.join(p, f) for f in sorted(os.listdir(p)) if f.endswith(".py")]
        elif os.path.exists(p):
            files.append(p)
    for f in files:
        src = open(f, encoding="utf-8").read()
        lines = src.splitlines()
        for ln, end, text in _strings(ast.parse(src)):
            if any("lint: not-model" in lines[k - 1] for k in range(ln, min(end, len(lines)) + 1)):
                continue
            for m in NUM.finditer(text):
                if UNIT.match(text, m.end()) or PAGE.search(text[max(0, m.start() - 24):m.start()]):
                    continue
                rng = RANGE.match(text, m.end())          # "117 to 122 MT": the unit is on the second number
                if rng and UNIT.match(text, rng.end()):
                    continue
                if REF.search(text[max(0, m.start() - 12):m.start()]):
                    continue
                raw = m.group(1).replace(",", "")
                if "." not in raw and text[m.end():m.end() + 1] == "%":   # whole-number percentages
                    continue
                v = float(raw)
                key = ("f", round(v, 1)) if "." in raw else ("i", round(v))
                if key in guard:
                    hits.append((os.path.relpath(f, root), ln, m.group(1), guard[key], text.strip()[:70]))
    return hits, len(files)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--root", required=True)
    ap.add_argument("--paths", nargs="+", default=["build_report.py", "scripts"])
    a = ap.parse_args()
    hits, n = lint(os.path.abspath(a.root), a.paths)
    for f, ln, num, where, ctx in hits:
        print(f"  {f}:{ln}  {num}  = {where}   \"{ctx}\"")
    print(f"{len(hits)} typed model output(s) in {n} file(s)" + ("" if hits else ": clean"))
    sys.exit(1 if hits else 0)


if __name__ == "__main__":
    main()
