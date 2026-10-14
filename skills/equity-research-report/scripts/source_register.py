"""source_register.py - what the report was built from, fingerprinted.

Every input document gets an ID, a SHA-256 content hash, its size, page count and file date, so a
reviewer can confirm they hold the same document and see when it entered the pipeline. Each
knowledge base is checked against its input: a KB built from a different file than the one in
inputs/ is a silent version mismatch. External (web) sources cited as evidence are listed with
whatever URL and date the citation carries, and flagged where it carries none.

    python source_register.py --root reports/<T>

Writes data/source_register.json. Exit 1 if a knowledge base does not match its input file.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime

KIND = [(r"annual_report|\bar\b", "annual report"), (r"concall|call", "earnings call transcript"),
        (r"investor_presentation|ambition|deck", "investor presentation"), (r"shareholding", "shareholding pattern"),
        (r"screener", "Screener.in export"), (r"q\dfy\d\d|results|operational", "quarterly results / operational update"),
        (r"peers/", "peer export")]


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def pages(path):
    if not path.lower().endswith(".pdf"):
        return None
    try:
        import pypdfium2 as pdfium
        return len(pdfium.PdfDocument(path))
    except Exception:
        return None


def build(root):
    inp = os.path.join(root, "inputs")
    docs = []
    for dp, _, files in os.walk(inp):
        for f in sorted(files):
            if not f.lower().endswith((".pdf", ".xlsx", ".xls", ".csv")):
                continue
            p = os.path.join(dp, f)
            rel = os.path.relpath(p, root).replace("\\", "/")
            kind = next((k for pat, k in KIND if re.search(pat, rel, re.I)), "other")
            docs.append({"id": f"SRC-{len(docs) + 1:02d}", "path": rel, "kind": kind, "sha256": sha256(p),
                         "bytes": os.path.getsize(p), "pages": pages(p),
                         "file_date": datetime.fromtimestamp(os.path.getmtime(p)).date().isoformat()})
    by_hash = {d["sha256"]: d for d in docs}
    kbs, mismatches = [], []
    kb_root = os.path.join(root, "kb")
    for name in sorted(os.listdir(kb_root)) if os.path.isdir(kb_root) else []:
        pdf = os.path.join(kb_root, name, "report.pdf")
        if not os.path.exists(pdf):
            continue
        h = sha256(pdf)
        src = by_hash.get(h)
        guess = next((d for d in docs if os.path.splitext(os.path.basename(d["path"]))[0] == name), None)
        row = {"kb": f"kb/{name}", "sha256": h, "built_from": src["id"] if src else None,
               "status": "MATCH" if src else ("MISMATCH" if guess else "NO_INPUT_COPY")}
        if row["status"] == "MISMATCH":
            row["why"] = f"kb/{name}/report.pdf differs from {guess['path']}: the knowledge base is not built from the input on file"
            mismatches.append(row)
        kbs.append(row)
    # external sources cited as evidence
    ext = []
    D = json.load(open(os.path.join(root, "decisions.json"), encoding="utf-8"))
    for key, a in (D.get("assumptions") or {}).items():
        for e in a.get("evidence") or []:
            s = str(e.get("source") or "")
            if s.startswith(("kb/", "inputs/", "data/")) or "kb/" in s or not s:
                continue
            url = re.search(r"https?://\S+|[a-z0-9.-]+\.(?:com|in|org|net)(?:/\S*)?", s, re.I)
            date = re.search(r"\b\d{1,2} [A-Z][a-z]{2,8} 20\d\d\b|\b20\d\d-\d\d-\d\d\b|\b[A-Z][a-z]{2,8} 20\d\d\b", s)
            ext.append({"assumption": key, "source": s[:160], "url": url.group(0) if url else None,
                        "dated": date.group(0) if date else None,
                        "gap": ", ".join(g for g, ok in (("no URL", url), ("no date", date)) if not ok) or None})
    out = {"built_at": datetime.now().isoformat(timespec="seconds"), "documents": docs, "knowledge_bases": kbs,
           "external_sources": ext, "status": "FAIL" if mismatches else "PASS"}
    json.dump(out, open(os.path.join(root, "data", "source_register.json"), "w", encoding="utf-8"), indent=1,
              ensure_ascii=False)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--root", required=True)
    a = ap.parse_args()
    out = build(os.path.abspath(a.root))
    for d in out["documents"]:
        print(f"  {d['id']}  {d['kind']:38} {d['path']:44} {d['pages'] or '':>4}p  {d['sha256'][:12]}  {d['file_date']}")
    for k in out["knowledge_bases"]:
        print(f"  {k['kb']:28} {k['status']:13} {k.get('built_from') or ''} {k.get('why') or ''}")
    gaps = [e for e in out["external_sources"] if e["gap"]]
    print(f"{len(out['documents'])} documents, {len(out['knowledge_bases'])} knowledge bases, "
          f"{len(out['external_sources'])} external citations ({len(gaps)} missing a URL or date) -> {out['status']}")
    sys.exit(1 if out["status"] == "FAIL" else 0)


if __name__ == "__main__":
    main()
