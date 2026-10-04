# HTML component library

Copy these blocks. Do not invent new class names — `report.css` is the only
stylesheet and the pre-flight gate does not catch unstyled markup.

## Document skeleton

```html
<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8">
<title>Eicher Motors Ltd — Equity Research Report</title>
<link rel="stylesheet" href="../../assets/report.css">
</head><body>

<div class="doc-disclaimer">Academic Research Project – Not a Recommendation</div>
<div class="doc-running">Eicher Motors Ltd</div>

<!-- one <section class="page"> per blueprint row -->

</body></html>
```

Paths are relative to the HTML file. With the standard scaffold
(`companies/<TICKER>/report.html`) that means `../../assets/report.css`,
`charts/revenue.svg`, `assets/logo.png`.

---

## Cover page

```html
<section class="page cover">
  <div class="cover-head">
    <div>
      <div class="kicker">Equity Research Report</div>
      <h1>Eicher Motors Ltd</h1>
      <p class="tagline">Fuelled by legacy, charged by growth</p>
    </div>
    <img class="cover-logo" src="assets/logo.png" alt="">
  </div>

  <div class="cover-grid">
    <div>
      <h3>About the company</h3>
      <p>…3–4 paragraphs…</p>

      <div class="thesis">
        <h3>Investment thesis</h3>
        <p>…one dense paragraph, ending in the valuation conclusion…</p>
      </div>

      <h3>Key highlights</h3>
      <ul class="bullet-sq tight">
        <li>Highest-ever annual volume of 13.78 lakh units in FY26, <b>+22.3% YoY</b>.</li>
      </ul>
    </div>

    <aside class="sidebar">
      <div class="sb-box">
        <div class="sb-title">Recommendation</div>
        <div class="sb-body">
          <div class="kv"><span class="k">Rating</span><span class="v">XXX</span></div>
          <div class="kv"><span class="k">CMP</span><span class="v">INR 7,312</span></div>
          <div class="kv hi"><span class="k">Target price</span><span class="v">INR 8,450</span></div>
          <div class="kv"><span class="k">Upside</span><span class="v pos">+15.6%</span></div>
        </div>
      </div>

      <div class="sb-box">
        <div class="sb-title">Stock data as on 12 Jun 2026</div>
        <div class="sb-body">
          <div class="kv"><span class="k">Nifty 50</span><span class="v">23,622.9</span></div>
          <div class="kv"><span class="k">52W H/L (INR)</span><span class="v">8,230 / 5,220</span></div>
          <div class="kv"><span class="k">Mkt cap (INR Cr)</span><span class="v">2,00,579</span></div>
          <div class="kv"><span class="k">O/S shares (Cr)</span><span class="v">27.43</span></div>
          <div class="kv"><span class="k">Dividend yield</span><span class="v">0.96%</span></div>
          <div class="kv"><span class="k">NSE / BSE</span><span class="v">EICHERMOT / 505200</span></div>
        </div>
      </div>

      <figure>
        <div class="fig-title">Relative performance – 1Y</div>
        <img src="charts/cover_relative.svg" alt="">
      </figure>

      <div class="sb-box">
        <div class="sb-title">Shareholding (%) — Mar 2026</div>
        <div class="sb-body">
          <div class="kv"><span class="k">Promoters</span><span class="v">49.06</span></div>
          <div class="kv"><span class="k">FII</span><span class="v">26.77</span></div>
          <div class="kv"><span class="k">DII</span><span class="v">14.73</span></div>
          <div class="kv"><span class="k">Public</span><span class="v">9.35</span></div>
          <div class="kv"><span class="k">Pledged</span><span class="v">Nil</span></div>
        </div>
      </div>

      <div class="sb-box">
        <div class="sb-title">Financial summary</div>
        <div class="sb-body">
          <table class="xs no-zebra">
            <thead><tr><th>INR Cr</th><th>FY26</th><th>FY27E</th><th>FY28E</th></tr></thead>
            <tbody>
              <tr><td>Net revenue</td><td>23,408</td><td>26,919</td><td>30,149</td></tr>
              <tr><td>YoY growth</td><td>24.0%</td><td>15.0%</td><td>12.0%</td></tr>
              <tr><td>EBITDA</td><td>5,785</td><td>6,595</td><td>7,386</td></tr>
              <tr><td>EBITDA margin</td><td>24.7%</td><td>25.0%</td><td>25.0%</td></tr>
              <tr><td>PAT</td><td>5,515</td><td>6,236</td><td>6,850</td></tr>
              <tr class="total"><td>EPS (INR)</td><td>202</td><td>228</td><td>251</td></tr>
            </tbody>
          </table>
        </div>
      </div>

      <p class="byline"><b>Prepared by: Vivek Rathod</b><br>vivekrathod107@gmail.com</p>
    </aside>
  </div>
</section>
```

---

## Chart conventions — two rules that are easy to get wrong

**1. Titles live in the HTML, not in the chart.** Never pass `title=` to a chart
function. Use `<div class="fig-title">` above the `<img>`. Passing both prints the
title twice at two different sizes.

**2. Size the chart to the column it lands in.** Matplotlib figure width is in
inches and the SVG is then stretched to 100% of its container, so a wide chart in a
narrow column renders with unreadably small text.

| Where it goes | `w`, `h` |
|---|---|
| Cover sidebar (62 mm) | `w=2.4, h=1.7` |
| One half of `.split` / `.split-even` | `w=3.5, h=2.4` |
| One third of `.cols-3` | `w=2.6, h=2.0` |
| Full page width | `w=7.0, h=2.8` |

## Standard analysis page — text left, chart right

```html
<section class="page">
  <h2>Revenue analysis</h2>
  <div class="split">
    <div>
      <p>…</p>
      <h3>What drove FY26</h3>
      <ul class="bullet-sq"><li>…</li></ul>
    </div>
    <div>
      <figure>
        <div class="fig-title">Revenue vs growth (%)</div>
        <img src="charts/revenue_growth.svg" alt="">
        <figcaption>Source: Company filings, Screener.in</figcaption>
      </figure>
      <div class="note"><b>Read-through:</b> …one sentence the chart proves…</div>
    </div>
  </div>
</section>
```

Swap `.split` for `.split-r` to put the chart on the left. Alternate between the two
across consecutive pages so the document does not look like a column of identical slabs.

## KPI strip

```html
<div class="kpis">
  <div class="kpi"><div class="lab">Revenue FY26</div><div class="val">23,408</div><div class="sub">INR Cr, +24.0%</div></div>
  <div class="kpi"><div class="lab">EBITDA margin</div><div class="val">24.7%</div><div class="sub">+40 bps YoY</div></div>
  <div class="kpi"><div class="lab">ROCE</div><div class="val">28.1%</div><div class="sub">10-yr median 24.6%</div></div>
  <div class="kpi"><div class="lab">Net cash</div><div class="val">18,240</div><div class="sub">INR Cr</div></div>
</div>
```

## Wide data table (10-yr P&L, quarterly snapshot, DCF)

```html
<table class="sm">
  <caption>Consolidated P&amp;L (INR Cr)</caption>
  <thead><tr><th>Particulars</th><th>FY17</th><th>FY18</th><th>…</th><th>FY26</th></tr></thead>
  <tbody>
    <tr><td>Revenue from operations</td><td>7,033</td><td>8,965</td><td>…</td><td>23,408</td></tr>
    <tr class="sub"><td>YoY growth</td><td>—</td><td class="pos">27.5%</td><td>…</td><td class="pos">24.0%</td></tr>
    <tr class="total"><td>Net profit</td><td>1,675</td><td>2,203</td><td>…</td><td>5,515</td></tr>
  </tbody>
</table>
<p class="source">Source: Company annual reports, Screener.in</p>
```

`class="sm"` fits ~11 columns, `class="xs"` fits ~15. Beyond that, split the table
across two pages rather than shrinking further.

## Product / brand portfolio

```html
<div class="photo-grid">
  <div class="photo">
    <img src="assets/products/hunter-350.png" alt="">
    <div class="cap"><b>Hunter 350</b>INR 1.50–1.82 lakh</div>
  </div>
  …
</div>
```

## Director / management profile

```html
<div class="people">
  <div class="person">
    <img src="assets/people/lal.jpg" alt="">
    <div>
      <div class="nm">Siddhartha Lal</div>
      <div class="role">Executive Chairman · on board since 2006</div>
      <p>…60–90 words: background, tenure, what they actually own or decide…</p>
    </div>
  </div>
</div>
```

## Screenshot / exhibit

```html
<div class="exhibit">
  <img src="assets/exhibits/group-structure.png" alt="">
  <div class="cap">Group structure as disclosed in the FY26 annual report, p. 142</div>
</div>
```

## SWOT

```html
<div class="swot">
  <div class="s"><h4>Strengths</h4><ul class="tight"><li>…</li></ul></div>
  <div class="w"><h4>Weaknesses</h4><ul class="tight"><li>…</li></ul></div>
  <div class="o"><h4>Opportunities</h4><ul class="tight"><li>…</li></ul></div>
  <div class="t"><h4>Threats</h4><ul class="tight"><li>…</li></ul></div>
</div>
```

## Porter's five forces

```html
<table class="matrix">
  <thead><tr><th>Force</th><th style="text-align:center">Intensity</th><th style="text-align:left">Interpretation</th></tr></thead>
  <tbody>
    <tr><td>Competitive rivalry</td><td style="text-align:center"><span class="pill high">High</span></td>
        <td style="text-align:left">…</td></tr>
  </tbody>
</table>
```

## Timeline

```html
<div class="timeline">
  <div class="tl-item"><span class="yr">1981–83</span> — Government establishes Maruti Udyog; JV with Suzuki signed.</div>
</div>
```

## DuPont tree

```html
<div class="tree">
  <div class="node"><div class="lab">Net profit margin</div><div class="val">23.6%</div></div>
  <div class="node"><div class="lab">Asset turnover</div><div class="val">0.79x</div></div>
  <div class="node"><div class="lab">Equity multiplier</div><div class="val">1.19x</div></div>
</div>
```

## Forensic flag table

```html
<table>
  <thead><tr><th>Test</th><th>Value</th><th>Verdict</th><th style="text-align:left">Why it matters</th></tr></thead>
  <tbody>
    <tr><td>CFO / PAT (10-yr mean)</td><td>113.4%</td><td class="pos">PASS</td>
        <td style="text-align:left">Earnings convert to cash…</td></tr>
  </tbody>
</table>
```
