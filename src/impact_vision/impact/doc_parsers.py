"""Pluggable document parsing with OCR for scanned pages (roadmap v8 W2.3).

PDF text comes from PyMuPDF's text layer. A page with (almost) no text layer
is usually a scan or a slide exported as a picture; those pages go to an OCR
backend when one is available:

* ``command``: any local OCR or layout model with a command-line entry point
  (for example a GLM-OCR or LightOnOCR-class model). Set
  ``IMPACT_VISION_OCR_COMMAND`` to a template such as
  ``"my-ocr --image {image}"``. Each page is rendered to PNG at 200 dpi, and the
  command's stdout becomes the page text. No shell is involved and nothing
  leaves the machine.
* ``tesseract``: PyMuPDF's built-in OCR, when the ``tesseract`` binary is
  installed.

``IMPACT_VISION_DOC_PARSER`` picks the mode: ``auto`` (default: text layer,
plus OCR on pages without one), ``text`` (never OCR), ``ocr`` (OCR every page).
The structured LLM extractor (``extractors/llm_extractor.py``) then reads the
text either way.
"""
from __future__ import annotations

import logging
import os
import shlex
import shutil
import subprocess  # nosec B404
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, runtime_checkable

logger = logging.getLogger(__name__)

MIN_TEXT_CHARS = 25  # fewer characters than this on a page = no usable text layer
OCR_DPI = 200
OCR_TIMEOUT_S = 120


@dataclass
class PageText:
    page: int
    text: str
    source: str = "text"  # text | ocr:<backend>


@dataclass
class ParsedDocument:
    pages: list[PageText]
    parser: str
    warnings: list[str] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "\n".join(p.text for p in self.pages)

    @property
    def ocr_pages(self) -> list[int]:
        return [p.page for p in self.pages if p.source.startswith("ocr")]


@runtime_checkable
class OCRBackend(Protocol):
    id: str

    def available(self) -> bool: ...

    def ocr_page(self, page: object) -> str: ...  # a pymupdf.Page


class CommandOCR:
    """A local OCR / layout model behind a command template with ``{image}``."""

    id = "command"

    def __init__(self, template: str | None = None) -> None:
        self.template = template if template is not None else os.environ.get("IMPACT_VISION_OCR_COMMAND", "")

    def available(self) -> bool:
        if "{image}" not in self.template:
            return False
        argv = shlex.split(self.template)
        return bool(argv) and shutil.which(argv[0]) is not None

    def ocr_page(self, page: object) -> str:
        with tempfile.TemporaryDirectory() as tmp:
            image = Path(tmp) / "page.png"
            page.get_pixmap(dpi=OCR_DPI).save(str(image))  # type: ignore[attr-defined]
            argv = [part.replace("{image}", str(image)) for part in shlex.split(self.template)]
            done = subprocess.run(argv, capture_output=True, text=True, timeout=OCR_TIMEOUT_S, check=False)  # nosec B603
            if done.returncode != 0:
                raise RuntimeError(f"OCR command failed ({done.returncode}): {done.stderr.strip()[:200]}")
            return done.stdout


class TesseractOCR:
    """PyMuPDF's OCR (needs the tesseract binary and its language data)."""

    id = "tesseract"

    def __init__(self, language: str | None = None) -> None:
        self.language = language or os.environ.get("IMPACT_VISION_OCR_LANG", "eng")

    def available(self) -> bool:
        return shutil.which("tesseract") is not None

    def ocr_page(self, page: object) -> str:
        tp = page.get_textpage_ocr(language=self.language, dpi=OCR_DPI, full=True)  # type: ignore[attr-defined]
        return str(page.get_text(textpage=tp))  # type: ignore[attr-defined]


def ocr_backend() -> OCRBackend | None:
    """The configured command first, then Tesseract; None when neither is usable."""
    for backend in (CommandOCR(), TesseractOCR()):
        if backend.available():
            return backend
    return None


def parse_pdf(path: str | Path, *, mode: str | None = None, ocr: OCRBackend | None = None) -> ParsedDocument:
    """Pages of text from a PDF, OCR-ing the pages that have no text layer."""
    import pymupdf

    mode = (mode or os.environ.get("IMPACT_VISION_DOC_PARSER", "auto")).strip().lower()
    backend = ocr if ocr is not None else (ocr_backend() if mode != "text" else None)
    pages: list[PageText] = []
    warnings: list[str] = []
    missing: list[int] = []
    with pymupdf.open(str(path)) as doc:  # type: ignore[no-untyped-call]
        for index in range(len(doc)):
            page = doc[index]
            text = page.get_text()
            needs_ocr = mode == "ocr" or (mode == "auto" and len(text.strip()) < MIN_TEXT_CHARS)
            if needs_ocr and backend is not None:
                try:
                    pages.append(PageText(index + 1, backend.ocr_page(page), f"ocr:{backend.id}"))
                    continue
                except (RuntimeError, OSError, subprocess.TimeoutExpired) as exc:
                    warnings.append(f"Page {index + 1}: OCR failed ({exc}); used the text layer.")
            elif needs_ocr and mode != "text" and page.get_images():
                missing.append(index + 1)
            pages.append(PageText(index + 1, text))
    if missing:
        listed = ", ".join(map(str, missing[:10])) + ("…" if len(missing) > 10 else "")
        warnings.append(f"Page(s) {listed} look scanned (no text layer). Install Tesseract or set "
                        "IMPACT_VISION_OCR_COMMAND to read them.")
    for w in warnings:
        logger.warning("%s: %s", Path(path).name, w)
    ocr_used = sorted({p.source.split(":", 1)[1] for p in pages if p.source.startswith("ocr:")})
    return ParsedDocument(pages, "+".join(["pymupdf", *ocr_used]), warnings)


__all__ = ["CommandOCR", "MIN_TEXT_CHARS", "OCRBackend", "PageText", "ParsedDocument", "TesseractOCR",
           "ocr_backend", "parse_pdf"]
