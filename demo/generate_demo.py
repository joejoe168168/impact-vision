"""Regenerate the Impact Vision demo bundle (real, reproducible output).

Runs the same offline pipeline as ``impact-vision demo`` on the three bundled
fictional sample decks (``data/sample_decks``) and writes, per company, the
impact report, IC memo, DD report, Word exports, a JSON summary and — when
Chromium is available — PDFs. The pig farm also gets audience, theme,
white-label and Chinese-language variants plus the investee data portal.

    python demo/generate_demo.py            # PDFs if the [pdf] extra is installed
    IMPACT_VISION_CHROMIUM=/path/to/chrome python demo/generate_demo.py

Everything in ``demo/`` except this script, README.md and
pig_farm_profile.json is deleted and rebuilt.
"""
from __future__ import annotations

import copy
import shutil
import sys
from pathlib import Path

DEMO = Path(__file__).resolve().parent
REPO = DEMO.parent
if str(REPO / "src") not in sys.path:
    sys.path.insert(0, str(REPO / "src"))

from openharness.impact.investee_portal import build_investee_portal  # noqa: E402
from openharness.impact.portfolio_home import (  # noqa: E402
    build_portfolio_home,
    record_from_bundle,
    render_portfolio_home,
)
from openharness.impact.pipeline import (  # noqa: E402
    SAMPLE_DECKS,
    assess_file,
    format_summary,
    sample_deck_path,
    slugify,
    write_deliverables,
    write_gallery,
)
from openharness.impact.report_templates.decision_report import render_decision_report  # noqa: E402
from openharness.impact.report_templates.pdf import PdfUnavailable, html_to_pdf  # noqa: E402

KEEP = {"generate_demo.py", "README.md", "pig_farm_profile.json"}
FUND = "Meridian Impact Partners (fictional)"
BRANDING = {
    "fund_name": FUND,
    "primary_color": "#0a7f5a",
    "footer_text": "Prepared for Meridian's LP advisory committee — illustrative example.",
}


def clean() -> None:
    for item in DEMO.iterdir():
        if item.name in KEEP:
            continue
        shutil.rmtree(item) if item.is_dir() else item.unlink()


def pdf_available() -> bool:
    try:
        html_to_pdf("<html><body>probe</body></html>", DEMO / ".probe.pdf")
    except PdfUnavailable as exc:
        print(f"[demo] PDFs skipped: {exc}")
        return False
    finally:
        (DEMO / ".probe.pdf").unlink(missing_ok=True)
    return True


def write(path: Path, html: str, pdf: bool) -> list[tuple[str, Path]]:
    path.write_text(html, encoding="utf-8")
    out = [("html", path)]
    if pdf:
        out.append(("pdf", html_to_pdf(html, path.with_suffix(".pdf"))[0]))
    return out


def main() -> int:
    clean()
    pdf = pdf_available()
    bundles, extras = [], {}
    for key in SAMPLE_DECKS:
        bundle = assess_file(sample_deck_path(key))
        folder = DEMO / slugify(bundle.company.name)
        write_deliverables(bundle, folder, pdf=pdf)
        print(format_summary(bundle) + "\n")
        bundles.append(bundle)

        if key != "pig-farm":
            continue
        variants: list[tuple[str, str]] = []
        data = bundle.report_data
        renders = {
            "LP edition": ("lp", render_decision_report(data, audience="lp")),
            "Public edition": ("public", render_decision_report(data, audience="public")),
            "Dark theme": ("dark", render_decision_report(dict(copy.deepcopy(data), theme="dark"))),
            "White-label": ("branded", render_decision_report(data, branding=BRANDING)),
            "繁體中文 (zh-HK)": ("zh-HK", render_decision_report(data, lang="zh-HK")),
            "简体中文 (zh-CN)": ("zh-CN", render_decision_report(data, lang="zh-CN")),
        }
        stem = slugify(bundle.company.name)
        for label, (suffix, html) in renders.items():
            for kind, path in write(folder / f"{stem}_impact_report_{suffix}.html", html,
                                    pdf and suffix in {"lp", "zh-HK"}):
                variants.append((f"{label}" + (" PDF" if kind == "pdf" else ""),
                                 path.relative_to(DEMO).as_posix()))
        portal = folder / f"{stem}_investee_portal.html"
        portal.write_text(build_investee_portal(fund_name=FUND, company_name=bundle.company.name),
                          encoding="utf-8")
        variants.append(("Investee data portal", portal.relative_to(DEMO).as_posix()))
        extras[bundle.company.name] = variants

    records = [record_from_bundle(b, link=f"{slugify(b.company.name)}/{slugify(b.company.name)}_impact_report.html")
               for b in bundles]
    home = DEMO / "portfolio_home.html"
    home.write_text(render_portfolio_home(build_portfolio_home(records, fund_name=FUND)), encoding="utf-8")
    print(f"[demo] wrote {home}")

    index = write_gallery(
        bundles, DEMO, extras=extras, title="Sample deliverables",
        intro=("Real, unedited output from Impact Vision for three fictional companies, generated "
               "offline from the PDF decks in data/sample_decks. Open any report in a browser; "
               "PDFs are A4 and print-ready."),
        home_href="portfolio_home.html",
    )
    print(f"[demo] wrote {index}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
