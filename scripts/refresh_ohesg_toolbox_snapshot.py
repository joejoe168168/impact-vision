#!/usr/bin/env python3
"""Refresh the reviewed ohESG toolbox source snapshot.

This is a maintainer helper, not runtime product code. It fetches the public
tool.ohesg.com landing page, extracts the 33-card TOOLS array, then fetches
each module page and records any embedded ``window.__*_DATA`` JSON blocks.
Review the generated snapshot before using it to update registry specs.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import date
from pathlib import Path
from urllib.parse import urljoin

from openharness.impact.toolbox.ingest import build_source_profile, extract_landing_tools, fetch_text


DEFAULT_BASE_URL = "https://tool.ohesg.com/"
DEFAULT_OUTPUT = Path("data/raw/ohesg_toolbox_snapshot.json")
DEFAULT_PROFILE_DIR = Path("data/raw/ohesg_toolbox")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--profile-dir", type=Path, default=DEFAULT_PROFILE_DIR)
    parser.add_argument("--timeout", type=int, default=20)
    args = parser.parse_args()

    landing_html = fetch_text(args.base_url, timeout=args.timeout)
    tools = extract_landing_tools(landing_html)
    pages: dict[str, object] = {}
    profiles: dict[str, object] = {}

    for tool in tools:
        page_url = urljoin(args.base_url, tool.url.lstrip("/"))
        try:
            html = fetch_text(page_url, timeout=args.timeout)
        except Exception as exc:  # noqa: BLE001 - snapshot should record fetch failures for review
            pages[tool.tool_id] = {"url": page_url, "error": str(exc), "embedded_data": {}}
            continue
        embedded_data = _extract_embedded_window_data(html)
        pages[tool.tool_id] = {
            "url": page_url,
            "title": _html_title(html),
            "meta_description": _meta_description(html),
            "embedded_data": embedded_data,
        }
        profile = build_source_profile(
            tool=tool,
            page_url=page_url,
            page_html=html,
            embedded_data=embedded_data,
            as_of=date.today().isoformat(),
        )
        profiles[tool.tool_id] = profile.model_dump(mode="json")

    payload = {
        "source": args.base_url,
        "fetched_on": date.today().isoformat(),
        "tool_count": len(tools),
        "tools": [tool.__dict__ for tool in tools],
        "pages": pages,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.profile_dir.mkdir(parents=True, exist_ok=True)
    for tool_id, profile_payload in profiles.items():
        (args.profile_dir / f"{tool_id}.json").write_text(
            json.dumps(profile_payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    print(f"Wrote {args.output} with {len(tools)} tools")
    print(f"Wrote {len(profiles)} source profiles to {args.profile_dir}")
    return 0


def _extract_embedded_window_data(html: str) -> dict[str, object]:
    data: dict[str, object] = {}
    for match in re.finditer(r"window\.(__[A-Z0-9_]+_DATA)\s*=\s*(\{.*?\})\s*</script>", html, flags=re.DOTALL):
        name = match.group(1)
        try:
            data[name] = json.loads(match.group(2))
        except json.JSONDecodeError as exc:
            data[name] = {"error": f"Could not parse embedded JSON: {exc}"}
    return data


def _html_title(html: str) -> str:
    match = re.search(r"<title>(.*?)</title>", html, flags=re.DOTALL | re.IGNORECASE)
    return _clean_html_text(match.group(1)) if match else ""


def _meta_description(html: str) -> str:
    match = re.search(r'<meta\s+name="description"\s+content="([^"]*)"', html, flags=re.IGNORECASE)
    return _clean_html_text(match.group(1)) if match else ""


def _clean_html_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


if __name__ == "__main__":
    raise SystemExit(main())
