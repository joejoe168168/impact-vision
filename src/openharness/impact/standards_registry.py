"""Versioned sustainability and impact standards registry."""

from __future__ import annotations

from pathlib import Path
from typing import Literal
import yaml

from pydantic import BaseModel, Field, field_validator


StandardStatus = Literal["active", "draft", "under_revision", "superseded"]


class StandardArticle(BaseModel):
    standard_id: str
    article_id: str
    chapter: str
    text_summary: str
    modality: Literal["shall", "encouraged", "neutral"]
    topics: list[str] = Field(default_factory=list)


def load_articles(standard_id: str) -> list[StandardArticle]:
    filename = standard_id.strip().lower().replace("-", "_")
    path = Path(__file__).resolve().parents[3] / "data" / "standard_articles" / f"{filename}.yaml"
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
    """Return the built-in institutional-readiness standards registry."""
    return StandardsRegistry(
        standards=[
            StandardVersion(
                standard_id="IRIS_PLUS",
                name="GIIN IRIS+ Catalog of Metrics",
                version="5.3c",
                status="active",
                effective_date="2025-12",
                source_url="https://iris.thegiin.org/",
                requirements_url="https://iris.thegiin.org/catalog/download/",
                aliases=["IRIS+", "GIIN IRIS", "IRIS"],
                scope=["impact metrics", "SDG alignment", "5 dimensions"],
                notes="Current public IRIS+ catalog is v5.3c, released December 2025.",
            ),
            StandardVersion(
                standard_id="EDCI",
                name="ESG Data Convergence Initiative Metrics",
                version="2026",
                status="active",
                source_url="https://www.esgdc.org/metrics/",
                requirements_url="https://www.esgdc.org/metrics/",
                aliases=["ILPA EDCI", "ESG Data Convergence Initiative"],
                scope=[
                    "private markets ESG",
                    "GHG",
                    "decarbonization",
                    "workforce",
                    "cybersecurity",
                ],
                requirement_ids=[
                    "GHG Emissions",
                    "Decarbonization",
                    "Renewable Energy",
                    "Diversity",
                    "Work-related Accidents",
                    "Net New Hires",
                    "Employee Engagement",
                    "Cybersecurity",
                ],
                notes="Public 2026 EDCI materials add cybersecurity and classify selected fields as non-core.",
            ),
            StandardVersion(
                standard_id="ISSB",
                name="IFRS Sustainability Disclosure Standards",
                version="S1-S2-2023",
                status="active",
                effective_date="2024-01-01",
                source_url="https://www.ifrs.org/issued-standards/ifrs-sustainability-standards-navigator/",
                requirements_url="https://www.ifrs.org/sustainability/knowledge-hub/introduction-to-issb-and-ifrs-sustainability-disclosure-standards/",
                aliases=["IFRS S1", "IFRS S2", "ISSB S1/S2"],
                scope=["general sustainability disclosure", "climate disclosure"],
                requirement_ids=[
                    "governance",
                    "strategy",
                    "risk_management",
                    "metrics_and_targets",
                ],
                notes="IFRS S1 and S2 were issued in June 2023 and are effective for annual reporting periods beginning on or after 2024-01-01.",
            ),
            StandardVersion(
                standard_id="ESRS",
                name="European Sustainability Reporting Standards",
                version="2023-delegated-act",
                status="active",
                effective_date="2024-01-01",
                source_url="https://finance.ec.europa.eu/capital-markets-union-and-financial-markets/company-reporting-and-auditing/company-reporting/corporate-sustainability-reporting_en",
                requirements_url="https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32023R2772",
                aliases=["CSRD ESRS", "EFRAG ESRS"],
                scope=[
                    "double materiality",
                    "EU sustainability reporting",
                    "12 sector-agnostic standards",
                ],
                requirement_ids=[
                    "ESRS 1",
                    "ESRS 2",
                    "E1",
                    "E2",
                    "E3",
                    "E4",
                    "E5",
                    "S1",
                    "S2",
                    "S3",
                    "S4",
                    "G1",
                ],
                notes="First set of adopted sector-agnostic ESRS: ESRS 1, ESRS 2, E1-E5, S1-S4, and G1.",
            ),
            StandardVersion(
                standard_id="ESRS",
                name="European Sustainability Reporting Standards Simplification Drafts",
                version="2025-exposure-draft",
                status="draft",
                source_url="https://www.efrag.org/",
                aliases=["ESRS Omnibus Draft"],
                scope=["double materiality", "EU sustainability reporting"],
                notes="Historical draft simplification package; finalised as Directive (EU) 2026/470 (see ESRS@2026-omnibus-i).",
            ),
            StandardVersion(
                standard_id="ESRS",
                name="ESRS under the Omnibus I simplification (Directive (EU) 2026/470)",
                version="2026-omnibus-i",
                status="under_revision",
                effective_date="2026-03-18",
                source_url="https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=OJ:L_202600470",
                requirements_url="https://finance.ec.europa.eu/capital-markets-union-and-financial-markets/company-reporting-and-auditing/company-reporting/corporate-sustainability-reporting_en",
                aliases=["Omnibus I", "Amended ESRS", "ESRS Omnibus", "CSRD Omnibus"],
                scope=["double materiality", "EU sustainability reporting", "scope reduction"],
                notes=(
                    "Omnibus I Directive (EU) 2026/470 entered into force 2026-03-18. "
                    "CSRD mandatory scope narrowed to undertakings with >1,000 employees "
                    "AND >EUR 450M net turnover (cumulative); listed-SME and most former "
                    "Wave 2/3 entities out of scope; sector-specific ESRS removed. "
                    "Member States transpose by 2027-03-19, applying from FY2027. A "
                    "SIMPLIFIED ESRS delegated act is targeted for 2026-09 (FY2027 use); "
                    "until adopted, the 2023-delegated-act ESRS remain the substantive "
                    "rule set for in-scope reporters."
                ),
            ),
            StandardVersion(
                standard_id="CSDDD",
                name="Corporate Sustainability Due Diligence Directive (as amended by Omnibus I)",
                version="2026-omnibus-i",
                status="active",
                effective_date="2029-07-26",
                source_url="https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=OJ:L_202600470",
                aliases=["CS3D", "CSDDD", "Corporate Sustainability Due Diligence"],
                scope=["human rights due diligence", "environmental due diligence", "value chain"],
                requirement_ids=[
                    "identify",
                    "prevent",
                    "mitigate",
                    "remediate",
                    "grievance",
                    "monitor",
                ],
                notes=(
                    "Amended by Omnibus I (Directive (EU) 2026/470). Application deferred "
                    "to 2029-07-26 (MS transposition by 2028-07-26). Scope narrowed to "
                    ">5,000 employees + EUR 1.5B net worldwide turnover (non-EU: EUR 1.5B "
                    "EU turnover). Climate transition-plan adoption obligation removed; "
                    "EU-harmonised civil-liability regime removed (national law applies); "
                    "penalties capped at 3% of net global turnover. HRDD/OECD-UNGP "
                    "expectations remain a market/LP norm regardless of legal scope."
                ),
            ),
            StandardVersion(
                standard_id="ESRS_SIMPLIFIED_2026",
                name="Simplified European Sustainability Reporting Standards",
                version="2026-draft",
                status="draft",
                effective_date="2027-01-01",
                source_url="https://www.efrag.org/en/sustainability-reporting/esrs-workstreams/amended-esrs",
                scope=["CSRD", "double materiality", "simplified datapoints"],
                notes="Draft exposure set as of 2026-07; final delegated act pending.",
            ),
            StandardVersion(
                standard_id="SFDR",
                name="Sustainable Finance Disclosure Regulation Principal Adverse Impact Indicators",
                version="2022-RTS",
                status="active",
                effective_date="2023-01-01",
                source_url="https://finance.ec.europa.eu/sustainable-finance/disclosures/sustainability-related-disclosure-financial-services-sector_en",
                requirements_url="https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32022R1288",
                aliases=["SFDR PAI", "PAI"],
                scope=["principal adverse impacts", "financial-market disclosure"],
                requirement_ids=[f"PAI-{n}" for n in range(1, 15)],
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
                requirements_url="https://www.impactprinciples.org/common-and-emerging-practices/",
                aliases=["IFC OPIM", "Impact Principles"],
                scope=["impact management system", "verification", "impact at exit"],
                requirement_ids=[f"Principle {n}" for n in range(1, 10)],
                notes="Principle 7 covers impact at exit; Principle 8 covers review, documentation, and learning.",
            ),
        ]
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


__all__ = [
    "StandardArticle",
    "StandardStatus",
    "StandardVersion",
    "StandardsRegistry",
    "default_standards_registry",
    "get_default_standard",
    "load_articles",
    "mandatory_gap_scan",
]
