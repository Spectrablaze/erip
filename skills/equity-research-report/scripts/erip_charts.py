"""erip_charts.py — dual-render orchestrator.

ECharts (Node) is the primary renderer. Matplotlib is the fallback, per chart,
and the fallback is never silent: every chart records renderer_used and any
fallback raises a QA warning that the report's pre-flight can surface.

    python erip_charts.py <spec.json> [--outdir DIR] [--brand brand.json]
                          [--qa qa.json] [--force-fallback]

The spec contract is unchanged, so india-macro-pack's macro_charts.json and the
existing data/charts.json both work untouched.
"""
from __future__ import annotations

import argparse, json, os, shutil, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
NODE_ENTRY = os.path.join(HERE, "erip", "render.js")
SKILL_SCRIPTS = HERE          # charts.py, the fallback renderer, sits beside this file

# archetypes that are deliberately not charts in ERIP
HTML_COMPONENTS = {"sensitivity_heat": "heat_table"}


def node_available():
    exe = shutil.which("node")
    if not exe or not os.path.exists(NODE_ENTRY):
        return None
    try:
        v = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=20)
        return exe if v.returncode == 0 else None
    except Exception:
        return None


def run_echarts(exe, spec_path, outdir, brand, qa_path):
    # Absolute paths throughout: the node process runs with cwd=HERE so that it
    # resolves its own node_modules, which would otherwise break every path the
    # caller passed relative to their own working directory.
    cmd = [exe, NODE_ENTRY, os.path.abspath(spec_path),
           "--outdir", os.path.abspath(outdir), "--qa", os.path.abspath(qa_path)]
    if brand:
        cmd += ["--brand", os.path.abspath(brand)]
    return subprocess.run(cmd, capture_output=True, text=True, cwd=HERE, timeout=300)


def matplotlib_fallback(spec, names, outdir, brand):
    """Render only `names` with the existing Matplotlib factory."""
    sys.path.insert(0, SKILL_SCRIPTS)
    import charts as mpl                      # noqa: E402
    if brand and os.path.exists(brand):
        mpl.set_brand(brand)
    mpl.set_outdir(outdir)
    done, failed = [], []
    for c in spec["charts"]:
        nm = c.get("name") or c.get("args", {}).get("name")
        if nm not in names:
            continue
        fn = c.get("fn")
        if not fn or not hasattr(mpl, fn):
            failed.append({"name": nm, "error": f"no matplotlib archetype '{fn}'"})
            continue
        try:
            getattr(mpl, fn)(**c["args"])
            done.append(nm)
        except Exception as e:                # noqa: BLE001
            failed.append({"name": nm, "error": f"{type(e).__name__}: {e}"})
    return done, failed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("--outdir")
    ap.add_argument("--brand")
    ap.add_argument("--qa")
    ap.add_argument("--force-fallback", action="store_true",
                    help="simulate an unavailable Node runtime, to exercise the fallback path")
    a = ap.parse_args()

    spec = json.load(open(a.spec, encoding="utf-8"))
    outdir = a.outdir or spec.get("outdir") or "charts"
    brand = a.brand or spec.get("brand") or os.path.join(
        os.path.dirname(outdir.rstrip("/\\")), "brand.json")
    brand = brand if os.path.exists(brand) else None
    qa_path = a.qa or os.path.join(outdir, "_qa_charts.json")
    os.makedirs(outdir, exist_ok=True)

    wanted = [c.get("name") or c.get("args", {}).get("name") for c in spec["charts"]]
    html_moves = {(c.get("name") or c.get("args", {}).get("name")): HTML_COMPONENTS[c["fn"]]
                  for c in spec["charts"] if c.get("fn") in HTML_COMPONENTS}

    report = {"generated": time.strftime("%Y-%m-%dT%H:%M:%S"),
              "spec": os.path.abspath(a.spec), "outdir": os.path.abspath(outdir),
              "brand_source": brand, "renderer_default": "echarts",
              "charts": {}, "warnings": [], "html_components": html_moves}

    exe = None if a.force_fallback else node_available()
    echarts_ok, echarts_qa = set(), {}

    if exe:
        ejson = os.path.join(outdir, "_qa_echarts.json")
        p = run_echarts(exe, a.spec, outdir, brand, ejson)
        if os.path.exists(ejson):
            echarts_qa = json.load(open(ejson, encoding="utf-8"))
            for r in echarts_qa.get("rendered", []):
                echarts_ok.add(r["name"])
                report["charts"][r["name"]] = {
                    "renderer_used": "echarts", "intent": r["intent"],
                    "archetype": r["archetype"], "bytes": r["bytes"],
                    "qa": r["warnings"]}
                for w in r["warnings"]:
                    report["warnings"].append({"chart": r["name"], "severity": "warn", **w})
            for f in echarts_qa.get("failed", []):
                if f.get("htmlComponent"):
                    report["charts"][f["name"]] = {"renderer_used": "html",
                                                   "component": f["htmlComponent"], "qa": []}
                    echarts_ok.add(f["name"])
        else:
            report["warnings"].append({"chart": "*", "severity": "error",
                                       "check": "renderer",
                                       "detail": f"ECharts produced no QA report; stderr: {p.stderr[:300]}"})
    else:
        report["warnings"].append({
            "chart": "*", "severity": "error", "check": "renderer_fallback",
            "detail": "Node/ECharts unavailable; every chart fell back to Matplotlib. "
                      "House style and label policy are NOT applied."})

    missing = [n for n in wanted if n not in echarts_ok]
    if missing:
        done, failed = matplotlib_fallback(spec, set(missing), outdir, brand)
        for nm in done:
            report["charts"][nm] = {"renderer_used": "matplotlib", "qa": []}
            report["warnings"].append({
                "chart": nm, "severity": "error", "check": "renderer_fallback",
                "detail": "rendered by the Matplotlib fallback, not ECharts; "
                          "ERIP house style and label policy were not applied"})
        for f in failed:
            report["charts"][f["name"]] = {"renderer_used": None, "qa": []}
            report["warnings"].append({"chart": f["name"], "severity": "error",
                                       "check": "render_failed", "detail": f["error"]})

    json.dump(report, open(qa_path, "w", encoding="utf-8"), indent=2)

    used = {}
    for v in report["charts"].values():
        used[v["renderer_used"]] = used.get(v["renderer_used"], 0) + 1
    errs = [w for w in report["warnings"] if w["severity"] == "error"]
    warns = [w for w in report["warnings"] if w["severity"] == "warn"]
    print(f"renderer mix: {used}")
    print(f"QA: {len(errs)} error(s), {len(warns)} warning(s)")
    for w in errs[:12]:
        print(f"  ERROR {w['chart']}: {w['check']} — {w['detail'][:110]}")
    for w in warns[:12]:
        print(f"  warn  {w['chart']}: {w['check']} — {w['detail'][:110]}")
    print(f"qa -> {qa_path}")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
