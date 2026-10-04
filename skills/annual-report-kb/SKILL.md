---
name: annual-report-kb
description: "Converts a single company annual report PDF (100-1000+ pages) into a structured knowledge base - page-level markdown, detected sections, extracted tables, classified images, entity databases, summary context files and navigation indexes - ready for a downstream equity research agent. This skill should be used when the user supplies an annual report PDF and asks to parse, index, extract, or build a knowledge base from it, or to prepare an annual report for research."
---

# Annual Report Knowledge Base

Turns one annual report PDF into `<Company Name> Annual Report/`, a folder a
later agent can navigate without ever opening the PDF.

The user provides only the PDF. Everything below runs without further input,
apart from two small classification decisions the scripts hand back.

## Non-negotiables

1. **Never read the whole report into context.** The parse is a background
   process; its output is designed to be read a page or a section at a time.
   Do not open `_work/chunks/*.md`, and do not read `pages/` in bulk.
2. **Preserve page references everywhere.** Every table, image, entity and
   context claim records the page it came from. This is what makes the output
   auditable downstream.
3. **Run `preflight.py` before parsing.** It catches the environment failure
   that otherwise surfaces an hour into a run.
4. **Parse in the background and poll.** A full report takes 15+ minutes.
5. Page numbers are 0-based in filenames and JSON; citations to the reader are
   1-based, written `(p. N)`.

## Workflow

Read `references/pipeline.md` for the full stage reference, including the two
plan schemas. The short form:

```bash
# 0. check environment + PDF, get the recommended command
python scripts/preflight.py "REPORT.pdf" --work "<OUT>/_work"

# 1. parse (background; resumable; ~1.1 s/page on CPU with --disable-ocr)
python scripts/parse_pdf.py "REPORT.pdf" --work "<OUT>/_work" --chunk-size 25 [--disable-ocr]

# 2. assemble everything deterministic
python scripts/build_kb.py --work "<OUT>/_work" --out "<OUT>"

# 3. write the two plans (below), then apply them
python scripts/apply_plan.py --work "<OUT>/_work" --out "<OUT>"

# 4. manifest.json + parse_report.md
python scripts/validate_kb.py --work "<OUT>/_work" --out "<OUT>" --company "<Company>" --year "<FY>"
```

Set `<OUT>` to `<Company Name> Annual Report`, taking the company name and
fiscal year from the report's cover page. Copy the source PDF to
`<OUT>/report.pdf`.

Use the exact command `preflight.py` prints - it decides `--disable-ocr` and
`--mode` from the machine and the document, and refuses combinations that would
silently produce blank pages.

### Stage 3 is the only judgement step

`build_kb.py` writes two small candidate files. Read them (not the report) and
write two plans:

- `_work/section_candidates.json` -> `_work/section_plan.json`: group the
  detected headers into the report's real sections, with page ranges.
- `_work/image_candidates.json` -> `_work/image_plan.json`: classify each image
  from its caption, section and page-text snippet.

Schemas are in `references/pipeline.md`; the section names, image categories and
entity schemas are in `references/taxonomy.md`. `apply_plan.py` then builds
`sections/`, files and renames every image, and repoints the markdown image
links at their new paths.

### Then write the interpreted files

Reading only the sections needed for each, and citing pages throughout:

- `entities/*.json` - seven files, schemas in `references/taxonomy.md`
- `context/*.md` - twelve summary files, from `assets/context_template.md`
- `index.md` - from `assets/index_template.md`; `README.md` - short orientation

Work section by section. To fill `context/manufacturing.md`, open the
manufacturing section and the plant tables, not the whole report.

Finish by running `validate_kb.py` and resolving what `parse_report.md` flags.

## Output structure

```
<Company Name> Annual Report/
├── report.pdf, README.md, index.md, manifest.json, parse_report.md
├── context/      12 summary files, each with page citations
├── sections/     one file per detected section (+ 99_remaining_sections.md)
├── pages/        page_NNNN.md - the unit to read one at a time
├── tables/       one markdown file per table, with page/section frontmatter
├── images/       directors, executives, plants, factories, products, brands,
│                 maps, charts, diagrams, logos, other
├── entities/     directors, executives, subsidiaries, plants, products,
│                 brands, locations (JSON, every record page-referenced)
├── metadata/     pages, toc, section_index, image_index, table_index
└── _work/        chunk artifacts, state.json, candidates and plans
```

`_work/` is retained deliberately: it makes the parse resumable and the plans
re-appliable. It is not part of the deliverable.

## Notes that matter in practice

- **Resumable.** Rerunning `parse_pdf.py` skips completed chunks. A failed chunk
  is recorded and retried, never aborting the document.
- **Smoke-test large reports first** with `--pages 0-19` before a full run.
- **`--disable-ocr` is normal on machines without a working OCR backend.** Text
  extraction is unaffected for digital PDFs; some infographic-style tables are
  left unreconstructed, recorded in `table_index.json` with `"extracted": false`
  and still readable in their page file.
- Tables detected but not reconstructed, unclassified images and stub context
  files are all reported by `validate_kb.py` rather than hidden.

For failures - `SpawnError: docker run failed`, slow parses, empty pages,
resuming - see `references/troubleshooting.md`.
