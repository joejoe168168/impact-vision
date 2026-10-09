"""HKFRS S1 gap tool (roadmap v8 Wave 4).

Reads a sustainability or annual report (English or Traditional Chinese) and
checks it against the HKFRS S1 requirements in ``data/regulatory/hkfrs_s1.yaml``:
for each requirement it reports *addressed* (two or more cues, quoted),
*partly* (one cue) or *gap*. It points the reader to where to look; it is not
a compliance opinion, and it never treats a compliance statement as evidence
that the requirements behind it are met.
"""
from __future__ import annotations

import re
from functools import lru_cache
from typing import Any

import yaml

from impact_vision.impact._paths import data_path

PILLARS = ("governance", "strategy", "risk_management", "metrics_targets", "general")
PILLAR_ZH = {"governance": "管治", "strategy": "策略", "risk_management": "風險管理",
             "metrics_targets": "指標及目標", "general": "一般規定"}


@lru_cache(maxsize=1)
def _config() -> dict[str, Any]:
    doc: dict[str, Any] = yaml.safe_load(data_path("regulatory/hkfrs_s1.yaml").read_text(encoding="utf-8"))
    for req in doc["requirements"]:
        req["_cues"] = [re.compile(c, re.IGNORECASE) for c in req["cues"]]
    return doc


def _sentences(text: str) -> list[str]:
    return [s.strip(" -•*\t") for s in re.split(r"(?<=[.!?;])\s+|(?<=[。；！？])|\n+", text or "") if len(s.strip()) > 3]


def hkfrs_s1_gap(text: str, *, lang: str = "en") -> dict[str, Any]:
    """Requirement-by-requirement gap list for one report."""
    cfg = _config()
    sentences = _sentences(text)
    rows = []
    for req in cfg["requirements"]:
        hits: list[str] = []
        matched = 0
        for cue in req["_cues"]:
            found = next((s for s in sentences if cue.search(s)), "")
            if found:
                matched += 1
                if found not in hits:
                    hits.append(found if len(found) <= 200 else found[:197] + "…")
        status = "addressed" if matched >= 2 else "partly" if matched == 1 else "gap"
        if req["id"] == "compliance_statement":
            status = "stated" if matched else "not stated"
        rows.append({"id": req["id"], "pillar": req["pillar"], "ref": req["ref"],
                     "title": req["zh"] if lang.startswith("zh") else req["title"], "status": status,
                     "evidence": hits[:2]})
    scored = [r for r in rows if r["id"] != "compliance_statement"]
    by_pillar = {}
    for pillar in PILLARS:
        group = [r for r in scored if r["pillar"] == pillar]
        if group:
            pts = sum(1.0 if r["status"] == "addressed" else 0.5 if r["status"] == "partly" else 0.0 for r in group)
            by_pillar[pillar] = {"label": PILLAR_ZH[pillar] if lang.startswith("zh") else pillar.replace("_", " "),
                                 "coverage_pct": round(100 * pts / len(group)), "requirements": len(group)}
    gaps = [r for r in scored if r["status"] == "gap"]
    stated = next(r for r in rows if r["id"] == "compliance_statement")["status"] == "stated"
    warnings = []
    if stated and gaps:
        warnings.append("The report states compliance with HKFRS S1 while some requirements look unaddressed; "
                        "¶72 allows the statement only when every requirement is met.")
    return {"standard": "HKFRS S1 (= IFRS S1, effective 2025-08-01)", "requirements": rows, "pillars": by_pillar,
            "coverage_pct": round(100 * sum(1.0 if r["status"] == "addressed" else 0.5 if r["status"] == "partly"
                                            else 0.0 for r in scored) / len(scored)),
            "gaps": [r["title"] for r in gaps], "warnings": warnings, "hkex_note": cfg.get("hkex_note", ""),
            "status": cfg.get("status", ""), "source_url": cfg.get("source_url", "")}


def to_text(result: dict[str, Any]) -> str:
    mark = {"addressed": "✓", "partly": "~", "gap": "✗", "stated": "✓", "not stated": "–"}
    lines = [f"{result['standard']} · coverage {result['coverage_pct']}%", ""]
    for r in result["requirements"]:
        lines.append(f"{mark[r['status']]} {r['ref']:<12} {r['title']}")
        for q in r["evidence"][:1]:
            lines.append(f"      “{q}”")
    lines += ["", *[f"! {w}" for w in result["warnings"]], result["hkex_note"]]
    return "\n".join(lines).rstrip() + "\n"


__all__ = ["hkfrs_s1_gap", "to_text"]
