---
name: equity-research-report
description: Generate an institutional-style equity research report on a listed Indian company - macro, industry, management, forensic screens, DuPont, ROIIC, DCF and relative valuation - rendered to a print-ready A4 PDF. Use when the user asks for an equity research report, a stock or company deep-dive, an initiating-coverage note, a valuation report, or names a ticker and asks for "the report".
---

# Equity research report

Produce an equity research report on a listed Indian company, in the format
of a sell-side initiating-coverage note: cover with a data sidebar, macro and industry
context, company and management analysis, ten years of financial analysis, forensic
screens, DuPont, ROIIC, a full FCFF DCF and relative valuation, rendered to A4 PDF.

## Orient

Everything you need is in this skill directory:

```
assets/report.css                     the design system — A4 print CSS
reference/blueprint.md                canonical section list, one row per page
reference/sectors.md                  which ratios mean anything, by business model
reference/components.md               HTML snippets for each page type
reference/research-and-writing.md     source map + analyst voice rules
scripts/kb.py                         knowledge base — read in Phase 0, written in Phase 8
scripts/docs_kb.py                    runs annual-report-kb over every supplied PDF
scripts/new_company.py                scaffold a company folder + asset checklist
scripts/parse_screener.py             Screener.in xlsx -> normalised JSON (+ learned aliases)
scripts/sectors.py                    sector profiles — suppress metrics that don't apply
scripts/model.py                      ratios, DuPont, ROIIC, forensic, DCF, relative val
scripts/brand.py                      company palette from the logo -> brand.json/.css
scripts/charts.py                     11 chart archetypes, company palette, SVG output
scripts/render.py                     HTML -> PDF with a pre-flight QA gate
templates/demo.html + demo.pdf        a working 11-page render of every page archetype
```

Read `reference/blueprint.md` and `reference/components.md` before writing any HTML.
Read `reference/research-and-writing.md` before writing any prose.

Dependencies, once:

```bash
pip install weasyprint openpyxl matplotlib --break-system-packages
```

`openpyxl`, `matplotlib` and `pillow` are pure Python and always install cleanly, so
Phases 3–5 work anywhere. Only the final PDF render is environment-sensitive.

**Seven companion skills.** None is bundled in this skill's zip — install them all
wherever this skill runs.

```
PDFs        ──annual-report-kb───────────▶ kb/                        (Phase 2a)
kb/         ──modeling-strategy──────────▶ model_strategy.json ★GATE★ (Phase 3b)
            ──financial-model-assumptions▶ assumptions.json           (Phase 3c)
peer .xlsx  ──peer-comps─────────────────▶ peers.json + decisions     (Phase 3d)
            ──financial-model────────────▶ three_statement/model.json (Phase 3e)
            ──model.py───────────────────▶ model.json ──▶ the report  (Phase 3f)
IMF/RBI/…   ──india-macro-pack───────────▶ macro.json + macro_pack.md (Phase 4)

                            … report published, call logged in Phase 8 …

next quarter ──research-note-update──────▶ updates/<date>/ + scored call
```

| Skill | Used in | Without it |
|---|---|---|
| **`annual-report-kb`** | Phase 2a, via `scripts/docs_kb.py` | source documents must be read as raw PDFs; no image harvest |
| **`modeling-strategy`** | Phase 3b | the business architecture is assumed rather than decided: every company gets a growth-rate revenue line and an FCFF DCF whether or not either fits, and nothing records why |
| **`financial-model-assumptions`** | Phase 3c | `assumptions.json` is typed by hand, uncited; the working-capital and terminal-growth traps are live |
| **`peer-comps`** | Phases 1, 3d, 5 | the comps table is typed by hand from per-peer exports; no relative-valuation bands and no peer betas |
| **`financial-model`** | Phase 3e | no projected balance sheet or cash flow; the DCF discounts a margin applied to a revenue line, unchecked against whether it funds itself |
| **`india-macro-pack`** | Phase 4 | macro figures are searched ad hoc per report, with no observation period, no per-figure staleness check and nothing written back to `macro.json` |
| **`research-note-update`** | after publication, each quarter | the standing call is never scored, falsifiers are never adjudicated, and the calibration ledger stays empty — so the loop Phase 8 opens never closes |

`annual-report-kb` is auto-discovered at `~/.claude/skills/annual-report-kb` or
`./.claude/skills/annual-report-kb`; override with `--arkb <path>` or `EQR_ARKB`. The
rest are invoked by path — they sit alongside in `~/.claude/skills/`.

They are one pipeline. The KB exists so the strategy is evidenced; the strategy exists so
the assumptions are about the right variables; the assumptions exist so the model is
arguable; the model exists so the cash flow being discounted comes from a company that
funds itself; the comps and the macro pack exist so the valuation is placed against
something. Each stage owns one thing and hands over a single artefact — which is why
there is only ever one DCF.

**`modeling-strategy` decides what is modelled, not what the values are.** It sits
between the knowledge base and the assumptions, and it is the only stage that can say
"this business does not fit the template". Its `--strategy` flag is optional in all four
consumers: without it every one of them behaves exactly as it did before.

**Every one of them stops at banks, NBFCs and insurers.** Interest is revenue for a lender, so
EBITDA, net debt, the revolver plug and FCFF are all undefined. Resolve the sector in
Phase 0 and stop there, not four stages in.

**Check the render engine before writing anything:**

```bash
python3 <skill>/scripts/render.py --engines
```

`render.py` auto-selects from three backends, in descending fidelity:

| Engine | Fidelity | Notes |
|---|---|---|
| `weasyprint` | full | needs native Pango/Cairo; the pip package alone is not enough |
| `wsl` | full | runs WeasyPrint inside WSL — the Windows escape hatch |
| `chromium` | **degraded** | headless Chrome/Edge; zero install |

Chromium does **not** implement CSS Paged Media margin boxes, so `@top-left`,
`string(disclaimer)` and the named `@page cover` rule are silently dropped — the
running header disappears. Use it for fast layout iteration, never for the final
deliverable. Force a backend with `--engine wsl`.

If only `chromium` is available, say so up front rather than after the report is
written. To get full fidelity on Windows, inside WSL run:

```bash
sudo apt install -y python3-pip
pip3 install --break-system-packages weasyprint openpyxl matplotlib
```

Work in a `reports/` directory next to wherever the user wants output, not inside the
skill directory.

## How this runs — nine gated phases

A full equity research report is not a single response. Work through the phases below **one at a
time**. At the end of each, report what was produced, name anything unresolved, and
**stop for the user's go-ahead** before starting the next. Never run several phases in
one turn, and never begin writing before Phase 3 has produced numbers.

| Phase | Produces | Gate |
|---|---|---|
| 0 Recall & profile | knowledge brief, company profile, peer proposal | user confirms entity + peers |
| 1 Scope & request docs | scaffolded folder, document checklist | user supplies documents |
| 2 Docs → KB, images, palette | `kb/`, `assets/`, `brand.json`, `brand.css` | user approves palette |
| 3a Extract | `financials.json` | — |
| 3b **Modeling strategy** | `model_strategy.json`, `model_strategy.md` | **analyst APPROVES / MODIFIES / REJECTS the architecture and the valuation methods** |
| 3c–3f Assume, comps, model, value | cited `assumptions.json`, `peers.json`, `three_statement/model.xlsx`, `model.json` | user confirms each assumption |
| 4 Macro & industry | sourced macro/industry figures | — |
| 5 Charts | `charts/*.svg` | — |
| 6 Write | `report.html` | — |
| 7 Render & verify | the PDF | — |
| 8 Retrospective | knowledge written back for the next report | — |

State which phase is starting and which just finished, so the user always knows the
position in the sequence.

**Phases 0 and 8 are the learning loop.** Phase 0 reads everything previous reports
learned; Phase 8 writes back what this one learned. Skipping Phase 8 does not break the
report — it breaks the next one.

## Phase 0 — Recall, then identify and profile the company

### Read the knowledge base first

Before any web search, ask what previous reports already established:

```bash
python3 <skill>/scripts/kb.py --root reports brief --ticker <TICKER> --sector "<sector>"
```

This prints, when available: the stored macro snapshot **with its age**, the sector's
peer set, industry bodies and market sizing, learned Screener aliases, any prior
coverage of this company, the calibration record of past calls, and process lessons.

Act on what comes back:

- **Macro flagged STALE** (older than 90 days) — re-research it in Phase 4. Do not copy
  stale figures into a new report. Then run `india-macro-pack`'s `audit_macro.py --root
  reports` for the per-figure picture: the 90-day rule is a blanket, and a G-sec yield
  or an INR rate is stale in a week regardless of what the brief says.
- **Calls due for review** — score them before starting new work. An unscored track
  record is what lets the same mistake repeat.
- **Calibration shows directional bias** — if past targets ran consistently optimistic,
  that is a live instruction about terminal growth and exit margins in Phase 3.
- **Prior coverage of this name** — re-read the old thesis. If the rating changes, the
  report must say what changed and why.
- **A stored peer set** — start from it rather than re-deriving, then adjust.

On the very first report the brief is empty. That is expected; Phase 8 fills it.

### Then research the company

Research the company before asking the user for anything. Arriving with a profile
already built is what makes the document request specific rather than generic.

Search for, and assemble into a short profile:

- **Exact listed entity** — full registered name, NSE and BSE codes, ISIN. Indian groups
  routinely have several listed arms with near-identical names; confirm which one.
- **Business** — what it actually sells, segments, revenue split, end markets.
- **Scale** — market cap, latest revenue and PAT, employee count.
- **Promoter group** and holding; whether it is a subsidiary of a larger group.
- **Recent developments** — last 2–4 quarters: results, capex, management change,
  regulatory action, anything that would reframe the thesis.
- **Where the documents live** — the company's actual investor-relations URL and its
  Screener.in page, so the Phase 1 request points at real links, not generic advice.

Then present to the user:

1. The profile, in 10–15 lines.
2. **Entity confirmation** — "this is the one you mean?" with the exact name and codes.
3. **A proposed peer set** — three to five, chosen on business model and justified in one
   line each. Choose on what the company competes with, never on index membership. If the
   Phase 0 brief printed a stored peer set for this sector, **start from it** and adjust
   rather than re-deriving. Confirm the list explicitly: Phase 1 requests a Screener
   export per name, and adding a peer later means going back for another file.
4. **The sector profile the model will use**, confirmed with the user:

   ```bash
   python3 <skill>/scripts/sectors.py --resolve "<sector>"
   ```

   This decides which ratios are meaningful. A software firm has no gross margin or
   inventory; a lender has no EBITDA, net debt or coverage ratio. Getting it wrong
   means printing metrics that do not apply — see `reference/sectors.md`. If it
   resolves to `generic`, say so: nothing will be suppressed and every metric needs
   checking by hand.

   **If it resolves to `financials`, stop.** This skill does not model banks, NBFCs or
   insurers, and the manufacturing template would produce confident nonsense. Tell the
   user before any work is done, not after.

   The sector decides which **ratios** mean anything. It does not decide the model
   architecture or the valuation method — Phase 3b does, from the company's own
   disclosures. Do not promise the user a DCF here.
5. Anything the search left ambiguous.

**Stop here.** Do not scaffold or request documents until the entity and peers are
confirmed. Everything downstream is keyed to that decision.

## Phase 1 — Scope and request documents

Confirm in one round:

- **Consolidated vs standalone** (default consolidated) — pick one, state it on the
  cover, use it everywhere.
- **Cover date** — all stock data, shareholding and prices are as at this date.
- **Target price** — a real number, or `XXX` in the academic convention?
- **Analyst byline** — name, email, phone for the cover.

Then scaffold:

```bash
python3 <skill>/scripts/new_company.py EICHERMOT --name "Eicher Motors Ltd" --root reports
```

Show the printed checklist **with the real URLs found in Phase 0** and wait. The report
cannot be written without these, in `reports/<TICKER>/inputs/`:

| File | Where from | What only it can give you |
|---|---|---|
| `screener.xlsx` | Screener.in → company page → Export to Excel | 10-yr P&L, BS, CF, quarters, prices |
| `annual_report.pdf` | company investor-relations page | segments, capacity, RPT, auditor, contingent liabilities, remuneration, board attendance |
| `investor_presentation.pdf` | latest quarterly deck | volumes, realisation, capex plan |
| `concall.pdf` or `.txt` | transcript | guidance, management tone |
| `shareholding.pdf` | NSE/BSE filing | promoter pledge |
| `peers/<ticker>.xlsx` | Screener export **per peer** confirmed in Phase 0 | the comps table, the relative-valuation bands and the peer betas |

**Ask for the peer exports here, in this round.** They are the one input a reader would
never think to send unprompted, and Phase 3 stalls waiting for files nobody requested.
Same Screener view and the **same reporting basis** as the subject — `peer_ingest.py`
reads the basis out of each file's header and hard-errors on a mismatch, so a standalone
file slipped into a consolidated set cannot get through.

`screener.xlsx` is the one true blocker — it is the spine of every financial page. The
others can be chased in parallel with Phase 2, but none can be skipped silently: a
section whose source is missing gets cut, and the report says which.

Every PDF here becomes a navigable knowledge base in Phase 2, so ask for the **full**
annual report rather than an extract — pages that look irrelevant carry the related-party
schedule, the contingent-liability note and the board-attendance table.

**Stop here** until the documents arrive.

## Phase 2 — Documents to knowledge base, then images and palette

### 2a. Build a knowledge base for every document

Do this **before** reading any source PDF. The `annual-report-kb` skill converts each
PDF into page-level markdown, extracted tables, classified images and page-referenced
entity JSON. That turns the most expensive part of the report — reading a 400-page
annual report — into lookups, and it supplies real images for the asset folder.

```bash
python3 <skill>/scripts/docs_kb.py --root reports/<T> plan     # inventory + estimate
python3 <skill>/scripts/docs_kb.py --root reports/<T> run      # build them
```

`docs_kb.py` assigns depth per document, because the two judgement stages are
independent and pay off differently:

| Depth | Applies to | Stages |
|---|---|---|
| `full` | `annual_report` | parse → build → **section plan + image plan** → apply → validate |
| `images` | `investor_presentation` | parse → build → **image plan** → apply |
| `light` | `concall`, `shareholding` | parse → build (text is the point) |

**Never read the whole report into context.** Read `kb/<doc>/pages/page_NNNN.md` a page
at a time, or a section, or a table — never `_work/chunks/`.

Two things that will bite:

- **The parse is long.** Roughly 1.1 s/page, so a 500-page annual report is ~10 minutes.
  Run it in the background and poll. It is resumable — re-running skips completed chunks.
- **`docs_kb.py` obeys `preflight.py`.** Preflight decides mode, device and whether OCR
  is usable. Where surya selects a GPU backend but Docker is not running, OCR would die
  mid-parse; preflight catches that and `docs_kb.py` passes `--disable-ocr`. Text
  extraction is unaffected for digital PDFs. Do not override this without reading
  `annual-report-kb/references/troubleshooting.md`.

After `run`, write the plans the full/images tiers need, apply them, then:

```bash
python3 <skill>/scripts/docs_kb.py --root reports/<T> harvest   # images -> assets/
```

`kb/INDEX.md` records what was built and where to look for what.

### 2b. Sourcing images

Collect into `reports/<TICKER>/assets/`: `logo.*`, `products/*` (6–12),
`people/<surname>.*` (one per director/KMP profiled), `plants/footprint.*`,
`exhibits/*` (group structure, segment slide, auditor's report extract).

Source them, in this order of preference:

1. **`docs_kb.py harvest`** — this is the default path now. It maps the knowledge
   base's classified images onto the asset layout: `directors`/`executives` →
   `people/` (keyed by surname), `products`/`brands` → `products/`,
   `plants`/`factories`/`maps` → `plants/`, `charts`/`diagrams` → `exhibits/`,
   `logos` → `logo.*`. These come from the company's own filings, so the provenance
   is better than anything a web search returns.
2. **The company's own web properties** — official site, investor-relations pages,
   press kit — for whatever the filings did not carry.
3. **Ask the user** for anything still missing, naming exactly what and for which page.

If `harvest` reports images "extracted but never filed by category", the image plan has
not been applied for that document. Classify and apply it rather than reaching for the
web — the pictures are already there.

**Integrity rules — these are not negotiable:**

- **Never generate, paint or synthesise an image of a real person.** A director headshot
  must be a real photograph of that director. If one cannot be found, drop that person's
  card, or run the section as text-only.
- **Never substitute a lookalike.** A stock photo of *a* factory is not this company's
  plant; a generic motorcycle is not this company's product. Wrong images in a research
  report are misstatements, not decoration.
- **Verify identity before use.** Confirm the image is of the right entity — same-name
  group companies are a real trap.
- Record where each non-obvious image came from, so the source can be stated if asked.
- Prefer official/press-kit material, and note the source for anything reused.

A section whose images are missing gets deleted, not shipped with an empty frame —
`render.py` blocks on missing files.

### 2c. Deriving the palette

The report should look like the company it covers. Once `logo.png` is in place:

```bash
python3 <skill>/scripts/brand.py reports/<TICKER>
```

This extracts the logo's dominant colours and writes `brand.json` (read by `charts.py`),
`brand.css` (a `:root` override) and `brand-preview.svg` (a swatch strip).

It enforces legibility rather than copying the logo blindly: `--brand` fills table
headers that carry white text, so an extracted hue is darkened until it clears WCAG AA
(4.5:1), preserving the hue and moving only lightness. Hairlines and panel fills are
desaturated so they stay subtle. The script prints every adjustment it made.

Override any colour when the logo misleads — many Indian logos are a single flat colour
that says nothing about the brand's actual identity:

```bash
python3 <skill>/scripts/brand.py reports/<TICKER> --brand "#1a4d2e" --accent "#d4a017"
```

**Show `brand-preview.svg` to the user and get approval before generating charts** —
re-rendering every chart after a late palette change is the most wasteful rework in the
whole pipeline.

Then link it in `report.html`, **after** `report.css` so the override wins:

```html
<link rel="stylesheet" href="report.css">
<link rel="stylesheet" href="brand.css">
```

`charts.py` picks up `brand.json` automatically when it sits one level above the chart
output directory; otherwise pass `"brand": "<path>"` in the chart spec or set `EQR_BRAND`.

## Phase 3 — Extract, decide the architecture, then model

Six steps, in order: **3a** extract, **3b** modeling strategy *(gate)*, **3c**
assumptions, **3d** comps, **3e** three-statement model, **3f** valuation.

### 3a. Extract the historical spine

```bash
python3 <skill>/scripts/parse_screener.py reports/<T>/inputs/screener.xlsx \
        -o reports/<T>/data/financials.json
```

Read the parser's summary. If a block is missing or a line item is absent, fix it now by
patching the JSON from `kb/annual_report/` — do not paper over it downstream. The two
gaps that recur, and where the KB answers them:

- **Trade Payables** (the model warns it approximated payable days from Other
  Liabilities) — find the balance-sheet schedule via `metadata/table_index.json`.
- **Raw Material Cost** (gross margin is null without it) — the P&L schedule, same route.

Patch the numbers into `financials.json` and re-run, recording the page you took them
from. Anything you could not resolve stays a stated limitation on the page where the
number appears.

### 3b. Decide what is actually being modelled — and stop for approval

Before any assumption is argued, settle what this business *is*. The
**`modeling-strategy`** skill decides the economic architecture — per segment
where the disclosure supports it — and which valuation methodologies make
economic sense for this company rather than which ones the pipeline happens to
contain.

```bash
MS=<modeling-strategy skill>

# 1. what the knowledge base actually supports, with page citations
python3 $MS/scripts/strategy_probe.py --kb reports/<T>/kb/annual_report \
        --kb reports/<T>/kb/investor_presentation \
        --financials reports/<T>/data/financials.json \
        -o reports/<T>/data/strategy_probe.json

# 2. write strategy_decisions.json from its template, then build
python3 $MS/scripts/build_strategy.py --in reports/<T>/strategy_decisions.json \
        --outdir reports/<T>/data/ --md reports/<T>/model_strategy.md \
        --financials reports/<T>/data/financials.json
```

Put `model_strategy.md` to the user and **stop**. They are approving the
decomposition, the drivers the next stage will have to evidence, and the
valuation lens the target price will come from. Record `APPROVED` / `MODIFIED` /
`REJECTED` in `strategy_decisions.json` and rebuild — never edit
`model_strategy.json` by hand.

Modelability is derived, not declared:

| | |
|---|---|
| **GREEN** | proceed once approved |
| **AMBER** | proceed only after the analyst resolves each named item |
| **RED** | **stop the report** — out of scope, no defensible architecture, or disclosure too thin to model without manufacturing precision |

Three things this stage is expected to do that the rest of the pipeline is not:

- **Refuse.** Banks, NBFCs and insurers are RED here as well as in Phase 0.
- **Name a valuation method the pipeline cannot compute.** If SOTP, NAV, FCFE or
  FFO/AFFO is the right primary lens, it is marked PRIMARY with
  `execution_owner: analyst_manual`, modelability is AMBER, and the manual steps
  are listed. Do not substitute the DCF because the DCF is what exists.
- **Say the DCF is wrong when it is.** `model.py --strategy` will then refuse to
  compute a headline DCF, and `--force-dcf` stamps the override into `model.json`.

**Where the architecture is a segment or driver build-up**, the segment maths runs
after the gate and lands as a derived consolidated growth path — `financial-model`
has one revenue row and cannot execute segments natively:

```bash
# after the assumption values exist (3c), with segment_values.json filled in
python3 $MS/scripts/segment_build.py --strategy reports/<T>/data/model_strategy.json \
        --values reports/<T>/data/segment_values.json \
        --outdir reports/<T>/data/ --md reports/<T>/segment_build.md
```

Every driver series starts at the **base year**, so the build must reproduce the
last reported year within 1%. It refuses above that rather than scaling the gap
away — and that refusal is usually pointing at a real problem: a missing revenue
stream, a unit error, or drivers taken from the wrong segment.

`segment_build.md` is an exhibit in its own right. Include it.

### 3c. Build the assumptions with evidence, not by hand

`assumptions.json` is where the valuation is actually decided, so it is built by the
**`financial-model-assumptions`** skill rather than typed in. Every number comes back
cited to a page, with a confidence level, and anything the documents cannot support is
returned as `Not enough evidence` instead of a plausible-looking guess.

It reads the knowledge base Phase 2 already built, so this is the payoff for that work:

```bash
FMA=<financial-model-assumptions skill>

# 1. what the KB supports, and the gaps to declare up front
python3 $FMA/scripts/kb_search.py profile --kb "reports/<T>/kb/annual_report"

# 2. historical anchors — never recommend a growth rate without the 3y and 5y CAGR
python3 $FMA/scripts/history.py --in reports/<T>/data/financials.json \
        --out reports/<T>/data/history.json

# 3. evidence per assumption, with page citations
python3 $FMA/scripts/kb_search.py find --kb "reports/<T>/kb/annual_report" \
        --for revenue_growth

# 4. write decisions.json, then build — against the approved strategy
python3 $FMA/scripts/build_assumptions.py --in reports/<T>/decisions.json \
        --outdir reports/<T>/data/ \
        --strategy reports/<T>/data/model_strategy.json \
        --segment-build reports/<T>/data/segment_build.json
```

`--strategy` makes every driver the approved architecture requires a **check
failure** if it has no entry — the gap is declared here rather than discovered
later as a silent historical-average default. `--segment-build` replaces
`revenue_growth` with the derived path and records where it came from. Both are
optional; without them the builder behaves exactly as it always has.

That emits `assumptions.json` (feeds `model.py` directly) and
`assumptions_evidence.md` (the audit trail — carry its citations into the report).

**`decisions.json` is the file to edit and rebuild from**, not `assumptions.json`.
Regenerating overwrites the latter.

Three things it gets right that are easy to get wrong by hand:

- **Working capital.** `NWC/Sales = DSO/365 + (DIO − DPO)/365 × (COGS/Sales)`. Summing
  the three day-counts and dividing by 365 overstates working capital badly for any
  high-gross-margin company. Set `wc_days_on_cogs` correctly — it changes the answer.
- **`terminal_growth >= WACC` makes `model.py` exit**, not warn. The builder replicates
  the WACC formula and catches it first.
- It derives `ebit_margin` from `ebitda_margin` where only the latter is evidenced.

**Where a field goes in `decisions.json`:**

| Kind | Goes | Examples |
|---|---|---|
| A judgement needing evidence | inside `assumptions`, as a block with `value`/`why`/`evidence` | `revenue_growth`, `ebit_margin`, `terminal_growth`, **`exit_multiple`** |
| A setting or pass-through | **top level** | `peers`, `peer_betas`, `scenarios`, `mid_year_convention`, `blume_adjust`, `non_operating_assets`, `sector` |

Put a judgement at the top level and it is silently dropped from `assumptions.json`.

`sector` in `decisions.json` flows through to `assumptions.json`, so `model.py` picks it
up without `--sector`. Keep it consistent with what Phase 0 resolved.

Report every check the builder raises. **Do not resolve a band warning by quietly
changing the value** — that is the difference between an assumption set and a fudge.

Four fields still decide most of the answer: `beta`, `terminal_growth`, the
`ebit_margin` path, and `non_operating_assets` (surplus treasury and strategic stakes
sit outside the FCFF stream — cash-rich Indian industrials are badly undervalued
without it).

### 3d. Build the comps table

The peer set was settled in Phase 0 and the exports arrived in Phase 1. The
**`peer-comps`** skill turns them into the comps table, the relative-valuation bands and
the peer betas.

```bash
PCS=<peer-comps skill>

# 1. fill assets/peers_manifest_template.json -> peers_manifest.json
#    (subject first, one entry per company, price = close on the cover date)
python3 $PCS/scripts/peer_ingest.py peers_manifest.json -o reports/<T>/data/peers_raw.json

# 2. optional: peer betas, for the WACC build
python3 $PCS/scripts/peer_beta.py reports/<T>/data/peers_raw.json \
        --index <index csv> -o reports/<T>/data/peer_betas.json

# 3. build, and patch the peer blocks into decisions.json
python3 $PCS/scripts/build_comps.py reports/<T>/data/peers_raw.json \
        -o reports/<T>/data/peers.json --md reports/<T>/data/comps.md \
        --sector "<sector from Phase 0>" \
        --strategy reports/<T>/data/model_strategy.json \
        --patch-decisions reports/<T>/decisions.json
```

`--strategy` keeps a relative-valuation band off the football field for any
multiple the approved strategy ruled inappropriate. The comps **table** still
reports every computable multiple — withholding a number the reader can compute
looks like concealment. What is withheld is the implication that it values the
business.

Then **rebuild `assumptions.json`** through `build_assumptions.py`. `--patch-decisions`
writes `peers` and `peer_betas` at the **top level**, beside `assumptions` — a `peers`
block placed inside `assumptions` is silently dropped and the report loses its relative
valuation with no error.

`peer_ingest.py` imports this skill's own `parse_screener.py` rather than carrying a
copy, so the aliases learned via `kb.py alias` apply to peer exports too.

Two things it enforces that are easy to get wrong by hand:

- **Reporting basis.** Mixing a standalone peer into a consolidated set corrupts every
  multiple. It hard-errors rather than warning.
- **Forward multiples stay separate.** Consensus estimates, where you have them, are
  reported apart from the trailing set and never blended into the median.

`build_comps.py` and `model.py`'s `relative()` compute the median and premium/discount
**independently**. They should agree exactly — if they ever diverge, the emitted array
and `relative()` have drifted apart, and that is a bug, not a rounding difference.

### 3e. Build the three-statement model

Before valuing anything, build the projections properly. The **`financial-model`** skill
produces a linked P&L, balance sheet and cash flow — with fixed-asset, working-capital,
debt/revolver and equity schedules — and **refuses to hand over a model whose balance
sheet does not tie**.

```bash
FMD=<financial-model skill>

python3 $FMD/scripts/ingest.py --screener reports/<T>/data/financials.json \
        --assumptions reports/<T>/data/assumptions.json \
        --strategy reports/<T>/data/model_strategy.json \
        -o reports/<T>/data/three_statement/model_input.json

python3 $FMD/scripts/build_model.py \
        --in  reports/<T>/data/three_statement/model_input.json \
        --outdir reports/<T>/data/three_statement/
```

**Write it to `data/three_statement/`, not `data/`.** Both skills emit a file called
`model.json`; sharing a directory means one silently overwrites the other.

That produces `model.xlsx` (live Excel formulas), `model.json` (with the `bridge` block)
and `model_review.md`. `ingest.py` reuses this skill's `parse_screener.py` when it can
find it, so the learned Screener aliases in `reports/_knowledge/aliases.json` apply here
too.

Read the checks it prints. **`BLOCKING` on the historical balance sheet is an ingest
problem**, not a modelling one — usually a missing line item. Trade payables are the
usual culprit: Screener does not carry them, so payable days read zero and net operating
assets are overstated until they are pulled from the annual report KB.

### 3f. Value it

```bash
python3 <skill>/scripts/model.py reports/<T>/data/financials.json \
        reports/<T>/data/assumptions.json --sector "<sector from Phase 0>" \
        --strategy reports/<T>/data/model_strategy.json \
        --fm reports/<T>/data/three_statement/model.json \
        -o reports/<T>/data/model.json
```

`--strategy` makes the valuation execute the methodology that was approved: each
method's role is written into `model.json`, and where the strategy classified the
FCFF DCF `NOT_APPROPRIATE` or `LOW_RELIABILITY` **no DCF is computed at all**.
`--force-dcf` overrides that and stamps the override into `model.json` and the
warnings — use it only when the strategy was wrong, and then fix the strategy.

Where the primary method is one nothing here computes (SOTP, NAV, FCFE,
FFO/AFFO), `model.json` carries `valuation_strategy.manual_completion_required`
with the steps. That is the report's headline valuation, and it is the analyst's
to finish.

`--fm` cross-checks the three-statement model's `bridge.fcff` against this DCF's own
driver-based projection and reports the gap. **A large gap is a finding, not a nuisance:
it means the drivers being discounted do not fund the balance sheet they imply.**
Reconcile capex, working capital and depreciation — never average the two answers.

Add `--fcff-from-model` to discount the three-statement cash flows themselves, so the
FCFF comes out of a company that funds itself rather than from a margin applied to a
revenue line. Where the model's horizon is shorter than the DCF's, the horizon is cut to
match and the run says so rather than inventing years.

Valuation lives here and only here. `financial-model` deliberately does not value the
company — the `bridge` block is the entire hand-off, so there is only ever one DCF.

**Always pass `--sector`.** Without it nothing is suppressed and metrics that do not
apply to this business model reach the page — a services company would otherwise show
inventory days, and the run prints `Unclassified — unfiltered` to say so. The output
lists what was suppressed, what to lead with, and the figures to pull from the annual
report KB. See `reference/sectors.md`.

Read every line of the output:

- **`TV as % of EV` above 75%** means the DCF is a bet on terminal assumptions. Say so
  in the body rather than presenting the per-share number as precise.
- **Any `WATCH` or `FAIL` forensic flag** becomes a paragraph in the forensic section
  and a bullet in the risks section. Do not bury it.
- **Every `!` warning** is an unresolved data gap. Resolve it from the annual report, or
  state the limitation on the page where the number appears.
- **The perpetuity-vs-exit-multiple gap.** The model prints the exit EV/EBITDA that the
  Gordon-Growth terminal value implies. If that is far from where the sector trades,
  reconcile the two in the text — do not quietly pick the flattering one.
- **The three-statement FCFF gap** (`three_statement.gap_%`). Above ~15% the drivers do
  not fund the balance sheet. Fix the drivers; do not split the difference.

### Assumptions that unlock the institutional layer

Beyond the four core fields, `assumptions.json` accepts:

| Key | Effect |
|---|---|
| `scenarios` | `{"bull": {...,"probability":0.25}, "base": {...}, "bear": {...}}` — each is a full DCF re-run, then probability-weighted. A scenario need only state the drivers it changes. |
| `exit_multiple` | Cross-checks the perpetuity terminal value against an EV/EBITDA exit. |
| `mid_year_convention` | `true` discounts at t+0.5. Cash flows accrue through the year, so this is the institutional default; it lifts value by roughly half a year of WACC. |
| `peer_betas` | `[{"beta":1.1,"debt_equity":0.35}, ...]` — unlevered (Hamada), median-ed, relevered at the target structure. Far more defensible than one regression beta. |
| `blume_adjust` | `true` applies 0.67β + 0.33, the standard reversion adjustment for a multi-year DCF. |
| `current_price` | Also enables the market-equity Altman Z. |

A sensitivity grid flexes the discount rate. **Scenarios flex the business** — which is
where the risk actually sits. A report with only a WACC × g grid has not stress-tested
the thesis, it has stress-tested the arithmetic.

Read `reference/research-and-writing.md` Part 4 before writing up Altman or Piotroski —
the two Altman variants are not interchangeable, and the score alone is not a finding.

**Gate on the assumptions, not just the output.** Before moving to Phase 4, put the
assumption set to the user — the summary table from `assumptions_evidence.md`, the
confidence levels, and every `Not enough evidence` item. They are approving the
valuation at this point; the DCF afterwards is arithmetic. Record any change as
`"status": "user_modified"` in `decisions.json`, keep the original under `recommended`,
and rebuild rather than editing `assumptions.json`.

Then work through the knowledge bases — `kb/annual_report/`, `kb/concall/`,
`kb/investor_presentation/` — for everything the export cannot give you. This is where
the report's value comes from, and it is the step most reports skip. Because Phase 2
already indexed these, it is now a series of targeted lookups rather than a read of the
whole document: start at `context/*.md` to orient, then open only the pages and tables
that matter. See `reference/research-and-writing.md` Part 1 for the full source map.

## Phase 4 — Research the macro and industry layer

Run the **`india-macro-pack`** skill. It is the executable form of what this phase used
to describe in prose, and it enforces the provenance that prose cannot:

```bash
python3 <imp>/scripts/fetch_macro.py --out reports/<T>/data/macro_raw.json
# fill reports/<T>/manual.json from the worksheet it prints
python3 <imp>/scripts/build_pack.py --raw reports/<T>/data/macro_raw.json \
        --manual reports/<T>/manual.json --root reports \
        --out-dir reports/<T> --ticker <T>
python3 <imp>/scripts/audit_macro.py --root reports
```

It produces `reports/<T>/macro_pack.md` (write pages 2–9 from it),
`reports/<T>/data/macro_charts.json` (feed to `charts.py` in Phase 5) and
`reports/_knowledge/macro.json` in the format `kb.py brief` already reads.

Search for current data; do not write macro from memory. Minimum set:

- IMF WEO latest edition — global and India GDP, inflation. Cite edition and month.
  **`imf.org` blocks programmatic access**; the skill fetches via a mirror and gates on
  the WEO vintage, because the mirror lags. If the gate fires, read the figures off
  imf.org by hand into `manual.json`'s `weo` block.
- MoSPI — India CPI, WPI, IIP, per-capita income.
- RBI — repo rate, 10Y G-sec, INR, credit growth.
- Industry body (SIAM/FADA/IBEF or the sector's association) — volumes, market size,
  penetration. Never state a market-size figure without its source and forecast year.

Three rules the skill enforces and the report must honour:

- **IMF reports India on a fiscal-year basis**, labelled by the year the FY starts. WEO
  2026 is FY27. Write the FY label; a bare WEO year reads one year early.
- **NSO and IMF will disagree** on the overlapping year. Cite NSO for actuals and IMF for
  forward years, and say which is which.
### Reconcile the macro pack against the valuation

Two figures appear in both the macro pages and the model. If they disagree, one of them
is wrong, and it is far cheaper to find out here than after the DCF is built:

| Macro figure | Must match | Consequence if it drifts |
|---|---|---|
| `india_10y_gsec` | `risk_free_rate` in `decisions.json` | the WACC is struck on a rate the report's own macro page contradicts |
| `usdinr` | the cover date `peer-comps` struck its multiples on | the comps table and the macro page quote different days |

Fix the mismatch in `decisions.json` and rebuild `assumptions.json` — never by editing
the macro pack to agree with the model.

- **Anything in §6 of `macro_pack.md` could not be sourced.** It must be absent from the
  report or explicitly marked unavailable — never filled from memory.

Re-run `audit_macro.py` before Phase 6 writes prose: market-class figures (yields, INR,
crude) expire in seven days, and a report can sit for longer than that between phases.

## Phase 5 — Build charts

Write a chart spec JSON, then:

```bash
python3 <skill>/scripts/charts.py reports/<T>/data/charts.json
# and the two macro exhibits Phase 4 already specced:
python3 <skill>/scripts/charts.py reports/<T>/data/macro_charts.json
```

`macro_charts.json` is written by `india-macro-pack` in the shape `charts.py` expects
and picks up `brand.json` automatically, so the macro exhibits match the company palette
with no extra argument. It only contains charts whose every figure was **accepted this
run** — carried-forward figures are deliberately not charted, because drawing them would
imply they were refreshed for this report.

Archetypes: `bar_grouped`, `bar_line_combo`, `line_multi`, `stacked_bar`, `donut`,
`indexed_performance`, `waterfall`, `scatter_peers`, `sensitivity_heat`, `area_stack`,
`football_field`, `tornado`.

**The valuation section needs two of these specifically:**

- **`football_field`** — every valuation method as a horizontal range against the
  current price. This is the exhibit that shows at a glance which methods bracket the
  market and which do not. **`data/peers.json` already carries a `football_field` array
  in exactly this function's shape** — the peer 25th–75th percentile bands with net debt
  bridged out. Concatenate the DCF scenario range and the 52-week range onto it:

  ```python
  pc = json.load(open("data/peers.json"))
  methods = pc["football_field"] + [
      {"label": "DCF (bear-bull)", "low": bear, "high": bull, "mid": base},
      {"label": "52-week range",   "low": lo,   "high": hi},
  ]
  charts.football_field("val_football", methods, current_price=cmp_)
  ```

- **`scatter_peers`** — also feeds from `peers.json`. ROE vs P/B is the standard pairing,
  with the subject highlighted.
- **`tornado`** — drivers ranked by how far each moves the value, widest at the top. It
  tells the reader which assumption is worth arguing about. Build it by re-running
  `model.py` with one driver flexed at a time.

Two rules that are easy to get wrong:

1. **Never pass `title=`.** Titles go in the HTML as `<div class="fig-title">`. Passing
   both prints it twice at two different sizes.
2. **Size to the column.** Cover sidebar `w=2.4,h=1.7`; half of a `.split`
   `w=3.5,h=2.4`; a third of `.cols-3` `w=2.6,h=2.0`; full width `w=7.0,h=2.8`.

## Phase 6 — Write the report

Create `reports/<T>/report.html`, one `<section class="page">` per blueprint row. Copy
component markup from `reference/components.md` verbatim — `report.css` defines every
class, and invented class names silently render unstyled.

Link both stylesheets, in this order, with relative paths that actually resolve from the
HTML file's location. `brand.css` only overrides the `:root` colour tokens, so it must
come second or the company palette is silently discarded:

```html
<link rel="stylesheet" href="report.css">
<link rel="stylesheet" href="brand.css">
```

Write in passes, not one shot:

1. **Skeleton** — all sections, headings only. Check the count against the blueprint.
2. **Data** — tables, KPI strips, chart embeds. Numbers only, from `model.json` and the
   source documents.
3. **Prose** — the analysis around the numbers.
4. **Read-throughs** — the bolded one-sentence conclusion under each chart.

Then render:

```bash
python3 <skill>/scripts/render.py reports/<T>/report.html \
        -o "<Company> - Equity Research Report.pdf"
```

The gate also flags charts whose title is baked into the SVG (rule 1 above) — if it
does, re-generate that chart without `title=` rather than shipping the duplicate.

## Voice — what separates this from a student report

- **Every claim carries a number.** "Margins expanded" is not analysis. "EBITDA margin
  expanded 240 bps to 24.7%, of which ~150 bps came from a 9% fall in alloy prices and
  the rest from operating leverage on 22% volume growth" is.
- **Every chart earns its page.** One bolded read-through sentence under each stating
  what it proves. If you cannot write that sentence, cut the chart.
- **Decompose growth.** Volume vs price vs mix, not a single percentage.
- **State falsifiers.** The verdict section ends with the two or three observable things
  that would break the thesis, each with a specific threshold and date. This is the
  single biggest quality gap between student and professional work.
- **When the methods disagree, say so.** If the DCF says expensive and the multiples say
  cheap, that tension is the most interesting thing in the report. Explain the gap
  rather than averaging it away.
- **Banned:** "robust" / "healthy" / "strong" as standalone verdicts, "poised to
  capitalise", "going forward", any market-size number without a source, any percentage
  without a base period, "as per our estimates" where no estimate was made.
- Length: 250–450 words of body text on a page with a chart, 150–250 with a wide table.
- Units: INR Cr throughout, `x` for multiples, `bps` for margin moves under 1pp. One
  currency symbol convention for the whole document.

## Typography and tables — the floors

**7pt is the floor for any text a reader has to read**, in tables and in charts
alike, and nothing shrinks below it to force a fit. A table that will not fit at
7pt loses columns, splits by period, or runs full width. A chart whose labels
will not fit drops labels; it does not shrink the type.

`scripts/type_audit.py` measures this **where the type lands on the page**, not
as authored. A chart is an SVG scaled to its container, so a 9px label in a
canvas displayed at 0.7x prints at 4.7pt. The audit reads each SVG's intrinsic
width, works out which slot the HTML puts it in, and reports the smallest size
that actually prints.

```bash
python type_audit.py reports/<T>/report.html --min 7.0
```

Two rules keep it passing:

- **Charts declare `place`** in the spec: `"body"` for the full text width,
  `"column"` for half a split. `render.js` builds the canvas at that width so
  the page never rescales it. Scaling down shrinks labels below the floor;
  scaling up inflates the block's height until it fits on no page at all. The
  audit fails any chart whose scale falls outside 0.92–1.08, which is what
  catches a spec whose `place` disagrees with where the report put it.
- **Archetypes author at 10px minimum** (`H.px()` in `house.js` floors every
  size). 10px at scale 1 is 7.5pt.

**Financial tables use one vocabulary of row classes**, so hierarchy reads the
same in every statement: `tr.group` for a section band, `tr.total` for a
subtotal ruled above, `tr.sub` for a derived or memo line, `tr.subject` for the
subject company in a peer table. Numbers are right-aligned, labels left; that is
in the base stylesheet and should not be overridden.

**Historical and projected periods must be visually distinct.** `table()` detects
a projected column from a fiscal-period header (`FY27E`, `Mar-28E`) and tints it,
italicises it and rules the boundary, with a stated legend. Pass `fcst="all"`
where every column is a projection: tinting all of them says nothing, so it gets
a legend instead. The detector matches a period label only — an early version
keyed on a trailing `P` and shaded the "Against CMP" column of the scenario
table.

**Subject-company emphasis is semantic, in tables as in charts.** `tr.subject`
marks the row because it is the subject; it is not the "last row" or the
"biggest row" treatment. The accent rules are the same ones the charts follow.

**Running headers stay restrained**: the disclaimer string and the company name
at 7.5pt in the soft ink, and a folio. The header is a locator, not a masthead.

## Charts must earn the axes

`render.js` refuses to draw a growth, trend or comparison chart of fewer than
four points and resolves it to a `kpi_strip` instead. Two or three plotted
values show no relationship a reader cannot read straight off the numbers, and
putting axes round them dresses a fact up as an analysis. The rule applies on
the legacy `fn` path too: it is a statement about what the data can support, not
about which entry point declared it.

Prefer an HTML analytical component wherever the intent resolves to one: a
mixed-unit comparison is a `kpi_strip`, a 2-D value grid is a `heat_table`, a
multiplicative identity is a `dupont_tree`.

## Page composition — the layout rules

A report is not finished because the analysis is right. Composition is a gate of its
own, and `scripts/layout_qa.py` enforces it against the rendered PDF.

**Do not generate a SWOT grid or a Porter five-forces diagram unless the user asks for
one by name.** Both restate material the rest of the report already carries, in a form
that adds no number and no falsifier. They read as coursework. If the user does ask,
build them; otherwise the competitive argument belongs in the market-share and moat
prose, where it can carry figures.

**A block is atomic.** `fig()`, `table()` and `kbfig()` each wrap title, visual, source
and read-through in a single `.block` with `break-inside: avoid`. A chart title on one
page and its chart on the next is a defect, not a near miss.

**Do not force a page break for an ordinary H2.** Sections are `page flow`; two short
sections sharing a page is the desired outcome. Reserve a hard break for the cover, the
verdict and the disclaimer.

**WeasyPrint fragments CSS grid unreliably.** A `.split` that breaks across a page can
push its second column off-canvas, which surfaces as glyphs above the page top. Keep
splits atomic and win page fill structurally instead: never stack two tall exhibits in
one column of one section.

**Ten-year blocks.** `split10()` renders two five-year halves; use it where each half is
under ~300pt. Where the block is deep (a 13-row balance sheet is ~380pt a half, so two
halves exceed the 720pt body) use `wide10()` — one wide table at `cls="xs"` — or the two
halves will never share a page and each leaves a third of a page empty.

**Reflow before you fill, and never decorate.** When `layout_qa.py` reports a page
below the floor, the first move is to reshape the block that would not fit — the
cause is almost always one atomic unit a little too tall for the gap above it.
`scripts/page_plan.py` names it:

```bash
python3 page_plan.py reports/<T>/report.html --qa data/_layout_qa.json
```

It reports, for each page, the measured free space and the height of the
heading-plus-block unit that moved overleaf, so "reflow adjacent content" becomes
an instruction rather than a guess. The reflows that work, in order of
preference: split one tall two-column block into two half-height blocks; lift a
table out of a column into its own block; use `wide10()` instead of `split10()`
where each half exceeds ~300pt.

Only when reflow is exhausted should you add content, and only content the
argument wanted anyway — a harvested KB exhibit that carries a finding, a table
the analysis already relies on, the paragraph that was missing. **Never add a
visual to occupy whitespace.** An image placed to fill a page is filler whatever
it depicts. Never shrink type or charts to close a gap.

**Do not force a page break to fix fill.** Giving a section `spread` moves the
problem: on this report it turned one 55% page into a 42% one.

**Every figure placed to fill a page still obeys the authoritative-data rule.** Build the
table from `model.json` / `financials.json` in code. A number typed into a report
component is a number nothing checks. The same applies to chart specs: generate them from
the data file rather than transcribing values into `charts_erip.json`.

**Verify a KB image before you place it.** Read the JPEG. The harvested `image_plan.json`
captions are model-generated and have been wrong (a debt-maturity ladder was classified
as "performance projections"). Never place an image of a person without confirming
identity, and never substitute a stand-in image.

Run the gate after every render:

```bash
python3 <skill>/scripts/layout_qa.py "<Company> - Equity Research Report.pdf" \
        --html reports/<T>/report.html --before <N> --removed "SWOT,Porter five forces"
```

It reports the occupied **extent** per page — how far down the body box the content
reaches, error under 65%, warning under 80% — plus orphan headings, exhibit titles
separated from their visual, isolated continuation pages, contiguous whitespace bands
over 150pt, clipping and overflow, page count before and after, removed sections and
duplicate exhibits.

Extent, not ink density. Counting inked bands marked a page carrying a tornado chart
half-empty because the chart's own whitespace scored as blank, and it scored every page
as full once the running header was included. The measurement is cropped to the body
box and spans first ink to last. Pair it with `reports/<T>/pdf_qa.py` for
the document-level checks: ink density, recap-aware duplicate visuals and cross-document
figure consistency.

## Phase 7 — Render, verify, deliver

The pre-flight gate catches missing images, placeholder text, unlinked CSS and low page
counts. It does not catch bad analysis. Before handing over the PDF, convert a sample of
pages to images and actually look at them:

```bash
pdftoppm -png -r 92 -f 1 -l 6 report.pdf pg && ls pg*
```

Read those images. Check for:

- Text overflowing the page bottom, or a page more than a third empty
- Charts with unreadable axis labels (wrong `w`/`h` for the column)
- Duplicated chart titles
- Tables squeezed past `class="xs"` legibility
- No SWOT grid or Porter diagram unless the user asked for one

Do not chase a page count. Depth decides length; `layout_qa.py` decides whether the
pages that exist are properly filled.

Then re-check the numbers: pick three figures from the prose and trace each back to
`model.json` or a source document. If any cannot be traced, it does not belong in the
report.

`model_review.md` from the three-statement build is an exhibit in its own right — the
projected statements and the checks that passed. Include it, or say why not.

Finish with a three-line summary: the valuation conclusion, the one thing that surprised
you in the data, and any unresolved data gap the user should know about.

## Phase 8 — Retrospective: write back what this report taught

Do this **every time**, immediately after delivering the PDF, while the details are
still to hand. It takes two minutes and it is the only reason report N+1 is better than
report N. All of it goes to `reports/_knowledge/`, which sits outside the skill
directory and therefore survives skill upgrades.

```bash
KB="python3 <skill>/scripts/kb.py --root reports"
```

**1. Any Screener label the parser missed.** This is the highest-value entry, because
the fix is mechanical and permanent:

```bash
$KB alias --canon "Sales" --alias "Revenue from Operations"
```

Log KB-navigation findings the same way — where a given disclosure actually lived is
worth knowing next time:

```bash
$KB lesson --text "RPT schedule was in the standalone notes, not the consolidated set" --tag kb
```

`parse_screener.py` loads these on every later run, so a label that broke the parser
once never breaks it again.

**2. Sector knowledge**, so the next company in this sector starts warm. Write back the
peer set **as confirmed and used**, not as first proposed — Phase 0 of the next report
reads this and it saves re-deriving the list and re-requesting exports:

```bash
$KB sector --sector "two-wheelers" --peers "BAJAJ-AUTO,TVSMOTOR,HEROMOTOCO" \
    --body "SIAM" --market-size "domestic 2W FY26=1.84 Cr units" \
    --archetype "capacity_utilisation_realisation" \
    --note "SIAM is wholesale despatches, FADA is retail registrations — never mix"
```

**Write back the archetype the report actually used**, not the one first proposed.
Phase 3b of the next report in this sector reads it as a starting point — which
saves re-deriving the architecture, and makes it visible when a company in a
familiar sector turns out to run on something else.

**3. Macro figures with their source**, so the next report does not re-research
unchanged data — and knows when it has gone stale:

```bash
$KB macro --set "india_gdp_fy27=6.5" --source "IMF WEO, April 2026"
```

**4. The call itself, with its falsifiers and a review date.** This is the part that
makes the loop honest rather than a filing cabinet:

```bash
$KB call --ticker EICHERMOT --rating REDUCE --target 6800 --cmp 7312 \
    --review-months 6 --falsifier "volume growth < 8% in H1FY27"
```

**Write falsifiers a later note can actually adjudicate.** `research-note-update` reads
these back verbatim and rules each one TRIPPED / NOT TRIPPED / UNRESOLVED against the
quarter's actuals. "Growth disappoints" cannot be ruled on; *"volume growth < 8% in
H1FY27"* can. Each needs an observable metric, a threshold and a date.

Later, when the review date passes, score it:

```bash
$KB close --ticker EICHERMOT --actual 5900 --note "volume miss, thesis played out"
```

`kb.py review` then reports mean and mean-absolute target error across all closed
calls, and says whether the bias is systematically optimistic or conservative. **That
number is the single most useful input to the next DCF** — a house that is reliably 15%
optimistic should be arguing about its terminal assumptions, not its spreadsheet.

**5. Where the evidence for a driver actually lived** — the next report in this sector
looks in the same place:

```bash
$KB sector --sector "two-wheelers" \
    --note "capex guidance was in the concall Q&A, not the capex note or the MD&A"
```

**6. Process lessons** — anything that cost time and would cost it again:

```bash
$KB lesson --text "annual report page 148 had the segment EBIT split, not the MD&A" --tag sourcing
```

Record a lesson only if it would change what a future report *does*. A log of vague
observations is noise, and the brief prints the last eight — keep them worth reading.

**Recurring failures belong in the skill, not the log.** If the same lesson appears
three times, the fix is a change to `SKILL.md`, `report.css` or a script — tell the
user, and offer to make it. The knowledge base is for what varies by company and
sector; the skill files are for what is always true.

## After publication — the update note

An initiating coverage report is not the end of the work; it is the start of a
position that has to be defended each quarter. That is the **`research-note-update`**
skill, and it is where the call recorded in Phase 8 finally pays off.

It is **not a phase of this skill** — it is a separate entry point that consumes what
this pipeline produced: `decisions.json`, both `model.json` files, `peers.json`, the
knowledge base and `calls.json`. Output lands in `reports/<T>/updates/<YYYY-MM-DD>/`.

Reach for it when results are out, a covered name has an event, or `kb.py brief`
reports a **review date has passed**.

Each note pulls the standing rating, target and falsifiers; adjudicates whether any
falsifier has tripped; runs the quarter's actuals against the standing forecast as a
variance table; decides whether the model needs a full re-forecast or only a re-strike;
applies the house rating policy; and closes or re-opens the call in `kb.py`.

**Two consequences that reach back into this skill:**

- **Build the three-statement model in Phase 3e even when the DCF alone would do.**
  Without it the variance table collapses to two lines — revenue and EBIT — and the
  EBITDA-margin check, the one thing a single quarter measures honestly, cannot be
  computed at all. `data/model.json`'s forecast rows carry only Sales, EBIT and EBIT %
  under `Y1..Yn` headings; the fiscal-year labels and the PAT and EPS lines live in
  `data/three_statement/model.json`.
- **Log the call properly in Phase 8.** The falsifiers written there are exactly what
  the next note adjudicates against. Vague ones ("growth disappoints") cannot be
  adjudicated; thresholded ones ("volume growth < 8% in H1FY27") can.

**A reiteration must not write to `calls.json`.** `kb.py call` always appends a new
open call and has no reiterate concept, so logging one per note would flood the ledger
with three-month horizons that were never the horizon you set. Only a genuine rating or
target change opens a new call.
