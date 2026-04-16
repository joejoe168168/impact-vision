"""Tool: Exclusion screening against norms-based criteria."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field

from openharness.tools.base import BaseTool, ToolExecutionContext, ToolResult


_DEFAULT_CRITERIA: dict[str, dict] = {
    "controversial_weapons": {
        "label": "Controversial Weapons",
        "keywords": ["cluster munition", "anti-personnel mine", "biological weapon", "chemical weapon", "nuclear weapon"],
        "severity": "mandatory",
    },
    "fossil_fuel": {
        "label": "Fossil Fuel Exposure",
        "keywords": ["coal mining", "oil exploration", "oil drilling", "petroleum", "fracking", "tar sands"],
        "severity": "mandatory",
    },
    "tobacco": {
        "label": "Tobacco",
        "keywords": ["tobacco", "cigarette", "vaping"],
        "severity": "mandatory",
    },
    "ungc_violations": {
        "label": "UN Global Compact Violations",
        "keywords": ["child labor", "forced labor", "human trafficking", "modern slavery", "corruption", "bribery"],
        "severity": "mandatory",
    },
}

_criteria_cache: dict | None = None


def _load_exclusion_criteria() -> dict[str, dict]:
    global _criteria_cache
    if _criteria_cache is not None:
        return _criteria_cache

    paths = [
        Path(__file__).parent.parent.parent.parent / "data" / "exclusion_criteria.yaml",
        Path("data/exclusion_criteria.yaml"),
    ]
    for path in paths:
        if path.exists():
            try:
                raw = yaml.safe_load(path.read_text(encoding="utf-8"))
                if isinstance(raw, dict) and "categories" in raw:
                    _criteria_cache = raw["categories"]
                    return _criteria_cache
            except Exception:
                pass

    _criteria_cache = _DEFAULT_CRITERIA
    return _criteria_cache


class ExclusionScreeningInput(BaseModel):
    company_name: str = Field(description="Name of the company")
    company_description: str = Field(default="", description="Company description")
    sector: str = Field(default="")
    geography: str = Field(default="", description="Country or region")
    severity_filter: Literal["all", "mandatory", "common", "watch"] = Field(
        default="all", description="Filter by severity level"
    )
    output_format: Literal["text", "json"] = Field(default="text")


class ExclusionScreeningTool(BaseTool):
    name = "exclusion_screening"
    description = (
        "Screen a company against norms-based exclusion criteria (UNGC, controversial weapons, "
        "fossil fuels, tobacco, predatory lending, etc.). Returns pass/fail with specific flags. "
        "This should be the first step in any impact due diligence workflow."
    )
    input_model = ExclusionScreeningInput

    def is_read_only(self, arguments: BaseModel) -> bool:
        return True

    async def execute(self, arguments: BaseModel, context: ToolExecutionContext) -> ToolResult:
        args = arguments if isinstance(arguments, ExclusionScreeningInput) else ExclusionScreeningInput.model_validate(arguments)

        criteria = _load_exclusion_criteria()
        text = f"{args.company_name} {args.company_description} {args.sector}".lower()

        hits: list[dict] = []
        for category_id, cat in criteria.items():
            severity = cat.get("severity", "common")
            if args.severity_filter != "all" and severity != args.severity_filter:
                continue

            matched_keywords = [kw for kw in cat.get("keywords", []) if kw.lower() in text]
            if matched_keywords:
                hits.append({
                    "category": category_id,
                    "label": cat.get("label", category_id),
                    "severity": severity,
                    "matched_keywords": matched_keywords,
                    "sfdr_pai": cat.get("sfdr_pai", ""),
                    "description": cat.get("description", ""),
                })

        passed = len(hits) == 0
        mandatory_fails = [h for h in hits if h["severity"] == "mandatory"]

        payload = {
            "company": args.company_name,
            "result": "PASS" if passed else "FAIL",
            "mandatory_fails": len(mandatory_fails),
            "total_flags": len(hits),
            "flags": hits,
        }

        if args.output_format == "json":
            return ToolResult(output=json.dumps(payload, indent=2), metadata=payload)

        if passed:
            lines = [
                f"EXCLUSION SCREENING: {args.company_name}",
                "=" * 50,
                "Result: PASS - No exclusion criteria triggered",
                f"Categories screened: {len(criteria)}",
            ]
        else:
            lines = [
                f"EXCLUSION SCREENING: {args.company_name}",
                "=" * 50,
                f"Result: FAIL - {len(hits)} exclusion flag(s) detected",
                f"Mandatory fails: {len(mandatory_fails)}",
                "",
            ]
            for hit in hits:
                sev = hit["severity"].upper()
                lines.append(f"  [{sev}] {hit['label']}")
                lines.append(f"    Matched: {', '.join(hit['matched_keywords'])}")
                if hit["sfdr_pai"]:
                    lines.append(f"    SFDR PAI: {hit['sfdr_pai']}")
                lines.append(f"    {hit['description']}")
                lines.append("")

        return ToolResult(output="\n".join(lines), metadata=payload)


def quick_exclusion_check(company_name: str, description: str, sector: str) -> dict:
    """Lightweight exclusion check for embedding in other tools. Returns {passed, flags}."""
    criteria = _load_exclusion_criteria()
    text = f"{company_name} {description} {sector}".lower()
    flags: list[str] = []
    for category_id, cat in criteria.items():
        matched = [kw for kw in cat.get("keywords", []) if kw.lower() in text]
        if matched:
            flags.append(f"{cat.get('label', category_id)} ({', '.join(matched)})")
    return {"passed": len(flags) == 0, "flags": flags}
