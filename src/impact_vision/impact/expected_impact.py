"""Methodology 2.0 — expected impact with ranges (roadmap v8 Wave 1).

v1 scores describe disclosure. This module answers the IC questions:

* **How much change?**  ``reach × depth × duration × (1 − deadweight) ×
  attribution × probability of success`` (Impact Multiple of Money
  structure), in natural units: depth-weighted person-years for people,
  tCO2e for climate.
* **How sure are we?**  Every factor is a lognormal whose spread follows the
  NESTA evidence level of the claim it came from; a seeded Monte Carlo gives
  P10 / P50 / P90. Evidence quality (0–100) is reported beside impact and
  never multiplied into it.
* **What would change our mind?**  The factors that carry most of the
  uncertainty, each with the action that narrows it and by how much.
* **Gate 2.0.**  Ready / Evidence plan required / Fails thesis — failing only
  on something *found* (greenwashing finding, exclusion), never on something
  missing.

All parameters live in ``data/methodology/v2.yaml``.
"""
from __future__ import annotations

import hashlib
import math
import re
from dataclasses import asdict, dataclass, field
from functools import lru_cache
from typing import Any, Iterable

import yaml

from impact_vision.impact._paths import data_path

V2_FILE = ("methodology", "v2.yaml")


@lru_cache(maxsize=2)
def _load(path: str) -> tuple[dict[str, Any], str]:
    raw = open(path, "rb").read()  # noqa: SIM115 - tiny file
    return yaml.safe_load(raw.decode("utf-8")) or {}, hashlib.sha256(raw).hexdigest()[:12]


def methodology_mode() -> str:
    """"2" (expected impact drives the verdict) unless IMPACT_VISION_METHODOLOGY_VERSION=1."""
    import os

    return "1" if os.environ.get("IMPACT_VISION_METHODOLOGY_VERSION", "").strip().startswith("1") else "2"


def headline(block: dict[str, Any] | None) -> dict[str, Any] | None:
    """The one number for tiles and summaries: people impact first, else climate."""
    outcomes = (block or {}).get("outcomes") or []
    if not outcomes:
        return None
    o = outcomes[0]
    return {k: o[k] for k in ("kind", "unit", "stakeholder", "p10", "p50", "p90", "uncertainty")}


def params() -> dict[str, Any]:
    return _load(str(data_path(*V2_FILE)))[0]


def stamp() -> dict[str, str]:
    cfg, digest = _load(str(data_path(*V2_FILE)))
    return {"methodology_version": str(cfg.get("version", "2")), "config_hash": digest,
            "status": str(cfg.get("status", ""))}


# --------------------------------------------------------------------------- parsing

# Left boundary so a year or a decimal does not bleed in ("2023 120 students" is 120, not 2,023,120);
# a regular, non-breaking or thin space separates thousands only in the "d ddd" shape.
_SP = "[ \u00a0\u2009\u202f]"
_NUM = (r"(?<![\d.,])(\d{1,3}(?:,\d{3})+|\d{1,3}(?:" + _SP + r"\d{3})+(?!\d)"
        r"|\d+(?:\.\d+)?)\s*(k|thousand|million|mn|m)?")
_PEOPLE = (
    "households", "household", "people", "persons", "individuals", "patients", "students", "learners",
    "pupils", "children", "farmers", "smallholders", "customers", "clients", "borrowers", "homes",
    "tenants", "residents", "beneficiaries", "women", "girls", "members", "users", "families",
    "businesses", "smes", "entrepreneurs", "elderly", "older people", "seniors", "villagers",
)
_PEOPLE_RE = re.compile(
    _NUM + r"\s+(?:[a-z][\w-]*\s+){0,3}?(" + "|".join(re.escape(p) for p in _PEOPLE) + r")\b", re.I)
# Chinese: "3,200 名長者" / "3200名长者"
_ZH_DIGITS = "〇零一二兩两三四五六七八九十百千"
_PEOPLE_ZH = re.compile(r"(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?|[" + _ZH_DIGITS + r"]+)\s*(萬|万|億|亿)?\s*(?:多|余|餘)?\s*[名位個个戶户]\s*(長者|长者|學生|学生|病人|農民|农民|居民|用戶|用户|婦女|妇女|兒童|儿童)")
_CHANGE_WORDS = (r"higher|lower|more|less|fewer|increase[sd]?|reduction|reduced|decrease[sd]?|cut|"
                 r"improve(?:d|ment)?|gain(?:ed)?|uplift|ris(?:e|en)|rose|grew|growth|drop(?:ped)?|fell|"
                 r"fall(?:en)?|declin(?:e|ed)|lowered|sav(?:ed|ings)|down|up|better|faster")
_DEPTH_RE = [
    re.compile(r"(\d+(?:\.\d+)?)\s*%\s*(?:" + _CHANGE_WORDS + r")\b", re.I),
    re.compile(r"\b(?:" + _CHANGE_WORDS + r")\b[^.%]{0,60}?\bby\s+(\d+(?:\.\d+)?)\s*%", re.I),
    re.compile(r"\b(?:" + _CHANGE_WORDS + r")\s+(?:about\s+|around\s+|nearly\s+)?(\d+(?:\.\d+)?)\s*%", re.I),
    re.compile(r"(\d+(?:\.\d+)?)\s*%\s*(?:比|較|较)?[^。]{0,12}(?:低|高|減少|减少|下降|提升|改善)"),
    re.compile(r"(?:低|高|減少|减少|下降|提升|改善)\s*(\d+(?:\.\d+)?)\s*%"),
]
_EFFECT_SIZE_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:standard deviations?|sd)\b", re.I)
_CO2_RE = re.compile(_NUM + r"\s*(?:t|tonnes|tons|metric tons)\b\s*(?:of\s+)?(?:co2e?|co₂e?|carbon)", re.I)
_CO2_UNIT_RE = re.compile(_NUM + r"\s*(?:tco2e?|tco₂e?)\b", re.I)
_AVOID_WORDS = re.compile(r"avoid|reduc|sav|cut|replac|displac|abat|lower|offset|减排|減排", re.I)
_TARGET_WORDS = re.compile(
    r"\b(target|aim|plan|goal|will|by 20\d\d|next (?:three|two|five|\d+) years|over the next)\b|目標|目标|未來|未来",
    re.I)
# A purpose clause is a goal, not a result: "USD 10m to reach 1 million students".
_GOAL_BEFORE = re.compile(
    r"\b(?:to|will|would|could|can|aims?\s+to|plans?\s+to|in\s+order\s+to)\s+"
    r"(?:reach|serve|connect|enrol+|train|cover|support|benefit|onboard|help|impact|scale\s+to|grow\s+to|"
    r"expand\s+to)\s+(?:(?:up\s+to|over|more\s+than|another|an\s+additional|at\s+least|a\s+further)\s+)?$",
    re.I)
# A running total is not an annual rate: "avoided 20,000 tCO2e since launch".
_CUMULATIVE = re.compile(
    r"\b(?:since\s+(?:launch|inception|20\d\d|we\s+started|founding)|cumulative(?:ly)?|to[\s-]date|so\s+far|"
    r"lifetime|in\s+total\s+since|over\s+(?:the\s+)?(?:past|last)\s+(?:\d+|two|three|four|five|six|ten)\s+years)\b"
    r"|累計|累计|至今|自成立以來|自成立以来", re.I)
# Prefixed dollar signs first (R$, S$, A$ are not US dollars); a bare "$" must not follow a letter.
_ASK_RE = re.compile(
    r"(usd|us\$|hkd|hk\$|r\$|brl|s\$|sgd|a\$|aud|c\$|cad|nz\$|nzd|(?<![a-z])\$|eur|€|gbp|£|myr|rm|kes|inr|₹|cop|"
    r"php|idr|cny|rmb|jpy|mxn|zar|ngn|ghs|thb|vnd|bdt|pkr|chf)\s*"
    r"(\d+(?:\.\d+)?)\s*(m|mn|million|k|bn|billion)?\b", re.I)
_CURRENCY_ALIASES = {"US$": "USD", "HK$": "HKD", "R$": "BRL", "S$": "SGD", "A$": "AUD", "C$": "CAD", "NZ$": "NZD",
                     "$": "USD", "€": "EUR", "£": "GBP", "RM": "MYR", "₹": "INR", "RMB": "CNY"}


_ZH_VALUE = {"〇": 0, "零": 0, "一": 1, "二": 2, "兩": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7,
             "八": 8, "九": 9}
_ZH_UNIT = {"十": 10, "百": 100, "千": 1000}
# Contexts where a count is accounts or traffic, not people served.
_NOT_SERVED = re.compile(r"\b(?:registered|sign[- ]?ups?|signed\s+up|downloads?|downloaded|visits?|visitors|"
                         r"page\s*views|impressions|followers|waitlist(?:ed)?)\b", re.I)


def _zh_number(raw: str) -> float:
    """三千 → 3000, 一百二十 → 120, 十五 → 15."""
    total, digit = 0, 0
    for ch in raw:
        if ch in _ZH_UNIT:
            total += (digit or 1) * _ZH_UNIT[ch]
            digit = 0
        else:
            digit = digit * 10 + _ZH_VALUE[ch]
    return float(total + digit)


def _number(raw: str, scale: str | None) -> float:
    if raw and raw[0] in _ZH_DIGITS:
        value = _zh_number(raw)
    else:
        value = float(re.sub(r"[, \u00a0\u2009\u202f]", "", raw))
    scale = (scale or "").lower()
    if scale in {"萬", "万"}:
        value *= 10_000
    elif scale in {"億", "亿"}:
        value *= 100_000_000
    if scale in {"k", "thousand"}:
        value *= 1_000
    elif scale in {"m", "mn", "million"}:
        value *= 1_000_000
    return value


@dataclass
class Figure:
    """One quantity read from one claim, with where it came from."""

    value: float
    text: str
    level: int = 1
    verified: bool = False
    noun: str = ""
    cumulative: bool = False   # a running total ("since launch"), not a yearly rate
    raw_value: float | None = None   # the figure as stated, when the calculation capped it
    effect_size: float | None = None  # standard deviations as stated ("0.21 SD"); value is the converted depth
    doubt: bool = False        # failed a plausibility check: its range is widened


@dataclass
class OutcomeInputs:
    reach: Figure | None = None
    depth: Figure | None = None
    tco2e_per_year: Figure | None = None
    ask_usd: float | None = None
    ask_text: str = ""
    targets: list[str] = field(default_factory=list)
    sector: str = ""
    other_reach: list[Figure] = field(default_factory=list)  # largest figure for each other noun


def _claim_fields(claim: Any) -> tuple[str, int, bool, str]:
    if isinstance(claim, dict):
        text, level = str(claim.get("text", "")), int(claim.get("evidence_strength") or 1)
        entities, category = claim.get("entities") or {}, str(claim.get("category", ""))
    else:
        text, level = claim.text, int(getattr(claim, "evidence_strength", 1) or 1)
        entities, category = getattr(claim, "entities", {}) or {}, getattr(claim, "category", "")
    signals = set(entities.get("evidence", []) or [])
    verified = bool(signals & {"third_party_verified", "audited", "certified"})
    if "controlled_evaluation" in signals:
        level = max(level, 3)
    elif "baseline_comparison" in signals:
        level = max(level, 2)
    return text, max(1, min(5, level)), verified, category


def _sentence_level(sentence: str) -> tuple[int, bool]:
    """Evidence level and verification of a raw sentence (for text not in claims)."""
    from impact_vision.impact.extractors.regex_extractor import evidence_signals

    signals = set(evidence_signals(sentence) or [])
    level = 3 if "controlled_evaluation" in signals else 2 if signals & {"baseline_comparison"} else 1
    return level, bool(signals & {"third_party_verified", "audited", "certified"})


def read_outcomes(claims: Iterable[Any], scoring_text: str = "", *, sector: str = "",
                  full_text: str = "") -> OutcomeInputs:
    """Pick the company's headline reach, depth of change and tCO2e from its claims.

    Only sentences that survive problem/market filtering count (so "25 million
    people in Kenya lack power" is context, not reach); targets are kept apart
    as ex-ante commitments. ``full_text`` is the whole document: the funding
    ask sits in the "ask / funding" section that ``scoring_text`` leaves out.
    """
    out = OutcomeInputs(sector=sector)
    scoring_lower = (scoring_text or "").lower()
    seen: set[str] = set()
    rows: list[tuple[str, int, bool, str]] = []
    for claim in claims:
        text, level, verified, category = _claim_fields(claim)
        key = text.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        if scoring_lower and key[:60] not in scoring_lower:
            continue  # problem statement / market context
        rows.append((text, level, verified, category))
    # Sentences the regex extractor missed (bullets, Chinese) still count.
    for sentence in re.split(r"(?<=[.!?。])\s+|\n+", scoring_text or ""):
        sentence = sentence.strip(" -•*\t")
        key = sentence.lower()
        if len(sentence) < 12 or key in seen or any(key[:40] in r[0].lower() for r in rows):
            continue
        seen.add(key)
        level, verified = _sentence_level(sentence)
        rows.append((sentence, level, verified, ""))

    by_noun: dict[str, Figure] = {}
    for text, level, verified, category in rows:
        is_target = category == "commitment" or bool(_TARGET_WORDS.search(text))
        if is_target:
            out.targets.append(text)
            continue
        for match in list(_PEOPLE_RE.finditer(text)) + list(_PEOPLE_ZH.finditer(text)):
            groups = match.groups()
            value = _number(groups[0], groups[1] if len(groups) > 2 else None)
            noun = groups[-1].lower()
            if "visit" in text[match.end():match.end() + 8].lower():
                continue  # patient visits are not people
            if value < 5:
                continue
            if _GOAL_BEFORE.search(text[:match.start()]):
                if text not in out.targets:
                    out.targets.append(text)  # what the money is meant to achieve, not what was achieved
                continue
            if _NOT_SERVED.search(text[match.end():match.end() + 24]) or _NOT_SERVED.search(
                    text[max(0, match.start() - 24):match.start()]):
                continue  # accounts and traffic are not people served
            if noun not in by_noun or value > by_noun[noun].value:
                by_noun[noun] = Figure(value, text, level, verified, noun)
        depth_val = None
        for pattern in _DEPTH_RE:
            m = pattern.search(text)
            if m:
                depth_val = float(m.group(1)) / 100.0
                break
        effect = None
        if depth_val is None:
            m = _EFFECT_SIZE_RE.search(text)
            if m:
                # Standard deviations are not a percentage: one documented conversion, labelled as such.
                conv = params().get("effect_size_to_depth") or {}
                effect = float(m.group(1))
                depth_val = min(effect * float(conv.get("per_sd", 0.4)), float(conv.get("cap", 0.5)))
        if depth_val is not None and 0 < depth_val <= 5:
            stated, depth_val = depth_val, min(depth_val, 1.0)
            better = out.depth is None or (level, depth_val) > (out.depth.level, out.depth.value)
            if better:
                out.depth = Figure(depth_val, text, level, verified, raw_value=stated, effect_size=effect)
        for pattern in (_CO2_RE, _CO2_UNIT_RE):
            for m in pattern.finditer(text):
                if not _AVOID_WORDS.search(text) or re.search(r"\bper\s+(?:kg|unit|item)", text, re.I):
                    continue
                value = _number(m.group(1), m.group(2))
                if out.tco2e_per_year is None or value > out.tco2e_per_year.value:
                    out.tco2e_per_year = Figure(value, text, level, verified, "tCO2e",
                                                cumulative=bool(_CUMULATIVE.search(text)))
    if by_noun:
        # Headline reach by stakeholder, not by size: beneficiary nouns before generic ones.
        generic = {str(n).lower() for n in (params().get("reach_noun_priority") or {}).get("generic", [])}
        ordered = sorted(by_noun.values(), key=lambda f: (f.noun in generic, -f.value))
        out.reach, out.other_reach = ordered[0], ordered[1:]
    out.ask_usd, out.ask_text = _ask(full_text or scoring_text)
    return out


def _fx_to_usd(currency: str) -> float | None:
    """USD per unit of *currency*: the methodology table first, then the offline FX snapshot."""
    rate = (params().get("fx_to_usd") or {}).get(currency)
    if rate is not None:
        return float(rate)
    from impact_vision.impact.fx import StaticFXRateProvider

    snapshot = StaticFXRateProvider().rate(from_ccy=currency, to_ccy="USD")
    return float(snapshot) if snapshot else None


def _ask(text: str) -> tuple[float | None, str]:
    """The funding ask in USD ("HKD 25m Series A") using the illustrative FX table."""
    for line in re.split(r"\n+", text or ""):
        if not re.search(r"\b(raise|raising|ask|series|seed|round|funding|investment|融資|融资)\b|融資|融资", line, re.I):
            continue
        m = _ASK_RE.search(line)
        if not m:
            continue
        currency = _CURRENCY_ALIASES.get(m.group(1).upper(), m.group(1).upper())
        rate = _fx_to_usd(currency)
        if rate is None:
            continue
        amount = float(m.group(2))
        scale = (m.group(3) or "").lower()
        amount *= {"k": 1e3, "m": 1e6, "mn": 1e6, "million": 1e6, "bn": 1e9, "billion": 1e9}.get(scale, 1)
        if amount < 10_000:
            continue
        return amount * float(rate), m.group(0)
    return None, ""


# --------------------------------------------------------------------------- simulation

@dataclass
class Factor:
    name: str
    median: float
    sigma: float
    why: str
    cap: float | None = None
    why_key: str = ""
    why_args: dict[str, Any] = field(default_factory=dict)


def _level_cfg(level: int) -> dict[str, Any]:
    levels: dict[int, dict[str, Any]] = params().get("evidence_levels") or {}
    return levels.get(level) or levels[1]


def _sigma(fig: Figure) -> float:
    sigma = float(_level_cfg(fig.level)["sigma"])
    if fig.verified:
        sigma *= float(params().get("verified_sigma_factor", 0.7))
    if fig.doubt:  # an implausible figure must not produce a narrow range
        sigma *= float((params().get("plausibility") or {}).get("sigma_multiplier", 1.5))
    return sigma


def _factors(inp: OutcomeInputs, primary: Figure, *, climate: bool) -> list[Factor]:
    p = params()
    who = "tCO2e" if climate else stakeholder_label(primary.noun)
    factors: list[Factor] = [Factor(
        "Reach" if not climate else "Tonnes per year", primary.value, _sigma(primary),
        f"{primary.value:,.0f} {who} reported (NESTA {primary.level}" + (", verified" if primary.verified else "") + ")",
        why_key="why_reported_verified" if primary.verified else "why_reported",
        why_args={"n": f"{primary.value:,.0f}", "who": who, "level": primary.level})]
    if not climate:
        if inp.depth is not None:
            factors.append(Factor("Depth of change", inp.depth.value, _sigma(inp.depth),
                                  (f"{inp.depth.value:.0%} change, converted from an effect size of "
                                   f"{inp.depth.effect_size:g} SD (NESTA {inp.depth.level})"
                                   if inp.depth.effect_size is not None else
                                   f"{inp.depth.value:.0%} change reported (NESTA {inp.depth.level})"), cap=1.0,
                                  why_key="why_depth", why_args={"pct": f"{inp.depth.value:.0%}",
                                                                 "level": inp.depth.level}))
        else:
            du = p["depth_unknown"]
            factors.append(Factor("Depth of change", du["mean"], du["sigma"],
                                  "no change measured: an assumed 10%", cap=1.0, why_key="why_depth_assumed"))
    dur: dict[str, dict[str, float]] = p.get("duration_years") or {}
    d = dur.get(inp.sector) or dur["default"]
    if climate and primary.cumulative:
        factors.append(Factor("Duration (years)", 1.0, 0.0, "a running total, counted once (not multiplied by years)",
                              why_key="why_cumulative"))
    else:
        factors.append(Factor("Duration (years)", d["mean"], d["sigma"],
                              f"typical for {inp.sector or 'this sector'}",
                              why_key="why_duration", why_args={"sector": inp.sector or "-"}))
    evidence_level = (inp.depth.level if (inp.depth is not None and not climate) else primary.level)
    if evidence_level >= int(p["deadweight"]["netted_from_level"]):
        factors.append(Factor("Without deadweight", 1.0, 0.0, "netted out by the comparison group", cap=1.0,
                              why_key="why_dw_netted"))
    else:
        dw = p["deadweight"]["default"]
        factors.append(Factor("Without deadweight", 1 - dw["mean"], dw["sigma"] * 0.5,
                              "no comparison group: ~30% would have happened anyway", cap=1.0,
                              why_key="why_dw_default"))
    at = p["attribution"]
    factors.append(Factor("Attribution", at["mean"], at["sigma"], "share credited to the enterprise", cap=1.0,
                          why_key="why_attribution"))
    factors.append(Factor("Probability of success", float(_level_cfg(evidence_level)["p_success"]), 0.0,
                          f"evidence level {evidence_level}", cap=1.0, why_key="why_p",
                          why_args={"level": evidence_level}))
    return factors


def _simulate(factors: list[Factor], seed_text: str) -> dict[str, Any]:
    """Seeded Monte Carlo over lognormal factors (standard library only: the
    core install has no numpy)."""
    import random
    import statistics

    cfg = params().get("monte_carlo") or {}
    # Seeded from the model inputs only: the same figures always give the same
    # range, and rewording the document (buzzwords) can't move it.
    key = seed_text.rsplit("|", 1)[-1] + "|" + "|".join(f"{f.name}:{f.median:.6g}:{f.sigma:.4g}" for f in factors)
    rng = random.Random(int(hashlib.sha256(key.encode("utf-8")).hexdigest()[:8], 16))
    n = int(cfg.get("draws", 4000))
    total = [1.0] * n
    log_vars: dict[str, float] = {}
    for f in factors:
        if f.sigma > 0:
            draw = [f.median * math.exp(rng.gauss(0.0, f.sigma)) for _ in range(n)]
        else:
            draw = [f.median] * n
        if f.cap is not None:
            draw = [min(x, f.cap) for x in draw]
        total = [t * x for t, x in zip(total, draw)]
        logs = [math.log(max(x, 1e-12)) for x in draw]
        log_vars[f.name] = statistics.pvariance(logs) if f.sigma > 0 else 0.0
    ordered = sorted(total)

    def pct(q: float) -> float:
        # Linear interpolation between order statistics (same as numpy's default).
        pos = (len(ordered) - 1) * q / 100.0
        lo, hi = math.floor(pos), math.ceil(pos)
        return ordered[lo] + (ordered[hi] - ordered[lo]) * (pos - lo)

    pcts = [int(x) for x in cfg.get("percentiles", [10, 50, 90])]
    values = {f"p{q}": float(pct(q)) for q in pcts}
    var_total = sum(log_vars.values()) or 1.0
    drivers = sorted(((k, v / var_total) for k, v in log_vars.items() if v > 0), key=lambda kv: -kv[1])
    sigma_total = math.sqrt(sum(log_vars.values()))
    return {**values, "drivers": [{"factor": k, "share": round(s, 3)} for k, s in drivers],
            "spread": round(values["p90"] / values["p10"], 1) if values["p10"] > 0 else None,
            "sigma": round(sigma_total, 3)}


def _words(sigma: float) -> str:
    for band in params().get("uncertainty_words") or []:
        if sigma <= band["max"]:
            return str(band["label"])
    return "wide"


# --------------------------------------------------------------------------- assessment

def evidence_quality(inp: OutcomeInputs, claims: Iterable[Any]) -> dict[str, Any]:
    cfg = params()["evidence_quality"]
    figures = [f for f in (inp.reach, inp.depth, inp.tco2e_per_year) if f is not None]
    levels = [f.level for f in figures] or [max((_claim_fields(c)[1] for c in claims), default=1)]
    verified = any(f.verified for f in figures) or any(_claim_fields(c)[2] for c in claims)
    score = min(100, round(cfg["per_level"] * (sum(levels) / len(levels)) + (cfg["verified_bonus"] if verified else 0)))
    label = next(b["label"] for b in cfg["bands"] if score >= b["min"])
    return {"score": score, "label": label, "levels": levels, "verified": verified}


def assess_expected_impact(
    claims: Iterable[Any],
    scoring_text: str = "",
    *,
    sector: str = "",
    company_name: str = "",
    data_completeness_pct: float | None = None,
    greenwashing: Any = None,
    v1_checks: Iterable[dict[str, Any]] = (),
    missing_metrics: Iterable[str] = (),
    negative: dict[str, Any] | None = None,
    claims_review: dict[str, Any] | None = None,
    full_text: str = "",
    conflicts: list[dict[str, str]] | None = None,
    geography: str = "",
) -> dict[str, Any]:
    """Methodology 2.0 result block stored in ``report_data['expected_impact']``.

    ``conflicts`` are evidence-plan entries for figures the documents give
    twice with different values; they go first, because every number built on
    a disputed figure is in doubt.
    """
    claims = list(claims)
    inp = read_outcomes(claims, scoring_text, sector=sector, full_text=full_text)
    from impact_vision.impact.consistency import plausibility_flags, plausibility_plan_items

    flags = plausibility_flags(inp, geography)
    for flag in flags:
        figure = {"reach": inp.reach, "tonnes": inp.tco2e_per_year}.get(flag["figure"])
        if figure is not None and flag["severity"] == "doubt":
            figure.doubt = True
    seed = f"{company_name}|{scoring_text[:4000]}"
    outcomes: list[dict[str, Any]] = []
    if inp.reach is not None:
        factors = _factors(inp, inp.reach, climate=False)
        sim = _simulate(factors, seed + "|people")
        outcomes.append(_outcome_row("people", inp, inp.reach, factors, sim,
                                     unit="depth-weighted person-years", per_usd=inp.ask_usd))
    if inp.tco2e_per_year is not None:
        factors = _factors(inp, inp.tco2e_per_year, climate=True)
        sim = _simulate(factors, seed + "|climate")
        outcomes.append(_outcome_row("climate", inp, inp.tco2e_per_year, factors, sim,
                                     unit="tCO2e", per_usd=inp.ask_usd))
    eq = evidence_quality(inp, claims)
    plan = _evidence_plan(inp, outcomes, eq, data_completeness_pct, list(missing_metrics))
    if negative:
        # W1.6: material negative impacts with no disclosed control are questions to ask.
        from impact_vision.impact.negative_impacts import plan_items

        plan = (plan[:3] + plan_items(negative, 1) + plan[3:])[:4]
    plan = ([*(conflicts or [])[:1], *plausibility_plan_items(flags), *plan])[:4]
    gate = _gate(outcomes, eq, data_completeness_pct, greenwashing, list(v1_checks), plan, claims_review)
    return {
        "methodology": stamp(),
        "outcomes": outcomes,
        "evidence_quality": eq,
        "data_completeness_pct": data_completeness_pct,
        "targets": inp.targets[:5],
        "ask": {"usd": inp.ask_usd, "text": inp.ask_text} if inp.ask_usd else None,
        "evidence_plan": plan,
        "plausibility": flags,
        "gate": gate,
    }


_STAKEHOLDER_WORDS = {
    "homes": "households", "household": "households", "smes": "small businesses", "elderly": "older people",
    "seniors": "older people", "長者": "older people", "长者": "older people", "學生": "students",
    "学生": "students", "病人": "patients", "農民": "farmers", "农民": "farmers", "居民": "residents",
    "用戶": "users", "用户": "users", "婦女": "women", "妇女": "women", "兒童": "children", "儿童": "children",
}


def stakeholder_label(noun: str) -> str:
    return _STAKEHOLDER_WORDS.get(noun, noun)


def _outcome_row(kind: str, inp: OutcomeInputs, primary: Figure, factors: list[Factor],
                 sim: dict[str, Any], *, unit: str, per_usd: float | None) -> dict[str, Any]:
    row = {
        "kind": kind,
        "unit": unit,
        "stakeholder": stakeholder_label(primary.noun) if kind == "people" else "tCO2e",
        "stakeholder_raw": primary.noun,
        "source": primary.text.strip().lstrip("-•* ").strip(),
        "evidence_level": primary.level,
        "verified": primary.verified,
        "depth_measured": inp.depth is not None if kind == "people" else None,
        "p10": sim["p10"], "p50": sim["p50"], "p90": sim["p90"],
        "spread": sim["spread"],
        "uncertainty": _words(sim["sigma"]),
        "drivers": sim["drivers"][:3],
        "factors": [{"name": f.name, "median": f.median, "sigma": f.sigma, "why": f.why,
                     "why_key": f.why_key, "why_args": f.why_args} for f in factors],
    }
    if per_usd:
        scale = per_usd / 1_000_000
        row["per_usd_1m"] = {k: sim[k] / scale for k in ("p10", "p50", "p90")}
    return row


def _evidence_plan(inp: OutcomeInputs, outcomes: list[dict[str, Any]], eq: dict[str, Any],
                   completeness: float | None, missing: list[str]) -> list[dict[str, str]]:
    """The few pieces of evidence that would move the answer most, biggest first."""
    plan: list[dict[str, str]] = []
    if not outcomes:
        plan.append({"action": "State how many people (or tonnes of CO2e) the business reached in the last 12 months.",
                     "why": "No quantified outcome was found, so expected impact can't be estimated.",
                     "kind": "quantify"})
    people = next((o for o in outcomes if o["kind"] == "people"), None)
    if people is not None:
        top = people["drivers"][0]["factor"] if people["drivers"] else ""
        if not people["depth_measured"]:
            plan.append({"action": f"Measure how much life changes for the {people['stakeholder']} "
                                   "(before/after on the outcome that matters, e.g. income, cost, health or learning).",
                         "why": f"Depth of change is assumed, and it carries "
                                f"{_share(people, 'Depth of change')} of the uncertainty.",
                         "kind": "measure_depth"})
        level = max(inp.depth.level if inp.depth else 1, people["evidence_level"])
        if level < 3:
            plan.append({"action": "Compare with a group that did not get the product (a comparison group or "
                                   "a credible baseline), ideally run by someone independent.",
                         "why": f"Moves evidence from level {level} to 3, nets out deadweight and narrows the "
                                f"range (now ×{people['spread']} from P10 to P90)." if people["spread"] else
                                f"Moves evidence from level {level} to 3.",
                         "kind": "comparison"})
        if not people["verified"] and top == "Reach" and inp.reach is not None:
            plan.append({"action": f"Have the headline reach figure ({int(inp.reach.value):,} "
                                   f"{people['stakeholder']}) verified by a third party.",
                         "why": "Reach drives most of the remaining uncertainty.", "kind": "verify_reach"})
    if completeness is not None and completeness < _completeness_floor(params()["gate"]["ready"]):
        names = ", ".join(missing[:3])
        plan.append({"action": f"Report the sector's core metrics{': ' + names if names else ''}.",
                     "why": f"Only {completeness:.0f}% of the core set is reported.", "kind": "core_metrics"})
    if eq["score"] < 60 and len(plan) < 3:
        plan.append({"action": "Back the main figures with data: monitoring records, surveys or audited accounts.",
                     "why": f"Evidence quality is {eq['label']} ({eq['score']}/100).", "kind": "back_figures"})
    return plan[:4]


def suggest_conditions(block: dict[str, Any] | None) -> list[dict[str, str]]:
    """Draft investment conditions for the IC to adopt, amend or drop.

    Each evidence-plan item becomes a condition precedent, a covenant or a
    reporting requirement (``conditions`` in ``methodology/v2.yaml`` says
    which, and when), and each target the company states itself becomes a
    covenant to report against. Nothing is suggested for a deal that fails
    the thesis: conditions do not cure an exclusion.
    """
    block = block or {}
    if (block.get("gate") or {}).get("state") == "fails_thesis":
        return []
    cfg = params().get("conditions") or {}
    kinds: dict[str, dict[str, str]] = cfg.get("kinds") or {}
    out: list[dict[str, str]] = []
    for item in block.get("evidence_plan") or []:
        rule = kinds.get(str(item.get("kind", "")))
        if rule:
            out.append({"type": rule["type"], "timing": rule["timing"], "text": item["action"],
                        "basis": item.get("why", ""), "source": "evidence plan"})
    target_rule = kinds.get("stated_target")
    stated = (block.get("targets") or [])[: int(cfg.get("max_stated_targets", 2))] if target_rule else []
    for sentence in stated:
        assert target_rule is not None
        out.append({"type": target_rule["type"], "timing": target_rule["timing"],
                    "text": f"Report progress against the company's own target: “{sentence.strip()}”",
                    "basis": "The company states this target; a covenant makes it binding rather than aspirational.",
                    "source": "stated target"})
    order = {"condition_precedent": 0, "covenant": 1, "reporting": 2}
    out.sort(key=lambda c: order.get(c["type"], 3))
    return out[: int(cfg.get("max_items", 6))]


def _share(outcome: dict[str, Any], factor: str) -> str:
    share = next((d["share"] for d in outcome["drivers"] if d["factor"] == factor), None)
    if share is None:
        share = next((d["share"] for d in _all_drivers(outcome) if d["factor"] == factor), 0)
    return f"{share:.0%}"


def _all_drivers(outcome: dict[str, Any]) -> list[dict[str, Any]]:
    drivers: list[dict[str, Any]] = outcome.get("drivers", [])
    return drivers


def _completeness_floor(ready: dict[str, Any]) -> float:
    """Core-metric coverage below this is a note and a reporting item, never a gate condition."""
    return float(ready.get("completeness_note_below", ready.get("min_data_completeness", 40)))


def _gate(outcomes: list[dict[str, Any]], eq: dict[str, Any], completeness: float | None,
          greenwashing: Any, v1_checks: list[dict[str, Any]], plan: list[dict[str, str]],
          claims_review: dict[str, Any] | None = None) -> dict[str, Any]:
    cfg = params()["gate"]
    reasons: list[str] = []
    found = []
    # Greenwashing 2.0 (W1.9): several claims that are themselves misleading.
    review = claims_review or {}
    if (review.get("score") or 0) >= 60 and review.get("flagged", 0) >= 2:
        found.append(f"{review['flagged']} claims likely misleading (claim-level greenwashing {review['score']}/100)")
    if greenwashing is not None and getattr(greenwashing, "is_finding", False) and not getattr(
            greenwashing, "evidence_gap", False):
        found.append(f"greenwashing finding ({greenwashing.overall_score:.0f}/100: {greenwashing.classification})")
    for check in v1_checks:
        name = str(check.get("name", "")).lower()
        if check.get("status") == "fail" and any(k in name for k in ("exclusion", "forbidden", "sector")):
            found.append(check.get("message") or name)
    if found:
        return {"state": "fails_thesis", "label": "Fails thesis", "reasons": found,
                "rationale": cfg["rationale"]["fails_thesis"]}
    ready = cfg["ready"]
    quantified = bool(outcomes)
    ok_eq = eq["score"] >= ready["min_evidence_quality"]
    # C8: completeness is disclosure, not evidence, so it no longer gates. The
    # headline figure must show change and its range must be narrow enough.
    head = outcomes[0] if outcomes else None
    min_level = int(ready.get("min_headline_level", 0) or 0)
    max_spread = float(ready.get("max_spread", 0) or 0)
    level = int(head.get("evidence_level") or 0) if head else 0
    spread = float(head.get("spread") or 0) if head else 0.0
    ok_level = head is None or level >= min_level
    ok_spread = head is None or not max_spread or spread <= max_spread
    low_comp = completeness is not None and completeness < _completeness_floor(ready)
    if (quantified or not ready.get("require_quantified_outcome", True)) and ok_eq and ok_level and ok_spread:
        gate = {"state": "ready", "label": "Ready for IC",
                "reasons": [f"evidence quality {eq['label']} ({eq['score']}/100)",
                            *(f"{o['kind']} impact P50 {o['p50']:,.0f} {o['unit']}" for o in outcomes)],
                "rationale": cfg["rationale"]["ready"]}
        if low_comp:
            gate["note"] = f"Ready, with {completeness:.0f}% of the core metric set reported."
        return gate
    if not quantified:
        reasons.append("no quantified outcome")
    if not ok_eq:
        reasons.append(f"evidence quality {eq['label']} ({eq['score']}/100, needs {ready['min_evidence_quality']})")
    if not ok_level:
        reasons.append(f"the headline figure is at evidence level {level} (needs {min_level}: data showing change)")
    if not ok_spread:
        reasons.append(f"the range is too wide to decide on (x{spread:g} from P10 to P90, needs x{max_spread:g} or less)")
    return {"state": "evidence_plan", "label": "Evidence plan required", "reasons": reasons,
            "plan": plan, "rationale": cfg["rationale"]["evidence_plan"]}


CONDITION_LABELS = {"condition_precedent": "Condition precedent", "covenant": "Covenant",
                    "reporting": "Reporting requirement"}


def figure_dict(fig: Figure | None) -> dict[str, Any] | None:
    return asdict(fig) if fig is not None else None


__all__ = ["assess_expected_impact", "evidence_quality", "headline", "methodology_mode", "params",
           "read_outcomes", "stamp", "stakeholder_label"]
