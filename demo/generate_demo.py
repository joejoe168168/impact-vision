"""Generate the Impact Vision DEMO bundle (real, reproducible output).

This regenerates every showcase deliverable from a single offline company
profile (a 3,000-sow pig farm in Johor, Malaysia) using the *current* code,
so the HTML always reflects the latest report chrome (audience filter, dark
mode, executive tear sheet, reading progress, collapsible sections, sticky
mini-header, print cover, etc.).

It is fully offline and deterministic — no AI gateway call — so the bundle
checked into the repo can be reproduced byte-for-similar on any machine::

    $env:PYTHONPATH = "src"
    python demo/generate_demo.py

Artifacts written next to this script (the ``demo/`` folder):

    01_impact_report.html         flagship assessment (light, audience=full)
    02_impact_report_dark.html    same report in the accessible dark palette
    03_impact_report_branded.html white-label example (custom fund colours)
    04_ic_memo.html               investment-committee memo
    05_dd_report.html             due-diligence coverage report
    06_investee_portal.html       offline data-collection portal (investee-facing)
    pig_farm_dd_questionnaire.docx editable DD questionnaire (if python-docx present)
    pig_farm_profile.json          the input profile (reproducibility)
    index.html                     gallery landing page linking everything
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
for extra in (REPO_ROOT / "src", REPO_ROOT / "examples"):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

# Reuse the exact offline profile + assembly pipeline from the examples demo
from generate_pig_farm_reports import (  # type: ignore[import-not-found]
    OFFLINE_PROFILE,
    assess_and_assemble,
)

from openharness.impact.ic_memo import render_ic_memo_html
from openharness.impact.investee_portal import build_investee_portal
from openharness.impact.report_templates import (
    render_dd_questionnaire_docx,
    render_dd_report_html,
)
from openharness.tools.impact.impact_report_tool import _to_html

# Resolve relative to this file so renaming the folder (DEMO -> demo) is safe.
DEMO_DIR = Path(__file__).resolve().parent
FUND_NAME = "Meridian Impact Partners"


def _write(path: Path, html: str) -> Path:
    path.write_text(html, encoding="utf-8")
    print(f"  wrote {path.name:<34} ({len(html.encode('utf-8')):,} bytes)", flush=True)
    return path


def build_index(items: list[tuple[str, str, str]]) -> str:
    """Render the gallery landing page.

    ``items`` is a list of (filename, title, description).
    """
    cards = []
    for fname, title, desc in items:
        shot = f"screenshots/{Path(fname).stem}.png"
        cards.append(
            f"""      <a class="card" href="{fname}">
        <div class="thumb"><img src="{shot}" alt="{title} preview" loading="lazy"></div>
        <div class="meta"><h3>{title}</h3><p>{desc}</p>
        <span class="open">Open deliverable &rarr;</span></div>
      </a>"""
        )
    cards_html = "\n".join(cards)
    generated = time.strftime("%Y-%m-%d", time.gmtime())
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Impact Vision — sample deliverables gallery</title>
<style>
  :root {{ --primary:#1a5d3a; --ink:#1f2937; --muted:#6b7280; --line:#e5e7eb; --bg:#f8fafc; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;
    color:var(--ink); background:var(--bg); line-height:1.55; }}
  header {{ background:linear-gradient(135deg,#1a5d3a,#0f766e); color:#fff; padding:48px 24px; }}
  header .wrap {{ max-width:1080px; margin:0 auto; }}
  header h1 {{ margin:0 0 8px; font-size:30px; }}
  header p {{ margin:0; max-width:760px; opacity:.92; }}
  .wrap {{ max-width:1080px; margin:0 auto; padding:0 24px; }}
  .note {{ background:#ecfdf5; border:1px solid #a7f3d0; color:#065f46; border-radius:10px;
    padding:14px 16px; margin:28px auto; font-size:14px; }}
  .grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(320px,1fr)); gap:22px;
    margin:8px auto 56px; }}
  .card {{ display:flex; flex-direction:column; text-decoration:none; color:inherit;
    background:#fff; border:1px solid var(--line); border-radius:14px; overflow:hidden;
    box-shadow:0 1px 2px rgba(0,0,0,.04); transition:transform .12s, box-shadow .12s; }}
  .card:hover {{ transform:translateY(-3px); box-shadow:0 10px 26px rgba(0,0,0,.10); }}
  .thumb {{ aspect-ratio:16/10; background:#eef2f7; overflow:hidden; border-bottom:1px solid var(--line); }}
  .thumb img {{ width:100%; height:100%; object-fit:cover; object-position:top center; display:block; }}
  .meta {{ padding:16px 18px 18px; }}
  .meta h3 {{ margin:0 0 6px; font-size:17px; color:var(--primary); }}
  .meta p {{ margin:0 0 12px; font-size:14px; color:var(--muted); }}
  .open {{ font-size:13px; font-weight:600; color:var(--primary); }}
  footer {{ color:var(--muted); font-size:13px; padding:8px 0 48px; }}
  footer code {{ background:#eef2f7; padding:2px 6px; border-radius:5px; }}
</style>
</head>
<body>
<header><div class="wrap">
  <h1>Impact Vision — sample deliverables</h1>
  <p>Every file below was generated by the open-source toolkit from a single
  offline company profile (a 3,000-sow pig farm in Johor, Malaysia). They are
  the <em>actual</em> HTML the agent produces — nothing was hand-edited.</p>
</div></header>
<div class="wrap">
  <div class="note"><strong>Reproducible &amp; offline.</strong> Regenerate any time with
  <code>python demo/generate_demo.py</code> — no API key, no network. Screenshots are
  captured headlessly with <code>python demo/_screenshot.py</code>.</div>
  <div class="grid">
{cards_html}
  </div>
  <footer>Generated {generated} · Impact Vision · illustrative data for demonstration only.</footer>
</div>
</body>
</html>"""


def main() -> int:
    DEMO_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[demo] output folder: {DEMO_DIR}", flush=True)

    # Archive the input profile for reproducibility
    (DEMO_DIR / "pig_farm_profile.json").write_text(
        json.dumps(OFFLINE_PROFILE, ensure_ascii=False, indent=2), encoding="utf-8",
    )

    bundle = assess_and_assemble(OFFLINE_PROFILE)
    report_data = bundle["report_data"]
    assess = bundle["assess"]
    dd = bundle["dd"]
    gw = bundle["gw"]
    thesis = bundle["thesis"]
    scorecard = bundle["scorecard"]
    comp = bundle["comp"]

    print("[demo] rendering deliverables …", flush=True)

    # 1. Flagship impact report (light, full audience)
    _write(DEMO_DIR / "01_impact_report.html", _to_html(report_data))

    # 2. Dark-palette variant
    dark_data = dict(report_data)
    dark_data["theme"] = "dark"
    _write(DEMO_DIR / "02_impact_report_dark.html", _to_html(dark_data))

    # 3. White-label / branded variant (custom palette + fund footer)
    branded = _to_html(report_data)
    try:
        from openharness.impact.branding import (
            branding_footer,
            inject_branding_css,
            load_branding,
        )
        brand = load_branding(raw={
            "fund_name": FUND_NAME,
            "primary_color": "#6d28d9",
            "accent_color": "#db2777",
            "footer_text": f"Confidential — prepared by {FUND_NAME} · illustrative data",
        })
        branded = inject_branding_css(branded, brand)
        # The branding API also exposes a fund footer; drop it in before </body>
        if "</body>" in branded:
            branded = branded.replace("</body>", branding_footer(brand) + "</body>", 1)
    except Exception as exc:  # noqa: BLE001 — branding is best-effort
        print(f"[demo] branding skipped: {exc}", flush=True)
    _write(DEMO_DIR / "03_impact_report_branded.html", branded)

    # 4. IC memo
    ic_html = render_ic_memo_html(
        assess, scorecard, thesis,
        dd_coverage_pct=dd.coverage_pct,
        greenwashing_score=gw.overall_score,
        greenwashing_classification=getattr(gw, "classification", None),
        deal_size_eur_m=12.0,
    )
    _write(DEMO_DIR / "04_ic_memo.html", ic_html)

    # 5. DD coverage report
    dd_html = render_dd_report_html(
        dd,
        company_name=comp.name,
        document_label="Founder pitch narrative",
        reviewer="Impact Vision demo",
    )
    _write(DEMO_DIR / "05_dd_report.html", dd_html)

    # 6. Investee data-collection portal
    portal_html = build_investee_portal(
        fund_name=FUND_NAME,
        company_name=comp.name,
    )
    _write(DEMO_DIR / "06_investee_portal.html", portal_html)

    # 7. Editable DD questionnaire (.docx) — optional
    try:
        render_dd_questionnaire_docx(
            dd,
            DEMO_DIR / "pig_farm_dd_questionnaire.docx",
            company_name=comp.name,
            document_label="Founder pitch narrative",
            reviewer="Impact Vision demo",
        )
        print("  wrote pig_farm_dd_questionnaire.docx", flush=True)
    except ImportError as exc:
        print(f"[demo] skipping DD .docx export: {exc}", flush=True)

    # 8. Gallery index
    index = build_index([
        ("01_impact_report.html", "Impact Assessment Report",
         "Full IMM assessment: executive tear sheet, 5-Dimension radar, SDG alignment, "
         "gap analysis, sector benchmark, greenwashing screen, opportunities &amp; risks."),
        ("02_impact_report_dark.html", "Impact Report — Dark Mode",
         "The same report in the accessible dark palette (WCAG 2.2 AA contrast)."),
        ("03_impact_report_branded.html", "Impact Report — White-Label",
         "Fund-branded variant with custom primary/accent colours and fund name."),
        ("04_ic_memo.html", "Investment Committee Memo",
         "IC gate decision, thesis fit scorecard, DD coverage and greenwashing summary."),
        ("05_dd_report.html", "Due-Diligence Coverage Report",
         "122-question DD checklist coverage with NESTA evidence levels and gaps."),
        ("06_investee_portal.html", "Investee Data-Collection Portal",
         "Self-contained, offline portal investees fill in — plain-language SFDR PAI, "
         "client-side validation, local JSON export."),
    ])
    _write(DEMO_DIR / "index.html", index)

    print("\n[demo] done. Open demo/index.html to browse.", flush=True)
    print(f"[demo] gate={scorecard.overall_status.upper()} · "
          f"DD coverage={dd.coverage_pct:.1f}% · GW={gw.overall_score:.1f}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
