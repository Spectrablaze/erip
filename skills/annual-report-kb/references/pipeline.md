# Pipeline reference

Five stages. Stages 0-2 and 4 are scripts; stage 3 is the only one requiring
judgement, and even there the agent writes two small JSON plans that a script
applies. The agent never copies page text by hand.

```
preflight.py -> parse_pdf.py -> build_kb.py -> [agent plans] -> apply_plan.py -> validate_kb.py
   stage 0        stage 1         stage 2         stage 3          stage 3          stage 4
```

Throughout, `<OUT>` is the output folder `<Company Name> Annual Report/` and
`<OUT>/_work/` holds intermediates. Page numbers are **0-based everywhere** in
JSON and filenames; `pdf_page` (1-based) is carried alongside for humans.

---

## Stage 0 - preflight

```bash
python scripts/preflight.py "REPORT.pdf" --work "<OUT>/_work"
```

Decides whether the parse can succeed *before* spending hours on it, and prints
the exact `parse_pdf.py` command to run. Reads its recommendation from two facts:

- **Which surya backend will be selected, and can it start.** See
  `troubleshooting.md` - this is the single most common cause of a failed run.
- **Whether the PDF has a text layer.** Digital reports can be parsed with
  `--disable-ocr` and need no VLM at all.

Exit code 1 means do not parse yet; read the `blocking` list and the `remedies`.

## Stage 1 - parse

```bash
python scripts/parse_pdf.py "REPORT.pdf" --work "<OUT>/_work" \
    --mode fast --chunk-size 25 [--disable-ocr]
```

Walks the PDF in page chunks. Each chunk is built once and rendered twice
(markdown for text, JSON for structure), then written to `_work/chunks/`.
Completed chunks are recorded in `_work/state.json`.

- **Resumable.** Re-running skips finished chunks. A failed chunk is recorded
  and retried next run; it never aborts the whole document.
- **Long-running.** Run it in the background and poll, rather than blocking on
  it. Roughly 1 s/page on CPU with `--disable-ocr`; several times that with OCR
  enabled. First ever run also downloads ~1 GB of models.
- Use `--pages 0-19` to smoke-test a big report before committing to a full run.

## Stage 2 - build

```bash
python scripts/build_kb.py --work "<OUT>/_work" --out "<OUT>"
```

Assembles everything derivable without judgement:

| Output | Contents |
|---|---|
| `pages/page_NNNN.md` | per-page markdown - **the unit to read one at a time** |
| `metadata/pages.json` | per-page extraction method, char count, table/image counts |
| `metadata/toc.json` | the PDF outline plus every detected section header |
| `tables/*.md` | one file per table, with page/section frontmatter |
| `metadata/table_index.json` | table catalogue, including detected-but-not-extracted |
| `_work/section_candidates.md` | **compact header listing - read this one** |
| `_work/section_candidates.json` | same data as JSON, for programmatic use |
| `_work/image_candidates.json` | image list with caption + page context |

## Stage 3 - the agent's two plans

This is the only judgement step. Read the two candidate files (both small - they
contain headers and image metadata, never full page text) and write two plans.

### `_work/section_plan.json`

Read **`_work/section_candidates.md`**, not the `.json` - a full report yields
well over a thousand headers, and the compact listing is less than half the
size. Lines marked `*` also appear in the PDF's own outline and are the
strongest section boundaries.

Group those headers into the report's real sections. Ranges are 0-based and
inclusive, must not overlap, and need not cover the whole document - any gap is
swept into `sections/99_remaining_sections.md`.

```json
{
  "sections": [
    {"name": "Letter to Shareholders", "start_page": 8,  "end_page": 13,
     "summary": "Chairman's review of FY26"},
    {"name": "Management Discussion & Analysis", "start_page": 60, "end_page": 118},
    {"name": "Financial Statements", "start_page": 300, "end_page": 640}
  ]
}
```

Aim for the canonical sections in `taxonomy.md`. Prefer a handful of large,
meaningful sections over dozens of fragments: these files exist so a downstream
agent can load exactly one topic.

### `_work/image_plan.json`

Classify each image. `file` must match the `file` field from
`image_candidates.json` (`_raw/pNNNN_type_N.jpg`). `category` must be one of the
categories in `taxonomy.md`; anything else is filed under `other`.

```json
{
  "images": [
    {"file": "_raw/p0123_picture_4.jpg",
     "category": "plants",
     "name": "dahej_manufacturing_facility",
     "caption": "Dahej Plant",
     "description": "Manufacturing facility shown in the operations review"}
  ]
}
```

Classify from the `caption`, `section` and `page_text_snippet` already in the
candidates file. Only open an actual image when those are inconclusive and the
image matters (a plant, a product, a segment chart). Do not attempt to view
every image in a large report - most are decorative.

Then apply both:

```bash
python scripts/apply_plan.py --work "<OUT>/_work" --out "<OUT>"
```

### Then write, by reading only the sections you need

- `entities/*.json` - schemas in `taxonomy.md`. Every record carries `page`.
- `context/*.md` - the twelve summary files. Each cites page numbers and links
  to the sections, tables and images it draws on.
- `index.md` and `README.md` - navigation, from `assets/` templates.

## Stage 4 - validate

```bash
python scripts/validate_kb.py --work "<OUT>/_work" --out "<OUT>" \
    --company "<Company>" --year "FY26"
```

Writes `manifest.json` and `parse_report.md`, and reports unparsed pages, failed
chunks, empty pages, OCR-heavy runs, duplicate images, stub context files and
broken internal links. Fix what it flags, then re-run it - it is cheap.
