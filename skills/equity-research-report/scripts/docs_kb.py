#!/usr/bin/env python3
"""
docs_kb.py — run the `annual-report-kb` skill over every PDF the user supplied.

    python3 docs_kb.py plan    --root reports/EICHERMOT
    python3 docs_kb.py run     --root reports/EICHERMOT [--doc annual_report]
    python3 docs_kb.py harvest --root reports/EICHERMOT [--dry-run]
    python3 docs_kb.py index   --root reports/EICHERMOT

WHY
Without this, the annual report is a 400-page PDF that has to be opened and skimmed
for every figure. `annual-report-kb` turns it into page-level markdown, extracted
tables, classified images and entity JSON — all page-referenced. That converts the
most expensive step of the report (reading source documents) into lookups, and it
supplies real, correctly-attributed images for the asset folder.

DEPTH IS PER DOCUMENT
The full five-stage pipeline includes two judgement stages (section plan, image plan)
that only earn their keep on a long report. A four-page shareholding filing needs the
text, not a section taxonomy. `plan` therefore assigns:

    full   annual_report            preflight -> parse -> build -> PLAN -> apply -> validate
    light  everything else          preflight -> parse -> build

LAYOUT
    reports/<T>/inputs/annual_report.pdf        source
    reports/<T>/kb/annual_report/               knowledge base for it
    reports/<T>/kb/INDEX.md                     what lives where
    reports/<T>/assets/                         harvest target (people, products, ...)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys

# Depth tiers. The two judgement stages are independent and earn their keep
# separately: the SECTION plan only pays off on a long report, but the IMAGE plan
# pays off on anything image-rich — and it is the image plan that files pictures
# into images/<category>/, which is what harvest reads. Without it, pictures stay
# unclassified in _work/images/_raw/ and cannot be mapped to people/products/plants.
FULL_DEPTH = {"annual_report", "annual report", "ar"}        # section + image plans
IMAGE_RICH = {"investor_presentation", "investor presentation", "deck"}   # image plan

# Order matters only for display.
KNOWN_DOCS = ["annual_report", "investor_presentation", "concall", "shareholding"]

# annual-report-kb image category  ->  (equity-report asset subfolder, keep how many)
IMAGE_MAP = {
    "directors":  ("people", None),
    "executives": ("people", None),
    "products":   ("products", 12),
    "brands":     ("products", 12),
    "plants":     ("plants", None),
    "factories":  ("plants", None),
    "maps":       ("plants", None),
    "charts":     ("exhibits", 12),
    "diagrams":   ("exhibits", 12),
    "logos":      ("_logo", 1),
}


# ------------------------------------------------------------------ locating
def find_arkb(explicit: str | None = None) -> str:
    """Locate the annual-report-kb skill directory."""
    cands = []
    if explicit:
        cands.append(explicit)
    if os.environ.get("EQR_ARKB"):
        cands.append(os.environ["EQR_ARKB"])
    home = os.path.expanduser("~")
    cands += [
        os.path.join(home, ".claude", "skills", "annual-report-kb"),
        os.path.join(os.getcwd(), ".claude", "skills", "annual-report-kb"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "..", "annual-report-kb"),
    ]
    for c in cands:
        c = os.path.normpath(c)
        if os.path.exists(os.path.join(c, "scripts", "parse_pdf.py")):
            return c
    sys.exit("annual-report-kb skill not found. Install it to ~/.claude/skills/ "
             "or pass --arkb <path> / set EQR_ARKB.")


def pdf_pages(path: str):
    """Best-effort page count; None when it cannot be determined cheaply."""
    try:
        from pypdf import PdfReader          # type: ignore
        return len(PdfReader(path).pages)
    except Exception:
        pass
    try:
        import re
        with open(path, "rb") as f:
            data = f.read()
        n = len(re.findall(rb"/Type\s*/Page[^s]", data))
        return n or None
    except OSError:
        return None


def _matches(stem: str, keys: set[str]) -> bool:
    """Multi-word keys match as a phrase; single-word keys must be a whole token.

    A bare substring test sent every shareholding filing down the full pipeline,
    because "ar" is inside "shareholding".
    """
    norm = re.sub(r"[^a-z0-9]+", "_", stem.lower()).strip("_")
    tokens = set(norm.split("_"))
    for k in keys:
        kn = re.sub(r"[^a-z0-9]+", "_", k.lower()).strip("_")
        if ("_" in kn and kn in norm) or kn in tokens:
            return True
    return False


def discover(root: str) -> list[dict]:
    """Every PDF in inputs/, with its assigned depth."""
    inp = os.path.join(root, "inputs")
    if not os.path.isdir(inp):
        sys.exit(f"no inputs directory at {inp} — run new_company.py first")
    out = []
    for fn in sorted(os.listdir(inp)):
        if not fn.lower().endswith(".pdf"):
            continue
        stem = os.path.splitext(fn)[0].lower()
        if _matches(stem, FULL_DEPTH):
            depth = "full"
        elif _matches(stem, IMAGE_RICH):
            depth = "images"
        else:
            depth = "light"
        p = os.path.join(inp, fn)
        out.append({"file": fn, "stem": os.path.splitext(fn)[0], "path": p,
                    "depth": depth, "pages": pdf_pages(p),
                    "size_mb": round(os.path.getsize(p) / 1e6, 1)})
    # Known documents first, then anything else the user dropped in.
    out.sort(key=lambda d: (KNOWN_DOCS.index(d["stem"]) if d["stem"] in KNOWN_DOCS else 99,
                            d["stem"]))
    return out


def kb_path(root: str, stem: str) -> str:
    return os.path.join(root, "kb", stem)


# ------------------------------------------------------------------ commands
def cmd_plan(args):
    docs = discover(args.root)
    arkb = find_arkb(args.arkb)
    if not docs:
        print("no PDFs in inputs/ — nothing to build")
        return
    print(f"annual-report-kb: {arkb}\n")
    print(f"{'document':<28} {'pages':>6} {'MB':>6}  depth   status")
    print("-" * 70)
    for d in docs:
        built = os.path.exists(os.path.join(kb_path(args.root, d['stem']), "manifest.json"))
        partial = os.path.exists(os.path.join(kb_path(args.root, d['stem']), "_work", "state.json"))
        status = "built" if built else ("partial" if partial else "-")
        print(f"{d['file']:<28} {str(d['pages'] or '?'):>6} {d['size_mb']:>6}  "
              f"{d['depth']:<7} {status}")

    total = sum(d["pages"] or 0 for d in docs)
    print(f"\n~{total} pages total. At ~1.1 s/page that is roughly "
          f"{max(1, round(total * 1.1 / 60))} minute(s) of parsing.")
    print("\nRun with:  python3 docs_kb.py run --root " + args.root)
    print("The annual report parse is long — run it in the background and poll.")
    fulls = [d for d in docs if d["depth"] == "full"]
    if fulls:
        print(f"\nAfter `run`, {fulls[0]['file']} still needs the two judgement stages "
              "(section_plan.json, image_plan.json) — see the annual-report-kb SKILL.md. "
              "Everything else is complete at build.")


def _sh(cmd: list[str], cwd: str | None = None) -> int:
    print("  $ " + " ".join(f'"{c}"' if " " in c else c for c in cmd))
    return subprocess.run(cmd, cwd=cwd).returncode


def cmd_run(args):
    docs = discover(args.root)
    if args.doc:
        docs = [d for d in docs if d["stem"] == args.doc or d["file"] == args.doc]
        if not docs:
            sys.exit(f"no input document matching {args.doc!r}")
    arkb = find_arkb(args.arkb)
    py = sys.executable or "python3"
    S = lambda n: os.path.join(arkb, "scripts", n)   # noqa: E731

    for d in docs:
        out = kb_path(args.root, d["stem"])
        work = os.path.join(out, "_work")
        os.makedirs(work, exist_ok=True)
        print(f"\n=== {d['file']}  ({d['depth']}) -> {out}")

        if os.path.exists(os.path.join(out, "manifest.json")) and not args.force:
            print("  already built — skipping (use --force to rebuild)")
            continue

        if _sh([py, S("preflight.py"), d["path"], "--work", work]) != 0:
            print("  preflight failed — skipping this document")
            continue

        # preflight decides device, mode and — critically — whether OCR is usable.
        # On a machine where surya picks the vllm backend but Docker is not running,
        # ignoring this recommendation means the parse dies mid-chunk with
        # SpawnError. Honour it unless the caller explicitly overrides.
        rec = {}
        pf = os.path.join(work, "preflight.json")
        if os.path.exists(pf):
            try:
                rec = (json.load(open(pf, encoding="utf-8")) or {}).get("recommendation") or {}
            except (json.JSONDecodeError, OSError):
                rec = {}
        if rec and rec.get("can_parse") is False:
            print("  preflight says this PDF cannot be parsed here. Remedies:")
            for r in (json.load(open(pf, encoding="utf-8")).get("backend") or {}).get("remedies", []):
                print(f"    - {r}")
            continue

        parse = [py, S("parse_pdf.py"), d["path"], "--work", work,
                 "--chunk-size", str(args.chunk_size or rec.get("chunk_size") or 25)]
        mode = args.mode or rec.get("mode")
        if mode:
            parse += ["--mode", mode]
        if rec.get("disable_ocr") and not args.force_ocr:
            parse += ["--disable-ocr"]
            print("  preflight: OCR unusable here -> --disable-ocr (text layer only)")
        if args.pages:
            parse += ["--pages", args.pages]
        if _sh(parse) != 0:
            print("  parse failed — see annual-report-kb references/troubleshooting.md")
            continue

        if _sh([py, S("build_kb.py"), "--work", work, "--out", out]) != 0:
            print("  build failed")
            continue

        # Copy the source PDF in, as annual-report-kb expects.
        try:
            shutil.copy2(d["path"], os.path.join(out, "report.pdf"))
        except OSError:
            pass

        n_raw = 0
        raw = os.path.join(work, "images", "_raw")
        if os.path.isdir(raw):
            n_raw = len([f for f in os.listdir(raw) if not f.startswith(".")])

        if d["depth"] == "full":
            print(f"  built. NEXT: write _work/section_plan.json and _work/image_plan.json "
                  f"({n_raw} images to classify), then run apply_plan.py and "
                  "validate_kb.py (annual-report-kb SKILL.md).")
        elif d["depth"] == "images":
            print(f"  built. NEXT: write _work/image_plan.json ({n_raw} images to "
                  "classify) and run apply_plan.py — this document is image-rich and "
                  "the pictures stay unusable until they are filed by category.")
        else:
            print("  built (light: pages/, tables/, metadata/ — text is the point here).")

    cmd_index(args)


def cmd_harvest(args):
    """Copy classified KB images into the report's assets/ folder."""
    docs = discover(args.root)
    assets = os.path.join(args.root, "assets")
    copied, skipped, logo = [], [], None
    unclassified = []

    for d in docs:
        imgroot = os.path.join(kb_path(args.root, d["stem"]), "images")
        if not os.path.isdir(imgroot):
            # Pictures were extracted but never filed by category — that only
            # happens via the image plan. Say so instead of silently finding none.
            raw = os.path.join(kb_path(args.root, d["stem"]), "_work", "images", "_raw")
            if os.path.isdir(raw):
                n = len([f for f in os.listdir(raw) if not f.startswith(".")])
                if n:
                    unclassified.append((d["stem"], n))
            continue
        for cat in sorted(os.listdir(imgroot)):
            dest_sub, cap = IMAGE_MAP.get(cat, (None, None))
            if dest_sub is None:
                continue
            files = [f for f in sorted(os.listdir(os.path.join(imgroot, cat)))
                     if not f.startswith(".")]
            if cap:
                files = files[:cap]
            for fn in files:
                src = os.path.join(imgroot, cat, fn)
                if dest_sub == "_logo":
                    if logo is None:
                        logo = src
                    continue
                if dest_sub == "people":
                    # equity report keys director photos by surname
                    stem, ext = os.path.splitext(fn)
                    parts = [p for p in stem.replace("_", "-").split("-") if p]
                    name = (parts[-1] if parts else stem) + ext
                else:
                    name = f"{d['stem'][:3]}_{fn}" if len(docs) > 1 else fn
                dst = os.path.join(assets, dest_sub, name)
                if os.path.exists(dst):
                    skipped.append(dst)
                    continue
                if not args.dry_run:
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    shutil.copy2(src, dst)
                copied.append((src, dst))

    if logo:
        dst = os.path.join(assets, "logo" + os.path.splitext(logo)[1])
        if not os.path.exists(dst):
            if not args.dry_run:
                os.makedirs(assets, exist_ok=True)
                shutil.copy2(logo, dst)
            copied.append((logo, dst))

    tag = "would copy" if args.dry_run else "copied"
    print(f"{tag} {len(copied)} image(s); {len(skipped)} already present")
    by_dest: dict[str, int] = {}
    for _, dst in copied:
        # The logo lands directly in assets/, so key it by filename rather than
        # by parent directory or it reports as "assets/assets/".
        parent = os.path.dirname(dst)
        label = os.path.basename(dst) if os.path.normpath(parent) == os.path.normpath(assets) \
            else os.path.basename(parent) + "/"
        by_dest[label] = by_dest.get(label, 0) + 1
    for k, v in sorted(by_dest.items()):
        print(f"  assets/{k}" + (f"  {v}" if not k.endswith((".png", ".jpg", ".jpeg")) else ""))
    if unclassified:
        print("\nNOT harvested — extracted but never filed by category:")
        for stem, n in unclassified:
            print(f"  {stem}: {n} image(s) in kb/{stem}/_work/images/_raw/")
        print("  Write _work/image_plan.json and run annual-report-kb's apply_plan.py, "
              "then re-run harvest. Until then these cannot be mapped to "
              "people/products/plants.")
    if not copied and not skipped and not unclassified:
        print("  nothing to harvest — has the KB been built?")
    if copied or skipped:
        print("\nThese came out of the company's own filings, so provenance is sound. "
              "Still check each director photo is the right person before it goes on a "
              "card — same-name group companies are a real trap.")


def cmd_index(args):
    docs = discover(args.root)
    lines = ["# Source document knowledge bases", "",
             "Built by `docs_kb.py` from `inputs/` using the `annual-report-kb` skill.",
             "Read these instead of opening the PDFs.", ""]
    lines.append("| Document | Pages | Depth | KB | Built |")
    lines.append("|---|---|---|---|---|")
    for d in docs:
        kb = kb_path(args.root, d["stem"])
        built = "yes" if os.path.exists(os.path.join(kb, "manifest.json")) else \
                ("partial" if os.path.isdir(kb) else "no")
        rel = os.path.relpath(kb, args.root).replace("\\", "/")
        lines.append(f"| `{d['file']}` | {d['pages'] or '?'} | {d['depth']} | `{rel}/` | {built} |")

    lines += ["", "## Where to look", "",
              "| Need | Path |", "|---|---|",
              "| a specific page | `<kb>/pages/page_NNNN.md` |",
              "| a financial table | `<kb>/tables/` + `<kb>/metadata/table_index.json` |",
              "| directors, plants, subsidiaries, products | `<kb>/entities/*.json` |",
              "| a topic summary | `<kb>/context/*.md` |",
              "| a whole section | `<kb>/sections/` |",
              "| images | `<kb>/images/<category>/` |", "",
              "Every table, entity and context claim carries the page it came from. "
              "Quote that page in the report.", ""]
    os.makedirs(os.path.join(args.root, "kb"), exist_ok=True)
    p = os.path.join(args.root, "kb", "INDEX.md")
    open(p, "w", encoding="utf-8").write("\n".join(lines))
    print(f"wrote {p}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--root", required=True, help="reports/<TICKER>")
    ap.add_argument("--arkb", help="path to the annual-report-kb skill")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("plan", help="inventory the PDFs and estimate the work")
    p.set_defaults(fn=cmd_plan)

    r = sub.add_parser("run", help="build a KB for each document")
    r.add_argument("--doc", help="only this document (stem or filename)")
    r.add_argument("--chunk-size", default=None)
    r.add_argument("--mode")
    r.add_argument("--pages", help="e.g. 0-19 for a smoke test")
    r.add_argument("--force", action="store_true", help="rebuild even if already built")
    r.add_argument("--force-ocr", action="store_true",
                   help="ignore preflight and attempt OCR anyway")
    r.set_defaults(fn=cmd_run)

    h = sub.add_parser("harvest", help="copy classified images into assets/")
    h.add_argument("--dry-run", action="store_true")
    h.set_defaults(fn=cmd_harvest)

    i = sub.add_parser("index", help="(re)write kb/INDEX.md")
    i.set_defaults(fn=cmd_index)

    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
