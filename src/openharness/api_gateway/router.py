"""FastAPI REST endpoints for Impact Vision core tools.

Usage:
    pip install fastapi uvicorn
    uvicorn openharness.api_gateway.router:app --reload

Endpoints:
    POST /api/v1/score          - 5-Dimension impact scoring
    POST /api/v1/sdg-map        - SDG alignment mapping
    POST /api/v1/data-quality   - Metric data quality assessment
    POST /api/v1/greenwashing   - Greenwashing risk detection
    POST /api/v1/gap-analysis   - Core metric gap analysis
    POST /api/v1/validate       - Metric data validation pipeline
    POST /api/v1/webhook        - Register metric update webhook
    GET  /api/v1/health         - Health check
"""

from __future__ import annotations

import logging
from typing import Any

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
except ImportError:
    raise ImportError(
        "FastAPI is required for the REST API gateway. "
        "Install with: pip install fastapi uvicorn"
    )

from pydantic import BaseModel, Field

from openharness.impact.database import get_metric_store
from openharness.impact.five_dimensions import assess_five_dimensions
from openharness.impact.gap_analysis import analyze_gaps
from openharness.impact.greenwashing import assess_greenwashing
from openharness.impact.models import Company
from openharness.impact.sdg_mapper import map_sdg_alignment
from openharness.tools.impact.common import infer_themes, normalize_metric_map, normalize_sdg_goals

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Impact Vision API",
    description="AI-powered impact measurement and SDG alignment API",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CompanyRequest(BaseModel):
    company_name: str
    company_description: str = ""
    sector: str = ""
    geography: str = ""
    impact_themes: list[str] = Field(default_factory=list)
    reported_metrics: dict[str, str] = Field(default_factory=dict)
    sdg_claims: list[int] = Field(default_factory=list)


class MetricValidationRequest(BaseModel):
    metrics: dict[str, Any] = Field(description="Metric ID -> value mapping to validate")
    sector: str = ""


class WebhookRegistration(BaseModel):
    url: str = Field(description="Webhook callback URL")
    events: list[str] = Field(
        default_factory=lambda: ["metric_update"],
        description="Events to subscribe to: metric_update, score_change, threshold_breach",
    )
    company_name: str = ""


_webhooks: list[dict] = []


def _build_company(req: CompanyRequest) -> Company:
    reported_metrics, _ = normalize_metric_map(req.reported_metrics)
    sdg_claims, _ = normalize_sdg_goals(req.sdg_claims)
    return Company(
        name=req.company_name,
        description=req.company_description,
        sector=req.sector,
        geography=req.geography,
        impact_themes=infer_themes(f"{req.company_description} {req.sector}", req.impact_themes),
        reported_metrics=reported_metrics,
        sdg_claims=sdg_claims,
    )


@app.get("/api/v1/health")
async def health():
    return {"status": "ok", "version": "0.2.0", "engine": "impact-vision"}


@app.post("/api/v1/score")
async def score_company(req: CompanyRequest):
    try:
        store = get_metric_store()
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))

    company = _build_company(req)
    result = assess_five_dimensions(company, store)
    return {
        "company": req.company_name,
        "overall_score": result.overall_score,
        "overall_grade": result.overall_grade,
        "overall_provenance": result.overall_provenance,
        "dimensions": {
            dim: {
                "score": getattr(result, dim).score,
                "provenance": getattr(result, dim).provenance,
                "metrics_reported": getattr(result, dim).metrics_reported,
            }
            for dim in ("what", "who", "how_much", "contribution", "risk")
        },
    }


@app.post("/api/v1/sdg-map")
async def sdg_map(req: CompanyRequest):
    try:
        store = get_metric_store()
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))

    company = _build_company(req)
    alignments = map_sdg_alignment(company, store)
    return {
        "company": req.company_name,
        "alignments": [
            {
                "goal": a.goal,
                "goal_name": a.goal_name,
                "score": a.score,
                "confidence": a.confidence,
                "provenance": a.provenance,
                "matched_metrics": a.matched_metrics,
            }
            for a in alignments
            if a.score > 0
        ],
    }


@app.post("/api/v1/data-quality")
async def data_quality(req: CompanyRequest):
    try:
        store = get_metric_store()
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))

    metrics = req.reported_metrics
    unknown_ids = [mid for mid in metrics if store.get(mid) is None]
    placeholder_values = [mid for mid, val in metrics.items() if str(val).strip().lower() in ("tbd", "n/a", "na", "pending", "")]

    total = len(metrics)
    valid = total - len(unknown_ids) - len(placeholder_values)
    quality_score = round((valid / total) * 100, 1) if total > 0 else 0

    return {
        "company": req.company_name,
        "total_metrics": total,
        "valid_metrics": valid,
        "unknown_ids": unknown_ids,
        "placeholder_values": placeholder_values,
        "quality_score": quality_score,
    }


@app.post("/api/v1/greenwashing")
async def greenwashing_check(req: CompanyRequest):
    company = _build_company(req)
    result = assess_greenwashing(company)
    return {
        "company": req.company_name,
        "overall_score": result.overall_score,
        "classification": result.classification,
        "flags": result.flags,
        "sub_scores": {
            "claim_metric_gap": result.claim_metric_gap,
            "adverse_omission": result.adverse_omission,
            "specificity": result.specificity,
            "selectivity": result.selectivity,
            "verification": result.verification,
        },
        "recommendations": result.recommendations,
    }


@app.post("/api/v1/gap-analysis")
async def gap_analysis(req: CompanyRequest):
    try:
        store = get_metric_store()
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))

    company = _build_company(req)
    result = analyze_gaps(company, store)
    return {
        "company": req.company_name,
        "coverage_percentage": result["coverage_percentage"],
        "metrics_reported": result["metrics_reported"],
        "metrics_missing": result["metrics_missing"],
        "recommendations": result.get("recommendations", []),
    }


@app.post("/api/v1/validate")
async def validate_metrics(req: MetricValidationRequest):
    """Data validation pipeline for incoming metric data."""
    try:
        store = get_metric_store()
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))

    issues: list[dict] = []
    valid_count = 0
    for mid, val in req.metrics.items():
        metric_def = store.get(mid)
        if metric_def is None:
            issues.append({"metric_id": mid, "issue": "unknown_metric_id", "severity": "error"})
            continue
        val_str = str(val).strip()
        if val_str.lower() in ("tbd", "n/a", "na", "pending", ""):
            issues.append({"metric_id": mid, "issue": "placeholder_value", "severity": "warning", "value": val_str})
            continue
        try:
            float(val_str.replace(",", "").replace("%", ""))
            valid_count += 1
        except ValueError:
            if len(val_str) < 500:
                valid_count += 1
            else:
                issues.append({"metric_id": mid, "issue": "invalid_format", "severity": "warning", "value": val_str[:100]})

    return {
        "total": len(req.metrics),
        "valid": valid_count,
        "issues_count": len(issues),
        "issues": issues,
        "passed": len(issues) == 0,
    }


@app.post("/api/v1/webhook")
async def register_webhook(reg: WebhookRegistration):
    """Register a webhook for metric update events."""
    _webhooks.append({
        "url": reg.url,
        "events": reg.events,
        "company_name": reg.company_name,
    })
    return {
        "status": "registered",
        "webhook_id": len(_webhooks),
        "url": reg.url,
        "events": reg.events,
        "note": "Webhooks will be triggered when matching events occur during tool execution.",
    }


@app.get("/api/v1/webhooks")
async def list_webhooks():
    return {"webhooks": _webhooks}
