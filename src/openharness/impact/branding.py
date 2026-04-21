"""Report branding from fund_thesis.yaml (Phase 15.6).

Loads the optional ``branding`` block from :class:`FundThesis` and
produces a small CSS override snippet + hero eyebrow customization so
every HTML surface (Impact Report, DD Questionnaire, IC Memo, LP
Portal) can be consistently themed to the fund's visual identity
*without* forking the templates.

Usage
-----
::

    from openharness.impact.branding import load_branding, inject_branding_css

    brand = load_branding(thesis_path="data/fund_thesis.yaml")
    html = inject_branding_css(raw_html, brand)

The ``fund_thesis.yaml`` schema for branding is intentionally small::

    branding:
      fund_name: "Example Climate Fund I"
      primary_color: "#0d47a1"
      accent_color: "#1976d2"
      logo_url: "https://example.com/logo.svg"
      footer_text: "Confidential — Example Capital LP"
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Branding:
    fund_name: str = ""
    primary_color: str = "#0d47a1"
    accent_color: str = "#1976d2"
    logo_url: str = ""
    footer_text: str = ""


_HEX_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{3,8}$")


def _safe_color(value: str, fallback: str) -> str:
    """Accept only hex colors to avoid CSS injection via user input."""
    if isinstance(value, str) and _HEX_COLOR_RE.match(value.strip()):
        return value.strip()
    return fallback


def _safe_url(value: str) -> str:
    """Allow only http(s), relative or data: URLs."""
    if not isinstance(value, str):
        return ""
    v = value.strip()
    if not v:
        return ""
    if v.startswith(("http://", "https://", "/", "data:image/")):
        return v
    return ""


def _safe_text(value: str, *, max_len: int = 200) -> str:
    if not isinstance(value, str):
        return ""
    v = value.replace("<", "").replace(">", "").strip()
    return v[:max_len]


def load_branding(
    thesis_path: str | None = None,
    *,
    raw: dict | None = None,
) -> Branding:
    """Parse the ``branding`` block out of ``fund_thesis.yaml``.

    Returns a default branding when the file (or block) is absent so
    reports keep rendering deterministically in offline environments.
    """
    block: dict = {}
    if raw is not None:
        block = raw or {}
    else:
        try:
            import yaml  # type: ignore
        except ImportError:
            yaml = None  # type: ignore
        candidates: list[Path] = []
        if thesis_path:
            candidates.append(Path(thesis_path))
        env = os.environ.get("IMPACT_VISION_FUND_THESIS")
        if env:
            candidates.append(Path(env))
        candidates.append(Path("data/fund_thesis.yaml"))
        if yaml is not None:
            for p in candidates:
                if p.is_file():
                    try:
                        with open(p, encoding="utf-8") as fh:
                            data = yaml.safe_load(fh) or {}
                        block = (data.get("branding") or {}) if isinstance(data, dict) else {}
                        if block:
                            break
                    except Exception:  # noqa: BLE001 — never let a bad yaml break the report
                        continue

    return Branding(
        fund_name=_safe_text(block.get("fund_name", ""), max_len=120),
        primary_color=_safe_color(block.get("primary_color", ""), "#0d47a1"),
        accent_color=_safe_color(block.get("accent_color", ""), "#1976d2"),
        logo_url=_safe_url(block.get("logo_url", "")),
        footer_text=_safe_text(block.get("footer_text", ""), max_len=400),
    )


def branding_css(brand: Branding) -> str:
    """Return a ``<style>`` block overriding the report CSS variables."""
    return (
        "<style data-source=\"impact-vision-branding\">:root{"
        f"--primary:{brand.primary_color};"
        f"--accent:{brand.accent_color};"
        f"--primary-dark:{brand.primary_color};"
        "}"
        ".report-hero .logo{max-height:48px;margin-bottom:12px;}"
        ".report-footer.branding-footer{border-top:1px solid var(--border);"
        "padding:16px 0;margin-top:32px;color:var(--text-secondary);"
        "font-size:0.85rem;text-align:center;}"
        "</style>"
    )


def branding_footer(brand: Branding) -> str:
    text = brand.footer_text or (
        f"Produced for {brand.fund_name}" if brand.fund_name else
        "Produced with Impact Vision"
    )
    return f'<div class="report-footer branding-footer">{text}</div>'


def branding_logo(brand: Branding) -> str:
    if not brand.logo_url:
        return ""
    return (
        f'<img class="logo" src="{brand.logo_url}" '
        f'alt="{brand.fund_name or "Fund"} logo" />'
    )


def inject_branding_css(html: str, brand: Branding) -> str:
    """Insert the branding CSS after the closing ``</style>`` or before ``</head>``."""
    css = branding_css(brand)
    if "</head>" in html:
        return html.replace("</head>", css + "</head>", 1)
    return css + html


__all__ = [
    "Branding",
    "load_branding",
    "branding_css",
    "branding_footer",
    "branding_logo",
    "inject_branding_css",
]
