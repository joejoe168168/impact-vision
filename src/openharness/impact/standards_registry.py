"""Versioned sustainability and impact standards registry."""

from __future__ import annotations

from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, field_validator

from openharness.impact._paths import data_path

StandardStatus = Literal["active", "draft", "under_revision", "superseded"]


class StandardArticle(BaseModel):
    standard_id: str
    article_id: str
    chapter: str
    text_summary: str
    modality: Literal["shall", "encouraged", "neutral"]
    topics: list[str] = Field(default_factory=list)
    content_status: Literal["source_text", "curated_summary", "generated_summary"] = "generated_summary"
    source_url: str = ""


def load_articles(standard_id: str) -> list[StandardArticle]:
    filename = standard_id.strip().lower().replace("-", "_")
    path = data_path("standard_articles", f"{filename}.yaml")
    if not path.exists():
        raise KeyError(f"No article data for {standard_id}")
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    modalities = [
        name for name, count in payload["modality_counts"].items() for _ in range(int(count))
    ]
    chapters = payload["chapter_ranges"]
    rows = []
    for number in range(1, int(payload["article_count"]) + 1):
        chapter = next(
            item["chapter"] for item in chapters if item["start"] <= number <= item["end"]
        )
        rows.append(
            StandardArticle(
                standard_id=payload["standard_id"],
                article_id=str(number),
                chapter=chapter,
                text_summary=f"Article {number} establishes a {chapter.lower()} reporting or governance requirement.",
                modality=modalities[number - 1],
                topics=[],
                content_status=payload.get("content_status", "generated_summary"),
                source_url=payload.get("source_url", ""),
            )
        )
    return rows


def mandatory_gap_scan(standard_id: str, covered_article_ids: list[str]) -> dict:
    articles = load_articles(standard_id)
    covered = {str(value) for value in covered_article_ids}
    mandatory = [article for article in articles if article.modality == "shall"]
    gaps = [
        article.model_dump(mode="json")
        for article in mandatory
        if article.article_id not in covered
    ]
    return {
        "standard_id": articles[0].standard_id if articles else standard_id,
        "mandatory_total": len(mandatory),
        "covered_mandatory": len(mandatory) - len(gaps),
        "coverage_pct": round(100 * (len(mandatory) - len(gaps)) / len(mandatory), 1)
        if mandatory
        else 100,
        "gaps": gaps,
    }


class StandardVersion(BaseModel):
    """One versioned standard, rule pack, or methodology family."""

    standard_id: str = Field(description="Stable registry ID, e.g. IRIS_PLUS")
    name: str
    version: str
    status: StandardStatus = "active"
    effective_date: str = ""
    source_url: str = ""
    requirements_url: str = ""
    aliases: list[str] = Field(default_factory=list)
    scope: list[str] = Field(default_factory=list)
    requirement_ids: list[str] = Field(default_factory=list)
    notes: str = ""
    as_of: str = ""
    last_verified: str = ""

    @field_validator("standard_id")
    @classmethod
    def normalize_standard_id(cls, value: str) -> str:
        cleaned = value.strip().upper().replace("+", "_PLUS").replace("-", "_").replace(" ", "_")
        if not cleaned:
            raise ValueError("standard_id is required")
        return cleaned

    @field_validator("aliases", "scope", "requirement_ids")
    @classmethod
    def dedupe_text_list(cls, values: list[str]) -> list[str]:
        out: list[str] = []
        seen: set[str] = set()
        for value in values:
            cleaned = str(value).strip()
            key = cleaned.lower()
            if cleaned and key not in seen:
                seen.add(key)
                out.append(cleaned)
        return out

    @property
    def key(self) -> str:
        return f"{self.standard_id}@{self.version}"


class StandardsRegistry(BaseModel):
    """In-memory registry for versioned impact, ESG, and climate standards."""

    standards: list[StandardVersion] = Field(default_factory=list)

    def model_post_init(self, __context: object) -> None:
        keys = [item.key for item in self.standards]
        duplicates = sorted({key for key in keys if keys.count(key) > 1})
        if duplicates:
            raise ValueError(f"Duplicate standard versions: {', '.join(duplicates)}")

    def list_standards(self, *, status: StandardStatus | None = None) -> list[StandardVersion]:
        """Return standards, optionally filtered by status."""
        if status is None:
            return list(self.standards)
        return [item for item in self.standards if item.status == status]

    def get(self, standard_id: str, version: str | None = None) -> StandardVersion:
        """Get a standard by ID or alias.

        When no version is supplied, prefer active/under-revision rule packs over
        drafts or superseded versions, then choose the newest version string.
        """
        matches = [
            item
            for item in self.standards
            if _matches_standard(item, standard_id) and (version is None or item.version == version)
        ]
        if not matches:
            suffix = f" version {version}" if version else ""
            raise KeyError(f"Unknown standard '{standard_id}'{suffix}")
        return sorted(
            matches, key=lambda item: (_status_rank(item.status), item.version), reverse=True
        )[0]

    def active_rule_packs(self) -> list[StandardVersion]:
        """Return standards that should be used by default in new reports."""
        return [item for item in self.standards if item.status in {"active", "under_revision"}]

    def summary(self) -> dict[str, int]:
        """Count registered standards by status."""
        counts: dict[str, int] = {}
        for item in self.standards:
            counts[item.status] = counts.get(item.status, 0) + 1
        counts["total"] = len(self.standards)
        return counts


def default_standards_registry() -> StandardsRegistry:
    """Return the built-in standards registry (``data/standards_registry.yaml``, W5.1)."""
    from openharness.impact.knowledge import load_knowledge

    payload = load_knowledge("standards_registry.yaml")
    return StandardsRegistry(
        standards=[StandardVersion.model_validate(row) for row in payload.get("standards", [])]
    )


def get_default_standard(standard_id: str, version: str | None = None) -> StandardVersion:
    """Convenience lookup against the built-in registry."""
    return default_standards_registry().get(standard_id, version)


def _matches_standard(item: StandardVersion, standard_id: str) -> bool:
    needle = standard_id.strip().lower().replace("-", "_").replace(" ", "_")
    candidates = {item.standard_id.lower()}
    candidates.update(alias.lower().replace("-", "_").replace(" ", "_") for alias in item.aliases)
    return needle in candidates


def _status_rank(status: StandardStatus) -> int:
    return {
        "active": 4,
        "under_revision": 3,
        "draft": 2,
        "superseded": 1,
    }[status]


# ---------------------------------------------------------------------------
# Moved from roadmap_v2 (v7 W5.4)
# ---------------------------------------------------------------------------

class RulePackTestResult(BaseModel):
    """Compatibility test result for a disclosure rule pack."""

    pack_name: str
    version: str
    passed: bool
    failures: list[str] = Field(default_factory=list)


def run_rule_pack_tests(pack_name: str, version: str, required_fields: list[str], payload: dict[str, Any]) -> RulePackTestResult:
    """Check that a rule pack can still resolve its required fields."""
    failures = [field for field in required_fields if field not in payload]
    return RulePackTestResult(pack_name=pack_name, version=version, passed=not failures, failures=failures)


__all__ = [
    "RulePackTestResult",
    "run_rule_pack_tests",

    "StandardArticle",
    "StandardStatus",
    "StandardVersion",
    "StandardsRegistry",
    "default_standards_registry",
    "get_default_standard",
    "load_articles",
    "mandatory_gap_scan",
]
