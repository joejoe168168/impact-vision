"""v7 W5.7 — numbers quoted in README.md / CLAUDE.md must match the code."""

from __future__ import annotations

import re
import runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_GEN = runpy.run_path(str(ROOT / "scripts" / "build_tool_reference.py"))

# fact -> regexes whose first group is a number the docs claim for that fact
PATTERNS: dict[str, list[str]] = {
    "impact_tools": [r"(\d+) impact agent tools", r"Agent Tools \((\d+)\)", r"(\d+) LLM-callable impact",
                     r"currently \*\*(\d+)\*\*"],
    "suite_actions": [r"\((\d+) actions;"],
    "crosswalk_concepts": [r"(\d+) cross-framework metric mappings", r"\((\d+) concept mappings\)",
                           r"(\d+) concepts mapped across", r"\((\d+) mappings\)", r"(\d+)-concept cross-reference"],
    "jurisdiction_profiles": [r"(\d+) jurisdiction profiles"],
    "sector_benchmarks": [r"[Bb]enchmarks for (\d+) sectors", r"(\d+) sectors \(GIIN", r"(\d+) sectors with benchmark"],
    "dd_questions": [r"(\d+) DD questions", r"\*\*(\d+) questions\*\*", r"(\d+) questions across",
                     r"\((\d+) questions"],
    "dd_categories": [r"(\d+) questions / (\d+) categories", r"across \*\*(\d+) categories\*\*",
                      r"questions across (\d+) categories"],
    "framework_modules": [r"\((\d+) framework modules\)", r"all (\d+) framework modules"],
}


def test_docs_quote_the_real_numbers() -> None:
    facts = _GEN["code_facts"]()
    problems = []
    for doc in ("README.md", "CLAUDE.md"):
        text = (ROOT / doc).read_text(encoding="utf-8")
        for fact, patterns in PATTERNS.items():
            for pattern in patterns:
                for match in re.finditer(pattern, text):
                    claimed = int(match.groups()[-1])
                    if claimed != facts[fact]:
                        line = text[: match.start()].count("\n") + 1
                        problems.append(f"{doc}:{line}: says {claimed} for {fact}, code has {facts[fact]}")
    assert not problems, "\n".join(problems)


def test_tool_reference_is_generated_and_current() -> None:
    path = ROOT / "docs" / "reference" / "tools.md"
    assert path.read_text(encoding="utf-8") == _GEN["render"](), (
        "docs/reference/tools.md is stale: run python scripts/build_tool_reference.py"
    )


def test_readme_tool_summary_lists_every_tool_once() -> None:
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    section = text.split("### Agent Tools (", 1)[1].split("\n## ", 1)[0]
    listed = re.findall(r"`([a-z_]+)`", section.split("| Task area | Tools |", 1)[1])
    real = {tool.name for tool in _GEN["impact_tools"]()}
    assert set(listed) == real and len(listed) == len(real)
