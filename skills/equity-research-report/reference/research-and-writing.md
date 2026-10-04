# Where each number comes from, and how to write it up

## Part 1 — Source map

Primary sources beat secondary ones everywhere. If a figure exists in the annual
report, quote the annual report, not a news article about it.

**Read the knowledge base, not the PDFs.** Phase 2 converts every supplied document
into `reports/<T>/kb/<doc>/`. Everything below points there. Opening the raw PDF is a
fallback for when the KB is missing something, not the default.

| What you need | Source | Notes |
|---|---|---|
| 10-yr P&L, BS, CF, quarters, ratios, price history | `inputs/screener.xlsx` | `parse_screener.py` handles it. This is the spine of the report. |
| Projected P&L, balance sheet, cash flow and the schedules behind them | `data/three_statement/model.json` + `model_review.md` | Built by the `financial-model` skill. The forecast tables in the report come from here, not from the DCF's internal projection. |
| Segment revenue & EBIT, capacity, RPT, contingent liabilities, auditor, pledging, remuneration, board attendance | `kb/annual_report/` — start at `metadata/table_index.json` and `sections/` | Not in Screener. Every table carries its page; quote it. |
| Directors, executives, subsidiaries, plants, products, brands | `kb/annual_report/entities/*.json` | Structured and page-referenced — use these rather than re-reading prose. |
| A topic overview before drilling in | `kb/annual_report/context/*.md` | Twelve summaries, each cited. Read one to find the pages worth opening. |
| Guidance, volumes, realisation, capex plan, management tone | `kb/concall/pages/`, `kb/investor_presentation/` | Quote guidance verbatim with the quarter attached. |
| Shareholding & pledge, latest quarter | `kb/shareholding/pages/` | |
| Director photos, product shots, plant maps, logo | `kb/*/images/<category>/` via `docs_kb.py harvest` | Real images from the company's own filings. |

**Navigating a KB without blowing up context:** `kb/INDEX.md` says what exists. Then
`context/*.md` to orient, `metadata/table_index.json` to find a table, `pages/page_NNNN.md`
one page at a time. Never read `_work/chunks/`, and never bulk-read `pages/`.

**Page citations.** KB filenames and JSON are 0-based; citations to the reader are
1-based, written `(p. N)`. The KB records both — use `pdf_page` for the citation.

**When a table is missing.** `table_index.json` marks entries `"extracted": false` where
the grid could not be reconstructed (common for infographic-style layouts, especially
with OCR disabled). The text is still in the page file — read it there and type the
numbers in, rather than assuming the data is absent.
| Global & India GDP, inflation | IMF World Economic Outlook (latest edition) | Cite the edition and month: "IMF WEO, April 2026". |
| India macro: CPI, WPI, IIP, per-capita income | MoSPI | |
| Repo rate, 10Y G-sec, INR, credit growth | RBI | |
| Industry volumes & market size | Industry body first (SIAM, FADA, IBEF, industry association), consultancy second | Never cite a market-size number without its source and forecast year. |
| Peer financials for comparison tables | `data/comps.md` + `data/peers.json`, built by `peer-comps` from a Screener export per peer | Same accounting basis throughout — the ingest hard-errors on a mismatch rather than warning. |
| Relative-valuation bands, peer betas | `data/peers.json` (`football_field`, `peer_betas`) | Bands are the peer 25th–75th percentile applied to the subject's own metric. |
| Analyst coverage universe | Broker notes, exchange filings, financial press | Include date, house, rating, target. |
| Prices for indexed performance | Screener price block, or NSE historical | Rebase all series to 100 on day one. |

**Rule:** if a number is not in a source document and not computed by `model.py`,
it does not go in the report. When something is genuinely unavailable, write
"not disclosed" — never estimate silently.

**Forecast assumptions carry their own citations.** `assumptions_evidence.md` (built in
Phase 3 by the `financial-model-assumptions` skill) holds the quote, page and confidence
behind every driver. Use those citations in the text: "management guided to low-teens
growth (p. 43)" is an argument; "we assume 12% growth" is an assertion. Anything the
skill returned as `Not enough evidence` must be stated as a limitation on the page where
it matters — never quietly replaced with a sector rule of thumb.

**Consolidated vs standalone:** pick one, state it on the cover, use it everywhere.
The samples use consolidated. Quarterly snapshots are often standalone — if you mix,
label the table.

**Units:** INR Cr throughout, one convention for lakh/crore, `x` for multiples,
`bps` for margin changes under 1pp. Never mix ₹ and INR in the same report.

---

## Part 2 — Writing rules

**Voice.** Third person, present tense for the business, past for events. No hedging
stacks ("may possibly tend to"). No filler openers ("It is important to note that").
A sell-side analyst writes to be argued with, not to be safe.

**Every claim carries a number.** "Margins expanded" is not analysis.
"EBITDA margin expanded 240 bps to 24.7%, of which ~150 bps came from a 9% fall in
alloy prices and the rest from operating leverage on 22% volume growth" is.

**Every chart earns its page.** Under each chart, one bolded read-through sentence
stating what the chart proves. If you cannot write that sentence, cut the chart.

**Say what would change your mind.** The investment rationale section ends with
falsifiers: the two or three observable things that would break the thesis. This is
the single biggest quality gap between a student report and a real one.

**On the target price.** The samples print `XXX` because they are academic. If you do
print a number: anchor it on one method, cross-check with the other, state the
weighting, and show the implied multiple. A DCF whose terminal value is >75% of EV is
a bet on the terminal assumptions — say so in the text.

**Section length.** 250–450 words of body text per page alongside a chart; 150–250
alongside a wide table. A page that is all prose and no exhibit should not exist
outside the cover and the management commentary.

**Bullets.** Number-led, one idea, max two lines. If a bullet runs three lines it is
a paragraph — make it one.

**Peers.** Name them once, then use them consistently in every comparison chart. Three
to five peers. Choose them on business model, not on index membership.

A premium or discount to the peer median is the start of the argument, not the end. Say
what the subject earns for it — a higher ROE, a longer growth runway, a cleaner balance
sheet — or say the premium is unjustified. "Trades at a 40% premium to peers" without
that sentence is a data point, not analysis. Where the DCF and the comps disagree, that
tension is the most interesting thing on the page: explain the gap rather than averaging
it away.

**Sector.** The ratios worth writing about differ by business model, and `model.json`'s
`sector_profile` block says which ones this company's profile suppressed and which to
lead with. Do not write around a suppressed metric — it is blank because it is
meaningless here, not because the data was missing. `reference/sectors.md` has the
reasoning per archetype.

**Forbidden.** "Robust", "healthy", "strong" as standalone verdicts; "poised to
capitalise"; "going forward"; any market-size number without a source; any percentage
without a base period; the phrase "as per our estimates" where no estimate was made.

---

## Part 3 — Two pieces of primary research that separate a real note

Both come out of documents the user has already supplied. Neither is in any data
export, and skipping them is what makes a report read like a summary of Screener.

### 3a. Guidance vs delivery scorecard

Pull management's own forward statements from concalls and presentations **two to
three years old**, then score them against what was actually reported. One row per
promise:

| Guided | When | What was said | Actual | Delivered? |
|---|---|---|---|---|
| FY25 EBITDA margin | Q3FY23 concall | "we see 24–25% exiting FY25" | 24.7% | Yes |
| Capacity by FY25 | FY23 annual report | 16 lakh units | 14 lakh | No — 12 months late |

Then state the hit rate, and use it explicitly when you weight current guidance. A
management team that has hit 8 of 10 commitments earns a different discount rate to
the thesis than one that has hit 3. This is the single strongest evidence available
on management quality, and almost no student report contains it.

Write it as: "Management has delivered on 7 of 9 quantified commitments since FY22;
the two misses were both capacity timelines, slipping an average of three quarters.
We therefore treat the FY28 volume guidance as credible on level and optimistic on
timing."

### 3b. Capital allocation track record

Where has every rupee of operating cash gone over ten years? Build the split from the
cash-flow statement: capex, acquisitions, dividends, buybacks, debt repayment,
treasury build. Then judge it against the returns actually earned — this is what
`ROIIC` in `model.json` is for.

Say what the record shows: a company compounding cash into 9% ROIIC projects while
holding 30% of its balance sheet in treasury has a capital-allocation problem, and
that belongs in the verdict, not buried in the cash-flow page.

Name the specific decisions. "The FY21 acquisition of X for INR 900 Cr has contributed
INR 40 Cr of EBIT against a INR 210 Cr cost of capital charge" is analysis. "Capital
allocation has been prudent" is not.

---

## Part 4 — Writing up the quantitative screens

`model.py` emits Altman Z, Piotroski F and the accrual screens. They are inputs to
an argument, never the argument.

**Piotroski F-score.** Report as `score/out_of` and name the failed tests. A 7/9 with
the two failures in leverage means something different to a 7/9 failing on margin and
turnover. Never print the score alone.

**Altman Z.** Two variants are emitted and they are not interchangeable:

- `score` / `latest` — the **Z' book-equity** series, consistent across all ten years.
  This is the one to chart, because the trend is comparable year to year.
- `market` — the **market-equity Z**, latest period only, with its own cut-offs.

Quote the *zone* (safe / grey / distress), not the raw number, whenever the model
notes that X4 is extreme. For a debt-free company X4 explodes and Z becomes a
statement about leverage, not about operating risk — the model says so in `notes`,
and repeating a Z of 25 as if it measured business quality is a category error.

Both scores are computed off Screener's aggregated balance-sheet buckets. The model
flags this. Reconcile working capital and total liabilities against the annual report
before either number goes in the text.

**When the screens disagree with the story, that is the finding.** A company with a
9/9 F-score and deteriorating cash conversion is more interesting than either fact
alone. Lead with the tension.

---

## Part 5 — Common failure modes

| Symptom | Cause | Fix |
|---|---|---|
| Ratios look wrong in early years | Screener's first column is often partial-year | Drop the first period from ratio tables |
| ROE spikes to absurd levels | Equity near zero, or you used closing not average equity | `model.py` uses averages — check you did not override |
| Payable days look off | Screener export lacks Trade Payables; the model approximates | Pull payables from the annual report, patch the JSON |
| DCF value 3–5× the market price | Terminal growth too close to WACC, or margins held at peak forever | Check `TV as % of EV`; fade margins toward the 10-yr median |
| Charts render as blank boxes | SVG path is wrong relative to the HTML file | Paths are relative to `report.html`, not to `scripts/` |
| PDF has 60+ pages | Sections overflowing their page | Cut body text, not font size |
| Text overflows the page bottom | Too much prose per section | The blueprint's word counts are limits, not targets |
