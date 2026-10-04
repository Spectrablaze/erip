---
name: peer-comps
description: Build a defensible peer comparables table for a listed Indian company from Screener exports - P/E, EV/EBITDA, EV/Sales, P/B and ROE for the subject and 3-5 peers, with the peer median, the subject's premium/discount, relative-valuation bands for a football-field chart, and optional peer betas for the WACC. This skill should be used when the user asks for comps, a comparables table, relative valuation, trading multiples, how a company is valued against its peers, peer betas, or asks to fill the peers block of a research model.
---

# Peer comparables

Turns one Screener export per company into a comps table that survives being argued
with, and into the exact inputs three downstream consumers expect: the `peers` array
`model.py`'s `relative()` reads, the `peer_betas` block its WACC build-up unlevers, and
the relative-valuation bands `charts.football_field` plots.

The arithmetic is trivial. The comparability is the work, and that is what this skill
mostly does: it refuses a set that mixes reporting bases, flags fiscal calendars that do
not line up, keeps undefined multiples out of the median, and stamps every number with
the period it came from.

## What it produces

| File | Contents |
|---|---|
| `peers_raw.json` | per company: basis, fiscal year end, trailing window, P&L and balance-sheet inputs, price series — every figure labelled with its period |
| `peers.json` | the model-ready `peers` array (subject first), full detail, medians and quartiles, comparability flags, football-field bands, forward table |
| `peer_betas.json` | regression beta, market D/E, observation count, R², window |
| `comps.md` | the exhibit — comps table, comparability section, provenance, EV bridge, bands |
| `market.json` | *optional* — Yahoo prices, daily history and a second source to cross-check against |

## Before starting

Confirm four things with the user. Do not guess any of them.

1. **The peer set** — 3 to 5 companies. Check `kb.py sector` first; the
   `equity-research-report` skill stores a peer list per sector from past reports, so the
   set may already exist. Otherwise use web search to propose candidates — listed
   competitors of comparable size and business model — and put the shortlist to the user
   with a one-line rationale each. Proposing peers is a judgement call and belongs to the
   user; searching for candidates is not. Fewer than 3 peers makes a median meaningless.
2. **The basis** — consolidated or standalone, matching the subject. Every export must be
   downloaded from the same Screener view.
3. **The cover date** — multiples move daily, and the whole table is struck on one date.
4. **Whether forward estimates exist.** They are optional and never computed here.

Then request one **Screener "Export to Excel"** per company, subject included, all on the
same basis. Nothing else is needed — no scraping, no price feed. A price scrape alone
would be insufficient anyway, because EV needs each peer's balance sheet.

## Workflow

### 0. Market data (optional, recommended)

```bash
python3 scripts/market_data.py peers_manifest.json -o data/market.json --as-of 2026-07-31
```

Needs `yfinance` (`pip install yfinance`) and network. Everything below works without it.

It does three jobs, and understanding why it does not do a fourth is the point:

- **Prices** — the cover-date close for every company at once, so the set is priced on
  one day without typing five numbers.
- **Daily price history and the index** — a far better beta than the monthly Screener
  block, and it removes the manual NIFTY CSV download.
- **A second source to disagree with the exports** — market cap, revenue and net debt,
  compared automatically in step 4.

**It is not a substitute for the exports.** Yahoo does not state whether its figures are
consolidated or standalone, which is the one check this skill treats as a hard error. Its
"EBITDA" is not the reported operating profit either — for Eicher Motors it reads ~35% of
revenue against a reported ~26%, because it sweeps in other income. That figure is
carried for reference and deliberately never cross-checked, because flagging a
definitional difference as a variance just teaches the reader to ignore flags.

Tickers default to `<TICKER>.NS`; set `yahoo` in the manifest for anything else.

### 1. Write the manifest

Copy `assets/peers_manifest_template.json` and fill it in — one entry per company, the
subject named by `subject`. Read the `_readme` block in that file; it explains `price`,
`surplus_investments` and `forward`, which are the three fields that are easy to get
wrong.

Supply `price` for every company, as the close on the cover date. If left null the
export's own price block is used and the mismatch is flagged, but then the table is not
struck on one date.

### 2. Ingest

```bash
python3 scripts/peer_ingest.py peers_manifest.json --market data/market.json -o data/peers_raw.json
```

Drop `--market` if step 0 was skipped. Price precedence is: what the analyst typed in the
manifest, then the market feed, then the export's own price block — the export is last
because it is the only one of the three that cannot be struck on the cover date.

Reads each export through `parse_screener.py` from the `equity-research-report` skill —
found automatically, or pass `--parser`. It is **not** copied into this skill, so learned
Screener aliases keep applying; see `references/integration.md`.

This step **hard-errors**, rather than warning, on:

- a reporting basis that disagrees with the manifest (read from the export header)
- forward estimates supplied without `source` and `as_of`

Read the per-company warnings before continuing. A company that fell back to a full year
instead of TTM, or that could not be priced, will distort the table.

### 3. Betas (optional)

```bash
python3 scripts/peer_beta.py data/peers_raw.json --market data/market.json -o data/peer_betas.json
```

With `--market`, daily log returns against the index already fetched — the better option.
Without it, pass `--index <csv>` (a NIFTY 50 export from the NSE historical-data page,
`Date` and `Close` columns) for a monthly regression, which is all the Screener price
block supports.

Minimum observations scale with frequency — 120 daily, 24 monthly — and below that no
beta is emitted at all rather than a number nobody should use. Thin windows and low R²
are flagged. Skip this step entirely if the WACC beta comes from elsewhere.

### 4. Build

```bash
python3 scripts/build_comps.py data/peers_raw.json -o data/peers.json --md data/comps.md --betas data/peer_betas.json --patch-decisions data/decisions.json
```

`--patch-decisions` writes `peers` and `peer_betas` into an existing `decisions.json` at
**top level** and keeps a `.bak`. Placed inside `assumptions` they are silently dropped.
Rebuild `assumptions.json` with `build_assumptions.py` afterwards — never hand-edit it.

Useful flags: `--sector financials` suppresses EV multiples (interest is revenue for a
bank, so EV/EBITDA has no interpretation); `--roe closing`; `--nm-policy keep` to leave
undefined multiples in the downstream median, which is almost never right.

`--strategy <model_strategy.json>` binds the output to an approved modeling strategy:
any multiple it ruled `NOT_APPROPRIATE` gets no relative-valuation band, and the
reason is carried in the warnings. The comps **table** is unchanged — every
computable multiple still appears, because withholding a number the reader can work
out themselves looks like concealment. What is withheld is the band, which is a claim
that the multiple values this business. The flag is optional; without it every
computable band is emitted, as before.

### 5. Read the flags before writing anything

`comps.md` has a **Comparability** section. Every flag there is a sentence that belongs
in the report. Do not paste the table without them.

| Flag | What it means |
|---|---|
| `fiscal_year_misalignment` | HIGH. Peers close in different months, so book value and net debt are measured months apart. Say so; the skill will not align them, because that would mean inventing a balance sheet. |
| `mixed_trailing_basis` | HIGH. Some companies on TTM, others on the last full year — the latter are up to four quarters stale. |
| `trailing_window_misalignment` | Twelve-month windows ending on different dates. |
| `not_meaningful` | Denominator ≤ 0. Already excluded from the median and printed `nm`. |
| `outlier` | A valid but extreme multiple, **kept** in the median. Decide whether the peer is genuinely comparable; if not, remove it from the manifest and rerun. |
| `unverified_basis` | The export header did not state the basis, so the manifest's declaration was trusted. |
| `price_date_mismatch` | Not every company was priced on the cover date. |
| `crosscheck` | The export and the market feed disagree beyond tolerance. Runs automatically when step 0 was used; `--no-crosscheck` disables it. |

**Reading a `crosscheck` flag.** It means two sources disagree, not that the export is
wrong — the export is still the record. Tolerances are loose on purpose (3% market cap,
10% revenue, 25% net debt), because the two sources have different definitions and
different as-of dates, and a tight threshold would flag everything and train you to
ignore flags. What each one usually means:

- **market cap** — both sides use the same price, so this is a *share count*
  disagreement. Check for a bonus issue or split the export predates.
- **revenue** — some gap is expected (the export is TTM, the feed is the last full
  year). A large one usually means the wrong ticker, or a standalone/consolidated
  mismatch the export header did not catch.
- **net debt** — the loosest check, because the two define cash differently. Worth a
  look, rarely worth acting on alone.

## The decisions this skill has already made

State these when presenting results; they are the questions a reader will ask.

- **Trailing multiples are computed; forward multiples are never computed.** A Screener
  export does not carry consensus estimates. Analyst-supplied forward figures require a
  source and a date, are reported in a separate table marked unverified, and are never
  blended into the trailing median.
- **TTM where possible, last full year otherwise.** TTM largely neutralises fiscal-year
  differences in the P&L. It cannot help the balance sheet, which has no quarterly
  equivalent in the export — hence the fiscal-year flag.
- **Median, not mean.** A five-company set cannot absorb an outlier in a mean.
- **One ROE convention for everyone** — PAT / average net worth, falling back to closing
  for the whole set if any company lacks a prior year. It will not tie to Screener's own
  ROE; internal consistency matters more.
- **Only explicitly declared surplus investments are netted from EV.** Screener's
  `Investments` line mixes surplus liquidity with strategic stakes.
- **Consolidated EV carries no minority interest** unless supplied — Screener does not
  export it.

`references/multiples.md` has the reasoning, the full EV bridge, and the Screener-specific
traps. Read it before overriding any of the above.

## Feeding the report

```python
import json, charts
pc = json.load(open("data/peers.json"))
methods = pc["football_field"] + [
    {"label": "DCF (bear-bull)", "low": ..., "high": ..., "mid": ...},
    {"label": "52-week range",   "low": ..., "high": ...},
]
charts.football_field("val_football", methods, current_price=cmp_)
```

`peers.json` also drives `charts.scatter_peers` — ROE vs P/B, with the subject as
`highlight`, is the standard exhibit. Never pass `title=` to a chart; titles go in the
HTML.

In the `equity-research-report` phase table this is **Phase 3** work, and Phase 1's
document request must include the peer exports or Phase 3 stalls. Write the confirmed
peer set back in Phase 8 with `kb.py sector --peers`. Full handoff detail, including the
`model.py` contract, is in `references/integration.md`.

## Troubleshooting

**`could not find parse_screener.py`** — pass `--parser <path>`, or set `EQR_SKILL` to
the `equity-research-report` skill directory. Do not copy the parser here.

**A peer's multiples are all null** — the share count was not found, so market cap could
not be struck. Check the export has an `Adjusted Equity Shares in Cr` row in the balance
sheet block.

**No betas emitted** — the index and the price series do not overlap. With `--index`,
check the CSV's date range and that its columns are named `Date` and `Close`. With
`--market`, check the ticker mapping resolved (a company in the Screener set but absent
from the feed is reported by name).

**`no price history for X.NS`** — wrong Yahoo symbol. NSE takes `.NS`, BSE takes `.BO`;
set `yahoo` in the manifest to override. Some smaller names are simply not on Yahoo, in
which case supply `price` by hand and let the cross-check skip that company.

**Every company throws a `crosscheck` revenue flag** — usually one cause, not many: the
exports are standalone and the feed is consolidated (or the reverse). Check the export
headers before touching anything else.

**The median in `comps.md` disagrees with `model.py`'s table** — the emitted array and
`relative()` have drifted. `build_comps.py` computes the statistics independently of
`model.py` precisely so that this is visible; investigate rather than picking one.
