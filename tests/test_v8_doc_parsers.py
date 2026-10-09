"""Pluggable parsing with OCR for scanned pages (roadmap v8 W2.3)."""
from __future__ import annotations

import sys

import pymupdf
import pytest

from impact_vision.impact.doc_parsers import CommandOCR, parse_pdf

TEXT = "We served 12,000 households in 2024, verified by an independent auditor."


def _deck(tmp_path):
    """Page 1 has a text layer; page 2 is the same sentence as a picture (a scan)."""
    path = tmp_path / "deck.pdf"
    doc = pymupdf.open()
    doc.new_page().insert_text((72, 72), TEXT, fontsize=11)
    src = pymupdf.open()
    src.new_page(width=600, height=120).insert_text((20, 60), TEXT, fontsize=11)
    png = src[0].get_pixmap(dpi=100).tobytes("png")
    doc.new_page().insert_image(pymupdf.Rect(36, 36, 576, 156), stream=png)
    doc.save(str(path))
    return path


@pytest.fixture
def fake_ocr(tmp_path):
    script = tmp_path / "ocr.py"
    script.write_text("import sys, pathlib\nassert pathlib.Path(sys.argv[1]).stat().st_size > 0\n"
                      f"print({TEXT!r})\n")
    return CommandOCR(f"{sys.executable} {script} {{image}}")


def test_scanned_page_is_read_by_the_ocr_command(tmp_path, fake_ocr):
    parsed = parse_pdf(_deck(tmp_path), ocr=fake_ocr)
    assert [p.source for p in parsed.pages] == ["text", "ocr:command"]
    assert TEXT in parsed.pages[1].text and parsed.parser == "pymupdf+command"
    assert parsed.ocr_pages == [2] and not parsed.warnings


def test_without_ocr_the_scanned_page_is_flagged(tmp_path, monkeypatch):
    monkeypatch.delenv("IMPACT_VISION_OCR_COMMAND", raising=False)
    monkeypatch.setattr("shutil.which", lambda name: None)
    parsed = parse_pdf(_deck(tmp_path))
    assert parsed.ocr_pages == [] and "look scanned" in parsed.warnings[0] and "Page(s) 2" in parsed.warnings[0]


def test_text_mode_never_ocrs_and_ocr_mode_always_does(tmp_path, fake_ocr):
    assert parse_pdf(_deck(tmp_path), mode="text", ocr=None).ocr_pages == []
    assert parse_pdf(_deck(tmp_path), mode="ocr", ocr=fake_ocr).ocr_pages == [1, 2]


def test_failing_ocr_falls_back_to_the_text_layer(tmp_path):
    bad = CommandOCR(f"{sys.executable} -c \"import sys; sys.exit(3)\" {{image}}")
    parsed = parse_pdf(_deck(tmp_path), ocr=bad)
    assert parsed.pages[1].source == "text" and "OCR failed" in parsed.warnings[0]


def test_command_template_needs_an_image_slot_and_a_real_binary():
    assert not CommandOCR("tesseract").available()
    assert not CommandOCR("definitely-not-installed-ocr {image}").available()


def test_scanned_claims_reach_the_assessment(tmp_path, fake_ocr, monkeypatch):
    from impact_vision.impact import doc_parsers
    from impact_vision.impact.pipeline import assess_file

    path = tmp_path / "scan.pdf"
    doc = pymupdf.open(str(_deck(tmp_path)))
    doc.delete_page(0)  # only the scanned page is left
    doc.save(str(path))
    monkeypatch.setattr(doc_parsers, "ocr_backend", lambda: fake_ocr)
    claims = assess_file(path).report_data["impact_claims"]
    assert any("12,000 households" in c["text"] for c in claims)
