"""Data-driven four-pillar disclosure checklist engine."""

from __future__ import annotations
import re
from pathlib import Path
from typing import Literal
import yaml
from pydantic import BaseModel, Field


class DisclosureItem(BaseModel):
    id: str
    requirement: str
    bullets: list[str] = Field(default_factory=list)
    modality: Literal["shall", "encouraged"]
    legal_basis: list[str] = Field(default_factory=list)


class DisclosurePillar(BaseModel):
    pillar: Literal["governance", "strategy", "iro_management", "metrics_targets"]
    items: list[DisclosureItem]


class DisclosureChecklist(BaseModel):
    topic_id: str
    frameworks: dict[str, str]
    pillars: list[DisclosurePillar]


def load_checklist(topic_id: str) -> DisclosureChecklist:
    path = (
        Path(__file__).resolve().parents[3] / "data" / "disclosure_checklists" / f"{topic_id}.yaml"
    )
    if not path.exists():
        raise KeyError(f"Unknown disclosure checklist topic: {topic_id}")
    return DisclosureChecklist.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


def _matches(item: DisclosureItem, text: str) -> bool:
    tokens = [
        token for token in re.findall(r"[a-z0-9]+", item.requirement.lower()) if len(token) > 4
    ]
    return sum(token in text for token in tokens) >= max(1, min(2, len(tokens)))


def analyze_disclosure(topic_id: str, report_text: str) -> dict:
    checklist = load_checklist(topic_id)
    text = report_text.lower()
    covered = []
    gaps = []
    per_pillar = {}
    for pillar in checklist.pillars:
        matches = [item for item in pillar.items if _matches(item, text)]
        covered.extend(item.id for item in matches)
        gaps.extend(
            {
                "id": item.id,
                "requirement": item.requirement,
                "modality": item.modality,
                "legal_basis": item.legal_basis,
            }
            for item in pillar.items
            if item not in matches
        )
        per_pillar[pillar.pillar] = round(100 * len(matches) / len(pillar.items), 1)
    gaps.sort(key=lambda row: row["modality"] != "shall")
    total = sum(len(p.items) for p in checklist.pillars)
    return {
        "topic_id": topic_id,
        "coverage_pct": round(100 * len(covered) / total, 1),
        "per_pillar": per_pillar,
        "covered_ids": covered,
        "gaps": gaps,
    }


def checklist_gap_report(topic_id: str, covered_ids: list[str]) -> dict:
    checklist = load_checklist(topic_id)
    covered = set(covered_ids)
    gaps = [
        {
            "id": item.id,
            "requirement": item.requirement,
            "modality": item.modality,
            "legal_basis": item.legal_basis,
        }
        for pillar in checklist.pillars
        for item in pillar.items
        if item.id not in covered
    ]
    gaps.sort(key=lambda row: row["modality"] != "shall")
    return {
        "topic_id": topic_id,
        "mandatory_gaps": [g for g in gaps if g["modality"] == "shall"],
        "encouraged_gaps": [g for g in gaps if g["modality"] == "encouraged"],
        "gaps": gaps,
    }


__all__ = [
    "DisclosureChecklist",
    "DisclosureItem",
    "DisclosurePillar",
    "analyze_disclosure",
    "checklist_gap_report",
    "load_checklist",
]
