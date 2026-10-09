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

import yaml

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


def corpus_paths() -> list[Path]:
    """The study corpus listed in ``data/calibration/manifest.yaml`` (held-out decks excluded)."""
    from impact_vision.impact._paths import data_path

    manifest = data_path("calibration/manifest.yaml")
    root = manifest.parents[2]  # repository root: paths in the manifest are repo-relative
    doc = yaml.safe_load(manifest.read_text(encoding="utf-8"))
    return [root / d["path"] for d in doc["decks"] if (root / d["path"]).exists()]


def build_packet(decks: Sequence[str | Path], out_dir: str | Path, *, raters: Sequence[str] = ("A", "B", "C"),
                 score: bool = True, seed: int = 2026) -> dict[str, Any]:
    """Build the study folder.

    ``rater_kit/`` is what raters receive: ``decks/`` under neutral IDs in a
    shuffled order, ``rate.html`` (an offline rating form that exports their
    sheet), ``GUIDE.md`` and a spreadsheet template. ``coordinator/`` stays with
    the study lead: the engine's scores and the key from IDs to source files.
    Filled sheets go back into ``returned/``.
    """
    import random

    out = Path(out_dir)
    kit, coord = out / "rater_kit", out / "coordinator"
    (kit / "decks").mkdir(parents=True, exist_ok=True)
    coord.mkdir(parents=True, exist_ok=True)
    (out / "returned").mkdir(exist_ok=True)
    sources = sorted(Path(d) for d in decks if Path(d).suffix.lower() in SUPPORTED)
    random.Random(seed).shuffle(sources)  # neighbours shouldn't share a batch, sector or quality
    names = []
    for i, deck in enumerate(sources, 1):
        name = f"D{i:03d}{deck.suffix.lower()}"  # neutral IDs: the file name mustn't hint at the answer
        shutil.copyfile(deck, kit / "decks" / name)
        names.append((name, deck))
    with open(kit / "ratings_TEMPLATE.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["deck", "rater", *QUESTIONS, "minutes", "notes"])
        for name, _ in names:
            w.writerow([name, "", *([""] * len(QUESTIONS)), "", ""])
    guide = ["# Rating guide", "",
             "Open `rate.html` in a browser. Enter your rater ID, read each deck, and answer the questions. "
             "Your answers are saved in the browser as you go. When you finish, press **Download my ratings** "
             "and send the CSV back to the study lead.", "",
             "Rate each deck on its own. Don't look at Impact Vision's output and don't discuss decks with the "
             "other raters. Leave an answer blank if you can't tell. A deck takes about 10–15 minutes.", "",
             "## Questions", ""]
    guide += [f"- **{key}**: {q['label']}" for key, q in QUESTIONS.items()]
    guide += ["", "Prefer a spreadsheet? Fill in `ratings_TEMPLATE.csv` (put your rater ID in the `rater` "
              "column) and send it back instead."]
    (kit / "GUIDE.md").write_text("\n".join(guide) + "\n", encoding="utf-8")
    (kit / "rate.html").write_text(rating_form([(name, kit / "decks" / name) for name, _ in names]),
                                   encoding="utf-8")
    with open(coord / "key.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["deck", "source"])
        w.writerows([(name, str(src)) for name, src in names])
    if score:
        rows = [{"deck": name, "source": str(src), **engine_features(src)} for name, src in names]
        if rows:
            with open(coord / "engine_scores.csv", "w", newline="", encoding="utf-8") as fh:
                dw = csv.DictWriter(fh, fieldnames=list(rows[0]))
                dw.writeheader()
                dw.writerows(rows)
    return {"decks": len(names), "raters": list(raters), "folder": str(out), "rater_kit": str(kit)}


def rating_form(decks: Sequence[tuple[str, Path]]) -> str:
    """A self-contained, offline rating form (no network, no external files except the decks)."""
    import html
    import json

    items = []
    for name, path in decks:
        text = path.read_text(encoding="utf-8", errors="replace") if path.suffix in (".md", ".txt") else ""
        items.append({"id": name, "text": text, "file": f"decks/{name}"})
    payload = json.dumps({"decks": items, "questions": QUESTIONS}, ensure_ascii=False).replace("</", "<\\/")
    return _FORM.replace("__DATA__", payload).replace("__COUNT__", html.escape(str(len(items))))


_FORM = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Deck rating</title>
<style>
:root{--bg:#fafaf8;--card:#fff;--ink:#1d1d1b;--muted:#6b6b66;--line:#e2e1dc;--brand:#1f5f8b;--ok:#2e7d4f}
@media (prefers-color-scheme:dark){:root{--bg:#161616;--card:#202020;--ink:#ececea;--muted:#a3a39e;--line:#3a3a38;--brand:#79b4dc;--ok:#7fcf9c}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,sans-serif}
header{position:sticky;top:0;background:var(--card);border-bottom:1px solid var(--line);padding:10px 16px;display:flex;gap:12px;flex-wrap:wrap;align-items:center;z-index:2}
header h1{font-size:16px;margin:0 12px 0 0}input,select,textarea,button{font:inherit;color:inherit}
input,select,textarea{background:var(--card);border:1px solid var(--line);border-radius:6px;padding:6px 8px}
button{border:0;border-radius:6px;padding:7px 12px;background:var(--brand);color:var(--card);cursor:pointer}
button.ghost{background:transparent;color:var(--brand);border:1px solid var(--line)}
main{display:grid;grid-template-columns:220px 1fr;gap:16px;padding:16px;max-width:1300px;margin:0 auto}
nav{max-height:calc(100vh - 90px);overflow:auto;position:sticky;top:70px}nav a{display:flex;justify-content:space-between;padding:4px 8px;border-radius:6px;color:var(--ink);text-decoration:none}
nav a.on{background:var(--line)}nav a .done{color:var(--ok)}
.deck{display:grid;grid-template-columns:minmax(0,1.3fr) minmax(280px,1fr);gap:16px}
.text{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:16px;white-space:pre-wrap;max-height:calc(100vh - 110px);overflow:auto}
form{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:16px;align-self:start}
label{display:block;margin:0 0 12px}label span{display:block;font-weight:600;margin-bottom:4px}
.scale{display:flex;gap:6px}.scale label{display:flex;align-items:center;gap:3px;margin:0;font-weight:400}
.muted{color:var(--muted);font-size:13px}
@media (max-width:760px){main{grid-template-columns:1fr}nav{position:static;max-height:none;display:flex;flex-wrap:wrap}.deck{grid-template-columns:1fr}}
</style></head><body>
<header><h1>Deck rating · __COUNT__ decks</h1>
<label style="margin:0">Rater ID <input id="rater" size="6" placeholder="A"></label>
<span id="progress" class="muted"></span><span style="flex:1"></span>
<button class="ghost" id="prev" type="button">← Previous</button><button class="ghost" id="next" type="button">Next →</button>
<button id="export" type="button">Download my ratings</button></header>
<main><nav id="nav" aria-label="Decks"></nav><section id="deck" class="deck"></section></main>
<script type="application/json" id="data">__DATA__</script>
<script>
const DATA = JSON.parse(document.getElementById('data').textContent);
const Q = DATA.questions, KEYS = Object.keys(Q);
let i = 0, store = {};
const $ = (s) => document.querySelector(s);
const key = () => 'iv-rating-' + ($('#rater').value.trim() || 'anon');
function load() { try { store = JSON.parse(localStorage.getItem(key()) || '{}'); } catch (e) { store = {}; } }
function save() { try { localStorage.setItem(key(), JSON.stringify(store)); } catch (e) { /* private mode: export often */ } }
function done(id) { const r = store[id] || {}; return KEYS.every((k) => r[k]); }
function nav() {
  $('#nav').replaceChildren(...DATA.decks.map((d, n) => {
    const a = document.createElement('a'); a.href = '#'; a.className = n === i ? 'on' : '';
    a.append(d.id.replace(/\.\w+$/, '')); const s = document.createElement('span'); s.className = 'done'; s.textContent = done(d.id) ? '✓' : '';
    a.append(s); a.onclick = (e) => { e.preventDefault(); i = n; show(); }; return a; }));
  $('#progress').textContent = DATA.decks.filter((d) => done(d.id)).length + ' / ' + DATA.decks.length + ' rated';
}
function show() {
  const d = DATA.decks[i], r = store[d.id] || {};
  const text = document.createElement('div'); text.className = 'text';
  if (d.text) text.textContent = d.text; else { const a = document.createElement('a'); a.href = d.file; a.target = '_blank'; a.textContent = 'Open ' + d.id + ' (opens in a new tab)'; text.append(a); }
  const form = document.createElement('form');
  const h = document.createElement('h2'); h.textContent = d.id.replace(/\.\w+$/, ''); h.style.marginTop = '0'; form.append(h);
  for (const k of KEYS) {
    const q = Q[k], lab = document.createElement('label'), t = document.createElement('span'); t.textContent = q.label; lab.append(t);
    const box = document.createElement('div'); box.className = 'scale';
    for (const v of q.scale) {
      const o = document.createElement('label'), inp = document.createElement('input');
      inp.type = 'radio'; inp.name = k; inp.value = v; inp.checked = String(r[k]) === String(v);
      inp.onchange = () => { (store[d.id] = store[d.id] || {})[k] = v; save(); nav(); };
      o.append(inp, String(v).replace('_', ' ')); box.append(o);
    }
    lab.append(box); form.append(lab);
  }
  for (const [k, label, tag] of [['minutes', 'Minutes spent', 'input'], ['notes', 'Notes (optional)', 'textarea']]) {
    const lab = document.createElement('label'), t = document.createElement('span'); t.textContent = label;
    const f = document.createElement(tag); if (tag === 'input') { f.inputMode = 'numeric'; f.size = 4; } else { f.rows = 3; f.style.width = '100%'; }
    f.value = r[k] || ''; f.oninput = () => { (store[d.id] = store[d.id] || {})[k] = f.value; save(); };
    lab.append(t, f); form.append(lab);
  }
  $('#deck').replaceChildren(text, form); nav(); window.scrollTo(0, 0);
}
function csv(v) { v = String(v == null ? '' : v); return /[",\n]/.test(v) ? '"' + v.replace(/"/g, '""') + '"' : v; }
$('#export').onclick = () => {
  const rater = $('#rater').value.trim(); if (!rater) { alert('Enter your rater ID first.'); $('#rater').focus(); return; }
  const rows = [['deck', 'rater', ...KEYS, 'minutes', 'notes']];
  for (const d of DATA.decks) { const r = store[d.id] || {}; rows.push([d.id, rater, ...KEYS.map((k) => r[k] || ''), r.minutes || '', r.notes || '']); }
  const blob = new Blob([rows.map((r) => r.map(csv).join(',')).join('\n') + '\n'], {type: 'text/csv'});
  const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = 'ratings_' + rater.replace(/[^\w-]/g, '_') + '.csv'; a.click();
};
$('#rater').onchange = () => { try { localStorage.setItem('iv-rating-rater', $('#rater').value.trim()); } catch (e) {} load(); show(); };
$('#prev').onclick = () => { i = Math.max(0, i - 1); show(); };
$('#next').onclick = () => { i = Math.min(DATA.decks.length - 1, i + 1); show(); };
try { $('#rater').value = localStorage.getItem('iv-rating-rater') || ''; } catch (e) {}
load(); show();
</script></body></html>
"""


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
                rater = (row.get("rater") or "").strip()
                answers = {q: (row.get(q) or "").strip() for q in QUESTIONS}
                if rater and any(answers.values()):
                    out[row["deck"]][rater] = answers
    return out


def analyse(packet: str | Path) -> dict[str, Any]:
    folder = Path(packet)
    sheets = [p for p in sorted(folder.rglob("ratings_*.csv")) if p.name != "ratings_TEMPLATE.csv"]
    ratings = _read_ratings(sheets)
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
    scores = folder / "coordinator" / "engine_scores.csv"
    if not scores.exists():
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
