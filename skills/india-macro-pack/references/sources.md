# Sources — who is authoritative, and where each figure actually lives

Read this before entering any figure by hand. `scripts/registry.py` holds the same
information in machine-readable form; this file explains the reasoning that the code
can only encode.

## The house rule on authority

When two sources disagree, this order decides which one the report cites:

| Figure type | Cite | Never cite instead |
|---|---|---|
| India GDP, GVA, CPI, WPI, IIP, per-capita income — **actuals** | MoSPI / NSO | IMF or World Bank estimates of the same year |
| Policy repo rate, G-sec yields, INR, credit growth, forex reserves, BoP | RBI | a broker note or newspaper repeat |
| Global GDP and inflation, and **forward years** for India | IMF WEO, with the edition month | last year's WEO |
| Union fiscal deficit | Budget documents / CGA, with BE/RE/Actual stated | a summary article |
| Industry volumes and market size | the industry body itself | a consultancy repeating the body |
| Anything | — | World Bank, which here is a **cross-check only** |

The distinction that matters most in practice: **NSO says what happened, IMF says what
is forecast.** They will not agree on the overlapping year and are not supposed to.
Quoting IMF's figure for a year the NSO has already printed makes the report look like
it has not read the national accounts. `build_pack.py` puts both in §2 of the pack with
a sentence saying which is which — keep that distinction in the report prose.

World Bank appears in the pack under a heading that says "not for citation". Its job is
to catch a mirror serving corrupted data: if WB and IMF disagree on India by more than
1pp for the same year, something is wrong and the pack says so. It never reaches the
report.

## Why IMF data arrives through a mirror

`imf.org` returns **HTTP 403 to every programmatic client, across the whole domain** —
the DataMapper API, the WEO landing pages, all of it. Verified with both `curl` and a
fetch tool, with and without a browser user-agent. This is not a transient outage and
retrying differently will not fix it.

The route that works is **DBnomics** (`api.db.nomics.world`), which republishes IMF WEO
with the vintage preserved in the dataset code:

```
IMF/WEO:<vintage>/<ISO3>.<SUBJECT>          countries, e.g. WEO:2025-04/IND.NGDP_RPCH
IMF/WEOAGG:<vintage>/<group>.<SUBJECT>      aggregates, e.g. WEOAGG:2025-04/001.NGDP_RPCH
```

Two dimension-filtered requests fetch the entire global block. Aggregate group codes:
`001` World, `110` Advanced economies, `200` Emerging market and developing economies,
`163` Euro area.

**The mirror lags the IMF.** When this skill was built (August 2026) DBnomics' newest
vintage was `2025-04` while `2026-04` had long been published. That is precisely how a
year-old growth forecast gets into five reports without anyone noticing, so
`fetch_macro.py` computes the edition that *should* exist for today's date and refuses
to write anything older. The refusal routes those figures to the manual worksheet with
the imf.org URL. `--accept-vintage` overrides it, and then every single figure carries
`stale_override` so `audit_macro.py` names them one by one.

## The IMF fiscal-year trap

**IMF WEO reports India on a fiscal-year basis, labelled by the year the fiscal year
starts.** Every other country in the database is calendar year.

| WEO period | Indian fiscal year | Written in the report as |
|---|---|---|
| 2025 | April 2025 – March 2026 | FY26 |
| 2026 | April 2026 – March 2027 | FY27 |
| 2027 | April 2027 – March 2028 | FY28 |

A WEO year copied straight into an Indian report reads one year early, and the error is
invisible — the number is plausible either way. `registry.weo_year_to_fy()` does the
conversion and the generated pack prints the FY label alongside every India WEO figure.
Write the FY label in the report; never the bare WEO year.

The same convention governs manual entry: an Indian fiscal year is recorded by its
**end** month. FY26 is `2026-03`. A bare `2026` means 31 December 2026, and
`build_pack.py` refuses it as a future period.

## Freshness — why the windows differ per figure

`kb.py` applies one blanket rule: macro.json is stale 90 days after it was written.
That is a reasonable outer guard and this skill does not fight it. But 90 days is
simultaneously far too long for a 10-year yield and too short for per-capita income,
so each figure additionally carries a class:

| Class | Window | Applies to | Reasoning |
|---|---|---|---|
| `market` | 7d | 10Y G-sec, USD/INR, Brent | move continuously; a month-old yield is simply a different number |
| `policy` | 75d | repo rate | constant *between* MPC meetings, which are ~2 months apart |
| `weekly` | 14d | forex reserves, bank credit | RBI Weekly Statistical Supplement |
| `monthly` | 45d | CPI, WPI, IIP | one print per month |
| `quarterly` | 100d | quarterly GDP, current account | one print per quarter |
| `annual` | 400d | FY actuals, per-capita, fiscal deficit | one print per year, plus slack for revisions |
| `weo` | 250d | IMF forecasts | editions are six months apart; the vintage gate is the real control |
| `industry` | 200d | volumes, market size | bodies publish on their own schedules |

**Publication lag is added on top.** IIP is released about 40 days after the month it
covers, so the freshest IIP that exists is already 40 days old; a flat 45-day rule would
reject nearly every one of them. The effective limit is `window + lag`, and the lag is
recorded per figure. This is the difference between a figure being stale and a figure
being as current as the statistical system permits — they look identical from the age
alone, and conflating them either blocks good data or admits bad data.

Ages are measured from the **end** of the observation period. June 2026 CPI ages from
30 June, not 1 June.

## Per-figure recipes

`scripts/registry.py` carries, for every India figure: the owning agency, the URL, the
page and table to open, the exact field name to read, the citation format, the freshness
class and the publication lag. `fetch_macro.py` prints all of it as a worksheet on every
run, so there is no need to duplicate the table here — run:

```bash
python3 scripts/fetch_macro.py --worksheet-only
```

That prints the complete list without touching the network. It is the fastest way to see
what a full pack requires.

## Adding a figure

Add a `Fig(...)` to `INDIA_FIGURES` in `registry.py`. The validator refuses an entry with
no `fallback` instruction or no `cite` format, and refuses a key longer than 28
characters because `kb.py brief` truncates its column there.

Do not invent keys in `manual.json` — `build_pack.py` rejects unknown keys deliberately.
Two spellings of one figure fragment the shared store in `reports/_knowledge/`, and then
`kb.py brief` stops recalling it, which quietly removes the whole point of the knowledge
base.
