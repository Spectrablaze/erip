#!/usr/bin/env python3
"""
render.py — HTML -> print-ready PDF, with a pre-flight QA gate.

    python3 render.py companies/EICHERMOT/report.html -o "Eicher Motors - Equity Research.pdf"

The gate runs BEFORE rendering and blocks on anything that would embarrass you in a
published report: missing image files, leftover placeholder text, empty table cells,
unresolved TODOs. Use --force to render anyway (it still prints the findings).
"""
from __future__ import annotations

import argparse
import contextlib
import os
import pathlib
import posixpath
import re
import shutil
import subprocess
import sys
import tempfile
from html.parser import HTMLParser

# Hard failures — these must never reach a PDF.
PLACEHOLDERS = [
    r"\bTODO\b", r"\bTBD\b", r"\bFIXME\b", r"\bLorem ipsum",
    r"\[insert", r"\[placeholder", r"\{\{\s*\w+\s*\}\}",
    r"\bundefined\b", r"\bNaN\b", r"\bnull\b", r"missing-asset",
]
# Soft — legitimate in an academic report (the samples print "XXX" for the rating),
# but worth a look before you publish.
SOFT = [r"\bXXX\b", r"\bN/?A\b"]


class _Scan(HTMLParser):
    def __init__(self):
        super().__init__()
        self.imgs, self.pages, self.text = [], 0, []
        self._in_style = False

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag == "img" and d.get("src"):
            self.imgs.append(d["src"])
        if tag in ("object", "embed") and d.get("data"):
            self.imgs.append(d["data"])
        if tag == "section" and "page" in (d.get("class") or "").split():
            self.pages += 1
        if tag == "style":
            self._in_style = True

    def handle_endtag(self, tag):
        if tag == "style":
            self._in_style = False

    def handle_data(self, data):
        if not self._in_style:
            self.text.append(data)


def preflight(html_path: str) -> tuple[list, list, int]:
    src = open(html_path, encoding="utf-8").read()
    base = os.path.dirname(os.path.abspath(html_path))
    s = _Scan()
    s.feed(src)

    errors, warns = [], []

    for ref in s.imgs:
        if ref.startswith(("http://", "https://", "data:")):
            warns.append(f"remote image (will fail offline): {ref}")
            continue
        p = os.path.normpath(os.path.join(base, ref))
        if not os.path.exists(p):
            errors.append(f"missing image file: {ref}")
        elif os.path.getsize(p) == 0:
            errors.append(f"zero-byte image: {ref}")

    # Duplicate chart titles: charts.py renders axes titles at 8.6px (axes.titlesize).
    # A title baked into the SVG plus the HTML's <div class="fig-title"> prints the
    # same words twice at two sizes — SKILL.md rule 1 of section 5.
    for ref in s.imgs:
        if not ref.lower().endswith(".svg") or ref.startswith(("http", "data:")):
            continue
        p = os.path.normpath(os.path.join(base, ref))
        if not os.path.exists(p):
            continue
        try:
            svg = open(p, encoding="utf-8", errors="ignore").read()
        except OSError:
            continue
        baked = re.findall(r'font-size:\s*8\.6px[^>]*>([^<]{3,})</text>', svg)
        if baked:
            warns.append(
                f"chart has a title baked into the SVG: {ref} -> {baked[0]!r}. "
                f"Re-generate without title= (the HTML .fig-title is the title).")

    body = " ".join(s.text)
    for pat in PLACEHOLDERS:
        hay = src if "missing-asset" in pat else body
        for m in set(re.findall(pat, hay, re.I)):
            errors.append(f"placeholder text left in document: {m!r}")
    for pat in SOFT:
        n = len(re.findall(pat, body))
        if n:
            warns.append(f"{n}x {pat.strip(chr(92)+'b')!r} in the text — intentional?")

    # Empty table cells are usually a data-plumbing bug, not a design choice
    empties = len(re.findall(r"<td[^>]*>\s*</td>", src))
    if empties:
        warns.append(f"{empties} empty <td> cells — confirm these are intentional")

    if not re.search(r'href=[\'"][^\'"]*report\.css', src) and "<style" not in src:
        errors.append("report.css is not linked and there is no inline <style>")

    # A company palette that exists but is not linked — or is linked before
    # report.css — is silently discarded, and the report ships in house colours.
    if os.path.exists(os.path.join(base, "brand.css")):
        m_report = re.search(r'href=[\'"][^\'"]*report\.css', src)
        m_brand = re.search(r'href=[\'"][^\'"]*brand\.css', src)
        if not m_brand:
            errors.append("brand.css exists but is not linked — the company palette "
                          "will be ignored and the report ships in house colours")
        elif m_report and m_brand.start() < m_report.start():
            errors.append("brand.css is linked BEFORE report.css — report.css will "
                          "overwrite the company palette. Swap the two <link> tags.")

    # An update note is a legitimately short document — `research-note-update` links
    # update.css on top of report.css. Without this the page-count warning fires on
    # every note ever rendered, and a warning that is always on is noise.
    is_update = bool(re.search(r'href=[\'"][^\'"]*update\.css', src))
    if is_update:
        if not 2 <= s.pages <= 8:
            warns.append(f"{s.pages} .page sections — an update note runs 2-8 pages")
    elif s.pages < 20:
        warns.append(f"only {s.pages} .page sections — the reference reports run 32-45 pages")

    return errors, warns, s.pages


# --------------------------------------------------------------------------
# Render engines
#
# report.css uses CSS Paged Media margin boxes (@top-left, string(disclaimer))
# and named pages (@page cover). Only WeasyPrint implements those. A browser
# engine lays the pages out correctly but silently DROPS the running headers,
# so it is a fallback, not an equal. Preference order is deliberate:
#
#   weasyprint  native import          full fidelity
#   wsl         WeasyPrint inside WSL   full fidelity  (Windows escape hatch)
#   chromium    headless Chrome/Edge    layout only, no running headers
# --------------------------------------------------------------------------

CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
]


@contextlib.contextmanager
def _muted():
    """Silence stdout+stderr at the fd level. WeasyPrint prints a multi-line
    banner when its native libraries are missing, and in auto mode the probe
    runs on every render."""
    saved = {}
    devnull = None
    try:
        devnull = open(os.devnull, "w")
        for stream in (sys.stdout, sys.stderr):
            try:
                fd = stream.fileno()
                saved[fd] = os.dup(fd)
                stream.flush()
                os.dup2(devnull.fileno(), fd)
            except Exception:
                continue
    except Exception:
        pass
    try:
        yield
    finally:
        # Flush BEFORE restoring: piped stdout is block-buffered, so anything
        # still in the buffer would otherwise drain onto the restored fd.
        for stream in (sys.stdout, sys.stderr):
            try:
                stream.flush()
            except Exception:
                pass
        for fd, dup in saved.items():
            try:
                os.dup2(dup, fd)
                os.close(dup)
            except Exception:
                pass
        if devnull is not None:
            devnull.close()


def find_weasyprint() -> bool:
    with _muted():
        try:
            import weasyprint  # noqa: F401
            return True
        except Exception:
            return False


def find_wsl_distro() -> str | None:
    """Name of a WSL distro whose python3 can import weasyprint, else None."""
    if os.name != "nt" or not shutil.which("wsl"):
        return None
    try:
        raw = subprocess.run(["wsl", "--list", "--quiet"],
                             capture_output=True, timeout=30).stdout
        names = raw.decode("utf-16le", errors="ignore").replace("\r", "").split("\n")
    except Exception:
        return None
    for name in (n.strip() for n in names):
        if not name or "docker" in name.lower():
            continue
        try:
            probe = subprocess.run(
                ["wsl", "-d", name, "--", "python3", "-c", "import weasyprint"],
                capture_output=True, timeout=90)
            if probe.returncode == 0:
                return name
        except Exception:
            continue
    return None


def find_chromium() -> str | None:
    for exe in CHROME_CANDIDATES:
        if os.path.exists(exe):
            return exe
    for name in ("chromium", "chromium-browser", "google-chrome", "chrome"):
        found = shutil.which(name)
        if found:
            return found
    return None


def _render_weasyprint(html_path: str, out_pdf: str) -> None:
    from weasyprint import HTML
    base = os.path.dirname(os.path.abspath(html_path)) or "."
    HTML(filename=html_path, base_url=base).write_pdf(out_pdf)


def _render_wsl(distro: str, html_path: str, out_pdf: str) -> None:
    def to_wsl(p: str) -> str:
        r = subprocess.run(
            ["wsl", "-d", distro, "--", "wslpath", "-a",
             os.path.abspath(p).replace("\\", "/")],
            capture_output=True, text=True, timeout=60)
        if r.returncode != 0 or not r.stdout.strip():
            raise RuntimeError(f"wslpath failed for {p}")
        return r.stdout.strip()

    src, dst = to_wsl(html_path), to_wsl(out_pdf)
    script = ("import sys; from weasyprint import HTML; "
              "HTML(filename=sys.argv[1], base_url=sys.argv[2])"
              ".write_pdf(sys.argv[3])")
    r = subprocess.run(
        ["wsl", "-d", distro, "--", "python3", "-c", script,
         src, posixpath.dirname(src), dst],
        capture_output=True, text=True, timeout=900)
    if r.returncode != 0:
        raise RuntimeError(f"WSL WeasyPrint failed:\n{r.stderr.strip()[-1500:]}")


def _render_chromium(exe: str, html_path: str, out_pdf: str) -> None:
    url = pathlib.Path(os.path.abspath(html_path)).as_uri()
    out_abs = os.path.abspath(out_pdf)
    with tempfile.TemporaryDirectory() as profile:
        r = subprocess.run(
            [exe, "--headless=new", "--disable-gpu", "--no-sandbox",
             f"--user-data-dir={profile}",
             "--no-pdf-header-footer", "--print-to-pdf-no-header",
             "--run-all-compositor-stages-before-draw",
             "--virtual-time-budget=30000",
             f"--print-to-pdf={out_abs}", url],
            capture_output=True, text=True, timeout=900)
    if not os.path.exists(out_abs) or os.path.getsize(out_abs) == 0:
        raise RuntimeError(f"Chromium produced no PDF:\n{r.stderr.strip()[-1500:]}")


def resolve_engine(requested: str) -> tuple[str, object]:
    """Return (engine_name, handle). Handle is a distro/exe where relevant."""
    if requested in ("auto", "weasyprint") and find_weasyprint():
        return "weasyprint", None
    if requested == "weasyprint":
        sys.exit("WeasyPrint cannot load its native Pango/Cairo libraries.\n"
                 "Use --engine wsl or --engine chromium, or install the GTK3 runtime.")

    if requested in ("auto", "wsl"):
        distro = find_wsl_distro()
        if distro:
            return "wsl", distro
        if requested == "wsl":
            sys.exit("No WSL distro has WeasyPrint installed. Inside WSL run:\n"
                     "  sudo apt install -y python3-pip\n"
                     "  pip3 install --break-system-packages weasyprint")

    if requested in ("auto", "chromium"):
        exe = find_chromium()
        if exe:
            return "chromium", exe
        if requested == "chromium":
            sys.exit("No Chrome or Edge binary found.")

    sys.exit("No usable render engine. Install WeasyPrint, set up WSL, or install Chrome.")


def render(html_path: str, out_pdf: str, engine: str = "auto") -> str:
    name, handle = resolve_engine(engine)
    if name == "weasyprint":
        _render_weasyprint(html_path, out_pdf)
    elif name == "wsl":
        _render_wsl(handle, html_path, out_pdf)
    else:
        _render_chromium(handle, html_path, out_pdf)
    return name


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("html", nargs="?", help="report HTML (not needed with --engines)")
    ap.add_argument("-o", "--out")
    ap.add_argument("--force", action="store_true", help="render even if the gate fails")
    ap.add_argument("--check-only", action="store_true")
    ap.add_argument("--engine", default="auto",
                    choices=["auto", "weasyprint", "wsl", "chromium"],
                    help="PDF backend; auto prefers WeasyPrint, then WSL, then Chrome")
    ap.add_argument("--engines", action="store_true",
                    help="report which engines are available and exit")
    args = ap.parse_args()

    if args.engines:
        distro = find_wsl_distro()
        exe = find_chromium()
        print("render engines:")
        print(f"  weasyprint (native) : {'yes' if find_weasyprint() else 'no'}")
        print(f"  wsl                 : {distro or 'no'}")
        print(f"  chromium            : {exe or 'no'}")
        sys.exit(0)

    if not args.html:
        ap.error("the following arguments are required: html")

    errors, warns, pages = preflight(args.html)
    print(f"pre-flight: {pages} pages, {len(errors)} error(s), {len(warns)} warning(s)")
    for w in warns:
        print(f"  warn  {w}")
    for e in errors:
        print(f"  ERROR {e}")

    if args.check_only:
        sys.exit(1 if errors else 0)
    if errors and not args.force:
        sys.exit("\nBlocked. Fix the errors above, or re-run with --force.")

    out = args.out or os.path.splitext(args.html)[0] + ".pdf"
    used = render(args.html, out, args.engine)
    size = os.path.getsize(out) / 1024
    print(f"\nwrote {out}  ({size:,.0f} KB)  [engine: {used}]")

    if used == "chromium":
        print("  WARN  Chromium does not implement CSS Paged Media margin boxes.\n"
              "        The running header/footer (@top-left, @top-right) and the\n"
              "        named @page cover rule are MISSING from this PDF. Use\n"
              "        --engine wsl for a submission-grade render.")

    try:
        import subprocess
        info = subprocess.run(["pdfinfo", out], capture_output=True, text=True).stdout
        for line in info.splitlines():
            if line.startswith(("Pages", "Page size")):
                print("  " + line)
    except Exception:
        pass


if __name__ == "__main__":
    main()
