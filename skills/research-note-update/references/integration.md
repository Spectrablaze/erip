# Integration — files, paths, and the sibling skills

This skill computes a delta. It owns almost no data: the knowledge base, the
model, the assumptions and the calibration ledger all belong to skills that ran
before it. Getting the paths wrong is the main way an update note goes wrong.

---

## The tree it works in

```
reports/
├── _knowledge/                     # SHARED, outside every skill directory
│   ├── calls.json                  # the calibration ledger — kb.py owns this
│   ├── macro.json                  # india-macro-pack writes; check staleness
│   ├── aliases.json                # learned Screener labels
│   ├── sectors/<sector>.json
│   └── lessons.md
└── <TICKER>/
    ├── decisions.json              # THE file to edit. revise.py patches it.
    ├── kb/<doc>/                   # annual-report-kb output per document
    ├── data/
    │   ├── financials.json         # parse_screener.py output
    │   ├── assumptions.json        # GENERATED from decisions.json — never edit
    │   ├── assumptions_evidence.md # GENERATED audit trail
    │   ├── model.json              # equity-research-report model.py — the DCF
    │   ├── peers.json              # peer-comps output
    │   └── three_statement/
    │       ├── model_input.json
    │       └── model.json          # financial-model — P&L/BS/CF, has `bridge`
    ├── charts/
    ├── assets/
    └── updates/                    # THIS SKILL'S OUTPUT
        └── <YYYY-MM-DD>/
            ├── standing.json       # standing.py — the position, pre-quarter
            ├── actuals.json        # you write this from the results release
            ├── variance.json/.md   # variance.py
            ├── falsifiers.json     # your Phase 3 adjudication
            ├── rating.json         # rating.py
            ├── note.html
            └── <Company> - Update <Period>.pdf
```

**The two `model.json` files are different files.** `data/model.json` is the DCF;
`data/three_statement/model.json` is the linked three-statement model. They share
a filename and would overwrite each other in one directory — this is why the
three-statement model lives in its own subdirectory, and why `standing.py` reads
both and labels which one the forecast came from.

**`reports/_knowledge/` is deliberately outside every skill folder** so it
survives skill re-installs and is shared by every copy of the skills. Do not
relocate it.

---

## Which forecast the variance scores against

`standing.py` prefers `data/three_statement/model.json`, because it carries
EBITDA, PAT and EPS and its columns are real fiscal-year labels. The DCF's
`forecast` rows only carry Sales, EBIT and EBIT % under `Y1..Yn` headings.

Practical consequence: **without the three-statement model, the variance table
is two lines** (revenue and EBIT) and the EBITDA-margin check — the one figure a
single quarter measures honestly — cannot be computed at all. If the initiating
work skipped the three-statement model, build it before the first update note.

---

## Commands, with the flags they actually take

Verified signatures — several of these differ from what looks natural.

```bash
FMA=<financial-model-assumptions skill>
FMD=<financial-model skill>
ERR=<equity-research-report skill>
T=EICHERMOT

# rebuild assumptions from a revised decisions.json  (--outdir, NOT --out)
python3 $FMA/scripts/build_assumptions.py --in reports/$T/decisions.json \
        --outdir reports/$T/data/

# three-statement model — two steps, and build_model.py reads model_input.json,
# not decisions.json
python3 $FMD/scripts/ingest.py --screener reports/$T/data/financials.json \
        --assumptions reports/$T/data/assumptions.json \
        -o reports/$T/data/three_statement/model_input.json
python3 $FMD/scripts/build_model.py \
        --in reports/$T/data/three_statement/model_input.json \
        --outdir reports/$T/data/three_statement/

# the DCF — financials and assumptions are POSITIONAL, and --sector is required
# in practice or nothing is suppressed
python3 $ERR/scripts/model.py reports/$T/data/financials.json \
        reports/$T/data/assumptions.json --sector "<sector>" \
        --fm reports/$T/data/three_statement/model.json \
        -o reports/$T/data/model.json

# render (run the gate first; it blocks on unresolved {{TOKENS}})
python3 $ERR/scripts/render.py reports/$T/updates/<date>/note.html --check-only
python3 $ERR/scripts/render.py reports/$T/updates/<date>/note.html \
        -o "reports/$T/updates/<date>/<Company> - Update <Period>.pdf"
```

`revise.py` prints this chain, filled in with the real paths and only the steps
the revision actually made stale.

---

## `decisions.json` — where a field goes

Getting this wrong fails silently, which is why it is worth restating.

- **Cited judgements go INSIDE `assumptions`**, as
  `{"value": …, "unit": …, "confidence": …, "status": …, "why": [], "evidence": []}`.
  That includes `exit_multiple`.
- **Settings go TOP-LEVEL**: `peers`, `peer_betas`, `scenarios`,
  `mid_year_convention`, `blume_adjust`, `non_operating_assets`, `sector`,
  `wc_days_on_cogs`.
- **A judgement placed top-level is silently dropped.** `build_assumptions.py`
  passes through a fixed whitelist and ignores everything else.

This skill adds three top-level keys of its own — `revisions`, `rating_bands`
and `tolerances`. They are outside that whitelist, so the builder ignores them;
verified against the real builder. They are this skill's record, not model
inputs.

---

## The `kb.py` surface this skill uses

From `equity-research-report/scripts/kb.py`. This skill does **not** modify it.

```bash
KB=$ERR/scripts/kb.py

python3 $KB brief --ticker $T --sector <sector>     # recall, incl. due reviews
python3 $KB review                                  # calibration + all open calls
python3 $KB close --ticker $T --actual <price> --note "..."
python3 $KB call  --ticker $T --rating BUY --target 5600 --cmp 4920 \
        --thesis "..." --falsifier "..." --falsifier "..." --review-months 6
python3 $KB lesson --text "..." --tag update
```

Two behaviours worth knowing:

- **`close` closes the most recent OPEN call** on that ticker and scores
  `target_error_% = actual/target − 1`. There is no way to close a specific
  older call.
- **`call` always appends a new open call.** It has no reiterate concept — which
  is exactly why a reiteration must not touch `calls.json` (see
  `policy.md` §4). Logging a call per note would flood the ledger with
  three-month horizons that were never the horizon you set.

---

## Sibling skills, and when an update note needs them

| Skill | When an update note calls it |
|---|---|
| `equity-research-report` | Always — it owns `kb.py`, `render.py`, `charts.py`, `model.py`, `report.css`. |
| `financial-model` | On a full re-forecast, to rebuild the three-statement model. |
| `financial-model-assumptions` | Whenever `decisions.json` changed — to regenerate `assumptions.json`. |
| `peer-comps` | Every note. Comps go stale in weeks even when nothing else does. |
| `annual-report-kb` | Only when a new document arrives (a fresh annual report). Quarterly releases are usually short enough to read directly. |
| `india-macro-pack` | When `kb.py brief` flags `macro.json` as stale, or when the note's argument turns on a macro figure — a rate, the currency, a tariff. |

---

## Rendering on this machine

Inherited from `equity-research-report`, unchanged:

- `render.py` auto-selects `weasyprint` → `wsl` → `chromium`. Check with
  `render.py --engines`.
- **WSL Ubuntu is the working full-fidelity path.** WeasyPrint does not work
  natively on Windows — the pip package installs but the native Pango/Cairo
  libraries are absent. Do not retry the native route.
- **Chromium silently drops CSS Paged Media running headers** (`@top-left`,
  `string(disclaimer)`) and named `@page` rules. Layout preview only — an update
  note rendered through Chromium loses its running header and its cover page
  rule.
- Windows has no `pdftoppm`, so PDFs cannot be rasterised for inspection
  directly. Go through WSL:
  `wsl -d Ubuntu -- pdftoppm -png -r 100 /mnt/c/... /mnt/c/...`, then read the PNG.

---

## Keeping the copies in sync

`equity-research-report` exists in three copies that do not auto-sync (user
global, project-local, and the uploaded Cowork/claude.ai zip). If this skill is
installed alongside it, it inherits the same problem. Edit the global copy under
`~/.claude/skills/`, then propagate. `reports/_knowledge/` is shared by all
copies precisely so the ledger does not fork — which is the one piece that
would be unrecoverable if it did.
