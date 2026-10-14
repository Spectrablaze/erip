"""lo_recalc.py - recalculate an .xlsx in headless LibreOffice and read cells back.

Runs under the system python3 that ships LibreOffice's UNO bridge (on Windows: inside WSL,
`apt install libreoffice-calc python3-uno`). openpyxl writes formulas without cached values, so
a workbook straight out of openpyxl shows blanks in any viewer that does not calculate. This
opens it, turns on iterative calculation (the three-statement model's interest is circular),
optionally sets input cells, recalculates and saves the values alongside the formulas.

    python3 lo_recalc.py in.xlsx [--out out.xlsx] [--set "Scenarios!B4=2" ...]
                         [--read "DCF!B34" ...] [--errors]

Prints one JSON object: {"read": {ref: value}, "errors": [ref, ...]}.
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
import time

import uno
from com.sun.star.beans import PropertyValue


def _p(name, value):
    p = PropertyValue()
    p.Name, p.Value = name, value
    return p


def _split(ref):
    sheet, cell = ref.rsplit("!", 1)
    return sheet.strip("'"), cell


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inp")
    ap.add_argument("--out")
    ap.add_argument("--set", action="append", default=[])
    ap.add_argument("--read", action="append", default=[])
    ap.add_argument("--max-passes", type=int, default=200)
    ap.add_argument("--errors", action="store_true", help="list every formula cell that evaluates to an error")
    args = ap.parse_args()

    pipe = f"lorecalc{os.getpid()}"
    profile = tempfile.mkdtemp(prefix="lo_profile_")
    proc = subprocess.Popen(["soffice", "--headless", "--invisible", "--norestore", "--nologo",
                             f"-env:UserInstallation=file://{profile}",
                             f"--accept=pipe,name={pipe};urp;"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        local = uno.getComponentContext()
        resolver = local.ServiceManager.createInstanceWithContext("com.sun.star.bridge.UnoUrlResolver", local)
        ctx = None
        for _ in range(120):
            try:
                ctx = resolver.resolve(f"uno:pipe,name={pipe};urp;StarOffice.ComponentContext")
                break
            except Exception:
                time.sleep(0.5)
        if ctx is None:
            sys.exit("LibreOffice did not start")
        desktop = ctx.ServiceManager.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)
        doc = desktop.loadComponentFromURL(uno.systemPathToFileUrl(os.path.abspath(args.inp)), "_blank", 0,
                                           (_p("Hidden", True),))
        doc.IsIterationEnabled = True
        doc.IterationCount = 1000
        doc.IterationEpsilon = 1e-7
        sheets = doc.Sheets
        for s in args.set:
            ref, val = s.split("=", 1)
            sh, c = _split(ref)
            cell = sheets.getByName(sh).getCellRangeByName(c)
            try:
                cell.setValue(float(val))
            except ValueError:
                cell.setString(val)
        # A circular model needs more than one pass: LibreOffice stops each pass at its
        # iteration limit, so recalculate until a probe of every sheet's numbers stops moving.
        def _probe():
            tot = 0.0
            for i in range(sheets.getCount()):
                sh = sheets.getByIndex(i)
                cur = sh.createCursor()
                cur.gotoEndOfUsedArea(False)
                a = cur.getRangeAddress()
                for row in sh.getCellRangeByPosition(0, 0, a.EndColumn, a.EndRow).getDataArray():
                    tot += sum(abs(v) for v in row if isinstance(v, float))
            return tot
        prev, passes = None, 0
        while passes < args.max_passes:
            doc.calculateAll()
            passes += 1
            cur_ = _probe()
            # one part in 1e13 of the whole workbook: tight enough that every line, not just the
            # headline value, settles to well under INR 0.01 Cr (the validation pack compares them)
            if prev is not None and abs(cur_ - prev) <= 1e-13 * max(1.0, abs(cur_)):
                break
            prev = cur_
        out = {"read": {}, "errors": [], "passes": passes}
        for ref in args.read:
            sh, c = _split(ref)
            cell = sheets.getByName(sh).getCellRangeByName(c)
            if cell.getError():
                out["read"][ref] = f"#ERR{cell.getError()}"
                continue
            # FormulaResultType2: 1 = VALUE, 2 = TEXT (com.sun.star.sheet.FormulaResult)
            is_text = (cell.getType().value == "TEXT" or
                       (cell.getType().value == "FORMULA" and cell.FormulaResultType2 == 2))
            out["read"][ref] = cell.getString() if is_text else cell.getValue()
        if args.errors:
            for i in range(sheets.getCount()):
                sh = sheets.getByIndex(i)
                cur = sh.createCursor()
                cur.gotoEndOfUsedArea(False)
                last_r, last_c = cur.getRangeAddress().EndRow, cur.getRangeAddress().EndColumn
                for r in range(last_r + 1):
                    for c in range(last_c + 1):
                        cell = sh.getCellByPosition(c, r)
                        if cell.getType().value == "FORMULA" and cell.getError():
                            out["errors"].append(f"{sh.Name}!{cell.AbsoluteName.split('.')[-1].replace('$', '')}")
        if args.out:
            doc.storeToURL(uno.systemPathToFileUrl(os.path.abspath(args.out)),
                           (_p("FilterName", "Calc MS Excel 2007 XML"),))
        doc.close(True)
        print(json.dumps(out))
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=20)
        except Exception:
            proc.kill()


if __name__ == "__main__":
    main()
