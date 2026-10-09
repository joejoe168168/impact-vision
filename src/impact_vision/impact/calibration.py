"""Expert calibration study toolkit (roadmap v8 W2.6).

The study: 2–3 practitioners rate 50–100 decks blind; their agreement is
measured with Krippendorff's α (target ≥ 0.67); where they agree, the
methodology is fitted to their consensus by ordinal regression and the result
is published with Methodology 2.x. This module does everything except the
rating:

1. :func:`build_packet` copies the decks, writes a blank rating sheet and a
   rater guide, and keeps the engine's own scores in a separate file the
   raters never see.
2. :func:`krippendorff_alpha` (nominal / ordinal / interval / ratio, missing
   values allowed).
3. :func:`proportional_odds` fits P(rating ≤ k) = σ(θ_k − x·β) by gradient
   ascent (no numpy), so each engine feature gets a weight on the experts'
   scale.
4. :func:`analyse` turns the filled sheet into a markdown report: α per
   question, engine-vs-consensus agreement, and suggested weights.
"""
from __future__ import annotations

import csv
import math
import shutil
from collections import Counter, defaultdict
from pathlib import Path
from statistics import median
from typing import Any, Sequence

QUESTIONS: dict[str, dict[str, Any]] = {
    "impact_magnitude": {"label": "How much positive change, for how many (1 = very little, 5 = very large)",
                         "level": "ordinal", "scale": [1, 2, 3, 4, 5]},
    "evidence_quality": {"label": "How strong is the evidence (1 = assertion only, 5 = independent, controlled)",
                         "level": "ordinal", "scale": [1, 2, 3, 4, 5]},
    "contribution": {"label": "Would the outcome have happened anyway? (1 = mostly yes, 5 = mostly no)",
                     "level": "ordinal", "scale": [1, 2, 3, 4, 5]},
    "greenwashing_risk": {"label": "Risk that the impact claims mislead (1 = low, 5 = high)",
                          "level": "ordinal", "scale": [1, 2, 3, 4, 5]},
    "verdict": {"label": "Your call: ready / evidence_plan / fails_thesis", "level": "nominal",
                "scale": ["ready", "evidence_plan", "fails_thesis"]},
}
ALPHA_TARGET = 0.67
SUPPORTED = (".pdf", ".docx", ".pptx", ".md", ".txt")


# ------------------------------------------------------------------ packet


def engine_features(path: Path) -> dict[str, Any]:
    """The engine's view of one deck: what the experts' ratings are compared with."""
    from impact_vision.impact.pipeline import assess_file

    data = assess_file(path).report_data
    ei = data.get("expected_impact") or {}
    eq = ei.get("evidence_quality") or {}
    people = next((o for o in ei.get("outcomes") or [] if o["kind"] == "people"), None)
    split = data.get("contribution_split") or {}
    claims = (data.get("greenwashing") or {}).get("claims_review") or {}
    signals = {s["signal"] for s in (split.get("enterprise") or {}).get("signals") or []}
    return {
        "expected_p50": round(float(people["p50"]), 1) if people else 0.0,
        "evidence_quality": eq.get("score", 0),
        "nesta_max": max(eq.get("levels") or [1]),
        "verified": int(bool(eq.get("verified"))),
        "comparison_group": int("controlled_evaluation" in signals),
        "baseline": int("baseline_comparison" in signals),
        "coverage_pct": round(float((data.get("gap_analysis") or {}).get("coverage_percentage") or 0), 1),
        "enterprise_contribution": (split.get("enterprise") or {}).get("score", 0),
        "greenwashing_claims": claims.get("score", 0),
        "verdict": (ei.get("gate") or {}).get("state", ""),
    }


def build_packet(decks: Sequence[str | Path], out_dir: str | Path, *, raters: Sequence[str] = ("A", "B", "C"),
                 score: bool = True) -> dict[str, Any]:
    """A folder to send to raters (``decks/``, ``ratings_<rater>.csv``, ``GUIDE.md``) plus
    ``engine_scores.csv`` for the coordinator only."""
    out = Path(out_dir)
    (out / "decks").mkdir(parents=True, exist_ok=True)
    names = []
    for i, deck in enumerate(sorted(Path(d) for d in decks), 1):
        if deck.suffix.lower() not in SUPPORTED:
            continue
        name = f"D{i:03d}{deck.suffix.lower()}"  # neutral IDs: the file name mustn't hint at the answer
        shutil.copyfile(deck, out / "decks" / name)
        names.append((name, deck))
    for rater in raters:
        with open(out / f"ratings_{rater}.csv", "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["deck", "rater", *QUESTIONS, "minutes", "notes"])
            for name, _ in names:
                w.writerow([name, rater, *([""] * len(QUESTIONS)), "", ""])
    guide = ["# Rating guide", "", "Rate each deck on its own, without looking at Impact Vision's output and "
             "without discussing it with the other raters. Leave a cell blank if you can't tell.", ""]
    guide += [f"- **{key}**: {q['label']}" for key, q in QUESTIONS.items()]
    guide += ["", "Record roughly how many minutes each deck took (column `minutes`)."]
    (out / "GUIDE.md").write_text("\n".join(guide) + "\n", encoding="utf-8")
    if score:
        rows = [{"deck": name, "source": str(src), **engine_features(src)} for name, src in names]
        if rows:
            with open(out / "engine_scores.csv", "w", newline="", encoding="utf-8") as fh:
                dw = csv.DictWriter(fh, fieldnames=list(rows[0]))
                dw.writeheader()
                dw.writerows(rows)
    return {"decks": len(names), "raters": list(raters), "folder": str(out)}


# ------------------------------------------------------------------ Krippendorff's alpha


def _delta(a: Any, b: Any, level: str, values: list[Any], counts: Counter[Any]) -> float:
    if a == b:
        return 0.0
    if level == "nominal":
        return 1.0
    if level == "interval":
        return float((a - b) ** 2)
    if level == "ratio":
        return float(((a - b) / (a + b)) ** 2) if a + b else 0.0
    # ordinal: (sum of the marginal counts from a to b, minus half of each end)²
    lo, hi = sorted((values.index(a), values.index(b)))
    between = sum(counts[values[i]] for i in range(lo, hi + 1))
    return float((between - (counts[values[lo]] + counts[values[hi]]) / 2) ** 2)


def krippendorff_alpha(units: Sequence[Sequence[Any]], level: str = "ordinal") -> float:
    """α for reliability data: one row per unit, one value (or None) per rater."""
    pairable = [[v for v in unit if v is not None and v != ""] for unit in units]
    pairable = [u for u in pairable if len(u) >= 2]
    if not pairable:
        return float("nan")
    coincidence: dict[tuple[Any, Any], float] = defaultdict(float)
    for unit in pairable:
        m = len(unit)
        for i, a in enumerate(unit):
            for j, b in enumerate(unit):
                if i != j:
                    coincidence[(a, b)] += 1.0 / (m - 1)
    counts: Counter[Any] = Counter()
    for (a, _b), n in coincidence.items():
        counts[a] += n  # type: ignore[assignment]
    values = sorted(counts)
    n_total = sum(counts.values())
    observed = sum(n * _delta(a, b, level, values, counts) for (a, b), n in coincidence.items())
    expected = sum(counts[a] * counts[b] * _delta(a, b, level, values, counts)
                   for a in values for b in values) / (n_total - 1)
    return 1.0 if expected == 0 else 1.0 - observed / expected


# ------------------------------------------------------------------ ordinal regression


def proportional_odds(x: Sequence[Sequence[float]], y: Sequence[int], *, iterations: int = 4000,
                      lr: float = 0.05, l2: float = 0.01) -> dict[str, Any]:
    """Fit P(y ≤ k | x) = σ(θ_k − x·β). Features are standardised first; β is per SD."""
    n, p = len(x), len(x[0]) if x else 0
    levels = sorted(set(y))
    k = len(levels)
    if n < 5 or k < 2:
        raise ValueError("need at least 5 rated decks and 2 distinct ratings")
    means = [sum(r[j] for r in x) / n for j in range(p)]
    sds = [math.sqrt(sum((r[j] - means[j]) ** 2 for r in x) / n) or 1.0 for j in range(p)]
    z = [[(r[j] - means[j]) / sds[j] for j in range(p)] for r in x]
    idx = [levels.index(v) for v in y]
    beta = [0.0] * p
    theta = [(i + 1) - k / 2 for i in range(k - 1)]

    def sig(t: float) -> float:
        return 1 / (1 + math.exp(-max(-35.0, min(35.0, t))))

    for _ in range(iterations):
        g_beta, g_theta = [-l2 * b for b in beta], [0.0] * (k - 1)
        for row, c in zip(z, idx):
            eta = sum(b * v for b, v in zip(beta, row))
            upper = sig(theta[c] - eta) if c < k - 1 else 1.0
            lower = sig(theta[c - 1] - eta) if c > 0 else 0.0
            prob = max(upper - lower, 1e-12)
            du = upper * (1 - upper) if c < k - 1 else 0.0
            dl = lower * (1 - lower) if c > 0 else 0.0
            for j in range(p):
                g_beta[j] += -(du - dl) * row[j] / prob
            if c < k - 1:
                g_theta[c] += du / prob
            if c > 0:
                g_theta[c - 1] -= dl / prob
        beta = [b + lr * g / n for b, g in zip(beta, g_beta)]
        theta = sorted(t + lr * g / n for t, g in zip(theta, g_theta))
    loglik = 0.0
    for row, c in zip(z, idx):
        eta = sum(b * v for b, v in zip(beta, row))
        upper = sig(theta[c] - eta) if c < k - 1 else 1.0
        lower = sig(theta[c - 1] - eta) if c > 0 else 0.0
        loglik += math.log(max(upper - lower, 1e-12))
    return {"beta_per_sd": [round(b, 3) for b in beta], "thresholds": [round(t, 3) for t in theta],
            "levels": levels, "log_likelihood": round(loglik, 3), "n": n}


def spearman(a: Sequence[float], b: Sequence[float]) -> float:
    def ranks(v: Sequence[float]) -> list[float]:
        order = sorted(range(len(v)), key=lambda i: v[i])
        out = [0.0] * len(v)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
                j += 1
            for t in range(i, j + 1):
                out[order[t]] = (i + j) / 2 + 1
            i = j + 1
        return out

    ra, rb = ranks(a), ranks(b)
    ma, mb = sum(ra) / len(ra), sum(rb) / len(rb)
    cov = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    den = math.sqrt(sum((x - ma) ** 2 for x in ra) * sum((y - mb) ** 2 for y in rb))
    return round(cov / den, 3) if den else float("nan")


# ------------------------------------------------------------------ analysis


def _read_ratings(paths: Sequence[Path]) -> dict[str, dict[str, dict[str, str]]]:
    """deck → rater → question → value."""
    out: dict[str, dict[str, dict[str, str]]] = defaultdict(dict)
    for path in paths:
        with open(path, newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                out[row["deck"]][row["rater"]] = {q: (row.get(q) or "").strip() for q in QUESTIONS}
    return out


def analyse(packet: str | Path) -> dict[str, Any]:
    folder = Path(packet)
    ratings = _read_ratings(sorted(folder.glob("ratings_*.csv")))
    raters = sorted({r for by_rater in ratings.values() for r in by_rater})
    decks = sorted(ratings)
    alpha: dict[str, float] = {}
    consensus: dict[str, dict[str, Any]] = {d: {} for d in decks}
    for q, spec in QUESTIONS.items():
        units = []
        for d in decks:
            vals: list[Any] = []
            for r in raters:
                v = ratings[d].get(r, {}).get(q, "")
                vals.append((int(v) if spec["level"] != "nominal" else v) if v else None)
            units.append(vals)
            present = [v for v in vals if v is not None]
            if present:
                consensus[d][q] = (median(present) if spec["level"] != "nominal"
                                   else Counter(present).most_common(1)[0][0])
        alpha[q] = round(krippendorff_alpha(units, spec["level"]), 3)
    engine = {}
    scores = folder / "engine_scores.csv"
    if scores.exists():
        with open(scores, newline="", encoding="utf-8") as fh:
            engine = {row["deck"]: row for row in csv.DictReader(fh)}
    comparisons: dict[str, Any] = {}
    shared = [d for d in decks if d in engine]
    pairs = {"impact_magnitude": "expected_p50", "evidence_quality": "evidence_quality",
             "contribution": "enterprise_contribution", "greenwashing_risk": "greenwashing_claims"}
    for q, feature in pairs.items():
        rows = [(float(engine[d][feature]), float(consensus[d][q])) for d in shared if q in consensus[d]]
        if len(rows) >= 5:
            comparisons[q] = {"spearman": spearman([a for a, _ in rows], [b for _, b in rows]), "n": len(rows)}
    verdicts = [(engine[d]["verdict"], consensus[d]["verdict"]) for d in shared if "verdict" in consensus[d]]
    if verdicts:
        comparisons["verdict"] = {"agreement": round(sum(a == b for a, b in verdicts) / len(verdicts), 3),
                                  "n": len(verdicts)}
    fit = None
    features = ["nesta_max", "verified", "comparison_group", "baseline", "coverage_pct"]
    eq_rows = [d for d in shared if "evidence_quality" in consensus[d]]
    if len(eq_rows) >= 5 and alpha.get("evidence_quality", 0) >= ALPHA_TARGET:
        try:
            fit = proportional_odds([[float(engine[d][f]) for f in features] for d in eq_rows],
                                    [int(round(float(consensus[d]["evidence_quality"]))) for d in eq_rows])
            fit["features"] = features
        except ValueError:
            fit = None
    return {"decks": len(decks), "raters": raters, "alpha": alpha, "alpha_target": ALPHA_TARGET,
            "comparisons": comparisons, "evidence_quality_fit": fit}


def to_markdown(result: dict[str, Any]) -> str:
    lines = [f"# Calibration study: {result['decks']} decks, raters {', '.join(result['raters'])}", "",
             f"## Inter-rater agreement (Krippendorff's α, target ≥ {result['alpha_target']})", "",
             "| Question | α | Usable for calibration |", "|---|---|---|"]
    for q, a in result["alpha"].items():
        ok = isinstance(a, float) and not math.isnan(a) and a >= result["alpha_target"]
        lines.append(f"| {q} | {a} | {'yes' if ok else 'no: agree on the rubric and re-rate'} |")
    lines += ["", "## Engine vs expert consensus", "", "| Question | Result | n |", "|---|---|---|"]
    for q, c in result["comparisons"].items():
        stat = f"Spearman ρ {c['spearman']}" if "spearman" in c else f"agreement {c['agreement']:.0%}"
        lines.append(f"| {q} | {stat} | {c['n']} |")
    fit = result.get("evidence_quality_fit")
    if fit:
        lines += ["", "## Evidence quality: what experts weight (proportional-odds, per SD)", "",
                  "| Feature | Weight |", "|---|---|"]
        lines += [f"| {f} | {b} |" for f, b in zip(fit["features"], fit["beta_per_sd"])]
        lines += ["", "Use these to set the evidence-quality weights in `data/methodology/v2.yaml`, re-run "
                  "the held-out evaluation, and publish the new version with this report."]
    else:
        lines += ["", "No weights were fitted: this needs at least 5 rated decks and α ≥ target on "
                  "evidence quality."]
    return "\n".join(lines) + "\n"


__all__ = ["ALPHA_TARGET", "QUESTIONS", "analyse", "build_packet", "engine_features", "krippendorff_alpha",
           "proportional_odds", "spearman", "to_markdown"]
