# What to pull from the annual report

A Screener export gets you ten years of consistent history in one file. It does
not get you everything, and two of the gaps matter enough to be worth a trip
into the annual report every time.

Use `ar_tables.py` to find the tables; read the numbers yourself; put them in
`overrides.actuals` with the page in `overrides.citations`.

```bash
python scripts/ar_tables.py list  --kb "<Company> Annual Report"
python scripts/ar_tables.py find  --kb "<Company> Annual Report" --for payables
python scripts/ar_tables.py show  --kb "<Company> Annual Report" --file tables/table_p0198_1.md
```

If the knowledge base does not exist yet, build it with the `annual-report-kb`
skill first. If a figure is in prose rather than a reconstructed table, search
the pages with `financial-model-assumptions/scripts/kb_search.py`.

## Always worth pulling

| Preset | Feeds | Why it matters |
|---|---|---|
| `payables` | `payables` | **Screener does not carry trade payables at all.** Without them payable days read zero, net operating assets are overstated by roughly a fifth of cost of sales, and free cash flow is understated for every forecast year. This is the single highest-value override. |
| `ppe` / `capex` | `capex` | Capex is backed out of the net block roll (`Δnet block + depreciation`), which equals true capex only with no disposals, impairment or revaluation. The additions line in the PPE note is the real number. Supplying it makes `chk_fa_roll_hist` meaningful - the residual it then reports *is* the disposals and impairment. |

## Worth pulling when the flag comes up

| Preset | Feeds | Pull it when |
|---|---|---|
| `expenses` | `cogs` | The build notes say there was no expense detail. Without it gross margin equals EBITDA margin and the opex line is zero. Cost of materials + purchases of stock-in-trade + changes in inventories gives you a real cost of sales. |
| `borrowings` | `term_debt`, `cost_of_debt`, `term_debt_repay` | Debt is material. The maturity table gives you the actual repayment schedule, which is far better than a growth rate; put it in `overrides.drivers.term_debt_repay` as a per-year list. |
| `leases` | `term_debt` | Lease liabilities are large and you want them in debt. Decide once and say so - a lease-adjusted model and an unadjusted one are not comparable. |
| `tax` | `tax_rate` | The effective rate computed as (PBT − PAT) / PBT looks odd. It absorbs minority interest and share of associates, so a company with large associates reads high. The tax reconciliation note tells you the real rate. |
| `equity` | `share_capital`, `reserves`, `shares`, `dividends` | `chk_reserves_hist` flagged. The statement of changes in equity tells you what moved reserves other than profit - OCI, a buyback, a share issue. |
| `otherincome` | `other_income_pct`, `interest_income_rate` | You want to model treasury income explicitly. Split reported other income into operating and treasury, cut `other_income_pct` to the operating part, then set `interest_income_rate`. Doing one without the other double counts. |
| `receivables` / `inventory` | `dso`, `dio` | The ageing schedules show whether receivable days are rising because of genuine credit terms or because old balances are not being written off. |
| `revenue` / `segments` | `rev_growth` | You are building a segment or volume-and-price revenue forecast rather than a single growth rate. Put the resulting growth in `overrides.drivers.rev_growth` as a per-year list and cite the segment table. |
| `statements` | the whole spine | Screener and the annual report disagree, or the company changed its reporting. Read the primary statements and override line by line. |

## The consolidated / standalone trap

Screener exports consolidated figures for most companies. The annual report
contains both, usually with standalone first. Pulling a standalone payables
figure onto a consolidated spine will show up in the reconciliation as a large
disagreement - which is the reconciliation doing its job. Check which set you
are reading before you copy a number.

## Recording it

```json
{
  "actuals": {
    "payables": {"Mar-23": 1075.0, "Mar-24": 1183.6},
    "capex":    {"Mar-23": 431.0,  "Mar-24": 470.0}
  },
  "citations": {
    "payables": {"source": "tables/table_p0198_1.md", "page": 198,
                 "quote": "Trade payables - total outstanding dues of creditors"},
    "capex":    {"source": "tables/table_p0176_2.md", "page": 176,
                 "quote": "Additions to property, plant and equipment"}
  }
}
```

Citations travel into `model.json`, the `Model info` sheet and the review, so
anyone reading the model can get back to the page. A figure from the annual
report without a citation should not go in.
