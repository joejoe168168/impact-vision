"""Held-out evaluation of extraction and verdicts (roadmap v8 W2.4).

Complements ``extraction_eval`` (sentence-level claims on a gold JSONL used
while developing the extractor): this one runs the full no-LLM pipeline on every deck in a labelled folder
(``tests/golden/heldout/``) and compares what it found with what a careful
analyst wrote down beforehand:

* **facts:** precision / recall / F1 of the company's quantified statements.
  A labelled number is found when any extracted claim states it; a claim's
  number counts against precision when it isn't a labelled fact. Years are
  ignored.
* **sector**, **geography**, **SDG** (a labelled goal in the top three
  material goals), **greenwashing** (finding or not) and **verdict**
  (Gate 2.0 state): agreement rates.

The set is never used for tuning. When it shows a miss, the miss is reported,
and the fix is tested on other documents.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

_NUM = re.compile(r"(?<![\w.])(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)(?![\w])")


def _numbers(text: str) -> set[float]:
    out = set()
    for raw in _NUM.findall(text or ""):
        value = float(raw.replace(",", ""))
        if "," not in raw and "." not in raw and 1900 <= value <= 2100:
            continue  # a year
        out.add(value)
    return out


def _f1(p: float, r: float) -> float:
    return round(2 * p * r / (p + r), 3) if p + r else 0.0


def evaluate_deck(path: Path, label: dict[str, Any]) -> dict[str, Any]:
    from impact_vision.impact.pipeline import assess_file
    from impact_vision.tools.impact.common import normalize_sector

    bundle = assess_file(path)
    data = bundle.report_data
    found: set[float] = set()
    for claim in data.get("impact_claims") or []:
        found |= _numbers(str(claim.get("text", "")))
    facts = {float(f) for f in label.get("facts") or []}
    hits = facts & found
    top3 = [a.goal for a in bundle.assessment.sdg_alignments if a.material][:3]
    gate = ((data.get("expected_impact") or {}).get("gate") or {}).get("state", "")
    return {
        "deck": path.name, "lang": label.get("lang", "en"),
        "facts": len(facts), "facts_found": len(hits), "numbers_extracted": len(found),
        "numbers_correct": len(found & facts), "missed": sorted(facts - found),
        "sector": normalize_sector(bundle.company.sector) == normalize_sector(label["sector"]),
        "sector_got": bundle.company.sector,
        "geography": bundle.company.geography == label["geography"], "geography_got": bundle.company.geography,
        "sdg": bool(set(label.get("sdg") or []) & set(top3)), "sdg_top3": top3,
        "greenwash": bool(bundle.greenwashing.is_finding) == bool(label["greenwash"]),
        "verdict": gate == label["gate"], "verdict_got": gate, "verdict_expected": label["gate"],
    }


def evaluate(folder: str | Path) -> dict[str, Any]:
    folder = Path(folder)
    labels = yaml.safe_load((folder / "labels.yaml").read_text(encoding="utf-8"))["decks"]
    rows = [evaluate_deck(folder / name, label) for name, label in sorted(labels.items())]
    n = len(rows)
    extracted = sum(r["numbers_extracted"] for r in rows)
    precision = sum(r["numbers_correct"] for r in rows) / extracted if extracted else 0.0
    total_facts = sum(r["facts"] for r in rows)
    recall = sum(r["facts_found"] for r in rows) / total_facts if total_facts else 0.0

    def rate(key: str, subset: list[dict[str, Any]] | None = None) -> float:
        group = subset if subset is not None else rows
        return round(sum(1 for r in group if r[key]) / len(group), 3) if group else 0.0

    by_lang = {}
    for lang in sorted({r["lang"] for r in rows}):
        group = [r for r in rows if r["lang"] == lang]
        by_lang[lang] = {"decks": len(group), "sector": rate("sector", group), "geography": rate("geography", group),
                         "sdg": rate("sdg", group), "verdict": rate("verdict", group)}
    return {
        "decks": n,
        "summary": {"fact_precision": round(precision, 3), "fact_recall": round(recall, 3),
                    "fact_f1": _f1(precision, recall), "sector": rate("sector"), "geography": rate("geography"),
                    "sdg": rate("sdg"), "greenwash": rate("greenwash"), "verdict": rate("verdict")},
        "by_lang": by_lang,
        "rows": rows,
    }


def to_markdown(result: dict[str, Any]) -> str:
    s = result["summary"]
    lines = [f"### Held-out evaluation ({result['decks']} decks)", "",
             "| Fact P | Fact R | Fact F1 | Sector | Geography | SDG | Greenwashing | Verdict |",
             "|---|---|---|---|---|---|---|---|",
             f"| {s['fact_precision']:.0%} | {s['fact_recall']:.0%} | {s['fact_f1']:.2f} | {s['sector']:.0%} | "
             f"{s['geography']:.0%} | {s['sdg']:.0%} | {s['greenwash']:.0%} | {s['verdict']:.0%} |", "",
             "| Deck | Facts | Sector | Geography | SDG top 3 | Greenwashing | Verdict |",
             "|---|---|---|---|---|---|---|"]
    for r in result["rows"]:
        lines.append(f"| {r['deck']} | {r['facts_found']}/{r['facts']} | {'✓' if r['sector'] else '✗ ' + r['sector_got']} | "
                     f"{'✓' if r['geography'] else '✗ ' + (r['geography_got'] or '—')} | "
                     f"{'✓' if r['sdg'] else '✗ '}{r['sdg_top3']} | {'✓' if r['greenwash'] else '✗'} | "
                     f"{'✓' if r['verdict'] else '✗ ' + r['verdict_got'] + ' (want ' + r['verdict_expected'] + ')'} |")
    return "\n".join(lines) + "\n"


__all__ = ["evaluate", "evaluate_deck", "to_markdown"]
