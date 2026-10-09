"""Enterprise vs investor contribution, scored on evidence (roadmap v8 W1.4).

*Enterprise contribution* asks how much of the outcome would not have happened
anyway. It reads the evidence design: a comparison or control group, a
baseline, and the NESTA level that Methodology 2.0 already assigns.

*Investor contribution* asks what the fund adds. It uses the four Impact
Frontiers strategies (signal that impact matters, engage actively, grow new
or undersupplied capital markets, provide flexible capital). Each channel is
levelled 0–3 by ``data/methodology/contribution_rubric.yaml``: text can show a
specific action (1) or a documented commitment (2); delivery (3) needs
evidence logged through the contribution tool.

Adjectives ("catalytic", "transformative", "unique") are listed and ignored.
"""
from __future__ import annotations

import re
from functools import lru_cache
from typing import Any

import yaml

from impact_vision.impact._paths import data_path


@lru_cache(maxsize=1)
def rubric() -> dict[str, Any]:
    path = data_path("methodology/contribution_rubric.yaml")
    doc: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else {}
    for channel in doc.get("investor") or []:
        channel["_l1"] = [re.compile(p, re.IGNORECASE) for p in channel.get("level1") or []]
        channel["_l2"] = [re.compile(p, re.IGNORECASE) for p in channel.get("level2") or []]
    return doc


def _sentences(text: str) -> list[str]:
    return [s.strip(" -•*\t") for s in re.split(r"(?<=[.!?。])\s+|\n+", text or "") if s.strip()]


def _quote(sentence: str) -> str:
    return sentence if len(sentence) <= 160 else sentence[:157].rstrip() + "…"


def enterprise_signals(text: str) -> list[dict[str, str]]:
    """Evidence-design signals in the text, one quote each."""
    from impact_vision.impact.extractors.regex_extractor import evidence_signals

    wanted = (rubric().get("enterprise") or {}).get("signals") or {}
    found: dict[str, dict[str, str]] = {}
    for sentence in _sentences(text):
        for sig in evidence_signals(sentence):
            if sig in wanted and sig not in found:
                found[sig] = {"signal": sig, "label": wanted[sig]["label"], "quote": _quote(sentence)}
    return list(found.values())


def enterprise_boost(text: str) -> float:
    """Points added to the 5D contribution baseline under Methodology 2.0."""
    wanted = (rubric().get("enterprise") or {}).get("signals") or {}
    return float(sum(wanted[s["signal"]]["points"] for s in enterprise_signals(text)))


def adjectives_in(text: str) -> list[str]:
    lowered = (text or "").lower()
    return [a for a in rubric().get("adjectives") or []
            if re.search(r"(?<![\w-])" + re.escape(a) + r"(?![\w-])", lowered)]


def investor_contribution(text: str, *, delivered: dict[str, list[str]] | None = None) -> dict[str, Any]:
    """Level each investor-contribution channel from the text (and logged delivery)."""
    sentences = _sentences(text)
    channels = []
    for ch in rubric().get("investor") or []:
        level, quote = 0, ""
        for lvl, patterns in ((2, ch["_l2"]), (1, ch["_l1"])):
            hit = next((s for s in sentences for p in patterns if p.search(s)), "")
            if hit:
                level, quote = lvl, _quote(hit)
                break
        evidence = (delivered or {}).get(ch["id"]) or []
        if evidence:
            level = 3
        channels.append({"id": ch["id"], "label": ch["label"], "level": level, "quote": quote,
                         "delivered": evidence[:3]})
    total = sum(c["level"] for c in channels)
    return {"channels": channels, "score": round(100 * total / (3 * max(1, len(channels)))),
            "adjectives_ignored": adjectives_in(text)}


def contribution_split(text: str, expected_impact: dict[str, Any] | None = None, *,
                       investor_text: str | None = None,
                       delivered: dict[str, list[str]] | None = None) -> dict[str, Any]:
    """Both halves of contribution for the report (``report_data['contribution_split']``)."""
    ent = rubric().get("enterprise") or {}
    signals = enterprise_signals(text)
    people = next((o for o in (expected_impact or {}).get("outcomes") or []), None)
    level = int(people.get("evidence_level") or 1) if people else 1
    level_score = (ent.get("evidence_level_score") or {}).get(level, 10)
    netted = bool(people) and any(f.get("name") == "Without deadweight" and float(f.get("median", 0)) >= 0.999
                                  for f in people.get("factors", []))
    bonus = 15 if any(s["signal"] == "controlled_evaluation" for s in signals) else (
        5 if any(s["signal"] == "baseline_comparison" for s in signals) else 0)
    return {
        "enterprise": {"score": min(100, level_score + bonus), "evidence_level": level, "signals": signals,
                       "deadweight_netted": netted},
        "investor": investor_contribution(investor_text if investor_text is not None else text,
                                          delivered=delivered),
        "rubric": {"source": rubric().get("source", ""), "status": rubric().get("status", "")},
    }


def delivered_from_claims(claims: list[dict[str, Any]], evidence: list[dict[str, Any]]) -> dict[str, list[str]]:
    """Map logged contribution activities (contribution.py) to rubric channels."""
    by_channel = {"market_signal": "signal", "non_financial_support": "engage", "new_market_catalysed": "grow",
                  "capital_additionality": "grow", "flexible_terms": "flexible"}
    out: dict[str, list[str]] = {}
    for claim in claims:
        channel = by_channel.get(str(claim.get("channel", "")))
        ids = {a.get("activity_id") for a in claim.get("planned_activities") or []}
        done = [e["description"] for e in evidence if e.get("activity_id") in ids and e.get("artifact_refs")]
        if channel and done:
            out.setdefault(channel, []).extend(done)
    return out


__all__ = ["adjectives_in", "contribution_split", "delivered_from_claims", "enterprise_boost",
           "enterprise_signals", "investor_contribution", "rubric"]
