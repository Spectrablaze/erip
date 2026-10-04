# Sector profiles — why the same ratio pack does not fit every company

The ratio pack in `model.py` is, by default, a **manufacturer's** ratio pack. It assumes
a company that buys materials, holds stock, sells on credit and owns factories. Most
listed Indian companies are not that.

Run a software firm through it unfiltered and it reports `Inventory Days: 0` and a cash
conversion cycle resting on a line that does not exist. Run a bank through it and it
reports an interest coverage ratio — for a business whose interest *is* its revenue.

`scripts/sectors.py` fixes this by suppressing metrics that do not apply, naming the
ones that carry the argument, listing the figures to pull from the annual report, and
setting the valuation lens.

## Using it

Phase 0 establishes the sector. Pass it through:

```bash
python3 scripts/model.py data/financials.json data/assumptions.json \
        --sector "IT services" -o data/model.json
```

Or set `"sector": "IT services"` in `assumptions.json`. Free text is fine — `Two-wheelers`,
`Cement`, `Housing Finance` all resolve. Check what a label maps to:

```bash
python3 scripts/sectors.py --resolve "speciality chemicals"
python3 scripts/sectors.py --list
```

An unmatched sector falls back to `generic`: **nothing is suppressed**, and the model
says so. That is a prompt to check each metric yourself, not a clean bill of health.

`model.json` carries a `sector_profile` block recording what was suppressed and why.

## The archetypes

| Profile | Suppressed | Leads with | Valuation |
|---|---|---|---|
| `manufacturing` | — | gross margin, fixed-asset turn, inventory days, CCC, ROCE | FCFF DCF |
| `services` | gross margin, inventory days | EBITDA margin, DSO, CFO/PAT, ROIC | FCFF DCF |
| `consumer` | — | gross margin, inventory days, CCC, ROCE | FCFF DCF |
| `commodity` | — | EBITDA margin, net debt/EBITDA, ROCE | DCF on **mid-cycle** margins, EV/tonne |
| `realestate` | inventory days, CCC | net debt, coverage, ROCE | NAV first, DCF second |
| `financials` | **blocked** — 12 metrics | ROE, ROA | not modelled by this skill |

## What each profile is really saying

**`manufacturing`** — the template the rest is measured against. Growth must be
decomposed into volume, price and mix. Capacity utilisation caps the forecast.

**`services`** — the cost base is people, not materials, so there is no gross margin and
no stock. Margin analysis runs through utilisation, pyramid and wage inflation. ROIC is
structurally enormous because invested capital is tiny — the *level* is not the insight,
the reinvestment rate is. Working capital is the receivable cycle alone.

**`consumer`** — gross margin is the pricing-power signal; EBITDA margin nets off the A&P
the company chose to spend. Discuss both. A negative cash conversion cycle is a genuine
competitive advantage — the trade funds the working capital — so say so when it appears.

**`commodity`** — holding peak margins through the forecast is the classic error. Fade
EBIT margin toward the 10-year median and state the cycle position you assumed. P/E is
near useless at a trough or peak because earnings are the volatile term.

**`realestate`** — "inventory" is capitalised project cost, not stock, so the turnover
ratios are suppressed. Reported revenue lags cash: lead with pre-sales and collections.

**`financials` — not modelled, and blocked deliberately.** For a lender, interest is
revenue. EBITDA, net debt, every EV multiple and all coverage ratios are undefined, not
merely noisy. FCFF is invalid — the right tools are FCFE, excess return or a dividend
discount model. Altman Z was fitted on non-financial firms and is not reported. The
model suppresses the offending metrics and warns loudly; it does not attempt a bank.
Doing one properly needs NIM, cost-to-income, GNPA/NNPA, PCR, credit cost, CASA and CAR,
plus a different valuation engine. Do not force one through the manufacturing template —
the output will be confident and wrong.

## Adding a profile

Add an entry to `PROFILES` in `scripts/sectors.py` with `suppress`, `focus`,
`manual_inputs`, `valuation` and `notes`. Keys in `suppress` must match the metric names
`model.ratios()` emits exactly, or the suppression silently does nothing — check with
`sectors.py --show <key>` and confirm against a real `model.json`.

Then log it so the next report starts warm:

```bash
python3 scripts/kb.py --root reports sector --sector "speciality chemicals" \
    --note "profile added to sectors.py; leads on spreads not volumes"
```
