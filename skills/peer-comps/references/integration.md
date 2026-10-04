# How peer-comps fits the rest of the pipeline

This skill sits beside `financial-model-assumptions` and feeds three consumers in
`equity-research-report`. It owns the comps table and nothing else — it does not value
the company, and it does not decide who the peers are.

```
Screener exports (subject + 3-5 peers)        Yahoo (optional second source)
        |                                              |
        |                                        market_data.py
        |                                              |
        |                                        market.json
        |                                       (prices, daily history,
        |                                        index, cross-check feed)
        |                                              |
   peer_ingest.py ---- parse_screener.py               |
        |     ^        (equity-research-report,        |
        |     |         NOT copied)         <----------+  prices
        |     +-- reports/_knowledge/aliases.json  (learned aliases)
        v
   peers_raw.json ----> peer_beta.py ----> peer_betas.json
        |                 ^      ^                     |
        |     index CSV --+      +-- market.json       |
        |     (monthly)              (daily, better)   |
        |                                              |
        +---------------> build_comps.py <-------------+
                               |
                     (cross-check runs here,
                      on market data carried
                      inside peers_raw.json)
        +----------------------+----------------------+------------------+
        v                      v                      v                  v
    peers.json           decisions.json          comps.md         football_field
   (peers array)      (peers, peer_betas)      (the exhibit)         (bands)
        |                      |                                        |
        |              build_assumptions.py                             |
        |                      v                                        |
        |               assumptions.json                                |
        +----------------------+----------------------------------------+
                               v
                    model.py  relative() + WACC        charts.py  football_field()
```

## The parser is shared, deliberately

`peer_ingest.py` imports `parse_screener.py` from the `equity-research-report` skill
rather than carrying a copy. This is load-bearing:

- Screener aliases learned via `kb.py alias` live in `reports/_knowledge/aliases.json`
  and are applied by that parser. A copy here would not benefit, so a label that broke
  the parser once would keep breaking it in comps only.
- The equity-research-report skill already exists in three copies that must be synced by
  hand. A fourth copy of its parser is a fourth place for a fix to fail to land.

Resolution order: `--parser` → `$EQR_SKILL/scripts/parse_screener.py` → sibling skill
directory → `~/.claude/skills/...` → `./.claude/skills/...`. If none resolve the script
exits with the list of paths it tried.

**One exception.** The share price series is read directly from the workbook by
`peer_ingest.py`, not through the shared parser. `parse_screener.py`'s block reader stops
at any row whose label matches its own block markers, and `Price` is one of them, so the
price rows are dropped before they reach the caller. Only the price series is read
locally; the financial statements still come from the shared parser. Both layouts
Screener has shipped are handled — dates across a header row, and a Date/Price column
pair running down the sheet.

## The second source, and its boundaries

`market_data.py` is optional and additive. With it absent, every other script behaves
exactly as it did before it existed — verified by running both paths against the same
fixtures and getting identical betas, medians and premium/discount.

What it is allowed to do:

- **supply prices**, because a closing price is mechanical and unambiguous
- **supply daily history**, because the regression is strictly better for it
- **disagree**, which is the only reason to have a second source at all

What it is *not* allowed to do, and why:

- **It never supplies a comps input.** Sales, EBITDA, PAT, book value and share count
  come from the export or not at all.
- **It cannot establish the reporting basis.** Yahoo does not label consolidated versus
  standalone. That is the check this skill treats as a hard error, and only the export
  header can answer it.
- **Its EBITDA is never cross-checked.** Yahoo's definition includes other income; for
  Eicher Motors it reports ~35% of revenue against a reported ~26%. Flagging a
  definitional difference as a variance produces a flag that is always on, and a flag
  that is always on is noise.

The cross-check tolerances (3% market cap, 10% revenue, 25% net debt) live in
`build_comps.TOL`. They are set to catch "wrong ticker, wrong company, wrong basis", not
"rounded differently". Market cap is the tight one because both sides use the same
price, which makes it a pure share-count test.

Market data travels inside `peers_raw.json` (each company's `market` block) rather than
being re-read at build time, so `peers.json` is reproducible from `peers_raw.json` alone
with no network.

## Into `decisions.json`

`build_comps.py --patch-decisions <path>` writes two keys and keeps a `.bak`:

```json
{
  "peers":      [ {"name": "...", "price": 0, "mcap": 0, "ev": 0, "sales": 0,
                   "ebitda": 0, "pat": 0, "bv": 0, "roe": 0}, ... ],
  "peer_betas": [ {"name": "...", "beta": 1.02, "debt_equity": 0.13}, ... ]
}
```

Both are **top level**, beside `assumptions`, never inside it. `build_assumptions.py`
passes exactly the top-level settings through to `assumptions.json`; a `peers` block
placed inside `assumptions` is silently dropped and the report loses its relative
valuation with no error.

After patching, rebuild `assumptions.json` through `build_assumptions.py`. Never hand-edit
`assumptions.json` — it is generated, and the next rebuild discards the edit.

## Into `model.py`

Two independent consumers of the patched keys:

- **`relative(A["peers"])`** builds the comps table. It expects the **subject first** and
  computes its own median and premium/discount rows. `build_comps.py` guarantees the
  ordering and computes the same statistics independently — the two agreeing is the
  cross-check that the handoff is intact. If they ever disagree, the emitted array and
  `relative()` have drifted apart.
- **`peer_betas`** is unlevered (Hamada), medianed, and relevered at
  `target_debt_weight`, replacing the input beta in the WACC build-up. Entries missing
  either `beta` or `debt_equity` are skipped by `model.py`, and it falls back to the
  input beta if none survive. `build_comps.py` only writes entries that have both.

`relative()` divides straight into the fields it is given, and its median skips `None`.
That is why a non-positive denominator is emitted as `null` rather than as its raw
negative value — it is the only way to keep a loss-making peer out of the P/E median
without dropping the peer's other multiples too.

## Into the football field

`peers.json` carries a `football_field` array already in `charts.football_field`'s
shape — `{label, low, high, mid}`, in rupees per share, built from the peer 25th–75th
percentile multiple applied to the subject's own metric, with net debt bridged out for
the EV-based ones.

```python
import json, charts
pc = json.load(open("data/peers.json"))
methods = pc["football_field"] + [
    {"label": "DCF (bear-bull)", "low": ..., "high": ..., "mid": ...},
    {"label": "52-week range",   "low": ..., "high": ...},
]
charts.football_field("val_football", methods, current_price=cmp_)
```

Do not pass `title=` — titles belong in the HTML as `<div class="fig-title">`.

## Where this lands in the report workflow

In `equity-research-report`'s phase table this belongs in **Phase 3**, alongside the
model and the assumptions, and it depends on Phase 0 having settled the peer set:

- **Phase 0** proposes and confirms the peers with the user, and `kb.py sector` already
  stores a peer list per sector — start from that rather than from scratch.
- **Phase 1** must request the peer Screener exports in the document checklist, or
  Phase 3 stalls waiting for files nobody asked for.
- **Phase 3** runs this skill, patches `decisions.json`, rebuilds `assumptions.json`,
  and runs `model.py`.
- **Phase 5** consumes `football_field` and can also feed `scatter_peers` from
  `peers.json` (ROE vs P/B is the standard one, with the subject as `highlight`).
- **Phase 8** should write the confirmed peer set back with
  `kb.py sector --sector "<sector>" --peers "TICK1,TICK2,..."` so the next report in the
  sector starts warm.
