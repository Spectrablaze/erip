#!/usr/bin/env python3
"""Stage 0 - check the environment and the PDF, then recommend parse settings.

Run this before every parse. It answers the two questions that decide whether a
multi-hour run will succeed:

  1. Is a surya inference backend actually usable on this machine?
     Marker routes OCR through surya, which auto-selects a backend:
       * an NVIDIA GPU is detected  -> "vllm", which spawns a **Docker** container
       * otherwise                  -> "llamacpp", which needs a `llama-server` binary
     Detection probes nvidia-smi and ignores whether torch can actually use the
     GPU, so a CPU-only torch build on a GPU laptop still selects vllm and dies
     with `SpawnError: docker run failed` the first time a page needs OCR -
     often an hour into the run.

  2. Does the PDF have a real text layer?
     If it does, --disable-ocr avoids the VLM entirely and parses fine. If it is
     scanned, --disable-ocr would yield blank pages and a working backend is
     mandatory.

Writes preflight.json next to the work directory when --work is given.

Usage:
    python preflight.py REPORT.pdf
    python preflight.py REPORT.pdf --work "<Company> AR/_work"
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

OK, WARN, BAD = "OK", "WARN", "FAIL"


def log(msg: str) -> None:
    print(msg, flush=True)


def check_marker() -> dict:
    try:
        from importlib.metadata import version
        return {"status": OK, "marker_version": version("marker-pdf")}
    except Exception as e:  # noqa: BLE001
        return {"status": BAD, "error": f"marker-pdf not installed ({e}). "
                                        "Install with: pip install marker-pdf"}


def check_torch() -> dict:
    try:
        import torch
    except Exception as e:  # noqa: BLE001
        return {"status": BAD, "error": f"torch missing: {e}"}
    cuda = torch.cuda.is_available()
    build_cpu_only = "+cpu" in torch.__version__
    out = {"status": OK, "torch_version": torch.__version__,
           "cuda_available": cuda, "cpu_only_build": build_cpu_only}
    if cuda:
        try:
            out["gpu"] = torch.cuda.get_device_name(0)
        except Exception:  # noqa: BLE001
            pass
    return out


def check_gpu_present() -> bool:
    """Mirror surya's own probe: does a GPU exist on the host at all?"""
    if os.path.exists("/dev/nvidia0"):
        return True
    smi = shutil.which("nvidia-smi")
    if not smi:
        return False
    try:
        r = subprocess.run([smi, "-L"], capture_output=True, text=True, timeout=15)
        return r.returncode == 0 and "GPU" in r.stdout
    except Exception:  # noqa: BLE001
        return False


def check_docker() -> bool:
    exe = shutil.which("docker")
    if not exe:
        return False
    try:
        r = subprocess.run([exe, "info"], capture_output=True, text=True, timeout=25)
        return r.returncode == 0
    except Exception:  # noqa: BLE001
        return False


def check_backend() -> dict:
    """Work out which backend surya will pick and whether it can start."""
    forced = os.environ.get("SURYA_INFERENCE_BACKEND")
    try:
        from surya.settings import settings as ssettings
        forced = forced or ssettings.SURYA_INFERENCE_BACKEND
    except Exception:  # noqa: BLE001
        pass

    gpu = check_gpu_present()
    backend = (forced or ("vllm" if gpu else "llamacpp")).lower()
    info = {"selected_backend": backend, "forced": bool(forced), "gpu_detected": gpu}

    if backend == "vllm":
        docker = check_docker()
        info["docker_running"] = docker
        info["status"] = OK if docker else BAD
        if not docker:
            info["error"] = (
                "surya selected the 'vllm' backend (an NVIDIA GPU is present) but "
                "Docker is not running, so OCR will fail mid-parse."
            )
            info["remedies"] = [
                "Parse with --disable-ocr (works only if the PDF has a text layer)",
                "Start Docker Desktop and re-run",
                "Force the CPU backend: set SURYA_INFERENCE_BACKEND=llamacpp "
                "and install a llama-server binary",
            ]
    else:
        binary = os.environ.get("LLAMA_CPP_BINARY")
        found = (binary if binary and os.path.isfile(binary) else shutil.which(binary or "llama-server"))
        info["llama_server"] = found
        info["status"] = OK if found else BAD
        if not found:
            info["error"] = ("surya selected the 'llamacpp' backend but no `llama-server` "
                             "binary is on PATH, so OCR will fail mid-parse.")
            info["remedies"] = [
                "Parse with --disable-ocr (works only if the PDF has a text layer)",
                "Install llama.cpp and put llama-server on PATH, or set LLAMA_CPP_BINARY",
            ]
    return info


def check_pdf(pdf: Path, sample: int = 24) -> dict:
    try:
        import pypdfium2
    except Exception as e:  # noqa: BLE001
        return {"status": BAD, "error": f"pypdfium2 missing: {e}"}

    try:
        doc = pypdfium2.PdfDocument(str(pdf))
    except Exception as e:  # noqa: BLE001
        return {"status": BAD, "error": f"cannot open PDF: {e}"}

    n = len(doc)
    idxs = sorted({int(i * (n - 1) / max(sample - 1, 1)) for i in range(min(sample, n))})
    counts = []
    for i in idxs:
        page = textpage = None
        try:
            page = doc[i]
            textpage = page.get_textpage()
            counts.append(len(textpage.get_text_range().strip()))
        except Exception:  # noqa: BLE001
            counts.append(0)
        finally:
            # pypdfium2 warns loudly at exit about handles left open
            for obj in (textpage, page):
                try:
                    obj.close()
                except Exception:  # noqa: BLE001
                    pass

    counts.sort()
    median = counts[len(counts) // 2] if counts else 0
    with_text = sum(1 for c in counts if c > 100)
    ratio = with_text / max(len(counts), 1)
    digital = ratio >= 0.6 and median >= 200

    return {
        "status": OK,
        "pages": n,
        "size_mb": round(pdf.stat().st_size / 1e6, 1),
        "sampled_pages": len(counts),
        "median_chars_per_page": median,
        "pages_with_text_ratio": round(ratio, 2),
        "has_text_layer": digital,
        "kind": "digital" if digital else ("mixed" if ratio > 0.2 else "scanned"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Preflight checks for an annual report parse")
    ap.add_argument("pdf")
    ap.add_argument("--work", default=None)
    args = ap.parse_args()

    pdf = Path(args.pdf).expanduser().resolve()
    if not pdf.exists():
        log(f"FAIL: no such PDF: {pdf}")
        return 2

    log("=" * 66)
    log(f"PREFLIGHT  {pdf.name}")
    log("=" * 66)

    report = {"pdf": str(pdf)}
    report["marker"] = check_marker()
    report["torch"] = check_torch()
    report["backend"] = check_backend()
    report["document"] = check_pdf(pdf)

    m, t, b, d = report["marker"], report["torch"], report["backend"], report["document"]
    log(f"marker        : {m.get('marker_version', m.get('error'))}")
    log(f"torch         : {t.get('torch_version')}  cuda_usable={t.get('cuda_available')}"
        + ("  [CPU-ONLY BUILD]" if t.get("cpu_only_build") else ""))
    log(f"surya backend : {b['selected_backend']}"
        + (f"  docker_running={b.get('docker_running')}" if b["selected_backend"] == "vllm"
           else f"  llama_server={b.get('llama_server')}")
        + f"   -> {b['status']}")
    if d.get("status") == OK:
        log(f"document      : {d['pages']} pages, {d['size_mb']} MB, kind={d['kind']}, "
            f"median {d['median_chars_per_page']} chars/page")
    else:
        log(f"document      : {d.get('error')}")

    # ---- recommendation --------------------------------------------------
    device = "cuda" if t.get("cuda_available") else "cpu"
    mode = "balanced" if device == "cuda" else "fast"
    backend_ok = b.get("status") == OK
    digital = d.get("has_text_layer")

    log("-" * 66)
    blocking = []
    if m.get("status") == BAD:
        blocking.append(m["error"])
    if d.get("status") == BAD:
        blocking.append(d["error"])

    if not backend_ok and not digital:
        blocking.append(
            "No usable OCR backend AND the PDF has no reliable text layer. "
            "Parsing now would produce blank pages. " + (b.get("error") or ""))

    disable_ocr = (not backend_ok) and bool(digital)

    if blocking:
        report["recommendation"] = {"can_parse": False, "blocking": blocking}
        log("CANNOT PARSE YET:")
        for x in blocking:
            log(f"  - {x}")
        for r in b.get("remedies", []):
            log(f"  fix: {r}")
    else:
        pages = d.get("pages") or 0
        # Measured: ~1.1 s/page on an 8-core CPU, fast mode, --disable-ocr.
        # Leaving OCR on costs several times that, since every unresolved block
        # is a VLM round-trip.
        per_page = 0.5 if device == "cuda" else (1.2 if disable_ocr else 4.0)
        eta_min = round(pages * per_page / 60)
        cmd = (f'python scripts/parse_pdf.py "{pdf.name}" --work "<OUT>/_work" '
               f'--mode {mode} --chunk-size 25' + (' --disable-ocr' if disable_ocr else ''))
        report["recommendation"] = {
            "can_parse": True, "mode": mode, "device": device,
            "disable_ocr": disable_ocr, "chunk_size": 25,
            "estimated_minutes": eta_min, "command": cmd,
        }
        log(f"RECOMMENDED   : mode={mode}, device={device}, "
            f"disable_ocr={disable_ocr}, chunk_size=25")
        log(f"ETA           : ~{eta_min} min for {pages} pages "
            f"(first run adds several minutes of model downloads)")
        if disable_ocr:
            log("NOTE          : running text-layer only because no OCR backend is "
                "usable. Digital text extracts fine; a few complex tables may come "
                "out partial. parse_report.md will flag empty pages.")
        log(f"COMMAND       : {cmd}")

    if args.work:
        wp = Path(args.work).expanduser().resolve()
        wp.mkdir(parents=True, exist_ok=True)
        (wp / "preflight.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        log(f"wrote {wp / 'preflight.json'}")

    log("=" * 66)
    return 0 if report.get("recommendation", {}).get("can_parse") else 1


if __name__ == "__main__":
    sys.exit(main())
