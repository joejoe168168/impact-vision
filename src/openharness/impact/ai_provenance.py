"""AI-provenance disclosure stamped on every deliverable (v7 W4.5).

The EU AI Act transparency rules (Art 50, Regulation (EU) 2024/1689 as
amended by the Digital Omnibus, Regulation (EU) 2026/1744) apply from
2026-08-02; marking AI-generated content applies from 2026-12-02 for systems
already on the market. ISSA 5000 / HKSSA 5000 assurers also ask *where* AI
was used for each figure. This module answers both from the report data:

* **extraction** – who pulled claims out of the documents (rules or an LLM),
* **calculation** – how scores were computed (deterministic model; whether
  they rest on reported metrics or were estimated from text),
* **tagging** – who mapped claims to IRIS+ / SDG codes,
* **drafting** – whether any narrative text was written by an LLM.

One :class:`AIProvenance` record feeds the HTML / PDF report badge and
appendix, the IC memo (HTML + DOCX), the DD report, the XLSX methodology
sheet, the CSV and the JSON export, so every format says the same thing.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, computed_field

AIStage = Literal["extraction", "calculation", "tagging", "drafting"]
AIMethod = Literal["llm", "rules", "deterministic", "human", "none", "unknown"]

AI_ACT_REFERENCE = (
    "EU AI Act Art 50 transparency (Regulation (EU) 2024/1689 as amended by "
    "Regulation (EU) 2026/1744)"
)

_LLM_EXTRACTORS = ("llm", "openai", "anthropic", "claude", "gpt")

GENERIC_DISCLOSURE = (
    "Machine-generated document: produced automatically from the supplied inputs; it may "
    "contain automatically extracted or estimated figures. Review before relying on it."
)


class AIUseRecord(BaseModel):
    """Where AI or automation touched one figure or artefact."""

    figure: str
    stage: AIStage
    method: AIMethod
    model: str = ""
    estimated: bool = False
    reviewed_by_human: bool = False
    note: str = ""


class AIProvenance(BaseModel):
    """Per-report record of how AI and automation were used."""

    extraction: AIMethod = "rules"
    calculation: AIMethod = "deterministic"
    tagging: AIMethod = "rules"
    drafting: AIMethod = "none"
    llm_model: str = ""
    human_reviewed: bool = False
    estimated_figures: int = 0
    total_figures: int = 0
    records: list[AIUseRecord] = Field(default_factory=list)
    regulation: str = AI_ACT_REFERENCE

    @computed_field  # type: ignore[prop-decorator]
    @property
    def ai_generated(self) -> bool:
        """True when a generative model extracted, tagged or drafted content."""
        return "llm" in (self.extraction, self.tagging, self.drafting)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def badges(self) -> list[str]:
        """Short labels: extracted / estimated / drafted (by AI or by rules)."""
        out = [
            "Extracted by AI" if self.extraction == "llm"
            else "Extracted by rules" if self.extraction == "rules"
            else "Extracted by people" if self.extraction == "human"
            else "Extraction method not declared"
        ]
        if self.estimated_figures:
            out.append(f"{self.estimated_figures} of {self.total_figures} scores estimated")
        if self.drafting == "llm":
            out.append("Text drafted by AI")
        return out

    @computed_field  # type: ignore[prop-decorator]
    @property
    def disclosure(self) -> str:
        """One-sentence plain-English disclosure for footers and cover pages."""
        if self.ai_generated:
            who = f" ({self.llm_model})" if self.llm_model else ""
            parts = [s for s in ("extraction", "tagging", "drafting") if getattr(self, s) == "llm"]
            head = f"AI-assisted: a generative AI model{who} was used for {', '.join(parts)}."
        else:
            head = "Automated analysis: produced by rules and a deterministic scoring model; no generative AI was used."
        est = (
            f" {self.estimated_figures} of {self.total_figures} scores are estimated from document "
            "text rather than reported metrics."
            if self.estimated_figures
            else ""
        )
        review = " Reviewed by a person before release." if self.human_reviewed else " Review before relying on it."
        return head + est + review

    def as_rows(self) -> list[tuple[str, str]]:
        """``(label, value)`` pairs for tables (XLSX sheet, DOCX, CSV)."""
        return [
            ("AI disclosure", self.disclosure),
            ("Claim extraction", self.extraction),
            ("Score calculation", self.calculation),
            ("Metric / SDG tagging", self.tagging),
            ("Narrative drafting", self.drafting),
            ("Generative AI used", "yes" if self.ai_generated else "no"),
            ("Model", self.llm_model or "—"),
            ("Scores estimated from text", f"{self.estimated_figures} of {self.total_figures}"),
            ("Human review", "yes" if self.human_reviewed else "not recorded"),
            ("Regulation", self.regulation),
        ]


def _method(value: Any, default: AIMethod) -> AIMethod:
    text = str(value or "").strip().lower()
    return text if text in ("llm", "rules", "deterministic", "human", "none", "unknown") else default  # type: ignore[return-value]


def _extraction_from_claims(claims: list[dict]) -> tuple[AIMethod, str]:
    ids = [str(c.get("extracted_by") or "") for c in claims if isinstance(c, dict)]
    ids = [i for i in ids if i]
    llm = [i for i in ids if i.lower().startswith(_LLM_EXTRACTORS) and "fallback" not in i.lower()]
    if llm:
        return "llm", llm[0]
    return "rules", ""


def ai_provenance_for_report(data: dict[str, Any]) -> AIProvenance:
    """Build the :class:`AIProvenance` record for a ``report_data`` dict.

    ``data["ai_usage"]`` (``extraction`` / ``calculation`` / ``tagging`` /
    ``drafting`` / ``model`` / ``human_reviewed``) overrides what can be
    inferred; otherwise extraction comes from each claim's ``extracted_by``
    and estimation from the Five Dimensions / SDG provenance.
    """
    usage = data.get("ai_usage") or {}
    claims = list(data.get("impact_claims") or [])
    inferred_extraction, inferred_model = _extraction_from_claims(claims)
    extraction = _method(usage.get("extraction"), inferred_extraction)
    tagging = _method(usage.get("tagging"), "llm" if extraction == "llm" else "rules")
    drafting = _method(usage.get("drafting"), "none")
    calculation = _method(usage.get("calculation"), "deterministic")
    model = str(usage.get("model") or inferred_model or "")

    records: list[AIUseRecord] = []
    fd = data.get("five_dimensions") or {}
    for dim in ("what", "who", "how_much", "contribution", "risk"):
        d = fd.get(dim) if isinstance(fd, dict) else None
        if not isinstance(d, dict):
            continue
        prov = str(d.get("provenance") or "estimated")
        records.append(AIUseRecord(
            figure=f"Five Dimensions: {dim.replace('_', ' ')}",
            stage="calculation", method=calculation,
            estimated=prov == "estimated",
            note=f"evidence: {prov}",
        ))
    for a in data.get("sdg_alignments") or data.get("sdg_alignment") or []:
        if not isinstance(a, dict) or not a.get("goal"):
            continue
        basis = str(a.get("scoring_basis") or a.get("provenance") or "estimated")
        records.append(AIUseRecord(
            figure=f"SDG {a['goal']} alignment",
            stage="calculation", method=calculation,
            estimated=basis == "estimated",
            note=f"basis: {basis}",
        ))
    if claims:
        records.append(AIUseRecord(
            figure=f"{len(claims)} impact claims", stage="extraction", method=extraction, model=model,
        ))
        records.append(AIUseRecord(
            figure="IRIS+ / SDG mapping of claims", stage="tagging", method=tagging, model=model if tagging == "llm" else "",
        ))
    if drafting != "none":
        records.append(AIUseRecord(figure="Narrative text", stage="drafting", method=drafting, model=model))

    scores = [r for r in records if r.stage == "calculation"]
    return AIProvenance(
        extraction=extraction,
        calculation=calculation,
        tagging=tagging,
        drafting=drafting,
        llm_model=model,
        human_reviewed=bool(usage.get("human_reviewed", False)),
        estimated_figures=sum(1 for r in scores if r.estimated),
        total_figures=len(scores),
        records=records,
    )


def ai_provenance_for_assessment(assessment: Any, ai_usage: dict | None = None) -> AIProvenance:
    """Same as :func:`ai_provenance_for_report` for an ``Assessment`` model."""
    fd = getattr(assessment, "five_dimensions", None)
    return ai_provenance_for_report({
        "impact_claims": [c.model_dump() for c in getattr(assessment, "impact_claims", []) or []],
        "five_dimensions": fd.model_dump() if fd is not None else None,
        "sdg_alignments": [a.model_dump() for a in getattr(assessment, "sdg_alignments", []) or []],
        "ai_usage": ai_usage or {},
    })


def ai_provenance_dict(data: dict[str, Any]) -> dict[str, Any]:
    return ai_provenance_for_report(data).model_dump(mode="json")


__all__ = [
    "AI_ACT_REFERENCE",
    "GENERIC_DISCLOSURE",
    "ai_provenance_for_assessment",
    "AIMethod",
    "AIProvenance",
    "AIStage",
    "AIUseRecord",
    "ai_provenance_dict",
    "ai_provenance_for_report",
]
