"""Registry-generated surfaces (v7 W3.1).

REST routes, MCP tools/prompts and the web console all describe the same
impact tools. Instead of hand-writing a wrapper per tool per surface, they
read the fund-profile tool registry through this module:

* :func:`surface_tools` – the impact tools exposed to external surfaces
  (fund profile, no deprecated aliases).
* :func:`tool_manifest` / :func:`tool_entry` – name, title, area, summary
  and the JSON schema of each tool's input model.
* :func:`run_tool` – validate a JSON payload against the input model and
  execute the tool.
* :func:`playbook_prompt` – a ready-to-send prompt for a tool_advisor
  playbook (used for MCP prompts and chat starters).

Remote callers (the REST API) must not make the server read local files or
fetch URLs on their behalf, so :func:`run_tool` rejects the path/URL fields
in :data:`SERVER_PATH_FIELDS` unless ``allow_paths=True`` (MCP over stdio,
which runs as the local user) or ``IMPACT_VISION_API_ALLOW_PATHS=1``.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any


ALLOW_PATHS_ENV = "IMPACT_VISION_API_ALLOW_PATHS"
SERVER_PATH_FIELDS = frozenset({
    "file_path", "output_path", "output_dir", "thesis_path", "url",
})

# Display grouping for consoles and docs; tools not listed fall under "More".
AREAS: dict[str, tuple[str, ...]] = {
    "Screen a deal": (
        "assess_deal", "pitch_deck_analyze", "exclusion_screening", "dd_checklist",
        "decision_workflow", "pipeline",
    ),
    "Score impact": (
        "five_dimension_assess", "sdg_mapper", "gap_analysis", "impact_quantifier",
        "impact_valuation", "contribution_tracker", "impact_risk_opportunity", "toc_builder",
    ),
    "Evidence & assurance": (
        "greenwashing_detect", "evidence_review", "verification_workspace", "dmrv_evidence",
        "impact_data_quality", "carbon_credit_integrity", "ai_governance", "stakeholder_voice",
        "survey_delivery",
    ),
    "Report & LPs": (
        "impact_report", "lp_narrative", "ddq_responder", "investee_portal", "portfolio_analyze",
        "portfolio_query", "trend_analysis", "monitoring", "exit_impact",
    ),
    "Standards & regulation": (
        "framework_assess", "cross_reference", "iris_catalog", "impact_metric_recommender",
        "regulatory_calendar", "emission_factors", "climate_scenario_risk", "lca_assessment",
        "product_passport", "hrdd_assess", "esg_toolbox", "impact_linked_finance",
    ),
    "Consulting": ("engagement_workspace", "engagement_suite", "improvement_advisor"),
    "Guidance": ("impact_advisor",),
}
_AREA_OF = {tool: area for area, tools in AREAS.items() for tool in tools}


class ToolNotFound(KeyError):
    """The requested tool is not on the external surface."""


class PathFieldRejected(ValueError):
    """A remote caller tried to pass a server-side path or URL."""


@lru_cache(maxsize=1)
def _registry():  # type: ignore[no-untyped-def]
    from openharness.tools import create_default_tool_registry

    return create_default_tool_registry(profile="fund")


def surface_tools() -> list[Any]:
    """Impact tools on the external surface, sorted by name."""
    tools = [
        t for t in _registry().list_tools()
        if type(t).__module__.startswith("openharness.tools.impact")
        and not getattr(t, "deprecated_for", None)
    ]
    return sorted(tools, key=lambda t: t.name)


def get_surface_tool(name: str) -> Any:
    tool = _registry().get(name)
    if tool is None or tool not in surface_tools():
        raise ToolNotFound(name)
    return tool


def _title(name: str) -> str:
    special = {"sdg": "SDG", "lp": "LP", "dd": "DD", "esg": "ESG", "ddq": "DDQ", "toc": "ToC",
               "hrdd": "HRDD", "lca": "LCA", "dmrv": "dMRV", "ai": "AI", "iris": "IRIS+"}
    return " ".join(special.get(part, part.capitalize()) for part in name.split("_"))


def _summary(description: str) -> str:
    first = (description or "").strip().split("\n", 1)[0]
    return first.split(". ", 1)[0].rstrip(".") + "." if first else ""


def tool_entry(tool: Any, *, include_schema: bool = True) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "name": tool.name,
        "title": _title(tool.name),
        "area": _AREA_OF.get(tool.name, "More"),
        "summary": _summary(tool.description),
        "description": tool.description,
    }
    if include_schema:
        entry["input_schema"] = tool.input_model.model_json_schema()
    return entry


def tool_manifest(*, include_schema: bool = True) -> list[dict[str, Any]]:
    return [tool_entry(t, include_schema=include_schema) for t in surface_tools()]


def _allow_paths(explicit: bool | None) -> bool:
    if explicit is not None:
        return explicit
    return os.environ.get(ALLOW_PATHS_ENV, "").strip().lower() in {"1", "true", "yes"}


def validate_payload(name: str, payload: dict[str, Any] | None, *,
                     allow_paths: bool | None = None) -> tuple[Any, Any]:
    """Return ``(tool, arguments)``; raises ToolNotFound / PathFieldRejected / ValidationError."""
    tool = get_surface_tool(name)
    payload = dict(payload or {})
    if not _allow_paths(allow_paths):
        blocked = sorted(k for k in payload if k in SERVER_PATH_FIELDS and payload[k])
        if blocked:
            raise PathFieldRejected(
                f"{', '.join(blocked)} cannot be set over this API (the server would read or "
                f"write its own files/URLs). Send the content inline, or set {ALLOW_PATHS_ENV}=1 "
                "on a trusted single-user deployment."
            )
    return tool, tool.input_model.model_validate(payload)


async def run_tool(name: str, payload: dict[str, Any] | None = None, *,
                   allow_paths: bool | None = None, cwd: str | Path | None = None) -> dict[str, Any]:
    """Validate and execute *name*; returns ``{tool, output, is_error, metadata}``."""
    from openharness.tools.base import ToolExecutionContext

    tool, arguments = validate_payload(name, payload, allow_paths=allow_paths)
    result = await tool.execute(arguments, ToolExecutionContext(cwd=Path(cwd or Path.cwd())))
    return {
        "tool": name,
        "output": result.output,
        "is_error": bool(result.is_error),
        "metadata": dict(result.metadata or {}),
    }


def playbook_prompt(playbook_id: str, subject: str = "") -> str:
    """A user message that walks an assistant through one advisor playbook."""
    from openharness.impact.tool_advisor import get_playbook

    playbook = get_playbook(playbook_id)
    if playbook is None:
        raise KeyError(playbook_id)
    lines = [f"Run the Impact Vision '{playbook.name}' playbook"
             + (f" for {subject}." if subject else "."),
             f"When to use: {playbook.when_to_use}", "", "Steps:"]
    lines += [f"{i}. `{step.tool}` — {step.purpose}" for i, step in enumerate(playbook.steps, 1)]
    lines += ["", "Pass the assessment_id between steps instead of re-typing company data, "
              "say which figures are reported versus inferred, and finish with the decision "
              "and the three most valuable missing pieces of evidence."]
    return "\n".join(lines)


__all__ = [
    "ALLOW_PATHS_ENV",
    "AREAS",
    "PathFieldRejected",
    "SERVER_PATH_FIELDS",
    "ToolNotFound",
    "get_surface_tool",
    "playbook_prompt",
    "run_tool",
    "surface_tools",
    "tool_entry",
    "tool_manifest",
    "validate_payload",
]
