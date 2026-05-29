"""End-to-end demo: generate a pig-farm-in-Malaysia impact bundle.

1. Calls an OpenAI-compatible chat gateway (default:
   ``https://runanytime.hxi.me/v1/chat/completions``, model
   ``minimax/minimax-m2.7``) for a realistic company profile.
2. Feeds the profile into :class:`ImpactVision` to produce:
     * the main Impact Report HTML  (``pig_farm_impact_report.html``)
     * the IC memo HTML             (``pig_farm_ic_memo.html``)
     * the DD coverage HTML         (``pig_farm_dd_report.html``)
3. If the gateway is unreachable / 504s / returns malformed JSON, the
   script falls back to a pre-written pig-farm profile so the demo
   always produces output.

Run from the repo root::

    $env:PYTHONPATH = "src"
    python examples/generate_pig_farm_reports.py
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from openharness.impact.ic_memo import render_ic_memo_html
from openharness.impact.models import Company
from openharness.impact.report_templates import (
    render_dd_questionnaire_docx,
    render_dd_report_html,
)
from openharness.impact.sdk import ImpactVision

# ---------------------------------------------------------------------------
# 1. AI gateway helpers
# ---------------------------------------------------------------------------

API_URL = os.environ.get("HXI_API_URL", "https://runanytime.hxi.me/v1/chat/completions")
API_KEY = os.environ.get("HXI_API_KEY", "sk-OB3CIBZfVBFB07LerwR5sjVbyoWIbsR6ITiOmSCBTiUN9lZe")
# Primary + fallback chain. The gateway has been observed to 504 on
# some models, so we retry down the list on gateway errors.
MODEL_PRIMARY = os.environ.get("HXI_MODEL", "minimax/minimax-m2.7")
MODEL_FALLBACKS = ["minimax/minimax-m2.5", "z-ai/glm-4.6", "z-ai/glm-4.7", "moonshotai/kimi-k2.5"]

THINK_RE = re.compile(r"<think>.*?</think>", flags=re.DOTALL | re.IGNORECASE)
JSON_RE = re.compile(r"\{.*\}", flags=re.DOTALL)


def _clean(raw: str) -> str:
    """Remove `<think>…</think>` blocks minimax emits in its reply."""
    out = THINK_RE.sub("", raw)
    # some models wrap JSON in ```json … ```
    out = re.sub(r"^```(?:json)?", "", out.strip())
    out = re.sub(r"```$", "", out.strip())
    return out.strip()


def _post(model: str, messages: list[dict], *, max_tokens: int, temperature: float, timeout: int) -> str:
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": False,
    }
    req = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}",
        },
    )
    resp = urllib.request.urlopen(req, timeout=timeout)
    body = json.loads(resp.read())
    choice = (body.get("choices") or [{}])[0]
    msg = choice.get("message") or {}
    return msg.get("content") or ""


def chat(
    messages: list[dict],
    *,
    model: str | None = None,
    max_tokens: int = 3000,
    temperature: float = 0.3,
    timeout: int = 240,
    attempts: int = 3,
) -> str:
    """Resilient chat call with `<think>` stripping and model fallback."""
    models = [model or MODEL_PRIMARY, *MODEL_FALLBACKS]
    last_err: Exception | None = None
    for m in models:
        for attempt in range(1, attempts + 1):
            t0 = time.time()
            try:
                print(f"  [ai] model={m} attempt={attempt} timeout={timeout}s …", flush=True)
                raw = _post(m, messages, max_tokens=max_tokens, temperature=temperature, timeout=timeout)
                cleaned = _clean(raw)
                dt = round(time.time() - t0, 1)
                if not cleaned:
                    print(f"  [ai] empty body after {dt}s — retrying", flush=True)
                    continue
                print(f"  [ai] ok in {dt}s ({len(cleaned)} chars)", flush=True)
                return cleaned
            except Exception as e:  # 504, timeout, SSL, etc.
                dt = round(time.time() - t0, 1)
                last_err = e
                print(f"  [ai] fail in {dt}s: {type(e).__name__} {e}", flush=True)
    raise RuntimeError(f"all AI models failed; last error: {last_err}")


# ---------------------------------------------------------------------------
# 2. Offline-safe profile
# ---------------------------------------------------------------------------

OFFLINE_PROFILE: dict[str, Any] = {
    "name": "Kampung Makmur Pig Farm Sdn Bhd",
    "sector": "agriculture",
    "geography": "Malaysia",
    "description": (
        "Kampung Makmur is a 3,000-sow commercial pig farm in Johor, Malaysia, "
        "operating an integrated breed-to-finish facility with a licensed biogas-to-power "
        "plant. It supplies 45,000 market hogs per year to the Klang Valley through three "
        "halal-adjacent processors and a cold-chain distribution partnership with a regional "
        "retailer. Founded in 2014 by a second-generation farmer, the company has repositioned "
        "itself around animal welfare, antibiotic-stewardship and manure-to-energy circularity "
        "following the regional ASF outbreaks."
    ),
    "impact_themes": [
        "sustainable agriculture", "waste-to-energy", "jobs",
        "animal welfare", "smallholder livelihoods",
    ],
    "sdg_claims": [2, 6, 7, 8, 12, 13],
    "pitch_text": (
        "Kampung Makmur is a 3,000-sow integrated pig farm in Kluang, Johor, serving West "
        "Malaysia's growing protein demand. Since 2022 we have reduced antibiotic use by 62% "
        "through vaccination and group-housing, and replaced 100% of conventional slatted "
        "housing with deep-litter, enrichment-enabled pens benchmarked against the EU "
        "Welfare Quality protocol. Our biogas plant captures methane from manure lagoons and "
        "generates 1.8 GWh of electricity per year, replacing ~920 tonnes CO2e of grid "
        "emissions and cutting our grid electricity purchases by 74%. Effluent is processed "
        "through a 3-stage anaerobic-lagoon + constructed-wetland system; treated water is "
        "reused for flushing. Water withdrawal per kg of live weight dropped 31% versus our "
        "2020 baseline, independently verified by SIRIM. We employ 142 staff, of whom 38% "
        "are women and 64% are from Kluang district; median wage is 42% above the Johor "
        "agricultural minimum and every worker is enrolled in SOCSO and EPF. We run an "
        "outgrower programme with 18 smallholder piggeries, supplying feed and veterinary "
        "support at wholesale cost; participating smallholders report average income uplifts "
        "of RM 1,850 per month (baseline: RM 900). A 2024 randomized pilot with Universiti "
        "Putra Malaysia compared 120 outgrower households to a matched control group and "
        "found 23% higher household food-security scores and 17% higher child school "
        "attendance. We are SEDEX-audited and have a 4-tier grievance mechanism. Risks we "
        "actively manage include: (i) ASF biosecurity — all farms are fenced, SPF breeding "
        "stock, shower-in/out protocol, quarterly third-party audit by the Department of "
        "Veterinary Services; (ii) nutrient run-off during monsoon — on-site retention "
        "ponds sized to 1-in-100-year storm, automated ammonia sensors; (iii) community "
        "odour — a covered-lagoon retrofit was completed in Q3 2025 and the formal "
        "complaints rate has dropped from 14 to 2 per year. Over the next five years we "
        "target: 45% reduction in Scope 1+2 emissions intensity (kg CO2e / kg live weight); "
        "80% of breeding sows in group-housing ≥ 10 weeks after weaning; 35 outgrower "
        "households onboarded; and a SBTi near-term target submission by 2027. We report "
        "against IRIS+, SDG 2/6/7/8/12/13, GRI standards, and have commissioned a first "
        "independent ESG audit for FY2026."
    ),
    "reported_metrics": {},
}


# ---------------------------------------------------------------------------
# 3. AI prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are an impact-investment analyst. When asked, you produce realistic,
quantified company profiles for impact due diligence. You MUST reply with a single JSON
object. No prose, no markdown fences, no commentary — just the JSON. Use concrete numbers
(percent reductions, absolute figures, years, headcounts, tonnes CO2e, etc.) everywhere."""

USER_PROMPT = """Produce a detailed company profile for an impact due-diligence dossier.

Subject: A commercial pig farm in Malaysia that is being evaluated for impact investment.

The farm should be plausible (real-sounding name, real state / district, real scale,
real risks including African Swine Fever, effluent management, animal welfare, community
odour). It should have a credible mix of strengths and gaps so the greenwashing screen has
something to chew on.

Return STRICT JSON with EXACTLY these keys:

{
  "name": "<company name, including 'Sdn Bhd'>",
  "sector": "agriculture",
  "geography": "Malaysia",
  "description": "<120-180 word professional description: location, scale, products, years in operation, unique angle>",
  "impact_themes": ["<4-6 short theme phrases>"],
  "sdg_claims": [<3-6 SDG goal numbers from 1-17>],
  "pitch_text": "<350-500 word narrative the founder might give to an impact LP. MUST include specific numbers: % antibiotic reduction, kWh/MWh/GWh of biogas energy, tonnes CO2e avoided, % water-withdrawal reduction, headcount, % women, % local hires, wage uplift vs minimum, outgrower scheme metrics, one independently-verified outcome study (RCT / quasi-experimental), ASF biosecurity controls, effluent risk mitigation, 5-year targets. Write in first-person plural.>"
}

Return ONLY the JSON. No extra keys. No ``` fences."""


def fetch_profile(*, offline: bool, model: str) -> dict[str, Any]:
    if offline:
        print("[demo] offline mode — using hand-crafted profile", flush=True)
        return OFFLINE_PROFILE
    try:
        raw = chat(
            [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": USER_PROMPT},
            ],
            model=model,
            max_tokens=3000,
            temperature=0.4,
            timeout=240,
            attempts=2,
        )
    except Exception as e:
        print(f"[demo] AI call failed ({e!r}) — falling back to offline profile", flush=True)
        return OFFLINE_PROFILE

    # Extract the first JSON object from the cleaned reply
    m = JSON_RE.search(raw)
    if not m:
        print("[demo] reply did not contain JSON — falling back to offline profile", flush=True)
        print("  --- reply preview ---")
        print(raw[:600])
        return OFFLINE_PROFILE
    try:
        profile = json.loads(m.group(0))
    except json.JSONDecodeError as e:
        print(f"[demo] JSON parse error: {e} — falling back to offline profile", flush=True)
        return OFFLINE_PROFILE

    # Minimal shape validation; fall back on any missing mandatory field
    required = ("name", "description", "pitch_text")
    if not all(profile.get(k) for k in required):
        print("[demo] AI reply missing required keys — falling back to offline profile", flush=True)
        return OFFLINE_PROFILE
    # Fill in defaults for optional keys
    profile.setdefault("sector", "agriculture")
    profile.setdefault("geography", "Malaysia")
    profile.setdefault("impact_themes", [])
    profile.setdefault("sdg_claims", [2, 12, 13])
    profile.setdefault("reported_metrics", {})
    print(f"[demo] AI profile: {profile['name']}", flush=True)
    return profile


# ---------------------------------------------------------------------------
# 4. Report generation
# ---------------------------------------------------------------------------

def assess_and_assemble(profile: dict[str, Any]) -> dict[str, Any]:
    """Run the full assessment pipeline and assemble the ``report_data`` dict.

    Returns a bundle with the company assessment, DD coverage, greenwashing
    screen, IC scorecard/thesis and the assembled ``report_data`` that the
    flagship ``impact_report`` HTML renderer expects. Split out from
    :func:`run` so other demos (e.g. ``DEMO/generate_demo.py``) can reuse the
    identical pipeline without duplicating ~80 lines of assembly.
    """
    # --- Assess the company using the pitch text so the extractor
    #     populates reported_metrics and the downstream engine runs
    #     full 5D + SDG + greenwashing + benchmark.
    iv = ImpactVision()
    comp = Company(
        name=profile["name"],
        sector=profile.get("sector", "agriculture"),
        geography=profile.get("geography", "Malaysia"),
        description=profile.get("description", ""),
        impact_themes=profile.get("impact_themes", []),
        sdg_claims=profile.get("sdg_claims", []),
        reported_metrics=profile.get("reported_metrics", {}),
    )
    pitch = profile["pitch_text"]

    print("[demo] running assessment …", flush=True)
    assess = iv.assess_company_text(
        comp.name,
        text=pitch,
        sector=comp.sector,
        country=comp.geography,
        impact_themes=comp.impact_themes,
    )
    # Re-inject the full company fields (model_dump overwrites description)
    assess.company.description = comp.description or pitch[:1000]
    assess.company.sdg_claims = comp.sdg_claims

    # --- DD + greenwashing so we can feed them into the IC memo
    print("[demo] running DD coverage + greenwashing screen …", flush=True)
    dd = iv.run_dd_coverage(pitch)
    gw = iv.screen_greenwashing(assess.company)

    # --- IC gate using default or repo-provided thesis
    print("[demo] running IC gate …", flush=True)
    thesis = iv.load_thesis()
    scorecard = iv.evaluate_deal_against_thesis(
        assess, thesis=thesis,
        dd_coverage_pct=dd.coverage_pct,
        greenwashing_score=gw.overall_score,
    )
    print(
        f"       gate={scorecard.overall_status.upper()} · DD coverage={dd.coverage_pct:.1f}% "
        f"· GW={gw.overall_score:.1f} ({getattr(gw, 'classification', '')})",
        flush=True,
    )

    # --- Assemble the same report_data shape the MCP `impact_report` tool
    #     builds, so the full stack (executive summary + KPI strip + TOC +
    #     gap analysis + benchmark + pathway + metric tracking + claims)
    #     renders.
    from openharness.impact.benchmarks import compare_to_benchmark
    from openharness.impact.database import get_metric_store
    from openharness.impact.gap_analysis import analyze_gaps
    from openharness.impact.sdg_mapper import generate_sdg_gap_recommendations
    from openharness.tools.impact.impact_report_tool import (
        _infer_opportunities_and_risks,
    )
    # Use the full IRIS+ catalog so missing-metric rows get names,
    # definitions, units, and dimension tags.
    store = get_metric_store()

    sdg_recs = generate_sdg_gap_recommendations(assess.sdg_alignments, assess.company, store)
    sdg_dicts = []
    for a in assess.sdg_alignments:
        d = a.model_dump()
        d["recommendations"] = sdg_recs.get(a.goal, [])
        sdg_dicts.append(d)

    gap_result = analyze_gaps(assess.company, store)

    gw_dump = gw.model_dump()
    gw_dump["sub_scores"] = {
        "claim_metric_gap": gw.claim_metric_gap,
        "adverse_omission": gw.adverse_omission,
        "specificity": gw.specificity,
        "selectivity": gw.selectivity,
        "verification": gw.verification,
    }

    report_data: dict[str, Any] = {
        "company": assess.company.model_dump(),
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "catalog_version": "IRIS+ 5.3c",
        "five_dimensions": assess.five_dimensions.model_dump() if assess.five_dimensions else None,
        "sdg_alignments": sdg_dicts,
        "sdg_alignment": sdg_dicts,  # executive-summary uses the singular key
        "gap_analysis": gap_result,
        "greenwashing": gw_dump,
        "impact_analysis": _infer_opportunities_and_risks(assess.company),
    }
    if report_data["five_dimensions"] and assess.company.sector:
        fd = report_data["five_dimensions"]
        five_d_scores = {
            "what": fd["what"]["score"],
            "who": fd["who"]["score"],
            "how_much": fd["how_much"]["score"],
            "contribution": fd["contribution"]["score"],
            "risk": fd["risk"]["score"],
        }
        bm = compare_to_benchmark(
            assess.company.sector, five_d_scores,
            fd["overall_score"], gap_result["coverage_percentage"],
        )
        if bm.get("benchmark_available"):
            report_data["benchmark_comparison"] = bm

    return {
        "comp": comp,
        "assess": assess,
        "dd": dd,
        "gw": gw,
        "thesis": thesis,
        "scorecard": scorecard,
        "report_data": report_data,
    }


def run(profile: dict[str, Any], out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)

    from openharness.tools.impact.impact_report_tool import _to_html

    bundle = assess_and_assemble(profile)
    comp = bundle["comp"]
    assess = bundle["assess"]
    dd = bundle["dd"]
    gw = bundle["gw"]
    thesis = bundle["thesis"]
    scorecard = bundle["scorecard"]
    report_data = bundle["report_data"]

    # --- Render the three HTML reports
    print("[demo] rendering HTML reports …", flush=True)

    impact_path = out_dir / "pig_farm_impact_report.html"
    impact_path.write_text(_to_html(report_data), encoding="utf-8")

    # (b) IC memo HTML
    ic_html = render_ic_memo_html(
        assess, scorecard, thesis,
        dd_coverage_pct=dd.coverage_pct,
        greenwashing_score=gw.overall_score,
        greenwashing_classification=getattr(gw, "classification", None),
        deal_size_eur_m=12.0,
    )
    ic_path = out_dir / "pig_farm_ic_memo.html"
    ic_path.write_text(ic_html, encoding="utf-8")

    # (c) DD coverage HTML
    dd_html = render_dd_report_html(
        dd,
        company_name=comp.name,
        document_label="Founder pitch narrative",
        reviewer="Impact Vision demo",
    )
    dd_path = out_dir / "pig_farm_dd_report.html"
    dd_path.write_text(dd_html, encoding="utf-8")

    # (d) DD questionnaire as editable Word (.docx), if python-docx is installed
    paths = [impact_path, ic_path, dd_path]
    dd_docx_path = out_dir / "pig_farm_dd_questionnaire.docx"
    try:
        render_dd_questionnaire_docx(
            dd,
            dd_docx_path,
            company_name=comp.name,
            document_label="Founder pitch narrative",
            reviewer="Impact Vision demo",
        )
        paths.append(dd_docx_path)
    except ImportError as exc:
        print(f"[demo] skipping DD .docx export: {exc}")

    return paths


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true", help="skip the AI call and use the bundled profile")
    parser.add_argument("--model", default=MODEL_PRIMARY, help=f"model id (default: {MODEL_PRIMARY})")
    parser.add_argument("--out-dir", default="examples/output", help="output folder")
    parser.add_argument("--profile", help="reuse a previously-generated profile JSON instead of calling the AI")
    args = parser.parse_args(argv)

    out_dir = (REPO_ROOT / args.out_dir).resolve() if not os.path.isabs(args.out_dir) else Path(args.out_dir)

    print(f"[demo] output folder: {out_dir}", flush=True)
    if args.profile:
        p = Path(args.profile)
        profile = json.loads(p.read_text(encoding="utf-8"))
        print(f"[demo] reusing cached profile: {p} ({profile.get('name', 'unknown')})", flush=True)
    else:
        profile = fetch_profile(offline=args.offline, model=args.model)
    # Archive the profile alongside the HTML so the run is reproducible
    (out_dir / "pig_farm_profile.json").parent.mkdir(parents=True, exist_ok=True)
    (out_dir / "pig_farm_profile.json").write_text(
        json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8",
    )

    paths = run(profile, out_dir)
    print()
    print("[demo] done — generated:")
    for p in paths:
        print(f"  {p}  ({p.stat().st_size:,} bytes)")
    print(f"  {out_dir / 'pig_farm_profile.json'}  (input profile)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
