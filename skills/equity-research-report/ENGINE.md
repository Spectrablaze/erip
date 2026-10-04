# Equity report engine

Generates institutional-style equity research reports in the format of the samples in the
parent folder, from a company ticker plus a Screener.in export and a folder of images.

```
equity-report-engine/
├── assets/report.css the design system — A4 print CSS
├── reference/
│ ├── blueprint.md canonical section list (what goes on every page)
│ ├── components.md HTML snippets for each page type
│ ├── research-and-writing.md source map + analyst voice rules
│ └── sectors.md ratio profiles per sector archetype
├── scripts/
│ ├── new_company.py scaffold a company folder + asset checklist
│ ├── parse_screener.py Screener.in xlsx -> normalised JSON
│ ├── model.py ratios, DuPont, ROIIC, forensic, DCF, relative val
│ ├── charts.py 11 chart archetypes, house style, SVG output
│ ├── erip_charts.py ECharts SSR entry point (primary renderer)
│ ├── erip_components.py HTML components (dupont_tree, kpi_strip, etc.)
│ ├── erip/ ECharts 6.1.0 + zrender, own node_modules
│ │ ├── render.js SVG server-side renderer
│ │ ├── qa.js post-render SVG quality checks
│ │ ├── archetypes.js chart intent → ECharts option mapping
│ │ └── house.js palette, typography, spacing constants
│ ├── brand.py logo colour extraction, palette, CSS emitter
│ ├── docs_kb.py PDF → knowledge base (annual-report-kb bridge)
│ ├── kb.py cross-report learning loop (_knowledge/)
│ ├── sectors.py sector profile definitions + suppression
│ ├── render.py HTML -> PDF with pre-flight QA gate
│ ├── layout_qa.py document-level QA (pagination, density, overflow)
│ ├── workbook/ ERIP Excel workbook generator
│ │ ├── build_workbook.py model.json -> 11-sheet .xlsx
│ │ ├── reconcile_workbook.py BS tie, cash recon, forecast round-trip
│ │ └── references/ contract, schemas, reconciliation checklist
│ └── audit_book/ ERIP audit book generator
│ ├── build_audit_book.py model.json -> provenance audit book
│ ├── templates/audit_book.md.j2 Jinja2 template
│ └── references/ contract, provenance types
├── templates/
│ ├── demo.html working 11-page reference render
│ ├── demo.pdf rendered reference output
│ ├── report.css stale copy (do not use — assets/report.css is canonical)
│ ├── charts/ pre-built SVG fallbacks (area, gdp, mgn, etc.)
│ └── assets/ logo, product photos, people headshots
└── companies/<TICKER>/ one folder per report
```

## Setup (once)

```bash
# WSL Ubuntu (recommended — native WeasyPrint + Pango/Cairo):
sudo apt install python3-pip poppler-utils
pip install weasyprint openpyxl matplotlib pillow pandas jinja2

# Windows (pip packages install, but native Pango/Cairo are absent):
# WeasyPrint will not render natively. Use WSL or Chromium (layout preview only).
```

## Interpreter

**Use Python 3.12** with the packages in the README (marker-pdf, pypdfium2, openpyxl,
matplotlib, pillow, weasyprint). If several interpreters are installed, point every
script at the one that has them; a bare `python` resolving to a different environment
makes the knowledge-base build silently skip every document.

```
<path-to>/Python312/python.exe
```

Set `PY312=...Python312\python.exe` and use it for all scripts.

Bare `python` on this machine resolves to 3.11, which does **not** carry openpyxl or
matplotlib. A script failing with `openpyxl required` almost always means `$PY312`
was not used.

WeasyPrint does not import on Windows (native Pango/Cairo absent) and is not meant to:
`render.py` auto-selects WSL, where it works. Check with `render.py --engines`.

### The ECharts renderer needs one install

`scripts/erip/` is Node, and its `node_modules` is deliberately excluded from the
packaged zip (`.gitignore` declares it; 66 MB of dependency for a 0.4 MB skill).
After installing the skill anywhere new:

```bash
cd scripts/erip && npm install
```

Without it every chart silently falls back to Matplotlib, which is a visible drop in
quality rather than an error.

## Running a report

```bash
cd equity-report-engine

# 1. scaffold, then read the printed checklist
$PY312 scripts/new_company.py EICHERMOT --name "Eicher Motors Ltd"

# 2. drop files into companies/EICHERMOT/inputs and /assets, then:
$PY312 scripts/parse_screener.py companies/EICHERMOT/inputs/screener.xlsx \
 -o companies/EICHERMOT/data/financials.json

# 3. edit companies/EICHERMOT/assumptions.json, then:
$PY312 scripts/model.py companies/EICHERMOT/data/financials.json \
 companies/EICHERMOT/assumptions.json -o companies/EICHERMOT/data/model.json

# 4. charts — primary renderer is ECharts SSR via Node:
$PY312 scripts/erip_charts.py companies/EICHERMOT/data/charts.json
# Matplotlib charts.py is the explicit non-silent fallback if Node is unavailable.

# 5. write companies/EICHERMOT/report.html, then:
$PY312 scripts/render.py companies/EICHERMOT/report.html \
 -o "Eicher Motors Ltd - Equity Research Report.pdf"

# 5b. Excel workbook (reads model.json + assumptions.json, does NOT recalculate):
$PY312 scripts/workbook/build_workbook.py \
 --model companies/EICHERMOT/data/model.json \
 --assumptions companies/EICHERMOT/assumptions.json \
 --outdir companies/EICHERMOT/data/

# 5c. Reconcile workbook against model.json:
$PY312 scripts/workbook/reconcile_workbook.py \
 --model companies/EICHERMOT/data/model.json \
 --workbook companies/EICHERMOT/data/Eicher_Motors_Ltd_ERIP_Model.xlsx \
 --assumptions companies/EICHERMOT/assumptions.json

# 5d. Audit book (provenance, data lineage, assumption register):
$PY312 scripts/audit_book/build_audit_book.py \
 --model companies/EICHERMOT/data/model.json \
 --assumptions companies/EICHERMOT/assumptions.json \
 --outdir companies/EICHERMOT/data/
```

Step 5's pre-flight blocks on missing images, placeholder text and unlinked CSS.
`--check-only` runs the gate without rendering; `--force` overrides it.
`--engines` shows available render backends; `--engine <name>` forces a specific one.

## The demo

`templates/demo.html` renders to 11 pages covering every page archetype: cover,
macro split, KPI strip, wide financial table, product photo grid, director cards,
SWOT + Porter, DCF with sensitivity heatmap, forensic flags, relative valuation, and
the verdict page. Copy it as a starting point.

```bash
cd templates && cp ../assets/report.css . && $PY312 ../scripts/render.py demo.html
```

## Charts — ECharts SSR (primary)

Charts render through Apache ECharts 6.1.0 server-side SVG via Node (`scripts/erip/`,
own `node_modules`). `charts.py`/Matplotlib is an explicit **non-silent** fallback.

**Specs declare analytical intent**, not a chart type: growth / trend / comparison /
composition / bridge / variance / relationship / sensitivity / distribution /
decomposition / performance. An intent may resolve to an **HTML component** instead of
a chart: mixed-dimension `comparison` → `kpi_strip`, 2-D `sensitivity` → `heat_table`,
`decomposition` → `dupont_tree` (in `scripts/erip_components.py`, CSS merged into
`assets/report.css`).

Every chart records `renderer_used`; any fallback raises a QA error.

`scripts/erip/qa.js` runs over the rendered SVG (both renderers): serialised
callbacks, clipping, collisions, duplicate/non-monotonic ticks, unit consistency,
nulls, waterfall reconciliation, label policy.

ECharts SSR evaluates `formatter` callbacks but NOT function-valued style props —
it writes `font-weight:(p) => ...` into the SVG as literal text. Put per-item styling
on the data item. `qa.js` checks for this.

## House palette

Fixed house colours; the company colour is an accent only, taken from
`brand.json`'s `accent` (not `brand`) and rejected if perceptually close to the house
blues. An accent needs a declared reason: latest / subject / conclusion / focal.

Forecast rule: mixed series → historical solid, forecast 42% opacity, dashed
boundary; wholly-forecast exhibit → full strength plus a FORECAST badge; never fade a
whole chart. Label policy: ≤5 label all, 6–8 selective, >8 endpoints + extrema.

## Keeping copies in sync

If you install this skill in more than one place (user-level, project-level, a hosted
account copy), they do not auto-sync. Edit one source of truth, validate it, copy it to
the others, and re-package for any hosted copy with `skill-creator/scripts/package_skill.py`.

## Render engines

`render.py` auto-selects: `weasyprint` → `wsl` → `chromium`. Check with `--engines`.

- **WSL Ubuntu 26.04 = the working full-fidelity path.** WeasyPrint 69.0 + openpyxl +
 matplotlib + poppler-utils + Carlito font.
- WeasyPrint does **not** work natively on Windows (no GTK3 runtime).
- Chromium silently drops CSS Paged Media running headers and named `@page` rules —
 layout preview only.

WSL admin: `wsl -d Ubuntu -u root -- <cmd>` gives root without password for apt.
`ensurepip` is absent, so pip comes from `apt install python3-pip`.

## Companion skills (six)

- `annual-report-kb` (Phase 2 — PDF→KB)
- `financial-model-assumptions` (Phase 3 — assumptions.json)
- `financial-model` (Phase 3 — three-statement model into `data/three_statement/`)
- `modeling-strategy` (Phase 3b — analyst approval gate)
- `peer-comps` (Phases 1/3/5)
- `research-note-update` (post-publication)

## Companion skills (eight)

- `annual-report-kb` (Phase 2 — PDF→KB)
- `financial-model-assumptions` (Phase 3 — assumptions.json)
- `financial-model` (Phase 3 — three-statement model into `data/three_statement/`)
- `modeling-strategy` (Phase 3b — analyst approval gate)
- `peer-comps` (Phases 1/3/5)
- `research-note-update` (post-publication)
- `model-workbook` (integrated — `scripts/workbook/`)
- `model-audit` (integrated — `scripts/audit_book/`)

## Integrated outputs

The full pipeline produces **three deliverables** from the same authoritative
`model.json`:

| Deliverable | Produced by | Output |
|---|---|---|
| Research report (PDF) | `render.py` | `<Company>_Equity_Research_Report.pdf` |
| Excel workbook | `scripts/workbook/build_workbook.py` | `<Company>_ERIP_Model.xlsx` (11 sheets) |
| Audit book | `scripts/audit_book/build_audit_book.py` | `<Company>_ERIP_Audit_Book.md` |

### Workbook (11 sheets)

1. **Model info** — company, periods, build metadata, integrity checks, citations
2. **Drivers** — forecast assumption drivers with percentage formatting
3. **Income Statement** — revenue through EPS
4. **Balance Sheet** — assets, equity, debt with derived totals
5. **Cash Flow** — CFO, CFI, CFF, net change, open/close cash
6. **Schedules** — net block roll-forward, NWC days
7. **Checks** — integrity check status
8. **Summary** — key metrics overview
9. **Scenarios** — scenario comparison (if assumptions.json has scenarios)
10. **Valuation** — WACC build, DCF bridge, scenario values
11. **Sensitivity** — equity value sensitivity grid

Forecast input cells are highlighted yellow in Drivers, blue-bold elsewhere.
The workbook is a **representation** of model.json — model.json remains the source
of truth. Neither the workbook nor the audit book recalculate financial model logic.

Reconcile before publishing with `reconcile_workbook.py`: balance sheet tie, cash
reconciliation, forecast round-trip, Screener reconciliation.

### Audit book

Produces a structured Markdown document documenting:
- **Source register** — every material input with provenance type (REPORTED / DERIVED /
 ASSUMPTION / MARKET / MODEL_DERIVED), confidence level, page reference
- **Assumption register** — every significant assumption with provenance, rationale,
 range, and approval status (PENDING / APPROVED / CHALLENGED)
- **Data lineage** — dependency graph from sources → assumptions → model outputs
- **Material valuation inputs** — WACC build-up, DCF bridge, terminal value
- **Model checks** — status of all integrity checks
- **Screener vs annual report reconciliation** — line-by-line comparison
- **Approval signatures** — analyst, reviewer, sign-off authority

Requires `jinja2`. Optionally rendered to PDF/DOCX via pandoc.

## Why HTML → PDF

HTML/CSS is the only format where you can say "fill this 22×26 mm box, crop to
centre, round the corners" and have it hold across 50 pages. `python-docx` cannot
crop; PowerPoint does not reflow. The trade-off: edit the HTML and re-render (~4 s).

## Cover page data contract

The sidebar is fixed. Every report carries these blocks in this order:

1. **Recommendation** — `Recommendation`, `CMP`, `Target Price`, `Upside %`
 (academic reports print `XXX`; only print a real target if the
 DCF and relative valuation agree on a range, and say which one you anchored on)
2. **Stock data (as on <date>)** — Nifty, 52-week H/L, market cap, O/S shares,
 dividend yield, NSE code, BSE code, sector
3. **Relative stock performance – 1Y** — chart
4. **Absolute returns** — 1Y / 3Y / 5Y (and CAGR block if you have it)
5. **Shareholding (%) as on <quarter>** — promoters / FII / DII / government / public,
 plus number of shareholders and pledge %
6. **Financial summary** — FY(n), FY(n+1)E, FY(n+2)E: net revenue, YoY growth,
 EBITDA, EBITDA margin, PAT, YoY growth, ROE, EPS, EV/EBITDA
7. **Prepared by** — name, email, phone

Left column: title, tagline, *About the Company* (3–4 paragraphs), *Investment
Thesis* (1 paragraph), *Key Highlights* (6–8 bullets, each one number-led).

## Header / disclaimer

Every page carries the academic disclaimer top-left and the company name top-right,
via `string-set`. Put these two hidden divs once at the top of `<body>`:

```html
<div class="doc-disclaimer">Academic Research Project – Not a Recommendation</div>
<div class="doc-running">Eicher Motors Ltd</div>
```
