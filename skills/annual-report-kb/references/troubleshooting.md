# Troubleshooting

## `SpawnError: docker run failed` mid-parse

The most common failure, and it surfaces only when a page first needs OCR -
often well into a long run.

Marker sends OCR to surya, which picks an inference backend automatically:

```
NVIDIA GPU detected  ->  "vllm"      -> spawns a Docker container
otherwise            ->  "llamacpp"  -> needs a `llama-server` binary on PATH
```

The GPU probe checks `nvidia-smi`, **not** whether torch can use the GPU. So a
machine with a CPU-only torch build (`torch.__version__` ends in `+cpu`) and any
NVIDIA card still selects `vllm`, then dies because Docker is not running.

Fixes, cheapest first:

1. **`--disable-ocr`** - correct for any PDF with a real text layer, which is
   most annual reports. `preflight.py` sets this recommendation automatically.
2. **Start Docker Desktop** and rerun - keeps full OCR quality.
3. **Force the CPU backend**: set `SURYA_INFERENCE_BACKEND=llamacpp` and install
   a `llama-server` binary (or point `LLAMA_CPP_BINARY` at one).

Always run `preflight.py` first; it detects all of this before the parse.

## What `--disable-ocr` costs

Text extraction is unaffected for digital PDFs - the PDF text layer is used
directly, and it is more accurate than OCR.

What degrades is table *structure*: tables the pdftext heuristics cannot resolve
into a grid are left unreconstructed. On a typical report this is a meaningful
fraction of detected tables, and they are mostly infographic-style layouts
rather than financial statements.

Nothing is lost from the text: those tables' numbers still appear in
`pages/page_NNNN.md`, just unstructured. They are recorded in
`metadata/table_index.json` with `"extracted": false` and a pointer to the page,
and counted in `parse_report.md` as *detected but not reconstructable*. If a
specific table matters, read its page file directly.

Never use `--disable-ocr` on a scanned PDF - `preflight.py` refuses that
combination, because it would yield blank pages.

## The parse is slow

Measured on an 8-core CPU, `--mode fast --disable-ocr`: **~1.1 s/page**, so an
855-page report takes roughly 15-20 minutes. With OCR enabled it is several
times slower, because each unresolved block is a VLM round-trip.

- Run it in the background and poll `state.json`; do not block a foreground call
  on a full report.
- The first ever run also downloads ~1 GB of models into two separate caches
  (`~/.cache/huggingface` and `%LOCALAPPDATA%\datalab`), and starts two local
  surya model servers. Allow several extra minutes once; later runs reuse both.
- `--mode balanced` is higher quality but needs a real CUDA-enabled torch build.
  With a CPU-only torch it is not worth it.

## The parse died / the machine rebooted

Just rerun the same command. Completed chunks are recorded in
`_work/state.json` and skipped. Individual chunk failures never abort the
document - they are recorded, retried on the next run, and listed in
`parse_report.md`.

Use `--force` only to deliberately reprocess everything.

## `parse_report.md` says pages were never parsed

Either the run was interrupted, or specific chunks failed. Rerun `parse_pdf.py`
with the same arguments; it resumes. If a chunk fails repeatedly, parse just
that range to see the error:

```bash
python scripts/parse_pdf.py REPORT.pdf --work "<OUT>/_work" --pages 300-324
```

## Many pages come back empty

If `text_extraction_method` is a text-layer method, the pages are probably
genuinely blank (section dividers, image-only pages). If the PDF is scanned and
`--disable-ocr` was used, that is the cause - get an OCR backend working and
re-run with `--force`.

## Images look wrong or duplicated

Repeated identical crops across pages are logos and page furniture; classify
them as `logos` or leave them in `other`. `validate_kb.py` hashes image content
and reports duplicate groups, so a large duplicate count is expected and not an
error.

## Windows notes

- Every script guards its entry point with `if __name__ == "__main__":`. Keep it
  that way - marker uses multiprocessing, and on Windows (spawn start method) an
  unguarded module re-executes itself in each worker.
- Long paths: keep the output folder reasonably shallow. `<Company> Annual
  Report/pages/page_0123.md` under a deep temp path can exceed `MAX_PATH`.
- Quote paths containing spaces - company names usually have them.
