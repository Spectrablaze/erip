# Multiples, and where they lie

Everything here is about getting a comps table that survives being argued with. The
arithmetic is trivial; the comparability is the work.

## The one rule

A comps table compares **one basis, one date, one convention**. Any table that mixes
those is not a valuation exhibit, it is a coincidence. `build_comps.py` enforces the
basis, flags the dates and applies one convention to everyone — but it cannot know that
a company is in a different business, and that is the judgement the analyst still owes.

## What each multiple is for

| Multiple | Reads through | Breaks when |
|---|---|---|
| **P/E** | the whole capital structure to the equity holder | earnings are negative, one-off, or geared very differently across the set |
| **EV/EBITDA** | capital structure and depreciation policy | capex intensity differs (EBITDA flatters the asset-heavy peer), or leases are capitalised inconsistently |
| **EV/Sales** | everything below the top line | margins differ — it is a growth/margin proxy, not a valuation, and only earns its place when earnings are not meaningful |
| **P/B** | accumulated book equity | intangible-heavy or buyback-heavy companies, where book value stops meaning anything |
| **ROE** | not a multiple — the thing that *justifies* a P/B | leverage differs; a high ROE on high gearing is not the same quality as one on net cash |

Pair P/B with ROE always. A peer on 2x book at 8% ROE and one on 4x book at 25% ROE are
not evidence of a premium — they are evidence the market can do arithmetic.

## The enterprise value bridge from a Screener export

```
EV = market cap
   + borrowings
   - cash & bank
   - surplus investments      (only the explicitly declared part)
   + minority interest        (manifest only — Screener does not export it)
   + preference capital       (manifest only)
```

Four things about this that are specific to Screener and easy to get wrong:

**1. `Investments` is not cash.** Screener's balance-sheet `Investments` line mixes
genuinely surplus liquid investments with strategic stakes, subsidiary carrying values
and long-dated instruments. Netting the whole line out of EV understates EV, sometimes
enormously. Nothing from it is netted unless `surplus_investments` is set explicitly in
the manifest, and the value for that comes from the annual report's investment
schedule, not from the export. The skill notes any company where a non-zero
`Investments` line was left un-netted.

**2. Consolidated EV has no minority interest in it.** Screener does not export minority
interest, so a consolidated EV built from the export understates EV for any company with
materially non-wholly-owned subsidiaries — you are counting 100% of the EBITDA against
less than 100% of the claims. Pull it from the balance sheet and set
`minority_interest`. The skill flags every consolidated company where this is zero.

**3. Screener carries no trade payables.** This does not affect EV, but it does mean the
export cannot be used to check a peer's working capital, and DPO reads as zero. Do not
try to build a peer working-capital comparison from these files.

**4. Net debt is struck at the balance sheet date, market cap is struck today.** They are
months apart. That is normal practice and not worth correcting, but it is worth knowing
before defending a 0.3x difference in EV/EBITDA.

## Consolidated vs standalone

Never mixed — this is a hard error, not a flag. Screener states the basis in the export
header (`Consolidated Figures in Rs. Crores`), and `peer_ingest.py` reads it and refuses
a set that disagrees. When the header does not state it, the declared basis is used and
the company is flagged `unverified_basis`.

Match the **subject's** basis. If the subject reports consolidated, download every peer
consolidated, even where the peer has no subsidiaries and the two are identical.

## Fiscal calendars and the trailing window

Indian companies do not all close in March. The skill handles this in two distinct places
and it is worth knowing which is which:

- **The P&L** is taken as TTM — the last four reported quarters — whenever four
  consecutive quarters exist. TTM largely neutralises fiscal-year differences, because
  it is a rolling twelve months rather than a fiscal year. Where fewer than four
  quarters exist, the last full year is used instead and the company is flagged as
  stale relative to the rest.
- **The balance sheet** has no quarterly equivalent in the export, so book value and net
  debt are as of each company's own year end. A March-year and a December-year peer are
  measured nine months apart, and that flows into P/B and into EV.

Both misalignments are flagged, never corrected. Aligning them silently would require
interpolating a balance sheet, which is a fabrication. Say it in the report instead: *"Gamma
Auto reports to December; its book value is measured nine months before the rest of the
set."* That sentence costs nothing and is the difference between a defensible table and
a wrong one.

## Not meaningful, and outliers

Two different problems:

- **Not meaningful (`nm`)** — the denominator is zero or negative. A negative P/E is not
  a cheap stock, it is an undefined ratio. These are excluded from the median (the
  emitted `peers` array carries `null` for that denominator so the downstream median
  skips it) and printed as `nm`.
- **Outlier** — the multiple is arithmetically valid but far from the set. A peer whose
  EBITDA has collapsed to near zero prints an EV/EBITDA of 90x that is technically fine
  and analytically useless. These are **kept** in the median and flagged, because the
  decision to drop a peer belongs to the analyst, not the script. If the peer is not
  genuinely comparable, remove it from the manifest and rerun.

The median is used throughout rather than the mean, precisely because a small comp set
cannot absorb an outlier in a mean.

## ROE convention

Computed as PAT / average net worth, using the same convention for every company in the
set. Where any company lacks a prior year, the whole set falls back to closing net
worth — a table where one company is on average equity and the rest on closing is worse
than a table that is uniformly on the cruder measure.

This will not tie to Screener's own displayed ROE, which uses a different convention.
That is expected; internal consistency beats agreement with a screen.

## Banks, NBFCs and insurers

EV-based multiples are suppressed for financials. For a bank, interest is revenue and
debt is raw material, so "net debt" has no meaning and EV/EBITDA has no interpretation.
Compare on P/E, P/B and ROE, and note that the wider `equity-research-report` skill
blocks the `financials` sector outright for DCF purposes.

## Forward multiples

The exports do not carry consensus estimates, so nothing forward is ever computed here.
The manifest's `forward` block accepts analyst-supplied figures and:

- requires `source` and `as_of` on any populated block, or ingestion fails
- reports coverage (`3 of 5 peers`) — a forward median over half the set is thin
- computes forward EV multiples against **today's** net debt, because forward net debt
  is not estimated; this understates leverage for a deleveraging company
- is rendered in a separate table, marked unverified, and never blended into the
  trailing median

If a forward band ends up in the report's football field, it must be labelled as
consensus-derived, not as this skill's output.

## Peer betas

Emitted for `model.py`'s Hamada relever, which unlevers each peer's beta, takes the
median, and relevers at the subject's target structure.

- **Monthly, not daily.** The Screener price block is collapsed to one observation per
  calendar month, so monthly is the finest frequency the data supports. A daily beta
  from this file would be false precision.
- **Minimum 24 monthly returns**, below which no beta is emitted at all. Below 36 it is
  emitted and flagged as thin.
- **R-squared is reported.** A beta with R² near zero means the index does not explain
  the stock; the number is arithmetically real and analytically empty.
- **D/E is market-value based** — net debt over market cap by default, matching the EV
  bridge. Net cash floors D/E at zero, so the unlevered beta equals the levered beta
  rather than exceeding it. Use `--debt gross` for the textbook Hamada treatment.

A median of fewer than three usable peer betas is barely more robust than the single
regression beta it replaces, and the script says so.
