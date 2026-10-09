"""Expert calibration toolkit (roadmap v8 W2.6)."""
from __future__ import annotations

import csv
import math
import random
from pathlib import Path

import pytest

from impact_vision.impact.calibration import (
    analyse,
    build_packet,
    krippendorff_alpha,
    proportional_odds,
    spearman,
    to_markdown,
)

# Krippendorff (2011) "Computing Krippendorff's Alpha-Reliability", worked example:
# 4 observers × 12 units, with missing values.
K = [
    [1, 2, 3, 3, 2, 1, 4, 1, 2, None, None, None],
    [1, 2, 3, 3, 2, 2, 4, 1, 2, 5, None, 3],
    [None, 3, 3, 3, 2, 3, 4, 2, 2, 5, 1, None],
    [1, 2, 3, 3, 2, 4, 4, 1, 2, 5, 1, None],
]
UNITS = [list(col) for col in zip(*K)]


@pytest.mark.parametrize("level,expected", [("nominal", 0.743), ("ordinal", 0.815), ("interval", 0.849),
                                            ("ratio", 0.797)])
def test_alpha_matches_the_published_example(level, expected):
    assert krippendorff_alpha(UNITS, level) == pytest.approx(expected, abs=0.001)


def test_alpha_edge_cases():
    assert krippendorff_alpha([[1, 1], [2, 2], [3, 3]]) == 1.0
    assert math.isnan(krippendorff_alpha([[1, None], [None, 2]]))


def test_proportional_odds_recovers_the_signal():
    rng = random.Random(7)
    x, y = [], []
    for _ in range(120):
        strong, noise = rng.gauss(0, 1), rng.gauss(0, 1)
        latent = 1.5 * strong + rng.gauss(0, 0.5)
        y.append(1 + sum(latent > c for c in (-1.0, 0.0, 1.0)))
        x.append([strong, noise])
    fit = proportional_odds(x, y)
    assert fit["beta_per_sd"][0] > 1.0 and abs(fit["beta_per_sd"][1]) < 0.4
    assert fit["thresholds"] == sorted(fit["thresholds"])


def test_spearman():
    assert spearman([1, 2, 3, 4], [10, 20, 30, 40]) == 1.0
    assert spearman([1, 2, 3, 4], [4, 3, 2, 1]) == -1.0


def test_packet_to_report(tmp_path):
    decks = sorted((Path(__file__).parent / "golden_decks").glob("*.md"))[:6]
    info = build_packet(decks, tmp_path / "pack", raters=("A", "B"))
    kit, coord = tmp_path / "pack" / "rater_kit", tmp_path / "pack" / "coordinator"
    assert info["decks"] == 6 and (kit / "GUIDE.md").exists() and (kit / "rate.html").exists()
    assert sorted(p.name for p in (kit / "decks").iterdir())[0] == "D001.md"  # neutral IDs
    assert not list(kit.rglob("engine_scores.csv")) and (coord / "engine_scores.csv").exists()
    html = (kit / "rate.html").read_text()
    assert "Download my ratings" in html and "<script src" not in html and "</script><script" not in html.split("id=\"data\">")[1][:50]
    engine = {r["deck"]: r for r in csv.DictReader(open(coord / "engine_scores.csv"))}
    template = list(csv.DictReader(open(kit / "ratings_TEMPLATE.csv")))
    for rater in ("A", "B"):  # two raters who agree closely, and follow the evidence score
        rows = []
        for row in template:
            eq = float(engine[row["deck"]]["evidence_quality"])
            rows.append({**row, "rater": rater, "evidence_quality": str(max(1, min(5, int(eq // 10) - 2))),
                         "impact_magnitude": "3", "contribution": "3", "greenwashing_risk": "2",
                         "verdict": engine[row["deck"]]["verdict"]})
        with open(tmp_path / "pack" / "returned" / f"ratings_{rater}.csv", "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
    result = analyse(tmp_path / "pack")
    assert result["raters"] == ["A", "B"]  # the blank template is ignored
    assert result["alpha"]["evidence_quality"] == 1.0
    assert result["comparisons"]["verdict"]["agreement"] == 1.0
    assert result["comparisons"]["evidence_quality"]["spearman"] > 0.9
    md = to_markdown(result)
    assert "Krippendorff" in md and "evidence_quality" in md


def test_the_study_corpus_excludes_the_held_out_set():
    from impact_vision.impact.calibration import corpus_paths

    paths = corpus_paths()
    assert len(paths) >= 50
    assert not any("heldout" in str(p) for p in paths)
