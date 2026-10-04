# Industry bodies — where sector data actually comes from

This layer feeds blueprint pages 4–9 (global industry, Indian industry, three growth
drivers, risks). It is **assisted, not automated**: industry bodies publish PDFs, press
releases and Flash Reports, several behind a membership wall. Nothing here is fetched.
Work through the relevant body below, read the figure, and record it as an `industry`
entry in `manual.json`.

Link status was checked when this file was written. Portals reorganise; if a deep link
404s, go to the base domain and navigate — the *release name* given below is the stable
identifier, not the URL.

## The distinction that trips up every auto report

**SIAM is wholesale. FADA is retail.** SIAM counts despatches from the factory to the
dealer; FADA counts vehicles registered by an actual buyer at an RTO. In a
channel-stuffing quarter these diverge sharply, and that divergence is often the most
interesting fact available about the sector.

A report that says "industry volumes grew 8%" without saying which of the two it means
is not wrong so much as unfalsifiable. State the basis every time. Where both are
available, quoting both and naming the gap is a genuine analytical edge.

The same wholesale/retail split exists in other sectors under different names — primary
vs secondary sales in FMCG, despatches vs offtake in cement. Ask which one a number is
before using it.

---

## Auto

### SIAM — Society of Indian Automobile Manufacturers
- <https://www.siam.in/statistics.aspx>
- **Release:** monthly *Flash Report*; annual industry statistics tables.
- **Read:** domestic sales (despatches) and exports, split PV / CV / 3W / 2W. Segment
  splits (hatch / sedan / UV) sit in the detailed tables, not the flash summary.
- **Basis:** wholesale despatches to dealers.
- **Cite:** `SIAM, Flash Report <Month Year>` or `SIAM industry statistics, FY<yy>`.
- Some detailed tables are members-only. If the split is not reachable, record the
  headline and say the split was unavailable — do not substitute a press estimate.

### FADA — Federation of Automobile Dealers Associations
- <https://www.fada.in/>
- **Release:** monthly *Vehicle Retail Data*, from VAHAN registrations.
- **Read:** retail registrations by segment, plus FADA's dealer-inventory commentary,
  which is the cleanest public read on channel stock.
- **Basis:** retail registrations. Excludes Telangana and a few RTOs that are not on
  VAHAN — FADA states the coverage caveat in each release; carry it into the report.
- **Cite:** `FADA Vehicle Retail Data, <Month Year>`.

## IT & services

### NASSCOM
- <https://nasscom.in/>
- **Release:** *Strategic Review* (annual, February); *Technology Sector in India*.
- **Read:** industry revenue (USD bn), export vs domestic split, headcount, growth rate.
- **Cite:** `NASSCOM Strategic Review <Year>`.
- The headline is a full-year estimate published before the year closes. Record whether
  it is an estimate or an actual — NASSCOM labels it and reports routinely drop the label.

## Pharma

### IPA — Indian Pharmaceutical Alliance
- <https://www.ipa-india.org/>
- **Release:** occasional sector reports and position papers; not a regular statistics
  series.
- **Read:** formulation export values, US generics commentary, R&D spend aggregates.
- **Cite:** `IPA, <report title>, <Month Year>`.
- Low frequency. For monthly domestic pharma sales the market standard is IQVIA/AWACS
  secondary-sales data, which is subscription-only. If the report needs it and it is not
  available, say so rather than sourcing it from a news article that quotes it.

## Cross-sector

### IBEF — India Brand Equity Foundation
- <https://www.ibef.org/industry>
- **Release:** per-sector reports, updated periodically. Trust arm of the Ministry of
  Commerce.
- **Read:** market size, forecast market size with a target year, FDI inflow, key policy.
- **Cite:** `IBEF <sector> report, <Month Year>`.
- **Caveat that matters:** IBEF is a *promotional* body. It republishes third-party
  forecasts and its market-size numbers skew optimistic. Use it to locate a figure, then
  follow IBEF's own footnote to the originating source and cite that. Where the original
  is not reachable, attribute to IBEF explicitly — never launder it into an unattributed
  "the market is expected to reach".

### CMIE — Centre for Monitoring Indian Economy
- <https://www.cmie.com/>
- **Products:** CapEx (project pipeline), Prowess (company financials), Consumer
  Pyramids (household survey), unemployment rate.
- **Cite:** `CMIE <product>, <Month Year>`.
- **Subscription.** The unemployment rate is widely republished; the rest is not public.
  Do not cite CMIE data reached through a news article as though it came from CMIE.

## Sector-specific

### CEA — Central Electricity Authority (power)
- <https://cea.nic.in/> → Reports → Monthly generation / installed capacity
- **Read:** installed capacity by fuel (MW), generation (BU), PLF for thermal, renewable
  share.
- **Cite:** `CEA, <report name>, <Month Year>`.
- The most reliable of the government portals for a monthly series, and the natural
  source for any power, capital-goods or energy-transition growth-driver page.

### JPC — Joint Plant Committee (steel)
- Reachable via the Ministry of Steel, <https://steel.gov.in/> → Statistics.
  The standalone JPC site was unreachable when this file was written.
- **Read:** crude steel production, finished steel consumption, imports/exports (mt).
- **Cite:** `JPC / Ministry of Steel, <Month Year>`.
- Note *apparent* vs *actual* consumption — JPC publishes apparent consumption, which
  includes inventory change.

### TRAI — Telecom Regulatory Authority of India
- <https://www.trai.gov.in/> → Release/Publication → Reports
- **Release:** monthly subscriber data; quarterly *Performance Indicator Report* (the
  richer one — ARPU, MBPU, subscriber market share).
- **Cite:** `TRAI Performance Indicator Report, Q<n> <Year>` or
  `TRAI subscriber data, <Month Year>`.
- The quarterly PIR lags about one quarter. ARPU is only in the PIR, not the monthly.

## Rating-agency research (secondary)

CRISIL <https://www.crisilratings.com/>, CareEdge <https://www.careratings.com/>,
ICRA <https://www.icra.in/> — sector outlooks, demand forecasts, margin commentary.

Use these for **forward-looking sector views**, which industry bodies rarely give:
"CRISIL expects PV volumes to grow 6–8% in FY27". That is a legitimate, attributable
forecast and it is often the best available.

Do **not** use them as the source for a historical volume or market-size figure when the
industry body publishes it. A rating agency quoting SIAM is a second-hand SIAM number,
and citing it that way hides one link of the chain.

Free press releases carry the headline; the full report is paid. If only the press
release was read, cite the press release — `CRISIL Ratings press release, <Month Year>` —
not the report.

---

## Recording a figure

```json
{
  "key": "siam_pv_volumes_fy26",
  "label": "Passenger vehicle domestic despatches, FY26",
  "value": 4.6,
  "unit": "units mn",
  "period": "2026-03",
  "body": "SIAM",
  "source": "SIAM Flash Report, April 2026",
  "url": "https://www.siam.in/statistics.aspx",
  "forecast_year": null,
  "note": "wholesale despatches, not retail registrations"
}
```

- `period` is the **end** of what the figure observes. An Indian FY uses its end month:
  FY26 is `2026-03`.
- `forecast_year` is **mandatory for any market-size figure**. "The market will reach
  US$50bn" is meaningless without the year, and a report that states one without it
  cannot be argued with — which is the same as saying it cannot be believed.
- `note` is where the basis goes: wholesale vs retail, apparent vs actual, estimate vs
  actual, coverage caveats. That sentence is usually what makes the figure defensible.
