/**
 * archetypes.js — the controlled ERIP visual vocabulary.
 *
 * Nine archetypes. A spec does not pick one directly; it declares analytical
 * intent and intent.js resolves the archetype. Every builder returns an ECharts
 * option object plus the metadata the QA layer needs.
 */
"use strict";
const H = require("./house");
const { S } = H;

/** Shared return envelope so qa.js can inspect what was drawn. */
const out = (option, meta) => ({ option, meta });

// ═══════════════════════════════════════════════ 1. bar + line (trend/growth)
function bar_line_combo(d) {
  const bars = d.bar_vals, cats = d.categories;
  const line = (d.line_vals || []).map((v) => (v === null || v === undefined ? null : v));
  const n = bars.length;
  const policy = d.labelPolicy || H.defaultPolicy(n);
  const keep = H.labelIndices(bars, policy, d.materialPoints);
  const dense = keep.size < n;
  const last = n - 1;
  const unit = d.bar_unit || "";
  // A time series has a defensible focal point: the latest observation. Any
  // other accent must be named in the spec.
  const acc = H.accentIndex({ accent: d.accent === undefined ? "latest" : d.accent,
                              accentIndex: d.accentIndex }, n);
  const fcFrom = H.forecastStart(cats, d.forecastFrom);
  const fcMode = H.forecastMode(fcFrom, n);
  const isFc = (i) => fcFrom >= 0 && i >= fcFrom;
  // Few growth observations: label them directly rather than making the reader
  // read a secondary axis for three numbers.
  const lineN = line.filter((v) => v !== null).length;
  const labelLine = lineN > 0 && lineN <= 5;

  return out({
    grid: H.baseGrid({ top: 30, right: (line.length && !labelLine) ? 34 : 14, bottom: 4 }),
    xAxis: H.catAxis(cats),
    yAxis: [
      H.valAxis({
        show: dense,
        axisLabel: Object.assign({ margin: 4,
          formatter: (v) => (Math.abs(v) >= 1000 ? v / 1000 + "k" : H.fmtNum(v, unit)) }, H.TYPE.axis),
      }),
      ...(line.length ? [H.valAxis({
        position: "right", show: !labelLine, splitLine: { show: false },
        axisLabel: Object.assign({ formatter: "{value}%", margin: 4 }, H.TYPE.axis),
      })] : []),
    ],
    series: [
      {
        name: d.bar_label, type: "bar", yAxisIndex: 0, barMaxWidth: 26,
        // ECharts SSR evaluates `formatter` callbacks but NOT function-valued
        // style properties: it serialises the function source into the SVG as
        // font-weight:(p) => ... , which is invalid CSS. Per-item styling has to
        // live on the data item itself.
        data: bars.map((v, i) => ({
          value: v,
          itemStyle: Object.assign(
            H.periodStyle(i === acc ? S.accent : S.navy, isFc(i), fcMode),
            { borderRadius: [2, 2, 0, 0] }),
          label: { color: i === acc ? S.accent : S.inkSoft, fontWeight: i === acc ? 700 : 400 },
        })),
        label: {
          show: true, position: "top", distance: 3,
          formatter: (p) => (keep.has(p.dataIndex) ? H.fmtNum(p.value, unit) : ""),
          fontSize: H.px(9.5), fontFamily: H.FONT,
        },
        markLine: H.forecastBoundary(fcFrom, n, fcMode),
      },
      ...(line.length ? [{
        name: d.line_label, type: "line", yAxisIndex: 1, data: line,
        connectNulls: false, smooth: false, symbol: "circle", symbolSize: 4.5,
        lineStyle: { color: S.blue, width: 1.6 }, itemStyle: { color: S.blue }, z: 5,
        // The growth line rides a secondary axis and will sometimes fall over a
        // bar. A white halo keeps the number readable wherever it lands, rather
        // than relying on the line clearing the bars.
        label: labelLine ? {
          show: true, position: "top", distance: 5,
          formatter: (p) => (p.value === null ? "" : H.fmtNum(p.value, "%")),
          fontSize: H.px(9), fontFamily: H.FONT, fontWeight: 700, color: S.blue,
          backgroundColor: "#ffffff", padding: [1.5, 2.5], borderRadius: 2,
        } : { show: false },
      }] : []),
    ],
    graphic: [
      // a FORECAST badge occupies the top-right, so the right-hand series tag
      // steps aside rather than overprinting it
      ...H.seriesTags([
        { text: d.bar_label, colour: S.navy },
        ...(line.length ? [{ text: d.line_label, colour: S.blue }] : []),
      ], fcMode === "forecast" ? (d.forecastBadge || "FORECAST").length * 5.2 + 16 : 0),
      ...H.forecastBadge(fcMode, d.forecastBadge),
      // With too few observations for a growth line, state the change in words
      ...(d.annotation ? [{ type: "text", right: fcMode === "forecast" ? 68 : 0, top: 2,
        style: { text: d.annotation, fill: S.blue, fontSize: 10, fontWeight: 700,
                 fontFamily: H.FONT } }] : []),
    ],
  }, { archetype: "bar_line_combo", policy, labelled: keep.size, n,
       series: [{ name: d.bar_label, values: bars, unit },
                ...(line.length ? [{ name: d.line_label, values: line, unit: "%" }] : [])] });
}

// ═══════════════════════════════════════════════ 2. grouped bars (comparison)
function bar_grouped(d) {
  const names = Object.keys(d.series);
  const cols = [S.navy, S.blue, S.blueLt, S.accent];
  const n = d.categories.length;
  const policy = d.labelPolicy || H.defaultPolicy(n * names.length);
  const accCat = H.accentIndex(d, n);
  return out({
    grid: H.baseGrid({ top: 30, bottom: 4 }),
    xAxis: d.horizontal ? H.valAxis({ show: false, splitLine: { show: false } }) : H.catAxis(d.categories),
    yAxis: d.horizontal ? H.catAxis(d.categories, { inverse: true }) : H.valAxis(),
    series: names.map((k, si) => ({
      name: k, type: "bar", barMaxWidth: 22,
      // accent a nominated category (the focal comparison), not a default one
      data: d.series[k].map((v, i) => ({
        value: v,
        itemStyle: { color: (i === accCat && si === 0) ? S.accent : cols[si % cols.length],
                     borderRadius: d.horizontal ? [0, 2, 2, 0] : [2, 2, 0, 0] },
      })),
      label: {
        show: policy !== "none", position: d.horizontal ? "right" : "top", distance: 3,
        formatter: (p) => H.fmtNum(p.value, d.unit || ""),
        fontSize: H.px(9.5), fontFamily: H.FONT, color: S.inkSoft,
      },
    })),
    legend: names.length > H.MAX_TAGGED_SERIES ? H.inlineLegend(names, cols) : undefined,
    graphic: H.seriesTags(names.map((k, i) => ({ text: k, colour: cols[i] }))),
  }, { archetype: "bar_grouped", policy, n,
       series: names.map((k) => ({ name: k, values: d.series[k], unit: d.unit || "" })) });
}

// ═══════════════════════════════════════════════ 3. line_multi (trend)
function line_multi(d) {
  const names = Object.keys(d.series);
  const cols = [S.navy, S.blue, S.accent, S.blueLt];
  const unit = d.unit || (d.pct === false ? "x" : "%");
  const n = (d.x || []).length;
  const policy = d.labelPolicy || H.defaultPolicy(n);
  return out({
    grid: H.baseGrid({ top: names.length > H.MAX_TAGGED_SERIES ? 34 : 30, bottom: 4, right: 24 }),
    xAxis: H.catAxis(d.x),
    yAxis: H.valAxis({
      axisLabel: Object.assign({ margin: 6, formatter: (v) => H.fmtNum(v, unit) }, H.TYPE.axis),
    }),
    series: names.map((k, si) => {
      const vals = d.series[k];
      const keep = H.labelIndices(vals, policy, d.materialPoints);
      return {
        name: k, type: "line", data: vals, connectNulls: false,
        smooth: false, symbol: "circle", symbolSize: 3.6,
        lineStyle: { color: cols[si % cols.length], width: 1.6 },
        itemStyle: { color: cols[si % cols.length] },
        // label only the final point of each line: the level the reader needs
        label: {
          show: true, position: "top", distance: 4,
          formatter: (p) => (p.dataIndex === vals.length - 1 ? H.fmtNum(p.value, unit) : ""),
          fontSize: H.px(9.5), fontFamily: H.FONT, fontWeight: 700,
          color: cols[si % cols.length],
        },
        ...(d.reference !== undefined && si === 0 ? {
          markLine: {
            silent: true, symbol: "none",
            data: [{ yAxis: d.reference, label: {
              formatter: d.referenceLabel || H.fmtNum(d.reference, unit),
              position: "insideStartTop", distance: 2, fontSize: H.px(9),
              color: S.inkFaint, fontFamily: H.FONT } }],
            lineStyle: { color: S.inkFaint, type: [5, 4], width: 1 },
          },
        } : {}),
      };
    }),
    legend: names.length > H.MAX_TAGGED_SERIES ? H.inlineLegend(names, cols) : undefined,
    graphic: H.seriesTags(names.map((k, i) => ({ text: k, colour: cols[i] }))),
  }, { archetype: "line_multi", policy, n,
       series: names.map((k) => ({ name: k, values: d.series[k], unit })) });
}

// ═══════════════════════════════════════════════ 4. composition (3 subtypes)
/**
 * subtype:
 *   snapshot_share        one period, parts of a whole      -> donut
 *   composition_over_time share shifting across periods     -> 100% stacked bar
 *   absolute_mix_over_time levels and mix together          -> stacked bar
 */
function composition(d) {
  const sub = d.subtype || "snapshot_share";
  // house palette only: a share breakdown has no analytical focal point,
  // so nothing here earns the accent unless the spec names one.
  const cols = [S.navy, S.blue, S.blueLt, "#a9c6dc", S.inkFaint, "#c3ced8"];

  if (sub === "snapshot_share") {
    return out({
      grid: H.baseGrid(),
      // Percentage sits inside the ring; names go in a compact legend. A donut has
      // no axis to carry category names, so leader lines in a 62mm column truncate
      // to ellipses. This is the one archetype where a legend beats direct labels.
      legend: {
        orient: "vertical", right: 0, top: "middle", itemWidth: 7, itemHeight: 7,
        itemGap: 7, icon: "roundRect",
        // name only: the value belongs in the adjacent table, and a name+value
        // string overflows a 62mm column. QA flags it if this regresses.
        formatter: (nm) => (nm.length > 16 ? nm.slice(0, 15) + "…" : nm),
        textStyle: { fontSize: H.px(8.6), color: S.inkSoft, fontFamily: H.FONT },
      },
      series: [{
        type: "pie", radius: ["42%", "62%"], center: ["31%", "52%"],
        avoidLabelOverlap: true, minAngle: 6,
        itemStyle: { borderColor: "#fff", borderWidth: 1.5 },
        data: d.values.map((v, i) => ({
          value: v, name: d.labels[i], itemStyle: { color: cols[i % cols.length] },
        })),
        label: {
          position: "inside",
          formatter: (p) => (p.percent >= 6 ? p.percent.toFixed(1) + "%" : ""),
          fontSize: H.px(9), fontFamily: H.FONT, color: "#fff", fontWeight: 700,
        },
        labelLine: { show: false },
      }],
      graphic: d.center ? [{ type: "text", left: "30%", top: "50%",
        style: { text: d.center, fill: S.inkSoft, fontSize: H.px(9.5), fontWeight: 700,
                 fontFamily: H.FONT, textAlign: "center" } }] : [],
    }, { archetype: "composition/snapshot_share", n: d.values.length,
         series: [{ name: "share", values: d.values, unit: d.unit || "" }] });
  }

  const names = Object.keys(d.series);
  const pct = sub === "composition_over_time";
  const totals = d.categories.map((_, i) => names.reduce((a, k) => a + (d.series[k][i] || 0), 0));
  return out({
    grid: H.baseGrid({ top: names.length > H.MAX_TAGGED_SERIES ? 34 : 30, bottom: 4 }),
    xAxis: H.catAxis(d.categories),
    yAxis: H.valAxis({
      max: pct ? 100 : undefined,
      axisLabel: Object.assign({ margin: 6,
        formatter: (v) => (pct ? v + "%" : (Math.abs(v) >= 1000 ? v / 1000 + "k" : v)) }, H.TYPE.axis),
    }),
    series: names.map((k, si) => ({
      name: k, type: "bar", stack: "c", barMaxWidth: 44,
      data: d.series[k].map((v, i) => (pct ? (totals[i] ? v / totals[i] * 100 : 0) : v)),
      itemStyle: { color: cols[si % cols.length] },
      label: {
        show: true, position: "inside",
        formatter: (p) => (p.value >= (pct ? 8 : Math.max(...totals) * 0.06)
          ? (pct ? p.value.toFixed(0) + "%" : H.fmtNum(p.value, d.unit || "")) : ""),
        fontSize: H.px(8.5), fontFamily: H.FONT, color: "#fff", fontWeight: 600,
      },
    })),
    legend: names.length > H.MAX_TAGGED_SERIES ? H.inlineLegend(names, cols) : undefined,
    graphic: H.seriesTags(names.map((k, i) => ({ text: k, colour: cols[i] }))),
  }, { archetype: "composition/" + sub, n: d.categories.length,
       series: names.map((k) => ({ name: k, values: d.series[k], unit: d.unit || "" })) });
}

// ═══════════════════════════════════════════════ 5. waterfall (bridge)
function waterfall(d) {
  const labels = d.labels.slice(), deltas = d.deltas.slice();
  const unit = d.unit || "";
  const support = [], rises = [], falls = [];
  let run = Number(d.start || 0);
  for (const v of deltas) {
    if (v >= 0) { support.push(run); rises.push(v); falls.push("-"); run += v; }
    else { run += v; support.push(run); rises.push("-"); falls.push(-v); }
  }
  const total = run;
  labels.push(d.totalLabel || "Total");
  support.push(0); rises.push("-"); falls.push("-");
  const totals = labels.map((_, i) => (i === labels.length - 1 ? total : "-"));

  const lbl = (col, weight, neg) => ({
    show: true, position: neg ? "bottom" : "top", distance: 3,
    formatter: (p) => (typeof p.value === "number"
      ? (neg ? H.paren(p.value, unit) : H.fmtNum(p.value, unit)) : ""),
    fontSize: H.px(9.5), fontFamily: H.FONT, color: col, fontWeight: weight,
  });

  return out({
    grid: H.baseGrid({ top: 28, bottom: 4, right: 8 }),
    xAxis: H.catAxis(labels, {
      axisLabel: Object.assign({ margin: 8, interval: 0, width: 62,
        overflow: "break", lineHeight: 11 }, H.TYPE.axis),
    }),
    yAxis: H.valAxis({ show: false }),
    series: [
      { name: "support", type: "bar", stack: "w", data: support, barMaxWidth: 34,
        itemStyle: { color: "transparent" }, silent: true, emphasis: { disabled: true } },
      { name: "increase", type: "bar", stack: "w", data: rises, barMaxWidth: 34,
        itemStyle: { color: S.navy }, label: lbl(S.inkSoft, 400, false) },
      { name: "decrease", type: "bar", stack: "w", data: falls, barMaxWidth: 34,
        itemStyle: { color: S.neg }, label: lbl(S.neg, 400, true) },
      { name: "total", type: "bar", stack: "w", data: totals, barMaxWidth: 34,
        itemStyle: { color: S.accent }, label: lbl(S.accent, 700, false) },
    ],
    graphic: [{ type: "text", left: 0, top: 2,
      style: { text: d.unitLabel || "INR Cr", fill: S.inkSoft, fontSize: H.px(9.5), fontFamily: H.FONT } }],
  }, { archetype: "waterfall", n: labels.length, bridge: { deltas, start: Number(d.start || 0), total },
       series: [{ name: "bridge", values: deltas, unit }] });
}

// ═══════════════════════════════════════════════ 6. football field (distribution)
function football_field(d) {
  const ms = d.methods;
  const labels = ms.map((m) => m.label);
  const lo = ms.map((m) => m.low);
  const span = ms.map((m) => m.high - m.low);
  const mids = ms.map((m, i) => (m.mid !== undefined && m.mid !== null ? [m.mid, i] : null)).filter(Boolean);
  const unit = d.unit || "";
  // Intrinsic and market-implied ranges answer different questions, so they are
  // drawn differently. `kind` is taken from the spec, else inferred from the label.
  const kindOf = (m) => m.kind || (/dcf|intrinsic/i.test(m.label) ? "dcf"
                                 : /52|market|price/i.test(m.label) ? "market" : "multiple");
  const barColour = (m) => ({ dcf: S.navy, multiple: S.blue, market: "#a9c6dc" }[kindOf(m)]);

  const marks = [];
  if (d.current_price !== undefined && d.current_price !== null) {
    marks.push({ xAxis: d.current_price,
      lineStyle: { color: S.ink, width: 2.0 },                 // the market, drawn boldly
      label: { formatter: `CMP ${H.fmtNum(d.current_price, unit)}`, position: "insideStartTop",
               distance: 4, fontSize: H.px(9.5), fontWeight: 700, color: S.ink,
               fontFamily: H.FONT } });
  }
  if (d.target !== undefined && d.target !== null) {
    marks.push({ xAxis: d.target,
      lineStyle: { color: S.accent, width: 1.8, type: [5, 3] },
      label: { formatter: `TP ${H.fmtNum(d.target, unit)}`, position: "insideEndBottom",
               distance: 4, fontSize: H.px(9.5), fontWeight: 700, color: S.accent,
               fontFamily: H.FONT } });
  }

  return out({
    // wide label gutter: method names are the point of this exhibit
    grid: H.baseGrid({ top: 26, left: 4, right: 34, bottom: 6 }),
    xAxis: H.valAxis({
      scale: true,
      axisLabel: Object.assign({ margin: 6, formatter: (v) => H.fmtNum(v, unit) }, H.TYPE.axis),
    }),
    yAxis: H.catAxis(labels, { inverse: true, axisLine: { show: false },
      axisLabel: Object.assign({ margin: 8, width: 132, overflow: "break", lineHeight: 11,
                                 fontSize: H.px(9.4), color: S.ink }, H.TYPE.axis) }),
    series: [
      { type: "bar", stack: "f", data: lo, itemStyle: { color: "transparent" }, silent: true },
      { type: "bar", stack: "f", barMaxWidth: 17,
        data: span.map((v, i) => ({ value: v,
          itemStyle: { color: barColour(ms[i]), borderRadius: 2 } })),
        label: { show: true, position: "insideLeft", distance: 4,
          formatter: (p) => H.fmtNum(ms[p.dataIndex].low, unit),
          fontSize: H.px(9), color: "#fff", fontWeight: 600, fontFamily: H.FONT },
        markLine: marks.length ? { silent: true, symbol: "none", data: marks } : undefined },
      { type: "scatter", data: mids, symbolSize: 8, symbol: "diamond",
        itemStyle: { color: S.ink, borderColor: "#fff", borderWidth: 1.2 }, z: 6 },
      { type: "bar", stack: "f2", data: ms.map((m) => m.high), itemStyle: { color: "transparent" },
        silent: true, barMaxWidth: 17,
        label: { show: true, position: "right", distance: 4,
          formatter: (p) => H.fmtNum(ms[p.dataIndex].high, unit),
          fontSize: H.px(9), color: S.inkSoft, fontFamily: H.FONT } },
    ],
  }, { archetype: "football_field", n: ms.length,
       series: [{ name: "range", values: ms.flatMap((m) => [m.low, m.high]), unit }] });
}

// ═══════════════════════════════════════════════ 7. tornado (sensitivity)
function tornado(d) {
  const items = d.drivers.map((x) => ({
    label: x.label, lo: Math.min(x.low, x.high), hi: Math.max(x.low, x.high),
  })).map((x) => Object.assign(x, { swing: x.hi - x.lo }))
    .sort((a, b) => a.swing - b.swing);
  const base = Number(d.base_value);
  const unit = d.unit || "";
  return out({
    grid: H.baseGrid({ top: 24, left: 4, right: 22, bottom: 4 }),
    xAxis: H.valAxis({ axisLabel: Object.assign({ margin: 6,
      formatter: (v) => H.fmtNum(v, unit) }, H.TYPE.axis) }),
    yAxis: H.catAxis(items.map((i) => i.label), { axisLine: { show: false },
      axisLabel: Object.assign({ margin: 8, width: 104, overflow: "break", lineHeight: 11 }, H.TYPE.axis) }),
    series: [
      { type: "bar", stack: "t", data: items.map((i) => i.lo),
        itemStyle: { color: "transparent" }, silent: true },
      // Split at the base so downside and upside carry the house negative and
      // positive treatment, the same convention the waterfall uses.
      { type: "bar", stack: "t", data: items.map((i) => Math.max(0, Math.min(base, i.hi) - i.lo)),
        barMaxWidth: 15, itemStyle: { color: S.neg },
        label: { show: true, position: "insideLeft", distance: 4,
          formatter: (p) => H.fmtNum(items[p.dataIndex].lo, unit),
          fontSize: H.px(8.5), color: "#fff", fontFamily: H.FONT } },
      { type: "bar", stack: "t", data: items.map((i) => Math.max(0, i.hi - Math.max(base, i.lo))),
        barMaxWidth: 15,
        itemStyle: { color: S.pos, borderRadius: [0, 2, 2, 0] },
        markLine: { silent: true, symbol: "none",
          data: [{ xAxis: base, lineStyle: { color: S.ink, width: 1.3 },
            label: { formatter: `Base ${H.fmtNum(base, unit)}`, position: "start", distance: 6,
                     rotate: 0, fontSize: H.px(9), fontWeight: 700, color: S.ink,
                     fontFamily: H.FONT, align: "center", verticalAlign: "bottom" } }] } },
      { type: "bar", stack: "t2", data: items.map((i) => i.hi), itemStyle: { color: "transparent" },
        silent: true, barMaxWidth: 15,
        label: { show: true, position: "right", distance: 3,
          formatter: (p) => H.fmtNum(items[p.dataIndex].hi, unit),
          fontSize: H.px(8.5), color: S.inkSoft, fontFamily: H.FONT } },
    ],
  }, { archetype: "tornado", n: items.length,
       series: [{ name: "swing", values: items.map((i) => i.swing), unit }] });
}

// ═══════════════════════════════════════════════ 8. scatter_peers (relationship)
function scatter_peers(d) {
  // accept both documented shapes
  const pts = Array.isArray(d.points)
    ? d.points.map((p) => ({ label: p.label || p.name, x: p.x, y: p.y }))
    : Object.entries(d.points).map(([k, v]) => ({ label: k, x: v[0], y: v[1] }));
  const hl = d.highlight;
  return out({
    grid: H.baseGrid({ top: 24, left: 10, right: 52, bottom: 6 }),
    xAxis: H.valAxis({ name: d.xlab, nameLocation: "end", nameGap: 4,
      nameTextStyle: Object.assign({}, H.TYPE.axis),
      axisLabel: Object.assign({ margin: 6 }, H.TYPE.axis) }),
    yAxis: H.valAxis({ name: d.ylab, nameLocation: "end", nameGap: 6,
      nameTextStyle: Object.assign({}, H.TYPE.axis) }),
    series: [{
      type: "scatter",
      // per-item label style, for the SSR reason noted in bar_line_combo
      data: pts.map((p) => ({
        value: [p.x, p.y], name: p.label,
        itemStyle: { color: p.label === hl ? S.accent : S.blue,
                     borderColor: "#fff", borderWidth: 1 },
        symbolSize: p.label === hl ? 13 : 8,
        label: { color: p.label === hl ? S.accent : S.inkSoft,
                 fontWeight: p.label === hl ? 700 : 400 },
      })),
      // keep point labels inside the canvas near the right edge
      labelLayout: { hideOverlap: true, moveOverlap: "shiftY" },
      label: { show: true, position: "right", distance: 4,
        formatter: (p) => p.data.name, fontSize: H.px(9), fontFamily: H.FONT },
    }],
  }, { archetype: "scatter_peers", n: pts.length,
       series: [{ name: "x", values: pts.map((p) => p.x), unit: "" },
                { name: "y", values: pts.map((p) => p.y), unit: "" }] });
}

// ═══════════════════════════════════════════════ 9. indexed_performance (deferred)
/** Interface preserved per the approved decision. Requires a market-data layer:
 *  company vs benchmark/sector/peers, rebased to 100. Not wired to a source. */
function indexed_performance(d) {
  const names = Object.keys(d.series || {});
  if (!names.length) {
    const e = new Error("indexed_performance requires a market-price series; no market-data layer is wired");
    e.deferred = true;
    throw e;
  }
  const cols = [S.accent, S.navy, S.blue, S.blueLt];
  return out({
    grid: H.baseGrid({ top: 26, bottom: 4, right: 30 }),
    xAxis: H.catAxis(d.dates, { axisLabel: Object.assign({ margin: 8, interval: "auto" }, H.TYPE.axis) }),
    yAxis: H.valAxis({ axisLabel: Object.assign({ margin: 6 }, H.TYPE.axis) }),
    series: names.map((k, i) => ({
      name: k, type: "line", data: d.series[k], symbol: "none", smooth: false,
      lineStyle: { color: cols[i % cols.length], width: i === 0 ? 1.8 : 1.2 },
      endLabel: { show: true, formatter: (p) => `${k} ${Math.round(p.value)}`,
        fontSize: H.px(9), color: cols[i % cols.length], fontFamily: H.FONT, fontWeight: 700 },
      markLine: i === 0 ? { silent: true, symbol: "none",
        data: [{ yAxis: 100, lineStyle: { color: S.rule, type: [4, 4] } }] } : undefined,
    })),
  }, { archetype: "indexed_performance", n: (d.dates || []).length,
       series: names.map((k) => ({ name: k, values: d.series[k], unit: "" })) });
}

module.exports = {
  bar_line_combo, bar_grouped, line_multi, composition,
  waterfall, football_field, tornado, scatter_peers, indexed_performance,
};
