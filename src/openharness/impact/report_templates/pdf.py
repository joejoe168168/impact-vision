"""HTML → PDF for every deliverable (v7 W2.4).

Prefers headless Chromium via Playwright (the ``[pdf]`` extra): it renders the
report exactly as a browser prints it, including the print stylesheet, page
breaks and colours. Falls back to WeasyPrint when that is what's installed.

``IMPACT_VISION_CHROMIUM`` may point at an existing Chromium / headless-shell
binary (useful on servers where ``playwright install`` can't download).
"""

from __future__ import annotations

import os
from pathlib import Path

INSTALL_HINT = (
    "PDF export needs Chromium: pip install 'impact-vision[pdf]' && playwright install chromium "
    "(or set IMPACT_VISION_CHROMIUM to an existing Chromium binary). "
    "Alternatively open the HTML report and use Print → Save as PDF."
)


class PdfUnavailable(RuntimeError):
    """No PDF engine is installed."""


def _chromium(html: str, out: Path) -> None:
    from playwright.sync_api import sync_playwright  # type: ignore[import-not-found]

    executable = os.environ.get("IMPACT_VISION_CHROMIUM") or None
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=executable)
        try:
            page = browser.new_page()
            page.set_content(html, wait_until="load")
            page.emulate_media(media="print")
            # Expand the glossary like the report's beforeprint hook does.
            page.evaluate("document.querySelectorAll('details.glossary').forEach(d => d.open = true)")
            page.pdf(
                path=str(out),
                format="A4",
                print_background=True,
                prefer_css_page_size=True,
                display_header_footer=True,
                header_template="<span></span>",
                footer_template=(
                    '<div style="font-size:7pt;color:#6e6c66;width:100%;padding:0 14mm;'
                    'display:flex;justify-content:space-between;font-family:system-ui,sans-serif">'
                    '<span class="title"></span><span><span class="pageNumber"></span> / '
                    '<span class="totalPages"></span></span></div>'
                ),
                margin={"top": "16mm", "bottom": "18mm", "left": "14mm", "right": "14mm"},
            )
        finally:
            browser.close()


def _weasyprint(html: str, out: Path) -> None:
    import weasyprint  # type: ignore[import-untyped]

    document = weasyprint.HTML(string=html)
    try:
        document.write_pdf(str(out), pdf_variant="pdf/ua-1")
    except TypeError:
        document.write_pdf(str(out))


def html_to_pdf(html: str, out_path: str | Path) -> tuple[Path, str]:
    """Write *html* as a PDF; return ``(path, engine)``.

    Raises :class:`PdfUnavailable` (with an install hint) when no engine works.
    """
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    errors: list[str] = []
    for engine, render in (("chromium", _chromium), ("weasyprint", _weasyprint)):
        try:
            render(html, out)
            return out, engine
        except ImportError:
            continue
        except Exception as exc:  # noqa: BLE001 - try the next engine, report all
            errors.append(f"{engine}: {exc}")
    detail = f" ({'; '.join(errors)})" if errors else ""
    raise PdfUnavailable(INSTALL_HINT + detail)


__all__ = ["INSTALL_HINT", "PdfUnavailable", "html_to_pdf"]
