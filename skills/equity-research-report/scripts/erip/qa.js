/**
 * qa.js — renderer QA.
 *
 * Runs over the produced SVG, not over the chart config, so it validates what a
 * reader will actually see. Works on ECharts and Matplotlib output alike, since
 * the Matplotlib fallback needs checking too.
 *
 * Checks: axis validity, duplicate ticks, label collisions, clipping,
 * unit consistency, missing data, waterfall reconciliation, label policy.
 */
"use strict";

/** Extract every rendered text run with an absolute bounding box.
 *  ECharts nests text in <g transform="translate(x,y)"> and uses discrete
 *  attributes; Matplotlib packs style into style="" and does not nest. Handle both. */
function parseTexts(svg) {
  const out = [];
  const stack = [{ x: 0, y: 0 }];
  const TOKEN = /<g\b([^>]*)>|<\/g\s*>|<text\b([^>]*)>([\s\S]*?)<\/text>/g;
  const TRANSLATE = /translate\(\s*(-?[\d.]+)\s*[, ]\s*(-?[\d.]+)\s*\)/;

  let m;
  while ((m = TOKEN.exec(svg)) !== null) {
    const tag = m[0];

    if (tag.charAt(1) === "/") {                      // </g>
      if (stack.length > 1) stack.pop();
      continue;
    }
    if (tag.charAt(1) === "g") {                      // <g ...>
      const top = stack[stack.length - 1];
      const t = TRANSLATE.exec(tag);
      stack.push(t ? { x: top.x + parseFloat(t[1]), y: top.y + parseFloat(t[2]) }
                   : { x: top.x, y: top.y });
      continue;
    }

    // <text ...>content</text>
    const attrs = m[2] || "";
    const raw = m[3] || "";
    const txt = raw.replace(/<[^>]*>/g, "").replace(/&#160;/g, " ")
                   .replace(/&amp;/g, "&").trim();
    if (!txt) continue;

    const g = stack[stack.length - 1];
    const num = (re) => { const r = re.exec(attrs); return r ? parseFloat(r[1]) : null; };
    const str = (re) => { const r = re.exec(attrs); return r ? r[1] : null; };

    // ECharts also puts translate() on the <text> element itself, not only on
    // ancestor <g> tags. Ignoring it stacks every label at the same coordinates
    // and manufactures collisions.
    const self = TRANSLATE.exec(attrs);
    const sx = self ? parseFloat(self[1]) : 0;
    const sy = self ? parseFloat(self[2]) : 0;

    const x = (num(/\sx="(-?[\d.]+)"/) || 0) + g.x + sx;
    const y = (num(/\sy="(-?[\d.]+)"/) || 0) + g.y + sy;
    const size = num(/font-size="([\d.]+)"/) || num(/font-size:\s*([\d.]+)/) || 10;
    const anchor = str(/text-anchor="(\w+)"/) || str(/text-anchor:\s*(\w+)/) || "start";

    // 0.46 em/char calibrated against ECharts' own layout for Carlito mixed case
    // (13 chars at 9.5px measured 53px). No font engine is available in Node.
    const w = txt.length * size * 0.46;
    const x0 = anchor === "middle" ? x - w / 2 : anchor === "end" ? x - w : x;
    out.push({ text: txt, x, y, x0, x1: x0 + w, w, h: size, anchor });
  }
  return out;
}

const NUMERIC = /^\(?-?[\d,]+\.?\d*\)?[%x]?$/;

function check(svgName, svg, meta, spec) {
  const warn = [];
  const T = parseTexts(svg);
  const add = (c, d) => warn.push({ check: c, detail: d });

  // 0 ── serialised callbacks. ECharts SSR evaluates `formatter` but writes any
  // function-valued STYLE property straight into the SVG as source text, which
  // is invalid CSS and silently drops the intended styling.
  if (/(?:font-weight|fill|stroke|font-size)\s*[:=]\s*"?\(?\w*\)?\s*=>/.test(svg))
    add("serialised_callback", "a function-valued style property was written into the SVG as source; "
                             + "move per-item styling onto the data item");

  // 1 ── clipping / overflow
  const vb = /viewBox="(-?[\d.]+)\s+(-?[\d.]+)\s+([\d.]+)\s+([\d.]+)"/.exec(svg);
  if (vb) {
    const W = parseFloat(vb[3]), Hh = parseFloat(vb[4]);
    // Text width is estimated from character count; there is no font engine in
    // Node. The error runs a few percent, so allow a proportional tolerance or
    // every right-aligned label reads as clipped. Genuine overflow is far larger.
    const tol = (t) => Math.max(3, t.w * 0.08);
    const bad = T.filter((t) => t.x0 < -tol(t) || t.x1 > W + tol(t) || t.y > Hh + 3 || t.y < -3);
    if (bad.length) {
      const worst = bad.reduce((a, b) => (b.x1 - W > a.x1 - W ? b : a));
      add("clipping", `${bad.length} label(s) outside the ${W}x${Hh} canvas, worst "${worst.text}" `
                    + `by ${Math.max(worst.x1 - W, -worst.x0).toFixed(0)}px`);
    }
  }

  // 2 ── label collisions
  let hits = 0, worst = null;
  for (let i = 0; i < T.length; i++) {
    for (let j = i + 1; j < T.length; j++) {
      const a = T[i], b = T[j];
      const dy = Math.abs(a.y - b.y);
      if (dy >= Math.max(a.h, b.h) * 0.9) continue;
      const ov = Math.min(a.x1, b.x1) - Math.max(a.x0, b.x0);
      if (ov > 1.0) { hits++; if (!worst) worst = `"${a.text}" / "${b.text}"`; }
    }
  }
  if (hits) add("label_collision", `${hits} overlapping pair(s), e.g. ${worst}`);

  // 3 ── duplicate ticks on an axis row/column
  const nums = T.filter((t) => NUMERIC.test(t.text));
  const rows = {};
  for (const t of nums) {
    const k = Math.round(t.y / 3);
    (rows[k] = rows[k] || []).push(t.text);
  }
  for (const arr of Object.values(rows)) {
    if (arr.length >= 3 && new Set(arr).size === 1) {
      add("duplicate_ticks", `tick "${arr[0]}" repeated ${arr.length} times`);
      break;
    }
  }

  // 4 ── axis validity: a vertical tick column must be monotonic in value
  // Bucket tightly on the right edge: real axis ticks are flush to a single x,
  // whereas bar endpoint labels sit at varying x and would otherwise be read as
  // a bogus "column" and reported non-monotonic.
  const colX = {};
  for (const t of nums) {
    if (/[%x]/.test(t.text)) continue;
    const k = Math.round(t.x1 / 2);
    (colX[k] = colX[k] || []).push({ y: t.y, v: parseFloat(t.text.replace(/[(),]/g, "")) });
  }
  for (const pts of Object.values(colX)) {
    if (pts.length < 3) continue;
    const seq = pts.slice().sort((a, b) => b.y - a.y).map((p) => p.v);   // bottom -> top
    if (seq.some(Number.isNaN)) continue;
    const inc = seq.every((v, i) => i === 0 || v >= seq[i - 1]);
    const dec = seq.every((v, i) => i === 0 || v <= seq[i - 1]);
    if (!inc && !dec) { add("axis_monotonic", `non-monotonic tick column: ${seq.join(", ")}`); break; }
  }

  // 5 ── unit consistency
  const units = new Set((meta.series || []).map((s) => s.unit).filter((u) => u !== undefined && u !== ""));
  if (units.size > 2) add("unit_consistency", `${units.size} units on one chart: ${[...units].join(", ")}`);

  // 6 ── missing / null handling
  for (const s of meta.series || []) {
    const vals = s.values || [];
    const nulls = vals.filter((v) => v === null || v === undefined || Number.isNaN(v)).length;
    if (vals.length && nulls === vals.length) add("missing_data", `series "${s.name}" is entirely null`);
    else if (vals.length >= 4 && nulls / vals.length > 0.5)
      add("missing_data", `series "${s.name}" is ${nulls}/${vals.length} null`);
  }

  // 7 ── waterfall closing total
  if (meta.bridge) {
    const { deltas, start, total } = meta.bridge;
    const expect = deltas.reduce((a, b) => a + b, start);
    if (Math.abs(expect - total) > 0.51)
      add("bridge_reconciliation", `closing total ${total} != component sum ${expect}`);
    if (spec && spec.expect_total !== undefined && Math.abs(total - spec.expect_total) > 1.01)
      add("bridge_reconciliation", `closing total ${total} != authoritative ${spec.expect_total}`);
  }

  // 8 ── label policy honoured
  if (meta.policy === "all" && meta.labelled !== undefined && meta.n && meta.labelled < meta.n)
    add("label_policy", `policy "all" but only ${meta.labelled}/${meta.n} labelled`);

  return warn;
}

module.exports = { parseTexts, check };
