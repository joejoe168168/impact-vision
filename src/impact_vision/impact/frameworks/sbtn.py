"""Science Based Targets Network five-step nature-readiness workflow."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from impact_vision.impact.models import Company
from impact_vision.tools.impact.common import keyword_match_with_context

SBTNStepName = Literal["assess", "prioritise", "measure", "act", "track"]


class SBTNStep(BaseModel):
    step: SBTNStepName
    questions: list[dict] = Field(default_factory=list)
    complete: bool = False
    answered_count: int = 0


# Questions follow SBTN Corporate Manual steps 1–5 and the AR3T action
# hierarchy (Avoid → Reduce → Restore/Regenerate → Transform).
_QUESTIONS: dict[str, list[tuple[str, str, str, tuple[str, ...]]]] = {
    "assess": [
        (
            "A1",
            "Map value-chain activities and locations that interface with nature",
            "activity × location inventory (direct operations and upstream)",
            ("value chain map", "nature interface", "location inventory", "tnfd locate"),
        ),
        (
            "A2",
            "Identify nature pressures across land, freshwater, ocean, biodiversity and climate",
            "pressure inventory (ENCORE, SBTN Materiality Screening, or equivalent)",
            ("nature pressure", "encore", "materiality screening", "land conversion", "water withdrawal"),
        ),
        (
            "A3",
            "Estimate pressure materiality and high-impact commodities / biomes",
            "material commodities list plus biome/ecoregion overlap",
            ("high-impact commodity", "biome", "ecoregion", "deforestation-risk", "soft commodity"),
        ),
        (
            "A4",
            "Screen dependencies and impacts using TNFD LEAP or equivalent",
            "LEAP locate/evaluate working papers",
            ("tnfd", "leap", "nature-related dependencies", "nature-related impacts"),
        ),
    ],
    "prioritise": [
        (
            "P1",
            "Rank locations by state of nature and residual pressure",
            "geospatial ranking (integrity, importance, pressure)",
            ("priority sites", "state of nature", "geospatial", "hotspot"),
        ),
        (
            "P2",
            "Set target boundaries (direct operations vs upstream/downstream)",
            "boundary note covering ≥67% of material pressures where required",
            ("target boundary", "value-chain boundary", "direct operations", "upstream"),
        ),
        (
            "P3",
            "Identify affected stakeholders, including Indigenous Peoples and local communities",
            "rights-holder map and engagement record",
            ("indigenous", "local communities", "rights-holder", "fpic", "affected stakeholders"),
        ),
        (
            "P4",
            "Document geospatial evidence for priority sites",
            "site coordinates, land-cover layers, or equivalent spatial evidence",
            ("geospatial evidence", "gis", "land-cover", "satellite", "site coordinates"),
        ),
    ],
    "measure": [
        (
            "M1",
            "Measure baseline land use, conversion and land occupation",
            "ha converted / occupied vs a 2020 (or earlier) baseline",
            ("land use baseline", "land conversion", "no-conversion", "hectares converted"),
        ),
        (
            "M2",
            "Measure baseline freshwater quantity and quality pressures",
            "withdrawals, consumption, and pollutant loads in stressed basins",
            ("freshwater baseline", "water stress", "water withdrawal", "basin"),
        ),
        (
            "M3",
            "Measure baseline biodiversity state (species, ecosystems, integrity)",
            "state indicator (MSA, STAR, ecosystem integrity, or equivalent)",
            ("biodiversity baseline", "msa", "star", "ecosystem integrity", "species"),
        ),
        (
            "M4",
            "Measure climate pressure overlapping the nature target (GHG / land-use emissions)",
            "GHG inventory covering land-use change where material",
            ("ghg inventory", "land-use emissions", "scope 1", "carbon baseline"),
        ),
    ],
    "act": [
        (
            "AC1",
            "Avoid: commit to no conversion of natural ecosystems from a 2020 cut-off",
            "no-conversion / no-deforestation policy with cut-off date",
            (
                "no conversion",
                "no-conversion",
                "no deforestation",
                "no-deforestation",
                "cutoff date",
                "cut-off date",
                "avoid conversion",
            ),
        ),
        (
            "AC2",
            "Reduce remaining pressures on land, water, ocean and biodiversity",
            "quantified reduction actions (intensity or absolute)",
            ("reduce pressure", "water efficiency", "restore flow", "bycatch reduction"),
        ),
        (
            "AC3",
            "Restore and regenerate ecosystems in the landscape / seascape",
            "restoration / regenerative-agriculture area and method",
            ("restore", "restoration", "regenerative", "rewild", "landscape restoration"),
        ),
        (
            "AC4",
            "Transform: contribute to system-wide and landscape-scale change",
            "landscape partnership, policy engagement, or sector transformation",
            ("landscape partnership", "jurisdictional", "sector transformation", "transform"),
        ),
    ],
    "track": [
        (
            "T1",
            "Operate a monitoring plan with leading and lagging nature indicators",
            "monitoring protocol and indicator set",
            ("monitoring plan", "nature kpi", "track progress", "nature indicators"),
        ),
        (
            "T2",
            "Disclose progress aligned to TNFD / GBF Target 15",
            "public TNFD-aligned or GBF-15 disclosure",
            ("tnfd disclosure", "gbf target 15", "nature disclosure", "target 15"),
        ),
        (
            "T3",
            "Obtain independent verification of nature data and claims",
            "third-party assurance or SBTN validation",
            ("independent verification", "third-party assurance", "sbtn validation", "assured nature"),
        ),
        (
            "T4",
            "Apply adaptive management and revise targets when methods update",
            "review cadence and method-version register",
            ("adaptive management", "target revision", "method update", "sbtn v2"),
        ),
    ],
}

_PRESSURE_RANGES: dict[str, dict] = {
    "land": {
        "indicative_reduction_pct": [0, 0],
        "unit": "natural-ecosystem conversion after 2020 cut-off",
        "note": "SBTN land: no conversion of natural ecosystems from 2020; additional landscape restoration is separate.",
    },
    "freshwater": {
        "indicative_reduction_pct": [10, 50],
        "unit": "% reduction in basin-level pressure vs baseline",
        "note": "Quantity and quality targets are basin-specific; the range is a screening placeholder pending local allocation.",
    },
    "ocean": {
        "indicative_reduction_pct": [10, 40],
        "unit": "% reduction in material ocean pressure vs baseline",
        "note": "Covers over-extraction, benthic disturbance and pollution; not a substitute for fishery science.",
    },
    "biodiversity": {
        "indicative_reduction_pct": [10, 30],
        "unit": "% improvement in state-of-nature indicator (MSA/STAR/integrity)",
        "note": "State-of-nature targets follow from pressure reductions plus restoration; site-level science required.",
    },
    "climate": {
        "indicative_reduction_pct": [42, 50],
        "unit": "% absolute GHG reduction by 2030 vs 2020 (1.5°C)",
        "note": "Climate pressure uses SBTi 1.5°C cross-over; land-use emissions should be inside the GHG inventory.",
    },
}

_SECTOR_PRESSURE_HINTS: dict[str, tuple[str, ...]] = {
    "agriculture": ("land", "freshwater", "biodiversity", "climate"),
    "livestock": ("land", "freshwater", "biodiversity", "climate"),
    "energy": ("land", "climate", "biodiversity"),
    "mining": ("land", "freshwater", "biodiversity"),
    "extractives": ("land", "freshwater", "biodiversity"),
    "manufacturing": ("freshwater", "climate", "biodiversity"),
    "water": ("freshwater", "biodiversity"),
    "real estate": ("land", "climate"),
    "construction": ("land", "climate", "biodiversity"),
    "tourism": ("land", "ocean", "biodiversity"),
    "transport": ("climate", "ocean"),
    "logistics": ("climate",),
}


def _company_corpus(company: Company) -> str:
    parts = [company.description or "", company.sector or "", " ".join(company.impact_themes)]
    for key, value in (company.reported_metrics or {}).items():
        parts.append(str(key))
        parts.append(str(value))
    return " ".join(parts)


def _answered(qid: str, answers: dict, keywords: tuple[str, ...], corpus: str) -> tuple[bool, str]:
    if answers.get(qid):
        return True, "caller"
    if any(keyword_match_with_context(corpus, keyword) for keyword in keywords):
        return True, "auto_detected"
    return False, ""


def sbtn_readiness(company: Company, answers: dict) -> dict:
    answers = answers or {}
    corpus = _company_corpus(company)
    steps: list[SBTNStep] = []
    auto_detected: list[str] = []
    for name, questions in _QUESTIONS.items():
        rows = []
        answered_count = 0
        for qid, text, ask, keywords in questions:
            ok, source = _answered(qid, answers, keywords, corpus)
            if ok:
                answered_count += 1
                if source == "auto_detected":
                    auto_detected.append(qid)
            rows.append(
                {
                    "id": qid,
                    "text": text,
                    "evidence_ask": ask,
                    "answered": ok,
                    "source": source or "unanswered",
                }
            )
        steps.append(
            SBTNStep(
                step=name,  # type: ignore[arg-type]
                questions=rows,
                complete=answered_count == len(questions),
                answered_count=answered_count,
            )
        )
    total_q = sum(len(q) for q in _QUESTIONS.values())
    answered_q = sum(step.answered_count for step in steps)
    pct = round(100 * answered_q / total_q, 1) if total_q else 0.0
    sector_pressures = _SECTOR_PRESSURE_HINTS.get((company.sector or "").lower(), ())
    return {
        "company": company.name,
        "steps": [s.model_dump() for s in steps],
        "completion_pct": pct,
        "steps_complete": sum(step.complete for step in steps),
        "readiness_band": "ready" if pct == 100 else "developing" if pct >= 40 else "early",
        "next_actions": [
            q["text"] for s in steps if not s.complete for q in s.questions if not q["answered"]
        ],
        "auto_detected": auto_detected,
        "material_pressures_for_sector": list(sector_pressures),
        "gbf_target_15": "Supports business assessment and disclosure under GBF Target 15",
        "status": "beta",
        "as_of": "2026-07",
        "citations": [
            "SBTN Corporate Manual (steps 1–5) and AR3T action framework",
            "SBTN methods v1; v2 methods in beta",
            "Kunming-Montreal GBF Target 15",
            "TNFD LEAP",
        ],
    }


def nature_target_ranges(
    pressure: Literal["land", "freshwater", "ocean", "biodiversity", "climate"], sector: str
) -> dict:
    spec = _PRESSURE_RANGES[pressure]
    sector_key = (sector or "").lower()
    material = pressure in _SECTOR_PRESSURE_HINTS.get(sector_key, (pressure,))
    return {
        "pressure": pressure,
        "sector": sector or "unknown",
        "indicative_reduction_pct": spec["indicative_reduction_pct"],
        "unit": spec["unit"],
        "note": spec["note"],
        "material_for_sector": material or not sector_key,
        "status": "indicative",
        "as_of": "2026-07",
        "citations": [
            "SBTN methods v1 / v2 beta",
            "SBTi 1.5°C cross-over for climate pressure",
            "GBF Target 15",
        ],
    }


__all__ = ["SBTNStep", "nature_target_ranges", "sbtn_readiness"]
