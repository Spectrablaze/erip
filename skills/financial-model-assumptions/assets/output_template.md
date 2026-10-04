# Output template

Reproduce this structure exactly. The summary table comes first, then one block
per assumption, then the closing line.

---

## Opening

State before the table, in two or three lines: the company, the knowledge base
used, what documents it contains, the forecast horizon, the sector profile, and
any evidence gap that limits the whole set (no transcript, no industry report,
financials only). `kb_search.py profile` produces the gap list.

## Summary table

| Assumption | Suggested Value | Confidence | Key Reason |
|------------|----------------|------------|------------|
| Revenue Growth | 13% → 9.5% (FY27-31) | High | Management guided to low-teens; 5y CAGR 14.4% decelerating |
| Gross Margin | 47.0% | High | FY26 actual, up 380bps over five years |
| Customer Retention | Not enough evidence | Low | Not disclosed in any document in the knowledge base |

Every required assumption gets a row, including the ones with no evidence. Group
the rows in the order below and keep the group headings visible.

## Per-assumption block

Repeat for every assumption:

---

## Assumption

Revenue Growth

### Suggested Value

13% in FY27 tapering to 9.5% by FY31

### Why

- Management guided for low-teens growth over the medium term.
- Revenue CAGR was 14.4% over five years and 11.1% over three - the trend is
  decelerating.
- The Dahej line adds capacity from FY28.
- The taper reaches the terminal rate by the final forecast year.

### Evidence

> "Management expects to sustain low-teens revenue growth over the medium term"
> — MD&A (p. 43), `context/management_discussion.md`

> Revenue rose 13.8% to Rs 9,455 cr in FY26; 5y CAGR 14.4% (computed from the
> historical financials, FY21-FY26)

### Confidence

High

### User Confirmation

Does 13% tapering to 9.5% look reasonable, or would you like to change it?

---

## Order of assumptions

**Revenue** — Revenue Growth, Volume Growth, Pricing Growth, New Customers,
Customer Retention
**Margins** — Gross Margin, EBITDA Margin, EBIT Margin, Operating Margin
**Expenses** — SG&A, R&D, Sales & Marketing, Employee Cost
**Capital** — Capex, Depreciation, Amortisation
**Working Capital** — DSO, DIO, DPO
**Tax** — Effective Tax Rate
**Financing** — Interest Rate, Debt Growth
**Valuation** — Terminal Growth Rate, WACC
**Industry-specific** — from `references/sectors.md`, for the resolved sector

Where EBIT margin and operating margin are the same measure for this company,
say so in one line rather than repeating the block.

## Insufficient evidence

Use the wording in `references/evidence-rules.md` verbatim. Name the document
that would resolve the gap.

## Closing line

End with exactly:

> Please review these assumptions. Let me know which ones you'd like to modify,
> and I'll update the financial model accordingly.
