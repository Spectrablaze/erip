/**
 * render.js — ERIP chart engine: intent resolution, render, QA.
 *
 *   node erip/render.js <spec.json> [--outdir DIR] [--brand brand.json] [--qa qa.json]
 *
 * Accepts BOTH spec shapes:
 *   legacy  {"charts":[{"fn":"bar_line_combo","args":{...}}]}     <- charts.py / india-macro-pack
 *   intent  {"charts":[{"intent":"growth","name":"x","data":{}}]} <- ERIP native
 * The legacy contract is frozen so companion skills keep working unchanged.
 */
"use strict";
const fs = require("fs");
const path = require("path");
const echarts = require("echarts");
const H = require("./house");
const A = require("./archetypes");

// ─────────────────────────────────────────── intent -> archetype
/**
 * Analytical intent decides the visual. A dataset being plottable is not a
 * reason to plot it; the spec must say what it is trying to communicate.
 */
/** Thrown when an intent resolves to an HTML component rather than a chart. */
function toHtml(component, reason) {
  const e = new Error(reason);
  e.htmlComponent = component;
  return e;
}

/**
 * An intent may legitimately resolve to NO chart. A "comparison" of quantities
 * that do not share a dimension (an inflation rate against a policy rate) is a
 * set of indicators, and a shared axis would assert a comparability that does
 * not exist. Those become a KPI strip.
 */
function comparisonResolver(d) {
  const units = new Set(
    (d.units || Object.values(d.series || {}).map(() => d.unit)).filter(Boolean));
  const notComparable = d.comparable === false || units.size > 1;
  if (notComparable)
    throw toHtml("kpi_strip",
      "values do not share a dimension, so a common axis would imply a comparability that does not exist");
  return ["bar_grouped", d];
}

/**
 * A chart earns its place by showing a relationship: a movement over time, a
 * ranking across a set, a decomposition. Two or three plotted values show no
 * relationship a reader cannot read straight off the numbers, and drawing axes
 * around them dresses a fact up as an analysis. Those become a KPI strip.
 */
const MIN_POINTS = 4;
function pointCount(d) {
  if (Array.isArray(d.categories)) return d.categories.length;
  if (Array.isArray(d.x)) return d.x.length;
  if (Array.isArray(d.bar_vals)) return d.bar_vals.length;
  if (d.series && typeof d.series === "object") {
    const first = Object.values(d.series)[0];
    if (Array.isArray(first)) return first.length;
  }
  return Infinity;      // shapes without a category axis are exempt
}
function needsRelationship(d, intent) {
  const n = pointCount(d);
  if (n < MIN_POINTS)
    throw toHtml("kpi_strip",
      `${n} plotted value(s) show no relationship over time or across a set; ` +
      `a ${intent} chart of ${n} points is a KPI, not an analysis`);
}

const INTENT = {
  growth:      (d) => (needsRelationship(d, "growth"), ["bar_line_combo", d]),
  trend:       (d) => (needsRelationship(d, "trend"),
                       d.series ? ["line_multi", d] : ["bar_line_combo", d]),
  comparison:  (d) => (needsRelationship(d, "comparison"), comparisonResolver(d)),
  composition: (d) => ["composition", d],
  bridge:      (d) => ["waterfall", d],
  variance:    (d) => ["bar_grouped", d],
  relationship:(d) => ["scatter_peers", d],
  // a 2-D grid of values is a table with shading, not a chart
  sensitivity: (d) => (d.grid ? (() => { throw toHtml("heat_table",
                        "a two-dimensional value grid reads better as a shaded table"); })()
                             : ["tornado", d]),
  distribution:(d) => ["football_field", d],
  decomposition:(d) => { throw toHtml("dupont_tree",
                        "a multiplicative identity is a decomposition, not a trend"); },
  performance: (d) => ["indexed_performance", d],
};

const LEGACY_TO_INTENT = {
  bar_line_combo: "growth", line_multi: "trend", bar_grouped: "comparison",
  stacked_bar: "composition", donut: "composition", area_stack: "composition",
  waterfall: "bridge", football_field: "distribution", tornado: "sensitivity",
  scatter_peers: "relationship", indexed_performance: "performance",
};

/** Legacy args -> archetype args, including the composition merge. */
function adaptLegacy(fn, args) {
  const a = Object.assign({}, args);
  if (fn === "donut") return ["composition", Object.assign(a, { subtype: "snapshot_share" })];
  if (fn === "stacked_bar")
    return ["composition", Object.assign(a, { subtype: a.pct ? "composition_over_time" : "absolute_mix_over_time" })];
  if (fn === "area_stack")
    return ["composition", Object.assign(a, { subtype: "absolute_mix_over_time", categories: a.x })];
  if (fn === "sensitivity_heat") {
    const e = new Error("sensitivity_heat is an HTML component in ERIP, not a chart");
    e.htmlComponent = "heat_table";
    throw e;
  }
  return [fn, a];
}

// ─────────────────────────────────────────── QA
const QA = require("./qa.js");
const qaChart = (name, svg, meta, spec) => QA.check(name, svg, meta, spec);

// ─────────────────────────────────────────── render
function renderOne(entry, outdir, defaults) {
  const name = entry.name || (entry.args && entry.args.name);
  let archetype, data, intent;

  if (entry.intent) {
    intent = entry.intent;
    const resolver = INTENT[intent];
    if (!resolver) throw new Error(`unknown analytical intent "${intent}"`);
    [archetype, data] = resolver(entry.data || {});
  } else {
    const fn = entry.fn;
    intent = LEGACY_TO_INTENT[fn] || fn;
    [archetype, data] = adaptLegacy(fn, entry.args || {});
    // The legacy path names a chart type directly, so it skips the intent
    // resolvers. The relationship test still applies: it is a rule about what
    // the data can support, not about which entry point declared it.
    if (["bar_line_combo", "line_multi", "bar_grouped"].includes(archetype))
      needsRelationship(data, intent);
  }

  const builder = A[archetype];
  if (!builder) throw new Error(`no ERIP archetype "${archetype}"`);
  const { option, meta } = builder(data);

  const inch = 96;
  // Type is authored in px on the canvas, but the page scales the SVG to its
  // container. Any scale below 1 shrinks the labels, and a 7.2in chart dropped
  // into an 87mm column printed at 3.3pt. Snap the canvas to the two widths the
  // stylesheet actually offers so the scale is ~1 and authored px ≈ printed px.
  // `place` is the spec's declaration of where the report puts this chart:
  // "body" for the full text width, "column" (default) for half a split. The
  // canvas is built at that width so the page never rescales it — scaling down
  // shrinks the labels below the 7pt floor, and scaling up bloats the height.
  // Legacy specs carry no `place`, so a wide `w` still implies the body.
  const askedW = entry.w || data.w || defaults.w;
  const place = entry.place || data.place ||
                (askedW >= H.COL_IN * 1.35 ? "body" : "column");
  if (place !== "body" && place !== "column")
    throw new Error(`chart "${name}": place must be "body" or "column", got "${place}"`);
  const width = Math.round((place === "body" ? H.BODY_IN : H.COL_IN) * inch);
  const height = Math.round((entry.h || data.h || defaults.h) * inch);

  const chart = echarts.init(null, null, { renderer: "svg", ssr: true, width, height });
  chart.setOption(Object.assign({ animation: false, backgroundColor: "transparent",
    textStyle: { fontFamily: H.FONT } }, option));
  let svg = chart.renderToSVGString();
  chart.dispose();
  svg = svg.replace(/<svg /, '<svg preserveAspectRatio="xMidYMid meet" ');

  fs.mkdirSync(outdir, { recursive: true });
  fs.writeFileSync(path.join(outdir, `${name}.svg`), svg, "utf8");

  return { name, intent, archetype: meta.archetype, width, height,
           bytes: svg.length, warnings: qaChart(name, svg, meta, entry) };
}

// ─────────────────────────────────────────── cli
function main() {
  const argv = process.argv.slice(2);
  const specPath = argv[0];
  const arg = (k, d) => { const i = argv.indexOf(k); return i >= 0 ? argv[i + 1] : d; };
  if (!specPath) { console.error("usage: node render.js <spec.json> [--outdir D] [--brand b.json] [--qa q.json]"); process.exit(2); }

  const spec = JSON.parse(fs.readFileSync(specPath, "utf8"));
  const outdir = arg("--outdir", spec.outdir || "charts");
  const brandPath = arg("--brand", spec.brand ||
    path.join(path.dirname(outdir.replace(/[\\/]$/, "")), "brand.json"));
  const brand = H.loadBrand(brandPath);

  const defaults = { w: 3.6, h: 2.4 };
  const results = [], failures = [];
  for (const entry of spec.charts) {
    const nm = entry.name || (entry.args && entry.args.name) || "?";
    try {
      results.push(renderOne(entry, outdir, defaults));
    } catch (e) {
      failures.push({ name: nm, error: e.message,
                      deferred: !!e.deferred, htmlComponent: e.htmlComponent || null });
    }
  }

  const report = {
    engine: "echarts", engine_version: require("echarts/package.json").version,
    generated: new Date().toISOString(),
    brand_source: brand.applied ? brand.source : null, accent: brand.accent,
    outdir, rendered: results, failed: failures,
  };
  const qaPath = arg("--qa", path.join(outdir, "_qa_echarts.json"));
  fs.mkdirSync(path.dirname(qaPath), { recursive: true });
  fs.writeFileSync(qaPath, JSON.stringify(report, null, 2), "utf8");

  const nWarn = results.reduce((a, r) => a + r.warnings.length, 0);
  for (const r of results) {
    const w = r.warnings.length ? `  ${r.warnings.length} QA` : "";
    console.log(`  ok   ${r.name.padEnd(22)} ${r.intent.padEnd(13)} ${r.archetype}${w}`);
    for (const x of r.warnings) console.log(`         ! ${x.check}: ${x.detail}`);
  }
  for (const f of failures)
    console.log(`  ${f.deferred ? "defer" : "FAIL "} ${f.name.padEnd(22)} ${f.error}`);
  console.log(`\n${results.length} rendered, ${failures.length} not rendered, ${nWarn} QA warning(s)`);
  console.log(`qa -> ${qaPath}`);
  process.exit(failures.filter((f) => !f.deferred && !f.htmlComponent).length ? 1 : 0);
}

if (require.main === module) main();
module.exports = { renderOne, qaChart, parseTexts: QA.parseTexts, INTENT, LEGACY_TO_INTENT };
