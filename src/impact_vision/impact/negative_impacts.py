"""Negative impacts scored by severity × likelihood (roadmap v8 W1.6).

ESRS-style impact materiality for the harms a business of this kind can
cause: each sector's potential negative impacts (``data/negative_impacts.yaml``)
get a severity (1–3) and a base likelihood (1–3); a control the company
discloses in its own words lowers the likelihood one step. Materiality =
severity × likelihood (1–9); 6 or more is material.

Material impacts with no disclosed control go into the evidence plan
("show how you manage X"). They never fail a deal on their own: a missing
disclosure is a question to ask, not a finding.
"""
from __future__ import annotations

import re
from functools import lru_cache
from typing import Any

import yaml

from impact_vision.impact._paths import data_path

MATERIAL_AT = 6


@lru_cache(maxsize=1)
def _config() -> dict[str, Any]:
    path = data_path("negative_impacts.yaml")
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _band(score: int) -> str:
    return "high" if score >= MATERIAL_AT else "medium" if score >= 3 else "low"


def assess_negative_impacts(sector: str, text: str) -> dict[str, Any]:
    """Score the sector's potential negative impacts against the company's own text."""
    from impact_vision.tools.impact.common import normalize_sector

    cfg = _config()
    sectors: dict[str, list[dict[str, Any]]] = cfg.get("sectors") or {}
    key = normalize_sector(sector or "")
    items = sectors.get(key) or sectors.get("default") or []
    from impact_vision.impact.negation import asserts_phrase

    sentences = [x.strip(" -•*\t") for x in re.split(r"(?<=[.!?。])\s+|\n+", text or "") if x.strip()]
    rows = []
    for item in items:
        # A control counts only where the company states it has one: "we do not
        # yet have a client protection policy" is the absence of a control.
        controls = []
        quotes = []
        for c in item.get("controls", []):
            hit = next((x for x in sentences if asserts_phrase(c, x)), "")
            if not hit:
                continue
            controls.append(c)
            if hit not in quotes:
                quotes.append(hit if len(hit) <= 160 else hit[:157].rstrip() + "…")
        likelihood = max(1, int(item["likelihood"]) - (1 if controls else 0))
        score = int(item["severity"]) * likelihood
        rows.append({
            "id": item["id"], "impact": item["impact"], "stakeholder": item.get("stakeholder", ""),
            "severity": int(item["severity"]), "likelihood": likelihood, "score": score, "band": _band(score),
            "controlled": bool(controls), "evidence": quotes[:2], "pai": item.get("pai", ""),
            "dnsh": item.get("dnsh", ""),
        })
    rows.sort(key=lambda r: (-r["score"], r["controlled"], r["impact"]))
    unaddressed = [r for r in rows if r["band"] == "high" and not r["controlled"]]
    return {
        "sector": key or "default",
        "items": rows,
        "material_unaddressed": unaddressed,
        "material_count": sum(1 for r in rows if r["band"] == "high"),
        "status": cfg.get("status", ""),
        "source": cfg.get("source", ""),
    }


def plan_items(result: dict[str, Any], limit: int = 2) -> list[dict[str, str]]:
    """Evidence-plan entries for material negative impacts with no disclosed control."""
    return [{"action": f"Show how you manage: {r['impact'].lower()} (affects {r['stakeholder']}).",
             "why": f"Material negative impact (severity {r['severity']} × likelihood {r['likelihood']}) "
                    "with no control described in the documents.", "kind": "negative_control"}
            for r in result.get("material_unaddressed", [])[:limit]]


__all__ = ["MATERIAL_AT", "assess_negative_impacts", "plan_items"]
