"""Do the documents give two different figures for the same thing?

When a deck states "42,000 households" on one page and "24,000 households" on
another, the first value used to win and the second vanished. A reviewer
looks for exactly this, so :func:`find_conflicts` keeps every reported value
per IRIS+ metric and reports the ones that disagree.

Two figures are a conflict when they map to the same metric, differ by more
than the tolerance in ``methodology/v2.yaml`` (``consistency``), and are not
explained by time: when the two sentences name different years, or only one
names a year ("24,000 in 2023" against "42,000 households"), the difference
reads as growth, not a contradiction. Targets and derived values are never
compared.
"""
from __future__ import annotations

import re
from functools import lru_cache
from typing import Any, Iterable

_YEAR = re.compile(r"\b(?:19|20)\d{2}\b")


def _claim(claim: Any) -> tuple[str, str, int | None]:
    get = claim.get if isinstance(claim, dict) else lambda k, d=None: getattr(claim, k, d)
    return str(get("text", "") or ""), str(get("category", "") or ""), get("source_page")


def find_conflicts(claims: Iterable[Any]) -> list[dict[str, Any]]:
    """Metrics the documents report with materially different values."""
    from impact_vision.impact.claim_metric_mapper import map_claim_metrics
    from impact_vision.impact.expected_impact import params

    cfg = params().get("consistency") or {}
    tolerance = float(cfg.get("tolerance", 0.10))
    seen: dict[str, list[dict[str, Any]]] = {}
    for claim in claims:
        text, category, page = _claim(claim)
        if not text or category in {"commitment", "intent"}:
            continue
        for mapping in map_claim_metrics(text):
            if mapping.derived:
                continue
            rows = seen.setdefault(mapping.metric_id, [])
            if all(r["sentence"] != text.strip(" -•*\t") for r in rows):
                rows.append({"value": float(mapping.value), "display": mapping.display,
                             "sentence": text.strip(" -•*\t"),
                             "page": page, "years": set(_YEAR.findall(text))})

    conflicts = []
    for metric_id, rows in seen.items():
        if len(rows) < 2:
            continue
        low, high = min(rows, key=lambda r: r["value"]), max(rows, key=lambda r: r["value"])
        if high["value"] <= 0 or (high["value"] - low["value"]) / high["value"] <= tolerance:
            continue
        if low["years"] != high["years"]:
            continue  # a dated figure against another period (or an undated one): growth, not a contradiction
        conflicts.append({
            "metric_id": metric_id,
            "values": [low["display"], high["display"]],
            "difference_pct": round(100 * (high["value"] - low["value"]) / high["value"]),
            "sources": [{"value": r["display"], "sentence": r["sentence"], "page": r["page"]} for r in (low, high)],
        })
    conflicts.sort(key=lambda c: -c["difference_pct"])
    return conflicts[: int(cfg.get("max_items", 5))]


def plan_items(conflicts: list[dict[str, Any]], names: dict[str, str] | None = None) -> list[dict[str, str]]:
    """Evidence-plan entry for the largest conflict: settle it before anything else."""
    names = names or {}
    out = []
    for c in conflicts[:1]:
        label = names.get(c["metric_id"]) or c["metric_id"]
        out.append({
            "action": f"Reconcile the two figures given for {label}: {c['values'][0]} and {c['values'][1]}.",
            "why": f"The documents disagree by {c['difference_pct']}%, so every number built on this one is in doubt.",
            "kind": "reconcile",
        })
    return out


# --------------------------------------------------------------------------- plausibility

@lru_cache(maxsize=1)
def _populations() -> dict[str, tuple[str, int, int]]:
    """Lower-cased name or alias → (display name, population, year)."""
    import yaml

    from impact_vision.impact._paths import data_path

    path = data_path("population.yaml")
    if not path.exists():
        return {}
    doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    out: dict[str, tuple[str, int, int]] = {}
    for row in [*(doc.get("regions") or []), *(doc.get("countries") or [])]:  # a country wins over a region
        entry = (str(row["name"]), int(row["population"]), int(row["year"]))
        for name in (row["name"], row.get("iso3", ""), *(row.get("aliases") or [])):
            text = str(name)
            # Short lower-case Latin strings ("Chad" is fine, "Fiji" is fine, "us" is not) would match by accident.
            if text and (len(text) > 3 or text.isupper() or not text.isascii()):
                out[text.lower()] = entry
    return out


def population_of(geography: str) -> tuple[str, int, int] | None:
    """Population of the place a company names, or None when it is not one known country or region."""
    geo = (geography or "").strip().lower()
    if not geo:
        return None
    table = _populations()
    if geo in table:
        return table[geo]
    # "Rural Kenya", "Kenya (14 counties)": one known place named inside the text.
    hits = {entry for name, entry in table.items() if len(name) > 3 and re.search(rf"\b{re.escape(name)}\b", geo)}
    return next(iter(hits)) if len(hits) == 1 else None


def plausibility_flags(inputs: Any, geography: str = "") -> list[dict[str, Any]]:
    """Figures that cannot be right, or that the calculation had to cap.

    *inputs* is ``expected_impact.OutcomeInputs``. Each flag names the figure,
    the limit it breaks and the sentence it came from. ``doubt`` flags widen
    the range of the figure they concern; ``note`` flags only inform.
    """
    from impact_vision.impact.expected_impact import params

    cfg = params().get("plausibility") or {}
    flags: list[dict[str, Any]] = []
    reach, depth, tonnes = inputs.reach, inputs.depth, inputs.tco2e_per_year
    place = population_of(geography)
    if reach is not None and place is not None:
        name, people, year = place
        if reach.value > people * float(cfg.get("max_reach_share_of_population", 1.0)):
            flags.append({
                "kind": "reach_exceeds_population", "severity": "doubt", "figure": "reach",
                "value": reach.value, "limit": people, "place": name, "year": year, "sentence": reach.text,
                "action": f"Check the reach figure: {reach.value:,.0f} {reach.noun} is more than the population of "
                          f"{name} ({people:,.0f}).",
            })
    if depth is not None and (depth.raw_value or 0) > 1.0:
        flags.append({
            "kind": "depth_capped", "severity": "note", "figure": "depth", "value": depth.raw_value, "limit": 1.0,
            "sentence": depth.text,
            "action": f"Say what the {depth.raw_value:.0%} change is a percentage of; the calculation counts it as 100%.",
        })
    cap = cfg.get("max_tco2e_per_usd_1m")
    if tonnes is not None and inputs.ask_usd and cap:
        per_million = tonnes.value / (inputs.ask_usd / 1_000_000)
        if per_million > float(cap):
            flags.append({
                "kind": "tonnes_per_usd", "severity": "doubt", "figure": "tonnes", "value": per_million,
                "limit": float(cap), "sentence": tonnes.text,
                "action": f"Check the emissions figure: {tonnes.value:,.0f} tCO2e against a US${inputs.ask_usd:,.0f} "
                          f"raise is {per_million:,.0f} tonnes per US$1m.",
            })
    return flags


def plausibility_plan_items(flags: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Evidence-plan entry for the first figure in doubt."""
    return [{"action": f["action"],
             "why": "A figure that cannot be right makes every number built on it unreliable.",
             "kind": "plausibility"} for f in flags if f["severity"] == "doubt"][:1]


__all__ = ["find_conflicts", "plan_items", "plausibility_flags", "plausibility_plan_items", "population_of"]
