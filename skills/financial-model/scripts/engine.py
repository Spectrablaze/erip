#!/usr/bin/env python3
"""
engine.py - a very small spreadsheet engine.

Every projected line in this skill is written ONCE, as a formula string in
`rows.py`. This module compiles that string twice:

    "prev(net_block) + capex - dep_charge"
        -> Python:  grid["net_block"][j-1] + grid["capex"][j] - grid["dep_charge"][j]
        -> Excel:   =F31+G18-G19

so the numbers in `model.json` and the formulas in `model.xlsx` are guaranteed
to be the same model. There is no second implementation to drift.

Formula language (a restricted Python expression, parsed with `ast`):

    revenue                 this row, this column
    prev(revenue)           this row, previous column  (0 before the first column)
    12.5  0.08              numeric literals
    + - * / ^ ( )           arithmetic; division is guarded both sides
    < <= > >= == !=         comparison (only useful inside IF)
    MIN MAX ABS SUM AVG     -> the same Excel functions (AVG -> AVERAGE)
    IF(cond, a, b)          -> Excel IF

Circular references (interest on average debt, revolver funded by a cash flow
that contains interest) are legal. `solve()` iterates the whole grid to a fixed
point; the workbook is written with iterative calculation switched on so Excel
resolves it the same way.
"""
from __future__ import annotations

import ast

BINOPS = {ast.Add: "+", ast.Sub: "-", ast.Mult: "*", ast.Div: "/", ast.Pow: "^"}
CMPOPS = {ast.Lt: "<", ast.LtE: "<=", ast.Gt: ">", ast.GtE: ">=",
          ast.Eq: "=", ast.NotEq: "<>"}
FUNCS = {"MIN": "MIN", "MAX": "MAX", "ABS": "ABS", "SUM": "SUM",
         "AVG": "AVERAGE", "IF": "IF", "ROUND": "ROUND"}


def col_letter(i: int) -> str:
    """0-based column index -> Excel column letter."""
    s = ""
    i += 1
    while i:
        i, r = divmod(i - 1, 26)
        s = chr(65 + r) + s
    return s


class FormulaError(ValueError):
    pass


# ---------------------------------------------------------------- compilation
class Formula:
    """A parsed model formula, compiled on demand to a value or to Excel."""

    def __init__(self, expr: str):
        self.expr = expr
        try:
            self.tree = ast.parse(expr, mode="eval").body
        except SyntaxError as e:
            raise FormulaError(f"cannot parse formula {expr!r}: {e}") from e
        self.refs = _collect_refs(self.tree)

    def __repr__(self) -> str:
        return f"Formula({self.expr!r})"

    def value(self, resolve) -> float:
        """`resolve(key, lag) -> float` gives the value of another row."""
        return _walk(self.tree, _PyEmit(resolve))

    def excel(self, ref) -> str:
        """`ref(key, lag) -> 'G31' or '0'` gives an A1 reference."""
        return _walk(self.tree, _XlEmit(ref))


def _collect_refs(node) -> set:
    """Every (row_key, lag) this formula reads."""
    out = set()

    def rec(n):
        if isinstance(n, ast.Name):
            out.add((n.id, 0))
        elif isinstance(n, ast.Call):
            fn = getattr(n.func, "id", None)
            if fn == "prev":
                if len(n.args) != 1 or not isinstance(n.args[0], ast.Name):
                    raise FormulaError("prev() takes exactly one row name")
                out.add((n.args[0].id, 1))
                return
            for a in n.args:
                rec(a)
        else:
            for child in ast.iter_child_nodes(n):
                rec(child)

    rec(node)
    return out


def _walk(node, emit):
    if isinstance(node, ast.Constant):
        if not isinstance(node.value, (int, float)) or isinstance(node.value, bool):
            raise FormulaError(f"only numeric literals are allowed, got {node.value!r}")
        return emit.num(node.value)

    if isinstance(node, ast.Name):
        return emit.ref(node.id, 0)

    if isinstance(node, ast.UnaryOp):
        if isinstance(node.op, ast.USub):
            return emit.neg(_walk(node.operand, emit))
        if isinstance(node.op, ast.UAdd):
            return _walk(node.operand, emit)
        raise FormulaError(f"unsupported unary operator in {ast.dump(node)}")

    if isinstance(node, ast.BinOp):
        op = BINOPS.get(type(node.op))
        if op is None:
            raise FormulaError("only + - * / ^ are supported")
        return emit.binop(op, _walk(node.left, emit), _walk(node.right, emit))

    if isinstance(node, ast.Compare):
        if len(node.ops) != 1:
            raise FormulaError("chained comparisons are not supported")
        op = CMPOPS.get(type(node.ops[0]))
        if op is None:
            raise FormulaError("unsupported comparison")
        return emit.compare(op, _walk(node.left, emit), _walk(node.comparators[0], emit))

    if isinstance(node, ast.Call):
        fn = getattr(node.func, "id", None)
        if fn == "prev":
            return emit.ref(node.args[0].id, 1)
        if fn not in FUNCS:
            raise FormulaError(f"unknown function {fn!r}; allowed: prev, "
                               + ", ".join(sorted(FUNCS)))
        return emit.call(fn, [_walk(a, emit) for a in node.args])

    raise FormulaError(f"unsupported expression node {type(node).__name__}")


# ------------------------------------------------------------------- emitters
class _PyEmit:
    """Evaluates to a float. Missing values and division by zero read as 0.0."""

    def __init__(self, resolve):
        self._resolve = resolve

    @staticmethod
    def _f(v):
        return 0.0 if v is None else float(v)

    def num(self, v):
        return float(v)

    def ref(self, key, lag):
        return self._f(self._resolve(key, lag))

    def neg(self, a):
        return -self._f(a)

    def binop(self, op, a, b):
        a, b = self._f(a), self._f(b)
        if op == "+":
            return a + b
        if op == "-":
            return a - b
        if op == "*":
            return a * b
        if op == "/":
            return 0.0 if b == 0 else a / b
        if op == "^":
            try:
                return float(a) ** float(b)
            except (ValueError, OverflowError, ZeroDivisionError):
                return 0.0
        raise FormulaError(op)

    def compare(self, op, a, b):
        a, b = self._f(a), self._f(b)
        return {"<": a < b, "<=": a <= b, ">": a > b, ">=": a >= b,
                "=": a == b, "<>": a != b}[op]

    def call(self, fn, args):
        if fn == "IF":
            cond, yes, no = args
            return self._f(yes) if cond else self._f(no)
        vals = [self._f(a) for a in args]
        if fn == "MIN":
            return min(vals)
        if fn == "MAX":
            return max(vals)
        if fn == "ABS":
            return abs(vals[0])
        if fn == "SUM":
            return sum(vals)
        if fn == "AVG":
            return sum(vals) / len(vals) if vals else 0.0
        if fn == "ROUND":
            return round(vals[0], int(vals[1]) if len(vals) > 1 else 0)
        raise FormulaError(fn)


class _XlEmit:
    """Emits an Excel formula body (no leading '=')."""

    def __init__(self, ref):
        self._ref = ref

    def num(self, v):
        return repr(float(v)) if isinstance(v, float) else str(v)

    def ref(self, key, lag):
        return self._ref(key, lag)

    def neg(self, a):
        return f"-({a})"

    def binop(self, op, a, b):
        # Guard division so Excel matches the Python evaluator instead of #DIV/0!.
        if op == "/":
            return f"IFERROR(({a})/({b}),0)"
        return f"({a}{op}{b})"

    def compare(self, op, a, b):
        return f"({a}{op}{b})"

    def call(self, fn, args):
        return f"{FUNCS[fn]}({','.join(args)})"


# ------------------------------------------------------------------ the solve
def solve(rows, ncols, fixed, formulas, max_iter=200, tol=1e-7):
    """Evaluate the whole grid to a fixed point.

    rows      ordered list of row keys
    ncols     number of columns
    fixed     {(key, j): value}      hardcoded cells (actuals, driver inputs)
    formulas  {(key, j): Formula}    everything else

    Returns (grid, iterations, max_residual). Cells that are neither fixed nor
    formula-driven stay 0.0.
    """
    grid = {k: [0.0] * ncols for k in rows}
    for (k, j), v in fixed.items():
        grid[k][j] = 0.0 if v is None else float(v)

    order = [(k, j) for j in range(ncols) for k in rows if (k, j) in formulas]
    resid = 0.0
    for it in range(1, max_iter + 1):
        resid = 0.0
        for key, j in order:
            def resolve(k, lag, _j=j):
                col = _j - lag
                if col < 0 or k not in grid:
                    return 0.0
                return grid[k][col]

            new = formulas[(key, j)].value(resolve)
            if new != new or new in (float("inf"), float("-inf")):  # NaN / inf
                new = 0.0
            resid = max(resid, abs(new - grid[key][j]))
            grid[key][j] = new
        if resid < tol:
            return grid, it, resid
    return grid, max_iter, resid
