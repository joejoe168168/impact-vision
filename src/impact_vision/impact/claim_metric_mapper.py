"""Map quantities in extracted claims to IRIS+ metric IDs (v7 W0.10).

An evidence-rich pitch rarely cites IRIS+ IDs. Without a mapping its numbers
("1.8 GWh of electricity", "replacing ~920 tonnes CO2e") never reach the 5D,
SDG or gap engines, which then score the company as if it had no hard data.

Rules live in ``data/claim_metric_map.yaml``. Matching is conservative: a
quantity is mapped only when its unit fits and exactly one rule matches the
clause around it (falling back to the whole sentence).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache

import yaml

from impact_vision.impact._paths import data_path
from impact_vision.impact.extractors.regex_extractor import _FORWARD_RE, _NUMBER_UNIT

# Clause boundaries inside a sentence (the decimal point in "1.8" is not one).
_CLAUSE_SPLIT = re.compile(
    r"[,;:()—–\n]|\s-\s|(?<!\d)\.(?!\d)|\b(?:and|while|but|whereas)\b",
    re.IGNORECASE,
)
# The extractor's unit regex stops at "tonnes"; look ahead for "CO2e".
_CO2_SUFFIX = re.compile(r"\s*(?:of\s+)?(?:co2e?|co₂e?)", re.IGNORECASE)


@dataclass(frozen=True)
class MetricMapping:
    metric_id: str
    value: float
    unit: str
    display: str  # human-readable value stored in reported_metrics
    source_text: str
    derived: bool = False


@lru_cache(maxsize=1)
def _rules() -> dict:
    path = data_path("claim_metric_map.yaml")
    if not path.is_file():
        return {"rules": [], "derived": []}
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {"rules": [], "derived": []}


def _norm_unit(unit: str, following: str) -> str:
    u = re.sub(r"\s+", "", unit.lower())
    if u in {"tonnes", "tonne", "tons", "ton"} and _CO2_SUFFIX.match(following):
        return "tco2e"
    return u


def _has(text: str, term: str) -> bool:
    return re.search(r"\b" + re.escape(term.lower()), text) is not None


def _rule_matches(rule: dict, unit: str, context: str, sentence: str = "") -> bool:
    """``all_of`` / ``none_of`` are tested on *context*. ``none_in_sentence`` is
    tested on the whole sentence: clause splitting at "and" would otherwise hide
    "scope 1 and 2" from the Scope 1 rule."""
    if unit not in {u.lower() for u in rule.get("units", [])}:
        return False
    if not all(any(_has(context, t) for t in group) for group in rule.get("all_of", [])):
        return False
    if any(_has(context, t) for t in rule.get("none_of", []) or []):
        return False
    return not any(_has(f"{context} {sentence}", t) for t in rule.get("none_in_sentence", []) or [])


def _clause(sentence: str, start: int, end: int) -> str:
    left = 0
    for m in _CLAUSE_SPLIT.finditer(sentence, 0, start):
        left = m.end()
    m = _CLAUSE_SPLIT.search(sentence, end)
    right = m.start() if m else len(sentence)
    return sentence[left:right]


def _format(value: float, unit: str) -> str:
    text = f"{value:,.3f}".rstrip("0").rstrip(".")
    return f"{text} {unit}".strip()


def map_claim_metrics(sentence: str, *, forward_looking: bool = False) -> list[MetricMapping]:
    """Return IRIS+ mappings for the quantities in *sentence*.

    Forward-looking sentences (targets, commitments) are never mapped: a
    target is not a reported value.
    """
    if not sentence or forward_looking or _FORWARD_RE.search(sentence):
        return []
    cfg = _rules()
    lowered = sentence.lower()
    found: dict[str, MetricMapping] = {}

    matches = list(_NUMBER_UNIT.finditer(sentence))
    unit_counts: dict[str, int] = {}
    for m in matches:
        u = _norm_unit(m.group("unit"), sentence[m.end():])
        unit_counts[u] = unit_counts.get(u, 0) + 1

    for m in matches:
        try:
            raw_value = float(m.group("value").replace(",", ""))
        except ValueError:
            continue
        unit = _norm_unit(m.group("unit"), sentence[m.end():])
        # The unit is part of the evidence ("tCO2e" says CO2 even when the
        # sentence doesn't), so it's always in the context.
        contexts = [f"{_clause(lowered, m.start(), m.end())} {unit}"]
        # Whole-sentence context only when this is the sentence's sole quantity
        # in this unit — otherwise "emitted X and avoided Y" would blur.
        if unit_counts.get(unit, 0) == 1:
            contexts.append(f"{lowered} {unit}")
        for context in contexts:
            hits = [r for r in cfg.get("rules", []) if _rule_matches(r, unit, context, lowered)]
            if len(hits) > 1:  # a strictly more specific rule wins a tie
                top = max(int(r.get("priority", 0)) for r in hits)
                best = [r for r in hits if int(r.get("priority", 0)) == top]
                hits = best if len(best) == 1 else hits
            if len(hits) == 1:
                rule = hits[0]
                scale = float((rule.get("scale") or {}).get(unit, 1))
                canonical = rule.get("canonical_unit") or ""  # counts are unitless
                value = raw_value * scale
                found.setdefault(
                    rule["metric_id"],
                    MetricMapping(
                        metric_id=rule["metric_id"],
                        value=value,
                        unit=canonical,
                        display=_format(value, canonical),
                        source_text=sentence,
                    ),
                )
                break
            if len(hits) > 1:
                break  # ambiguous: don't guess

    for rule in cfg.get("derived", []) or []:
        base = found.get(rule.get("from_metric", ""))
        if base is None or rule["metric_id"] in found:
            continue
        share = re.search(rule["share_pattern"], sentence, re.IGNORECASE)
        if not share:
            continue
        pct = float(share.group(1))
        value = round(base.value * pct / 100)
        found[rule["metric_id"]] = MetricMapping(
            metric_id=rule["metric_id"],
            value=value,
            unit="",
            display=f"{value:,.0f} (derived: {pct:g}% of {base.value:,.0f})",
            source_text=sentence,
            derived=True,
        )
    return list(found.values())


__all__ = ["MetricMapping", "map_claim_metrics"]
