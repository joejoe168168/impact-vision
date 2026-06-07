"""Optional extraction helpers for refreshing toolbox snapshots.

These helpers are intentionally not used by runtime tools. They let maintainers
refresh local snapshots from public pages, then review and commit normalized
data explicitly.
"""

from __future__ import annotations

import ast
import html
import json
import re
from dataclasses import dataclass
from typing import Any
from urllib.request import urlopen

from openharness.impact.toolbox.models import ToolboxSourceProfile


@dataclass(frozen=True)
class ExtractedToolSummary:
    tool_id: str
    title: str
    description: str
    url: str
    categories: list[str]
    tags: list[str]


def fetch_text(url: str, timeout: int = 20) -> str:
    """Fetch a public text resource with a small stdlib-only dependency surface."""
    with urlopen(url, timeout=timeout) as response:  # noqa: S310 - maintainer-triggered public fetch helper
        return response.read().decode("utf-8", errors="replace")


def extract_landing_tools(html: str) -> list[ExtractedToolSummary]:
    """Extract the landing-page ``TOOLS`` JavaScript array.

    The page currently stores an object-literal array. This parser handles the
    stable fields Impact Vision needs and avoids evaluating JavaScript.
    """
    match = re.search(r"const\s+TOOLS\s*=\s*(\[.*?\]);", html, flags=re.DOTALL)
    if not match:
        return []
    block = match.group(1)
    out: list[ExtractedToolSummary] = []
    for obj in _split_top_level_objects(block):
        tool_id = _string_field(obj, "id")
        title = _string_field(obj, "title")
        desc = _string_field(obj, "desc")
        url = _string_field(obj, "url")
        categories = _list_field(obj, "categories")
        tags = re.findall(r"\{\s*n\s*:\s*'([^']+)'", obj)
        if tool_id and title:
            out.append(ExtractedToolSummary(tool_id, title, desc, url, categories, tags))
    return out


def extract_window_json(html: str, variable_name: str) -> dict[str, Any]:
    """Extract a ``window.__NAME={...}`` JSON assignment from a page."""
    match = re.search(rf"window\.{re.escape(variable_name)}\s*=\s*(\{{.*?\}})\s*</script>", html, flags=re.DOTALL)
    if not match:
        return {}
    return json.loads(match.group(1))


def build_source_profile(
    *,
    tool: ExtractedToolSummary,
    page_url: str,
    page_html: str,
    embedded_data: dict[str, object] | None = None,
    as_of: str = "",
) -> ToolboxSourceProfile:
    """Build one reviewed source profile from an ohESG module page."""
    text = html_to_text(page_html)
    embedded = embedded_data or {}
    embedded_terms = _embedded_terms(embedded)
    keywords = extract_keywords(
        " ".join([
            tool.title,
            tool.description,
            " ".join(tool.tags),
            _meta_description(page_html),
            text,
            " ".join(embedded_terms),
        ])
    )
    return ToolboxSourceProfile(
        tool_id=tool.tool_id,
        url=page_url,
        source_title=tool.title,
        source_description=tool.description,
        source_tags=tool.tags,
        page_title=_html_title(page_html),
        meta_description=_meta_description(page_html),
        headings=_extract_headings(page_html),
        links=_extract_links(page_html),
        keywords=keywords,
        embedded_data_keys=list(embedded.keys()),
        embedded_data_summary={key: summarize_embedded_data(value) for key, value in embedded.items()},
        as_of=as_of,
    )


def html_to_text(page_html: str) -> str:
    """Convert HTML to rough visible text for source keyword extraction."""
    cleaned = re.sub(r"<script\b.*?</script>", " ", page_html, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r"<style\b.*?</style>", " ", cleaned, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    cleaned = html.unescape(cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def extract_keywords(text: str, *, limit: int = 5000) -> list[str]:
    """Extract stable source terms from mixed Chinese/English ESG page text."""
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9+./&-]{1,}|[\u4e00-\u9fff]{2,}", text)
    stop = {
        "https",
        "http",
        "html",
        "com",
        "www",
        "工具",
        "助手",
        "实践",
        "速查",
        "查看",
        "使用",
        "开始",
        "支持",
        "了解",
        "企业",
        "标准",
        "合规",
        "数据",
        "要求",
        "准备",
    }
    scored: dict[str, int] = {}
    display: dict[str, str] = {}
    for token in tokens:
        cleaned = token.strip(".,;:()[]{}<>\"'").strip()
        if len(cleaned) < 2:
            continue
        key = cleaned.lower()
        if key in stop or cleaned in stop:
            continue
        scored[key] = scored.get(key, 0) + 1
        display.setdefault(key, cleaned)
    ordered = sorted(scored, key=lambda key: (-scored[key], key))
    return [display[key] for key in ordered[:limit]]


def summarize_embedded_data(value: object) -> object:
    """Summarize large embedded page data without copying the whole payload into runtime."""
    if isinstance(value, dict):
        summary: dict[str, object] = {"type": "object", "keys": list(value.keys())[:40]}
        for key, child in value.items():
            if isinstance(child, list):
                summary[key] = {
                    "type": "list",
                    "count": len(child),
                    "sample_terms": _sample_terms(child),
                }
            elif isinstance(child, dict):
                summary[key] = {
                    "type": "object",
                    "keys": list(child.keys())[:25],
                    "sample_terms": _sample_terms(child),
                }
            else:
                summary[key] = {"type": type(child).__name__, "sample": str(child)[:160]}
        return summary
    if isinstance(value, list):
        return {"type": "list", "count": len(value), "sample_terms": _sample_terms(value)}
    return {"type": type(value).__name__, "sample": str(value)[:160]}


def _string_field(obj: str, field: str) -> str:
    match = re.search(rf"{field}\s*:\s*'([^']*)'", obj)
    return match.group(1) if match else ""


def _html_title(page_html: str) -> str:
    match = re.search(r"<title>(.*?)</title>", page_html, flags=re.DOTALL | re.IGNORECASE)
    return _clean_text(match.group(1)) if match else ""


def _meta_description(page_html: str) -> str:
    match = re.search(r'<meta\s+name="description"\s+content="([^"]*)"', page_html, flags=re.IGNORECASE)
    return _clean_text(match.group(1)) if match else ""


def _extract_headings(page_html: str) -> list[str]:
    headings = re.findall(r"<h[1-4][^>]*>(.*?)</h[1-4]>", page_html, flags=re.DOTALL | re.IGNORECASE)
    return _dedupe([_clean_text(re.sub(r"<[^>]+>", " ", heading)) for heading in headings])[:80]


def _extract_links(page_html: str) -> list[str]:
    links = re.findall(r"href=[\"']([^\"'#]+)[\"']", page_html, flags=re.IGNORECASE)
    return _dedupe([link for link in links if not link.startswith(("javascript:", "mailto:"))])[:120]


def _embedded_terms(data: dict[str, object]) -> list[str]:
    return _sample_terms(data, limit=5000)


def _sample_terms(value: object, *, limit: int = 1000) -> list[str]:
    text = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    return extract_keywords(text, limit=limit)


def _clean_text(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def _dedupe(values: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = str(value).strip()
        key = cleaned.lower()
        if cleaned and key not in seen:
            seen.add(key)
            out.append(cleaned)
    return out


def _list_field(obj: str, field: str) -> list[str]:
    match = re.search(rf"{field}\s*:\s*(\[[^\]]*\])", obj)
    if not match:
        return []
    try:
        value = ast.literal_eval(match.group(1))
    except (SyntaxError, ValueError):
        return []
    return [str(item) for item in value] if isinstance(value, list) else []


def _split_top_level_objects(array_literal: str) -> list[str]:
    """Split a JavaScript array literal into top-level object literals."""
    objects: list[str] = []
    depth = 0
    start: int | None = None
    quote: str | None = None
    escape = False

    for index, char in enumerate(array_literal):
        if quote:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == quote:
                quote = None
            continue
        if char in {"'", '"'}:
            quote = char
            continue
        if char == "{":
            if depth == 0:
                start = index
            depth += 1
            continue
        if char == "}":
            depth -= 1
            if depth == 0 and start is not None:
                objects.append(array_literal[start : index + 1])
                start = None
    return objects
