/**
 * house.js — the ERIP visual system.
 *
 * One palette for every report in the series. The covered company's colour is a
 * controlled accent, never the base. Historical and forecast periods, and
 * positive and negative values, get one treatment everywhere.
 */
"use strict";
const fs = require("fs");
const path = require("path");

// ───────────────────────────────────────────────────────── palette
const HOUSE = {
  ink: "#16202c",
  inkSoft: "#5b6875",
  inkFaint: "#8a97a4",
  navy: "#0b3d62",     // primary series / historical actuals
  blue: "#1173a8",     // secondary series
  blueLt: "#7fb2d1",   // tertiary
  pos: "#1a7f4b",
  neg: "#b3261e",
  rule: "#dbe3ea",
  panel: "#f4f7fa",
  accent: "#c8801f",   // replaced by the company colour via loadBrand()
};

const S = Object.assign({}, HOUSE);

/** brand.json is the single source of truth, shared with report.css and charts.py.
 *  Only the accent slot is taken from it; the house identity is fixed. */
function loadBrand(brandPath) {
  if (!brandPath || !fs.existsSync(brandPath)) return { applied: false, accent: S.accent };
  const b = JSON.parse(fs.readFileSync(brandPath, "utf8"));
  // Prefer brand.json's accent over its primary. A company primary is often a
  // blue, which collides with the house navy/blue and stops reading as an
  // accent at all. If the chosen colour is too close to the house series
  // colours, keep the house accent instead.
  const company = b.accent || b.brand;
  if (company && !tooClose(company, [S.navy, S.blue, S.blueLt])) S.accent = company;
  return { applied: true, accent: S.accent, source: brandPath,
           rejected: company && tooClose(company, [S.navy, S.blue, S.blueLt]) ? company : null };
}

/** Crude perceptual distance, enough to stop an accent disappearing into the
 *  house blues. Returns true when `hex` is within `d` of any of `others`. */
function tooClose(hex, others, d = 70) {
  const rgb = (h) => {
    const x = h.replace("#", "");
    return [0, 2, 4].map((i) => parseInt(x.substr(i, 2), 16));
  };
  const a = rgb(hex);
  return others.some((o) => {
    const b = rgb(o);
    return Math.hypot(a[0] - b[0], a[1] - b[1], a[2] - b[2]) < d;
  });
}

const FONT = "Carlito, Calibri, 'DejaVu Sans', sans-serif";

// The two widths report.css offers: the body box and one half of a .split.
// Canvases are snapped to these so the page never scales a chart down.
const BODY_IN = 180 / 25.4;
const COL_IN = 87 / 25.4;

// 7pt is the floor for anything a reader has to read. At scale 1 that is
// 7 / 0.75 = 9.34px, so 10px is the smallest size any archetype may author.
// Nothing shrinks below this to make a label fit; the label is dropped or the
// chart is given more room instead.
const MIN_PX = 10;
const px = (v) => Math.max(MIN_PX, v);

const TYPE = {
  axis: { fontSize: px(10), color: S.inkSoft, fontFamily: FONT },
  value: { fontSize: px(10), fontFamily: FONT },
  seriesTag: { fontSize: px(10), fontWeight: 700, fontFamily: FONT },
};

// ───────────────────────────────────────────────────────── semantics
/** Forecast periods are drawn hollow so a reader never mistakes an estimate for
 *  an actual. Detected from the label unless the spec says otherwise. */
const isForecast = (label) => /(^|[^A-Za-z])(E|F|P|EST|FCST)$/i.test(String(label).trim());

/** Index of the first forecast period, or -1. Spec wins over label detection. */
function forecastStart(labels, explicit) {
  if (explicit !== undefined && explicit !== null) return explicit;
  const i = (labels || []).findIndex((l) => isForecast(l));
  return i;
}

/**
 * GLOBAL FORECAST RULE, three cases:
 *   mixed        historical solid, forecast at reduced opacity, dashed boundary
 *   all forecast full visual strength plus a FORECAST badge; fading an entire
 *                exhibit only makes it hard to read and says nothing
 *   all history  ordinary house treatment
 */
function forecastMode(fcFrom, n) {
  if (fcFrom === undefined || fcFrom === null || fcFrom < 0 || n === 0) return "historical";
  if (fcFrom === 0) return "forecast";
  if (fcFrom >= n) return "historical";
  return "mixed";
}

/** Only a mixed series fades; a wholly forecast exhibit stays at full strength. */
function periodStyle(base, isFc, mode) {
  return (mode === "mixed" && isFc) ? { color: base, opacity: 0.42 } : { color: base, opacity: 1 };
}

/** Dashed rule at the actual/forecast boundary. Mixed series only. */
function forecastBoundary(fcFrom, nCats, mode) {
  if (mode !== "mixed") return undefined;
  return {
    silent: true, symbol: "none", animation: false,
    data: [{ xAxis: fcFrom - 0.5,
             label: { formatter: "forecast", position: "insideEndTop", rotate: 0,
                      fontSize: px(8.4), color: S.inkFaint, fontFamily: FONT } }],
    lineStyle: { color: S.inkFaint, type: [4, 3], width: 0.9 },
  };
}

/** Corner badge for an exhibit that is entirely estimates. */
function forecastBadge(mode, text) {
  if (mode !== "forecast") return [];
  return [{
    type: "group", right: 0, top: 0,
    children: [
      { type: "rect", shape: { x: 0, y: 0, width: (text || "FORECAST").length * 5.2 + 8, height: 12, r: 2 },
        style: { fill: S.panel, stroke: S.rule, lineWidth: 0.8 } },
      { type: "text", style: { x: 4, y: 3, text: text || "FORECAST", fill: S.inkSoft,
                               fontSize: px(7.6), fontWeight: 700, fontFamily: FONT } },
    ],
  }];
}

const signColour = (v) => (v >= 0 ? S.pos : S.neg);

/**
 * ACCENT POLICY. The accent carries meaning; it is not decoration and it is not
 * automatically "the last value". Permitted reasons:
 *   latest      the most recent observation in a time series
 *   subject     the company being researched, among peers
 *   conclusion  the valuation answer
 *   focal       an explicitly nominated datapoint
 * Anything else stays inside the house palette. Charts with no analytical focus
 * (a share donut, for instance) get no accent at all.
 */
const ACCENT_REASONS = new Set(["latest", "subject", "conclusion", "focal"]);
function accentIndex(spec, n) {
  const reason = spec && spec.accent;
  if (!reason) return -1;
  if (typeof reason === "number") return reason;            // explicit index = focal
  if (!ACCENT_REASONS.has(reason)) return -1;
  if (reason === "latest") return n - 1;
  return spec.accentIndex !== undefined ? spec.accentIndex : -1;
}

// ───────────────────────────────────────────────────────── numbers
/** Indian grouping, because the report is denominated in INR crore throughout. */
function fmtNum(v, unit) {
  if (v === null || v === undefined || Number.isNaN(v)) return "";
  const a = Math.abs(v);
  if (unit === "%") return `${round(v, a < 10 ? 1 : 1)}%`;
  if (unit === "x") return `${round(v, 2)}x`;
  if (unit === "days") return `${Math.round(v)}`;
  if (a >= 1000) return Math.round(v).toLocaleString("en-IN");
  if (a >= 100) return String(Math.round(v));
  return String(round(v, 1));
}
const round = (v, d) => {
  const s = Number(v).toFixed(d);
  return s.includes(".") ? s.replace(/\.?0+$/, "") : s;   // never eat integer zeros
};
const paren = (v, unit) => `(${fmtNum(Math.abs(v), unit)})`;

// ───────────────────────────────────────────────────────── label policy
/**
 * Density rule, per the approved policy. Escalation is never automatic: if a
 * policy cannot be drawn cleanly the caller downgrades one level and the QA
 * layer records a warning. Type size is never reduced to make labels fit.
 */
const POLICY_ORDER = ["all", "selective", "endpoints", "none"];

function defaultPolicy(n) {
  if (n <= 5) return "all";
  if (n <= 8) return "selective";
  return "endpoints";
}

/** Indices to label under a policy. `material` lets a spec force extra points. */
function labelIndices(values, policy, material) {
  const n = values.length;
  const nums = values.map((v) => (typeof v === "number" ? v : null));
  const finite = nums.map((v, i) => [v, i]).filter(([v]) => v !== null);
  if (!finite.length) return new Set();
  const maxI = finite.reduce((a, b) => (b[0] > a[0] ? b : a))[1];
  const minI = finite.reduce((a, b) => (b[0] < a[0] ? b : a))[1];
  const first = finite[0][1], last = finite[finite.length - 1][1];

  let idx;
  if (Array.isArray(policy)) idx = policy.slice();
  else if (policy === "all") idx = nums.map((_, i) => i);
  else if (policy === "none") idx = [];
  else if (policy === "selective") idx = [first, last, maxI, minI];
  else idx = [first, last, maxI];                       // endpoints
  for (const m of material || []) idx.push(m);
  return new Set(idx.filter((i) => i >= 0 && i < n && nums[i] !== null));
}

// ───────────────────────────────────────────────────────── axes
const baseGrid = (x) => Object.assign({ left: 4, right: 12, top: 26, bottom: 4, containLabel: true }, x);

function catAxis(data, opts = {}) {
  return Object.assign({
    type: "category", data,
    axisLine: { lineStyle: { color: S.rule } },
    axisTick: { show: false },
    axisLabel: Object.assign({ margin: 8, interval: 0, hideOverlap: false }, TYPE.axis),
  }, opts);
}

function valAxis(opts = {}) {
  return Object.assign({
    type: "value",
    splitNumber: 4,
    axisLine: { show: false },
    axisTick: { show: false },
    splitLine: { lineStyle: { color: S.rule, width: 0.8, type: [4, 4] } },
    axisLabel: Object.assign({ margin: 6 }, TYPE.axis),
  }, opts);
}

/**
 * Series identification. Corner headings read as a title when there are more
 * than two series, so they are only used for one or two. Beyond that the caller
 * must take a compact inline legend instead.
 */
const MAX_TAGGED_SERIES = 2;

function seriesTags(pairs, rightInset = 0) {
  if (pairs.length > MAX_TAGGED_SERIES) return [];
  return pairs.map((p, i) => ({
    type: "text",
    [i === 0 ? "left" : "right"]: i === 0 ? 0 : rightInset, top: 2,
    style: Object.assign({ text: p.text, fill: p.colour }, TYPE.seriesTag),
  }));
}

/** Compact top legend for 3+ series, in place of corner headings. */
function inlineLegend(names, colours) {
  return {
    top: 0, left: "center", itemWidth: 8, itemHeight: 8, itemGap: 10,
    icon: "roundRect", padding: 0,
    textStyle: { fontSize: px(8.8), color: S.inkSoft, fontFamily: FONT },
    data: names.map((n, i) => ({ name: n, itemStyle: { color: colours[i % colours.length] } })),
  };
}

module.exports = {
  S, HOUSE, FONT, TYPE, loadBrand, MAX_TAGGED_SERIES,
  BODY_IN, COL_IN, MIN_PX, px,
  isForecast, forecastStart, forecastMode, forecastBoundary, forecastBadge,
  periodStyle, signColour,
  accentIndex, ACCENT_REASONS, inlineLegend,
  fmtNum, round, paren,
  defaultPolicy, labelIndices, POLICY_ORDER,
  baseGrid, catAxis, valAxis, seriesTags,
};
