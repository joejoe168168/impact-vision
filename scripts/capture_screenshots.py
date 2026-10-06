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
                clip = {"x": box["x"] - 8, "y": box["y"] - 8, "width": box["width"] + 16,
                        "height": min(box["height"] + 16, max_h or 10_000)}
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
        browser.close()
    written.append(pdf_contact_sheet())
    return written


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
    args = parser.parse_args()
    files = capture(args.chat_url)
    DEMO_SHOTS.mkdir(exist_ok=True)
    for f in files:
        shutil.copy2(f, DEMO_SHOTS / f.name)
    for f in files:
        print("wrote", f.relative_to(REPO))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
