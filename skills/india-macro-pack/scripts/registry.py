#!/usr/bin/env python3
"""
registry.py -- the single source of truth for WHAT a macro pack contains.

Every other script in this skill imports this module. Nothing here fetches anything;
this is the vocabulary, the freshness policy and the fallback instructions.

THREE IDEAS WORTH UNDERSTANDING BEFORE EDITING
--------------------------------------------------------------------------------
1. A figure is stale by its OBSERVATION PERIOD, not by when it was written down.
   Recording April-2025 CPI today does not make it fresh. Every figure therefore
   carries `period` (what it observes) separately from `retrieved` (when it was
   pulled), and the audit tests `period`.

2. Every figure that cannot be fetched still has a complete recipe: the URL, the
   page, the table, and the exact field name to look for. A fetch failure must
   degrade to "go and read this" -- never to a carried-forward number. `fallback`
   is mandatory on every entry and the validator below enforces it.

3. Figure keys are stable across quarters. If one quarter writes `india_cpi` and
   the next writes `cpi_india`, the accumulated store in reports/_knowledge/
   fragments and kb.py's brief stops being a recall of the same thing.

A PERIOD IS A SPAN, AND INDIAN FISCAL YEARS END IN MARCH
--------------------------------------------------------------------------------
`days_old()` ages a period from its END: June 2026 CPI ages from 30 June, not 1 June.
Consequently an Indian fiscal year must be written with its END month -- FY26 is
'2026-03', not '2026'. A bare '2026' means 31 December 2026, which is in the future
for most of the year, and build_pack.py refuses future periods for exactly that
reason. IMF WEO figures are the one exception: they are forecasts, so observing a
future year is what they are for.

THE IMF FISCAL-YEAR TRAP
--------------------------------------------------------------------------------
IMF WEO reports India on a fiscal-year basis (April-March), labelled by the year
the fiscal year STARTS. So WEO period "2026" for India is FY2026-27, which Indian
sell-side calls FY27 -- one higher than a naive reading. Every other country in
WEO is calendar year. `weo_year_to_fy()` below does the conversion, and India
figures are labelled with both so a reader can never mistake which is meant.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

# --------------------------------------------------------------- freshness policy
# Max age of a figure's OBSERVATION PERIOD before it must not be used.
# Deliberately finer than kb.py's blanket 90 days: a 10Y yield 60 days old is
# probably wrong, an annual per-capita figure 60 days old is fine.
FRESHNESS_DAYS = {
    "market":    7,    # 10Y G-sec, INR, crude -- move continuously
    "policy":    75,   # repo rate: constant BETWEEN MPC meetings, which are ~2 months
    "weekly":    14,   # forex reserves, bank credit (RBI WSS)
    "monthly":   45,   # CPI, WPI, IIP, GST, PMI
    "quarterly": 100,  # quarterly GDP/GVA prints, current account
    "annual":    400,  # FY actuals, per-capita income, fiscal deficit
    "weo":       250,  # WEO editions are ~6 months apart; see vintage gate
    "industry":  200,  # industry-body volumes and market size
}

# Typical days between the END of the observation period and its publication.
# The effective limit is FRESHNESS_DAYS[cls] + lag. Without this, a figure could be
# refused for being older than its own release schedule allows it ever to be: IIP is
# published about 40 days after the month it covers, so the freshest IIP in existence
# is already ~40 days old and a flat 45-day rule would reject almost all of them.
DEFAULT_LAG = {"market": 0, "policy": 0, "weekly": 7, "monthly": 15,
               "quarterly": 60, "annual": 60, "weo": 0, "industry": 60}


def effective_limit(cls: str, lag: int | None = None) -> int:
    """Max acceptable age of an observation, allowing for its publication lag."""
    base = FRESHNESS_DAYS.get(cls, 90)
    return base + (DEFAULT_LAG.get(cls, 0) if lag is None else int(lag))

# WEO publishes twice a year, April and October. Allow a grace period after the
# nominal month before demanding the new edition -- the database drops mid-month.
WEO_GRACE_DAYS = 21


def expected_weo_vintage(today: date | None = None) -> str:
    """The newest WEO edition that should exist as of `today`, e.g. '2026-04'."""
    d = today or date.today()
    apr = date(d.year, 4, 1)
    oct_ = date(d.year, 10, 1)
    if (d - oct_).days >= WEO_GRACE_DAYS:
        return f"{d.year}-10"
    if (d - apr).days >= WEO_GRACE_DAYS:
        return f"{d.year}-04"
    return f"{d.year - 1}-10"


def weo_year_to_fy(weo_year: int) -> str:
    """WEO period year (India, fiscal basis) -> Indian FY label. 2026 -> 'FY27'."""
    return f"FY{str(weo_year + 1)[-2:]}"


def horizon_years(today: date | None = None) -> list[int]:
    """The three calendar years a report struck today shows: prior actual, current,
    next. Blueprint page 2 wants exactly this shape -- '2025A / 2026P / 2027P'."""
    y = (today or date.today()).year
    return [y - 1, y, y + 1]


# --------------------------------------------------------------- global block (fetched)
# DBnomics mirrors IMF WEO. imf.org itself is bot-blocked (HTTP 403 on the whole
# domain, verified), so the mirror is the only automated route -- and it lags, which
# is why fetch_macro.py gates on the vintage rather than trusting `latest`.
DBNOMICS = "https://api.db.nomics.world/v22"

# WEOAGG holds aggregates, WEO holds countries. Same subject codes, different
# dimension name for the geography -- that asymmetry is why they are fetched apart.
WEO_AGGREGATES = {
    "world":    ("001", "World"),
    "advanced": ("110", "Advanced economies"),
    "emde":     ("200", "Emerging market and developing economies"),
    "euro":     ("163", "Euro area"),
}
WEO_COUNTRIES = {
    "us":    ("USA", "United States"),
    "china": ("CHN", "China"),
    "japan": ("JPN", "Japan"),
    "india": ("IND", "India"),
}
# Order used on the blueprint page-2 chart, most-to-least aggregate.
GLOBAL_CHART_ORDER = ["world", "advanced", "emde", "us", "euro", "china", "japan", "india"]

WEO_SUBJECTS = {
    "gdp":       ("NGDP_RPCH", "Real GDP growth", "%"),
    "cpi":       ("PCPIPCH", "Inflation, average consumer prices", "%"),
    "gdp_usd":   ("NGDPD", "GDP, current prices", "USD bn"),
    "gdp_pc":    ("NGDPDPC", "GDP per capita, current prices", "USD"),
    "cad":       ("BCA_NGDPD", "Current account balance", "% of GDP"),
    "govt_debt": ("GGXWDG_NGDP", "General government gross debt", "% of GDP"),
}
# GDP growth is fetched for every geography -- that is the page-2 chart.
# CPI is fetched only where the report actually cites it. Pulling CPI for all eight
# would add a dozen figures nothing quotes, and `kb.py brief` prints every figure it
# holds: an over-full brief stops being read, which defeats the point of Phase 0.
GLOBAL_SUBJECTS = ["gdp", "cpi"]
CPI_GEOS = ["world", "advanced", "emde", "india"]
INDIA_EXTRA_SUBJECTS = ["gdp_usd", "gdp_pc", "cad", "govt_debt"]

WEO_MANUAL_URL = "https://www.imf.org/en/Publications/WEO/weo-database"
WEO_FALLBACK = (
    "Open the WEO database ({url}), select 'By Countries', pick the geography, tick "
    "the subject, and read the row for the year wanted. Cite as 'IMF WEO, <Month Year>'. "
    "Remember India is on a FISCAL year basis -- WEO year Y is FY(Y+1)."
).format(url=WEO_MANUAL_URL)


def global_key(geo: str, subject: str, year: int) -> str:
    """Canonical key for a fetched WEO figure. e.g. gdp_world_2026, cpi_india_2027."""
    return f"{subject}_{geo}_{year}"


# --------------------------------------------------------------- India block (manual)
# Every entry: what it is, who owns it, where exactly to read it, how to cite it,
# and how fast it goes off. `fallback` is the instruction printed when nothing can
# be fetched -- it is the whole safety net, so it must be specific enough to act on.
class Fig(dict):
    def __init__(self, key, label, unit, cls, owner, url, fallback, cite, note="",
                 lag=None):
        super().__init__(key=key, label=label, unit=unit, cls=cls, owner=owner,
                         url=url, fallback=fallback, cite=cite, note=note,
                         lag=DEFAULT_LAG.get(cls, 0) if lag is None else lag)


INDIA_FIGURES = [
    # --- real economy: MoSPI / NSO owns the actuals ---
    Fig("india_gdp_fy_actual", "India real GDP growth, latest full FY", "%", "annual",
        "MoSPI / NSO", "https://www.mospi.gov.in/data",
        "MoSPI > Data > National Accounts > 'Provisional Estimates of Annual GDP'. "
        "Read 'GDP at Constant (2011-12) Prices -- percentage change over previous year'. "
        "The press note PDF states it in paragraph 1.",
        "MoSPI, Provisional Estimates of Annual GDP, <Month Year>",
        "This is the number the market quotes for 'India grew X%'. It will differ "
        "from IMF WEO's India figure -- WEO is a forecast vintage, NSO is the print."),
    Fig("india_gva_fy_actual", "India real GVA growth, latest full FY", "%", "annual",
        "MoSPI / NSO", "https://www.mospi.gov.in/data",
        "Same press note as GDP; the GVA table sits directly below the GDP table. "
        "Use 'GVA at Basic Prices, constant prices, % change'.",
        "MoSPI, Provisional Estimates of Annual GDP, <Month Year>",
        "GVA strips indirect taxes less subsidies; a wide GDP-GVA gap is a subsidy story "
        "worth a sentence on the India economy page."),
    Fig("india_gdp_latest_q", "India real GDP growth, latest quarter", "%", "quarterly",
        "MoSPI / NSO", "https://www.mospi.gov.in/data",
        "MoSPI > Data > National Accounts > 'Quarterly Estimates of GDP'. Read the "
        "y-o-y % change for the most recent quarter and note WHICH quarter it is.",
        "MoSPI, Quarterly Estimates of GDP, Q<n> FY<yy>",
        "Record the quarter in `period` -- a quarterly print with no quarter label is "
        "the single easiest way to put a year-old number in a report."),
    Fig("india_cpi", "India CPI inflation, y-o-y", "%", "monthly",
        "MoSPI", "https://www.mospi.gov.in/cpi",
        "MoSPI CPI page > latest monthly press release PDF. Read 'All India Combined "
        "CPI inflation rate (y-o-y)'. Use Combined, not Rural or Urban alone.",
        "MoSPI CPI release, <Month Year>",
        "Released around the 12th for the prior month.", lag=12),
    Fig("india_cpi_core", "India core CPI inflation, y-o-y", "%", "monthly",
        "MoSPI (derived)", "https://www.mospi.gov.in/cpi",
        "Not published directly. Either take the CPI-excluding-food-and-fuel series "
        "some releases carry, or quote a bank/rating-agency estimate WITH that "
        "attribution. Do not compute it silently.",
        "<house> estimate of CPI ex-food-and-fuel, <Month Year>",
        "Optional. Omit rather than compute an unattributed core."),
    Fig("india_wpi", "India WPI inflation, y-o-y", "%", "monthly",
        "Office of the Economic Adviser, DPIIT", "https://eaindustry.nic.in/",
        "eaindustry.nic.in > 'Press Note' for the latest month. Read the all-commodities "
        "y-o-y inflation rate.",
        "Office of the Economic Adviser, WPI release, <Month Year>",
        "WPI leads input costs for manufacturers -- it belongs on the margin discussion, "
        "not just the macro page.", lag=14),
    Fig("india_iip", "India IIP growth, y-o-y", "%", "monthly",
        "MoSPI", "https://www.mospi.gov.in/iip",
        "MoSPI IIP page > latest press release. Read 'General Index, y-o-y growth'. "
        "The manufacturing sub-index is on the same table and is often the more "
        "relevant one for an industrial name.",
        "MoSPI IIP release, <Month Year>",
        "Released around the 28th, for the month two months prior -- so the freshest "
        "IIP in existence is already about 40 days old. That is the lag, not staleness.",
        lag=40),
    Fig("india_gdp_per_capita", "India GDP per capita", "INR", "annual",
        "MoSPI / NSO", "https://www.mospi.gov.in/data",
        "Annual national accounts press note, 'Per Capita Income' table, current prices. "
        "State current vs constant prices explicitly.",
        "MoSPI, National Accounts Statistics, <Year>",
        "For a consumption name this is the affordability anchor; pair it with the "
        "product's price to make the premiumisation argument concrete."),

    # --- money and markets: RBI owns these ---
    Fig("repo_rate", "RBI policy repo rate", "%", "policy",
        "RBI", "https://website.rbi.org.in/en/web/rbi/press-releases",
        "RBI > Press Releases > latest Monetary Policy Statement. The repo rate is in "
        "the first paragraph of the resolution. Also note the STANCE "
        "(accommodative / neutral / withdrawal of accommodation) -- record it as a note.",
        "RBI Monetary Policy Statement, <Month Year>",
        "MPC meets roughly every two months. The stance matters more than the level for "
        "a rate-sensitive sector; quote both."),
    Fig("india_10y_gsec", "India 10-year G-sec yield", "%", "market",
        "RBI / CCIL", "https://www.ccilindia.com/",
        "CCIL home page carries the benchmark 10Y yield. RBI's Weekly Statistical "
        "Supplement Table 6 also has it, one week behind. Record the exact date.",
        "CCIL, <DD Month Year>",
        "This is the risk-free rate the DCF should be using. If it disagrees with "
        "assumptions.json's risk_free, one of the two is wrong -- reconcile before Phase 5."),
    Fig("usdinr", "USD/INR reference rate", "INR", "market",
        "RBI", "https://www.rbi.org.in/scripts/ReferenceRateArchive.aspx",
        "RBI Reference Rate Archive > pick the date. Use the RBI reference rate, not a "
        "broker quote, so it is reproducible.",
        "RBI Reference Rate, <DD Month Year>",
        "Match this to the cover date used by peer-comps, or EV and the comps table "
        "are struck on different currencies-of-the-day."),
    Fig("bank_credit_growth", "Scheduled commercial bank credit growth, y-o-y", "%", "weekly",
        "RBI", "https://website.rbi.org.in/en/web/rbi/statistics",
        "RBI Weekly Statistical Supplement, Table 5 'Scheduled Commercial Banks -- "
        "Business in India'. Take y-o-y % on 'Bank Credit'.",
        "RBI Weekly Statistical Supplement, <DD Month Year>",
        "Credit growth is the demand proxy for anything financed at the point of sale -- "
        "autos, housing, consumer durables."),
    Fig("forex_reserves", "India foreign exchange reserves", "USD bn", "weekly",
        "RBI", "https://website.rbi.org.in/en/web/rbi/statistics",
        "RBI Weekly Statistical Supplement, Table 2 'Foreign Exchange Reserves'. "
        "Take the total, and note the week-ended date.",
        "RBI Weekly Statistical Supplement, week ended <DD Month Year>", ""),

    # --- fiscal and external ---
    Fig("fiscal_deficit_pct_gdp", "Union fiscal deficit", "% of GDP", "annual",
        "Union Budget / CGA", "https://www.indiabudget.gov.in/",
        "Budget at a Glance, the fiscal deficit row. State whether it is Budget "
        "Estimate, Revised Estimate or Actual -- they differ materially.",
        "Union Budget <FY>, Budget at a Glance (<BE/RE/Actual>)",
        "Always carry the BE/RE/Actual qualifier into the report text."),
    Fig("cad_pct_gdp", "India current account deficit", "% of GDP", "quarterly",
        "RBI", "https://website.rbi.org.in/en/web/rbi/press-releases",
        "RBI press release 'Developments in India's Balance of Payments', latest "
        "quarter. Read CAD as % of GDP and note the quarter.",
        "RBI, Developments in India's Balance of Payments, Q<n> FY<yy>", ""),
    Fig("brent_crude", "Brent crude", "USD/bbl", "market",
        "EIA / market close", "https://www.eia.gov/dnav/pet/pet_pri_spt_s1_d.htm",
        "EIA spot price series, Europe Brent, daily. Record the exact date.",
        "EIA Europe Brent spot, <DD Month Year>",
        "Relevant to almost every Indian manufacturer through freight and petrochemical "
        "inputs, and to the CAD through the import bill."),
]

INDIA_FIGURE_INDEX = {f["key"]: f for f in INDIA_FIGURES}


# --------------------------------------------------------------- validation
def validate_registry() -> list[str]:
    """Enforce the invariants this whole design rests on. Called by every script."""
    errs = []
    seen = set()
    for f in INDIA_FIGURES:
        k = f["key"]
        if k in seen:
            errs.append(f"duplicate figure key: {k}")
        seen.add(k)
        if len(k) > 28:
            errs.append(f"key too long for kb.py brief column (28 chars): {k}")
        if not f["fallback"].strip():
            errs.append(f"{k}: no fallback instruction -- a fetch failure would have "
                        "nowhere to degrade to")
        if not f["cite"].strip():
            errs.append(f"{k}: no citation format")
        if f["cls"] not in FRESHNESS_DAYS:
            errs.append(f"{k}: unknown freshness class {f['cls']!r}")
    return errs


def days_old(period_iso: str | None) -> int | None:
    """Age of an observation period, measured from the END of what it covers.

    Accepts YYYY-MM-DD, YYYY-MM or YYYY. A period is a span, not an instant: the
    June 2026 CPI observes all of June, so it ages from 30 June. Measuring from the
    1st would overstate every monthly figure's age by up to a month and refuse
    perfectly current data."""
    if not period_iso:
        return None
    s = str(period_iso).strip()
    try:
        return (date.today() - datetime.strptime(s, "%Y-%m-%d").date()).days
    except ValueError:
        pass
    try:
        d = datetime.strptime(s, "%Y-%m").date()
        nxt = date(d.year + (d.month == 12), (d.month % 12) + 1, 1)
        return (date.today() - (nxt - timedelta(days=1))).days
    except ValueError:
        pass
    try:
        return (date.today() - date(int(s), 12, 31)).days
    except ValueError:
        return None


if __name__ == "__main__":
    problems = validate_registry()
    if problems:
        print("REGISTRY INVALID:")
        for p in problems:
            print("  -", p)
        raise SystemExit(1)
    print(f"registry OK: {len(INDIA_FIGURES)} India figures, "
          f"{len(WEO_AGGREGATES) + len(WEO_COUNTRIES)} WEO geographies")
    print(f"expected WEO vintage today: {expected_weo_vintage()}")
    print(f"horizon years: {horizon_years()}")
