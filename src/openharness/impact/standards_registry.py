"""Versioned sustainability and impact standards registry."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


StandardStatus = Literal["active", "draft", "under_revision", "superseded"]


class StandardVersion(BaseModel):
    """One versioned standard, rule pack, or methodology family."""

    standard_id: str = Field(description="Stable registry ID, e.g. IRIS_PLUS")
    name: str
    version: str
    status: StandardStatus = "active"
    effective_date: str = ""
    source_url: str = ""
    aliases: list[str] = Field(default_factory=list)
    scope: list[str] = Field(default_factory=list)
    notes: str = ""

    @field_validator("standard_id")
    @classmethod
    def normalize_standard_id(cls, value: str) -> str:
        cleaned = value.strip().upper().replace("+", "_PLUS").replace("-", "_").replace(" ", "_")
        if not cleaned:
            raise ValueError("standard_id is required")
        return cleaned

    @field_validator("aliases", "scope")
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
        """Get a standard by ID or alias, selecting the newest entry when version is omitted."""
        matches = [
            item
            for item in self.standards
            if _matches_standard(item, standard_id) and (version is None or item.version == version)
        ]
        if not matches:
            suffix = f" version {version}" if version else ""
            raise KeyError(f"Unknown standard '{standard_id}'{suffix}")
        return sorted(matches, key=lambda item: item.version, reverse=True)[0]

    def active_rule_packs(self) -> list[StandardVersion]:
        """Return standards that should be used by default in new reports."""
        return [
            item
            for item in self.standards
            if item.status in {"active", "under_revision"}
        ]

    def summary(self) -> dict[str, int]:
        """Count registered standards by status."""
        counts: dict[str, int] = {}
        for item in self.standards:
            counts[item.status] = counts.get(item.status, 0) + 1
        counts["total"] = len(self.standards)
        return counts


def default_standards_registry() -> StandardsRegistry:
    """Return the built-in institutional-readiness standards registry."""
    return StandardsRegistry(standards=[
        StandardVersion(
            standard_id="IRIS_PLUS",
            name="GIIN IRIS+ Catalog of Metrics",
            version="5.3c",
            status="active",
            effective_date="2023",
            source_url="https://iris.thegiin.org/",
            aliases=["IRIS+", "GIIN IRIS", "IRIS"],
            scope=["impact metrics", "SDG alignment", "5 dimensions"],
        ),
        StandardVersion(
            standard_id="EDCI",
            name="ESG Data Convergence Initiative Metrics",
            version="2025",
            status="active",
            source_url="https://ilpa.org/industry-guidance/environmental-social-governance/data-convergence-initiative/",
            aliases=["ILPA EDCI", "ESG Data Convergence Initiative"],
            scope=["private markets ESG", "GHG", "workforce", "governance"],
        ),
        StandardVersion(
            standard_id="ISSB",
            name="IFRS Sustainability Disclosure Standards",
            version="S1-S2-2023",
            status="active",
            effective_date="2024-01-01",
            source_url="https://www.ifrs.org/issued-standards/ifrs-sustainability-standards-navigator/",
            aliases=["IFRS S1", "IFRS S2", "ISSB S1/S2"],
            scope=["general sustainability disclosure", "climate disclosure"],
        ),
        StandardVersion(
            standard_id="ESRS",
            name="European Sustainability Reporting Standards",
            version="2023-delegated-act",
            status="active",
            effective_date="2024-01-01",
            source_url="https://finance.ec.europa.eu/capital-markets-union-and-financial-markets/company-reporting-and-auditing/company-reporting/corporate-sustainability-reporting_en",
            aliases=["CSRD ESRS", "EFRAG ESRS"],
            scope=["double materiality", "EU sustainability reporting"],
        ),
        StandardVersion(
            standard_id="ESRS",
            name="European Sustainability Reporting Standards Simplification Drafts",
            version="2025-exposure-draft",
            status="draft",
            source_url="https://www.efrag.org/",
            aliases=["Amended ESRS", "ESRS Omnibus Draft"],
            scope=["double materiality", "EU sustainability reporting"],
            notes="Draft simplification package; keep separate from adopted ESRS rule packs.",
        ),
        StandardVersion(
            standard_id="SFDR",
            name="Sustainable Finance Disclosure Regulation Principal Adverse Impact Indicators",
            version="2022-RTS",
            status="active",
            effective_date="2023-01-01",
            source_url="https://finance.ec.europa.eu/sustainable-finance/disclosures/sustainability-related-disclosure-financial-services-sector_en",
            aliases=["SFDR PAI", "PAI"],
            scope=["principal adverse impacts", "financial-market disclosure"],
        ),
        StandardVersion(
            standard_id="GHG_PROTOCOL",
            name="GHG Protocol Corporate Accounting and Reporting Standard",
            version="corporate-2004",
            status="under_revision",
            source_url="https://ghgprotocol.org/corporate-standard",
            aliases=["GHG Corporate", "GHGP Corporate"],
            scope=["scope 1", "scope 2", "corporate inventory"],
            notes="Corporate, Scope 2, and Scope 3 standards are in the active update process.",
        ),
        StandardVersion(
            standard_id="GHG_PROTOCOL_SCOPE2",
            name="GHG Protocol Scope 2 Guidance",
            version="scope2-2015",
            status="under_revision",
            source_url="https://ghgprotocol.org/scope-2-guidance",
            aliases=["GHG Scope 2", "GHGP Scope 2"],
            scope=["location-based electricity", "market-based electricity"],
        ),
        StandardVersion(
            standard_id="PCAF",
            name="Partnership for Carbon Accounting Financials Global GHG Accounting Standard",
            version="2022",
            status="active",
            source_url="https://carbonaccountingfinancials.com/",
            aliases=["PCAF Global Standard", "Financed Emissions"],
            scope=["financed emissions", "attribution factor", "data quality score"],
        ),
        StandardVersion(
            standard_id="OPIM",
            name="Operating Principles for Impact Management",
            version="2019",
            status="active",
            source_url="https://www.impactprinciples.org/",
            aliases=["IFC OPIM", "Impact Principles"],
            scope=["impact management system", "verification", "impact at exit"],
        ),
    ])


def get_default_standard(standard_id: str, version: str | None = None) -> StandardVersion:
    """Convenience lookup against the built-in registry."""
    return default_standards_registry().get(standard_id, version)


def _matches_standard(item: StandardVersion, standard_id: str) -> bool:
    needle = standard_id.strip().lower().replace("-", "_").replace(" ", "_")
    candidates = {item.standard_id.lower()}
    candidates.update(alias.lower().replace("-", "_").replace(" ", "_") for alias in item.aliases)
    return needle in candidates


__all__ = [
    "StandardStatus",
    "StandardVersion",
    "StandardsRegistry",
    "default_standards_registry",
    "get_default_standard",
]
