"""W2.7: accessibility + responsive QA for every deliverable, in a real browser.

Runs axe-core (no serious/critical violations) and checks there is no
horizontal scrolling at phone, tablet and laptop widths, in light and dark.
Skipped unless Playwright, its Chromium (or IMPACT_VISION_CHROMIUM) and
axe-playwright-python are installed — the `report-qa` CI job installs them.
"""

from __future__ import annotations

import os

import pytest

playwright = pytest.importorskip("playwright.sync_api")
axe_mod = pytest.importorskip("axe_playwright_python.sync_playwright")

from openharness.impact.investee_portal import build_investee_portal  # noqa: E402
from openharness.impact.pipeline import (  # noqa: E402
    assess_file,
    sample_deck_path,
    write_deliverables,
    write_gallery,
)
from openharness.impact.report_templates.decision_report import render_decision_report  # noqa: E402

WIDTHS = (390, 1024, 1440)


@pytest.fixture(scope="module")
def pages(tmp_path_factory):
    out = tmp_path_factory.mktemp("qa")
    bundle = assess_file(sample_deck_path("pig-farm"))
    write_deliverables(bundle, out, include_docx=False)
    write_gallery([bundle], out)
    data = bundle.report_data
    variants = {
        "lp": render_decision_report(data, audience="lp"),
        "public": render_decision_report(data, audience="public"),
        "zh-HK": render_decision_report(data, lang="zh-HK"),
        "zh-CN": render_decision_report(data, lang="zh-CN"),
        "dark": render_decision_report(dict(data, theme="dark")),
    }
    for name, html in variants.items():
        (out / f"variant_{name}.html").write_text(html, encoding="utf-8")
    from openharness.impact.portfolio_home import (
        build_portfolio_home,
        record_from_bundle,
        render_portfolio_home,
    )

    (out / "portfolio_home.html").write_text(
        render_portfolio_home(build_portfolio_home([record_from_bundle(bundle)], fund_name="Fund")),
        encoding="utf-8",
    )
    from openharness.impact.engagement_home import build_engagement_home, render_engagement_home
    from openharness.impact.engagements.workspace import EngagementWorkspace

    ws = EngagementWorkspace()
    eng = ws.create_engagement(name="Fund I DD", client_name="Acme Capital", bundle_id="dd_light")
    ws.add_deliverable(eng.engagement_id, name="IC memo", owner="analyst", due_date="2026-01-15")
    (out / "engagements.html").write_text(
        render_engagement_home(build_engagement_home(ws.list_engagements())), encoding="utf-8"
    )
    (out / "portal.html").write_text(
        build_investee_portal(fund_name="Fund", company_name=bundle.company.name), encoding="utf-8"
    )
    return sorted(p for p in out.glob("*.html"))


@pytest.fixture(scope="module")
def browser():
    with playwright.sync_playwright() as pw:
        try:
            b = pw.chromium.launch(executable_path=os.environ.get("IMPACT_VISION_CHROMIUM") or None)
        except Exception as exc:  # noqa: BLE001
            pytest.skip(f"Chromium not available: {exc}")
        yield b
        b.close()


@pytest.mark.parametrize("scheme", ["light", "dark"])
def test_no_serious_accessibility_violations(pages, browser, scheme):
    axe = axe_mod.Axe()
    problems = []
    for path in pages:
        page = browser.new_page(viewport={"width": 1280, "height": 900}, color_scheme=scheme)
        page.goto(path.as_uri())
        for v in axe.run(page).response["violations"]:
            if v["impact"] in ("serious", "critical"):
                problems.append(f"{path.name}: {v['id']} ({len(v['nodes'])} nodes)")
        page.close()
    assert problems == []


@pytest.mark.parametrize("width", WIDTHS)
def test_no_horizontal_scroll(pages, browser, width):
    overflowing = []
    for path in pages:
        page = browser.new_page(viewport={"width": width, "height": 900})
        page.goto(path.as_uri())
        scroll = page.evaluate("document.documentElement.scrollWidth")
        if scroll > width + 1:
            overflowing.append(f"{path.name}: {scroll}px at {width}px")
        page.close()
    assert overflowing == []
