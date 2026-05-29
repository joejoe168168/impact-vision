"""Capture real headless screenshots of the DEMO deliverables.

Uses Playwright driving the installed Microsoft Edge (Chromium) — no separate
browser download required. Plotly charts load from the CDN, so this needs
network access; the script reports how many charts actually rendered so you
can tell whether a shot is missing its chart.

    python demo/_screenshot.py

Writes PNGs to ``demo/screenshots/``.
"""
from __future__ import annotations

import sys
from pathlib import Path

DEMO = Path(__file__).resolve().parent
SHOTS = DEMO / "screenshots"
PLOTLY_CACHE = DEMO / ".cache" / "plotly-2.27.0.min.js"
CHANNEL = "msedge"
VIEWPORT = {"width": 1280, "height": 860}
SCALE = 1.5
STICKY_OFFSET = 84  # px to scroll up so a section heading clears the sticky bar


def _url(name: str) -> str:
    return (DEMO / name).resolve().as_uri()


def _install_routes(ctx) -> None:
    """Serve plotly from the local cache; abort other network so headless
    rendering is deterministic and never hangs on blocked CDNs/fonts."""
    plotly_js = PLOTLY_CACHE.read_bytes() if PLOTLY_CACHE.exists() else None

    def handler(route):
        url = route.request.url
        if url.startswith("file:"):
            route.continue_()
            return
        if "plot.ly" in url or "plotly" in url:
            if plotly_js is not None:
                route.fulfill(status=200, content_type="application/javascript", body=plotly_js)
            else:
                route.continue_()
            return
        # Everything else external -> drop quickly (fonts/analytics/etc.)
        route.abort()

    ctx.route("**/*", handler)


def _settle(page, expect_charts: bool) -> int:
    if expect_charts:
        try:
            page.wait_for_selector("svg.main-svg", timeout=15000)
        except Exception:  # noqa: BLE001
            pass
    page.wait_for_timeout(1400)
    try:
        return page.evaluate("document.querySelectorAll('svg.main-svg').length")
    except Exception:  # noqa: BLE001
        return 0


def _park_mouse(page) -> None:
    """Move the cursor out of the chart area so Plotly's hover modebar hides."""
    try:
        page.mouse.move(2, 2)
        page.wait_for_timeout(250)
    except Exception:  # noqa: BLE001
        pass


def _shot_top(page, out: str) -> None:
    page.evaluate("window.scrollTo(0, 0)")
    _park_mouse(page)
    page.screenshot(path=str(SHOTS / out))
    print(f"  + {out}")


def _shot_section(page, sel: str, out: str) -> None:
    try:
        page.eval_on_selector(sel, "el => el.scrollIntoView({block:'start'})")
        page.evaluate(f"window.scrollBy(0, -{STICKY_OFFSET})")
        page.wait_for_timeout(450)
        _park_mouse(page)
        page.screenshot(path=str(SHOTS / out))
        print(f"  + {out}")
    except Exception as e:  # noqa: BLE001
        print(f"  ! skipped {out}: {type(e).__name__}: {str(e)[:120]}")


def main() -> int:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:  # noqa: BLE001
        print("Playwright not available:", e)
        return 2

    SHOTS.mkdir(parents=True, exist_ok=True)
    reports = {
        "01_impact_report.html",
        "02_impact_report_dark.html",
        "03_impact_report_branded.html",
    }
    gallery = [
        "01_impact_report.html", "02_impact_report_dark.html",
        "03_impact_report_branded.html", "04_ic_memo.html",
        "05_dd_report.html", "06_investee_portal.html",
    ]

    with sync_playwright() as p:
        browser = p.chromium.launch(channel=CHANNEL, headless=True)
        ctx = browser.new_context(viewport=VIEWPORT, device_scale_factor=SCALE)
        _install_routes(ctx)
        page = ctx.new_page()
        page.set_default_navigation_timeout(20000)

        # --- Gallery thumbnails (top-of-page) for every deliverable
        print("[shots] gallery thumbnails")
        for f in gallery:
            page.goto(_url(f), wait_until="domcontentloaded")
            charts = _settle(page, expect_charts=f in reports)
            if f in reports and charts == 0:
                print(f"  WARNING: {f} rendered 0 charts (CDN/network?)")
            _shot_top(page, f"{Path(f).stem}.png")

        # --- Feature shots from the flagship light report
        print("[shots] feature close-ups (light report)")
        page.goto(_url("01_impact_report.html"), wait_until="domcontentloaded")
        charts = _settle(page, expect_charts=True)
        print(f"  charts rendered: {charts}")
        _shot_section(page, "#sec-5d", "feature_5d_radar.png")
        _shot_section(page, "#sec-sdg", "feature_sdg_alignment.png")
        _shot_section(page, "#sec-opp-risk", "feature_opportunities_risks.png")
        _shot_section(page, "#sec-greenwashing", "feature_greenwashing.png")
        _shot_section(page, "#sec-gap", "feature_gap_analysis.png")
        _shot_section(page, "#sec-benchmark", "feature_benchmark.png")

        # methodology / "how this grade was calculated" (no id -> locate by text)
        try:
            page.get_by_text("How this grade was calculated").first.scroll_into_view_if_needed()
            page.evaluate(f"window.scrollBy(0, -{STICKY_OFFSET})")
            page.wait_for_timeout(400)
            _park_mouse(page)
            page.screenshot(path=str(SHOTS / "feature_methodology.png"))
            print("  + feature_methodology.png")
        except Exception as e:  # noqa: BLE001
            print(f"  ! skipped feature_methodology.png: {str(e)[:120]}")

        # audience filter -> LP view
        try:
            page.click('.audience-bar [data-aud="lp"]', timeout=4000)
            page.wait_for_timeout(500)
            _shot_top(page, "feature_audience_lp.png")
        except Exception as e:  # noqa: BLE001
            print(f"  ! skipped feature_audience_lp.png: {str(e)[:120]}")

        # sticky mini-header appears after scrolling down
        try:
            page.evaluate("window.scrollTo(0, 1400)")
            page.wait_for_timeout(600)
            _park_mouse(page)
            page.screenshot(path=str(SHOTS / "feature_sticky_header.png"))
            print("  + feature_sticky_header.png")
        except Exception as e:  # noqa: BLE001
            print(f"  ! skipped feature_sticky_header.png: {str(e)[:120]}")

        # print cover page (print-media emulation)
        try:
            page.emulate_media(media="print")
            page.evaluate("window.scrollTo(0, 0)")
            page.wait_for_timeout(400)
            page.screenshot(path=str(SHOTS / "feature_print_cover.png"))
            page.emulate_media(media="screen")
            print("  + feature_print_cover.png")
        except Exception as e:  # noqa: BLE001
            print(f"  ! skipped feature_print_cover.png: {str(e)[:120]}")

        # --- Dark-mode close-up
        print("[shots] feature close-up (dark report)")
        page.goto(_url("02_impact_report_dark.html"), wait_until="domcontentloaded")
        _settle(page, expect_charts=True)
        _shot_section(page, "#sec-5d", "feature_dark_radar.png")

        browser.close()

    pngs = sorted(SHOTS.glob("*.png"))
    print(f"\n[shots] wrote {len(pngs)} screenshots to {SHOTS}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
