"""Capture the README / demo screenshots from the generated demo bundle.

    python demo/generate_demo.py
    python scripts/capture_screenshots.py [--chat-url http://127.0.0.1:8787/]

Needs Playwright with Chromium (``pip install 'impact-vision[pdf]' &&
playwright install chromium``) or ``IMPACT_VISION_CHROMIUM`` pointing at a
Chromium binary. Writes PNGs to docs/images/ (README) and demo/screenshots/.
"""
from __future__ import annotations

import argparse
import os
import shutil
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DEMO = REPO / "demo"
OUT = REPO / "docs" / "images"
DEMO_SHOTS = DEMO / "screenshots"

PIG = DEMO / "kampung_makmur_sdn_bhd" / "kampung_makmur_sdn_bhd"
SOLAR = DEMO / "sunpath_energy_ltd" / "sunpath_energy_ltd"

# name, file, width, colour scheme, selector (None = top of page), max height
SHOTS = [
    ("report-overview", f"{PIG}_impact_report.html", 1240, "light", None, 1180),
    ("report-glance", f"{SOLAR}_impact_report.html", 1240, "light", "#sec-glance", None),
    ("report-5d", f"{SOLAR}_impact_report.html", 1240, "light", "#sec-5d", None),
    ("report-sdg", f"{PIG}_impact_report.html", 1240, "light", "#sec-sdg", None),
    ("report-evidence", f"{PIG}_impact_report.html", 1240, "light", "#sec-evidence", 900),
    ("report-greenwashing", f"{PIG}_impact_report.html", 1240, "light", "#sec-greenwashing", None),
    ("report-dark", f"{SOLAR}_impact_report.html", 1240, "dark", None, 1180),
    ("report-zh-hk", f"{PIG}_impact_report_zh-HK.html", 1240, "light", None, 1180),
    ("report-mobile", f"{SOLAR}_impact_report.html", 390, "light", None, 1500),
    ("ic-memo", f"{PIG}_ic_memo.html", 1240, "light", None, 1100),
    ("dd-report", f"{PIG}_dd_report.html", 1240, "light", None, 1100),
    ("investee-portal", f"{PIG}_investee_portal.html", 1240, "light", None, 1000),
    ("gallery", str(DEMO / "index.html"), 1240, "light", None, 1100),
    ("portfolio-home", str(DEMO / "portfolio_home.html"), 1300, "light", None, 1250),
    ("engagements", str(DEMO / "engagements.html"), 1300, "light", None, 1000),
]


def _browser(pw):  # type: ignore[no-untyped-def]
    return pw.chromium.launch(executable_path=os.environ.get("IMPACT_VISION_CHROMIUM") or None)


def capture(chat_url: str | None) -> list[Path]:
    from playwright.sync_api import sync_playwright

    OUT.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    with sync_playwright() as pw:
        browser = _browser(pw)
        for name, file, width, scheme, selector, max_h in SHOTS:
            page = browser.new_page(viewport={"width": width, "height": 900}, color_scheme=scheme,
                                    device_scale_factor=2 if width < 600 else 1.5)
            page.goto(Path(file).resolve().as_uri())
            page.wait_for_timeout(250)
            out = OUT / f"{name}.png"
            if selector:
                element = page.locator(selector)
                box = element.bounding_box()
                height = box["height"] + 16
                if max_h and height > max_h:
                    # Cut at the last table row / block that fits, never mid-row.
                    height = page.evaluate(
                        """([sel, top, limit]) => {
                            let best = 0;
                            for (const el of document.querySelector(sel).querySelectorAll('tr, p, h2, h3')) {
                                const b = el.getBoundingClientRect().bottom + window.scrollY - top;
                                if (b <= limit && b > best) best = b;
                            }
                            return best;
                        }""", [selector, box["y"] - 8, max_h]) + 12 or max_h
                clip = {"x": box["x"] - 8, "y": box["y"] - 8, "width": box["width"] + 16, "height": height}
                page.screenshot(path=str(out), clip=clip, full_page=True)
            else:
                height = page.evaluate("document.documentElement.scrollHeight")
                page.screenshot(path=str(out), full_page=True,
                                clip={"x": 0, "y": 0, "width": width, "height": min(height, max_h)})
            page.close()
            written.append(out)
        if chat_url:
            page = browser.new_page(viewport={"width": 1360, "height": 860}, color_scheme="light",
                                    device_scale_factor=1.5)
            page.goto(chat_url)
            page.wait_for_timeout(1500)
            out = OUT / "web-chat.png"
            page.screenshot(path=str(out))
            written.append(out)
            # Report viewer: needs at least one saved report in the web app's home
            # (python scripts/capture_screenshots.py --seed-web <dir> prepares one).
            page.click("#togglePanel")  # the right panel starts collapsed
            page.wait_for_timeout(300)
            page.click(".panel-tabs button[data-tab=reports]")
            page.wait_for_timeout(500)
            if page.locator(".rep").count():
                page.locator(".rep").first.click()
                page.wait_for_timeout(2500)
                out = OUT / "web-report-viewer.png"
                page.screenshot(path=str(out))
                written.append(out)
        written.append(cli_shot(browser))
        browser.close()
    written.append(pdf_contact_sheet())
    return written


def cli_shot(browser) -> Path:  # noqa: ANN001
    """`impact-vision assess` on a sample deck, rendered as a terminal window.

    Runs the real command offline (no API key) in a temp folder so the printed
    paths are short, then screenshots the output in a terminal-style frame.
    """
    import html
    import subprocess
    import sys
    import tempfile

    deck = REPO / "data" / "sample_decks" / "sunpath_solar.pdf"
    with tempfile.TemporaryDirectory() as tmp:
        shutil.copy2(deck, Path(tmp) / deck.name)
        cmd = [sys.executable, "-m", "openharness", "assess", deck.name, "-o", "reports"]
        env = dict(os.environ, COLUMNS="100", PYTHONPATH=str(REPO / "src"))
        out = subprocess.run(cmd, cwd=tmp, env=env, capture_output=True, text=True, timeout=300).stdout
    body = html.escape(out.rstrip())
    body = body.replace("INSUFFICIENT EVIDENCE", '<b class="amber">INSUFFICIENT EVIDENCE</b>')
    body = "\n".join(
        f'<span class="dim">{line[:18]}</span>{line[18:]}' if line.startswith("  ") and ":" in line[:18] else line
        for line in body.splitlines()
    )
    page_html = f"""<!doctype html><meta charset="utf-8"><style>
body{{margin:0;background:#e9e8e3;padding:28px;font-family:system-ui,sans-serif}}
.win{{max-width:1020px;background:#0f1115;border-radius:12px;box-shadow:0 10px 30px rgba(0,0,0,.25);overflow:hidden}}
.bar{{background:#1c1f26;padding:10px 14px;display:flex;gap:8px;align-items:center;color:#9aa0a6;font-size:13px}}
.bar i{{width:12px;height:12px;border-radius:50%;display:inline-block}}
pre{{margin:0;padding:18px 22px 22px;color:#e6e6e6;font:15px/1.55 ui-monospace,Menlo,Consolas,monospace;white-space:pre-wrap}}
.p{{color:#7ee787}} .dim{{color:#9aa0a6}} .amber{{color:#f2c14e}}
</style><div class="win"><div class="bar"><i style="background:#ff5f57"></i><i style="background:#febc2e"></i>
<i style="background:#28c840"></i><span style="margin-left:8px">impact-vision — no API key</span></div>
<pre><span class="p">$</span> impact-vision assess {deck.name} -o reports
{body}</pre></div>"""
    page = browser.new_page(viewport={"width": 1080, "height": 600}, device_scale_factor=1.5)
    page.set_content(page_html)
    out_path = OUT / "cli-assess.png"
    page.locator(".win").screenshot(path=str(out_path))
    page.close()
    return out_path


def seed_web(home: Path) -> None:
    """Fill a fresh web-app home with the three sample-deck reports."""
    import sys

    os.environ["IMPACT_VISION_WEB_HOME"] = str(home)
    os.environ.setdefault("IMPACT_VISION_DB", str(home / "impact_vision.db"))
    sys.path.insert(0, str(REPO / "src"))
    from openharness.impact.pipeline import SAMPLE_DECKS, sample_deck_path
    from openharness.web.reports_api import create_report

    home.mkdir(parents=True, exist_ok=True)
    for key in SAMPLE_DECKS:
        record = create_report(sample_deck_path(key))
        print(f"[seed] {record.get('company')} -> {home}")


def pdf_contact_sheet() -> Path:
    """First four pages of the impact-report PDF side by side."""
    import pymupdf
    from PIL import Image

    doc = pymupdf.open(f"{PIG}_impact_report.pdf")
    tiles = []
    for i in range(min(4, len(doc))):
        pix = doc[i].get_pixmap(dpi=70)
        tmp = OUT / f".page{i}.png"
        pix.save(tmp)
        tiles.append(Image.open(tmp).convert("RGB"))
        tmp.unlink()
    w, h = tiles[0].size
    gap = 24
    sheet = Image.new("RGB", (len(tiles) * w + (len(tiles) + 1) * gap, h + 2 * gap), "#e9e8e3")
    for i, tile in enumerate(tiles):
        sheet.paste(tile, (gap + i * (w + gap), gap))
    out = OUT / "report-pdf.png"
    sheet.save(out)
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--chat-url", help="URL of a running `impact-vision serve-web` to capture")
    parser.add_argument("--seed-web", metavar="DIR",
                        help="Create sample reports in a fresh web-app home DIR, then exit "
                             "(start serve-web with IMPACT_VISION_WEB_HOME=DIR to capture it)")
    args = parser.parse_args()
    if args.seed_web:
        seed_web(Path(args.seed_web))
        return 0
    files = capture(args.chat_url)
    DEMO_SHOTS.mkdir(exist_ok=True)
    for f in files:
        shutil.copy2(f, DEMO_SHOTS / f.name)
    for f in files:
        print("wrote", f.relative_to(REPO))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
