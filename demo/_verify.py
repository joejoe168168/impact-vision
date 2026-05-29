"""Structural QA for the generated DEMO HTML (run before committing)."""
from __future__ import annotations

import re
import sys
from html.parser import HTMLParser
from pathlib import Path

DEMO = Path(__file__).resolve().parent

REPORTS = ["01_impact_report.html", "02_impact_report_dark.html", "03_impact_report_branded.html"]
ALL_HTML = REPORTS + ["04_ic_memo.html", "05_dd_report.html", "06_investee_portal.html", "index.html"]

# Strings that should NEVER appear in finished output
POISON = ["Traceback (most recent", "KeyError", "jinja2.exceptions", "{{ ", " }}", "object at 0x", "None None"]
# v5 report chrome markers
CHROME = ["read-progress", "util-dock", 'class="mini-header"', "print-cover", "audience-bar", "sec-toggle"]


class TagBalance(HTMLParser):
    VOID = {"area","base","br","col","embed","hr","img","input","link","meta","param","source","track","wbr"}
    def __init__(self):
        super().__init__()
        self.stack = []
        self.errors = 0
    def handle_starttag(self, tag, attrs):
        if tag not in self.VOID:
            self.stack.append(tag)
    def handle_endtag(self, tag):
        if tag in self.VOID:
            return
        if tag in self.stack:
            while self.stack and self.stack.pop() != tag:
                pass
        # stray close tags are tolerated by browsers; don't count


def check(fname: str) -> list[str]:
    p = DEMO / fname
    if not p.exists():
        return [f"MISSING FILE {fname}"]
    html = p.read_text(encoding="utf-8")
    probs: list[str] = []

    if not html.lstrip().lower().startswith("<!doctype html"):
        probs.append("no <!DOCTYPE html>")
    if "</html>" not in html.lower():
        probs.append("no closing </html>")
    for bad in POISON:
        if bad in html:
            probs.append(f"poison string present: {bad!r}")

    # tag balance (light heuristic — browsers are lenient, this catches gross breakage)
    tb = TagBalance()
    tb.feed(html)
    if tb.stack:
        probs.append(f"unclosed tags remain: {tb.stack[:8]}")

    if fname in REPORTS:
        if "Plotly" not in html and "cdn.plot.ly" not in html:
            probs.append("no Plotly chart payload")
        missing = [c for c in CHROME if c not in html]
        if missing:
            probs.append(f"missing v5 chrome: {missing}")

    if fname == "02_impact_report_dark.html" and "theme-dark" not in html:
        probs.append("dark variant missing theme-dark body class")
    if fname == "03_impact_report_branded.html":
        if "Meridian Impact Partners" not in html:
            probs.append("branded variant missing fund name")
        if "#6d28d9" not in html.lower() and "6d28d9" not in html.lower():
            probs.append("branded variant missing custom primary colour")
    return probs


def main() -> int:
    rc = 0
    for f in ALL_HTML:
        probs = check(f)
        size = (DEMO / f).stat().st_size if (DEMO / f).exists() else 0
        if probs:
            rc = 1
            print(f"FAIL  {f:<34} ({size:,} B)")
            for pr in probs:
                print(f"        - {pr}")
        else:
            # count charts + sections as a sanity signal
            html = (DEMO / f).read_text(encoding="utf-8")
            charts = len(re.findall(r"Plotly\.newPlot", html))
            h2 = len(re.findall(r"<h2", html))
            print(f"OK    {f:<34} ({size:,} B; {charts} charts, {h2} h2)")
    print("\nRESULT:", "ALL GOOD" if rc == 0 else "PROBLEMS FOUND")
    return rc


if __name__ == "__main__":
    sys.exit(main())
