"""FastAPI REST endpoints for Impact Vision — full tool coverage.

Usage:
    pip install fastapi uvicorn
    uvicorn openharness.api_gateway.router:app --reload

Endpoints (v1):
    GET  /api/v1/health               - Health check
    POST /api/v1/score                - 5-Dimension impact scoring
    POST /api/v1/sdg-map              - SDG alignment mapping
    POST /api/v1/data-quality         - Metric data quality assessment
    POST /api/v1/greenwashing         - Greenwashing risk detection
    POST /api/v1/gap-analysis         - Core metric gap analysis
    POST /api/v1/validate             - Metric data validation pipeline
    POST /api/v1/framework            - Multi-framework ESG assessment
    POST /api/v1/cross-reference      - Cross-framework metric lookup
    POST /api/v1/risk-opportunity     - Impact risk/opportunity assessment
    POST /api/v1/metric-recommend     - IRIS+ metric recommendations
    POST /api/v1/exclusion-screen     - Exclusion criteria screening
    POST /api/v1/report               - Impact report generation
    POST /api/v1/pitch-deck           - Pitch deck analysis
    POST /api/v1/ddq-export           - LP DDQ export
    POST /api/v1/pipeline             - Pipeline management
    POST /api/v1/monitoring           - Continuous monitoring
    POST /api/v1/improvement-advisor  - Improvement recommendations
    POST /api/v1/narrative            - Narrative generation
    POST /api/v1/batch                - Batch multi-company assessment
    POST /api/v1/webhook              - Register webhook
    GET  /api/v1/webhooks             - List webhooks
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import secrets
import time
import uuid
from pathlib import Path
from typing import Any

try:
    from fastapi import Depends, FastAPI, HTTPException, Request
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
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


def _parse_cors_origins(raw: str | None) -> list[str]:
    """Parse comma-separated CORS origins, defaulting to local/dev openness."""
    origins = [item.strip() for item in (raw or "").split(",") if item.strip()]
    return origins or ["*"]


_CORS_ORIGINS = _parse_cors_origins(os.environ.get("IMPACT_VISION_CORS_ORIGINS"))
_CORS_ALLOW_CREDENTIALS = "*" not in _CORS_ORIGINS


app = FastAPI(
    title="Impact Vision API",
    description=(
        "AI-powered impact measurement and SDG alignment API for "
        "VC and impact investment funds. 26+ endpoints covering "
        "5-Dimension scoring, SDG mapping, greenwashing detection, "
        "pipeline management, and comprehensive impact reporting."
    ),
    version="0.15.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_credentials=_CORS_ALLOW_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Authentication (API Key)
# ---------------------------------------------------------------------------

_API_KEY = os.environ.get("IMPACT_VISION_API_KEY", "")
_bearer_scheme = HTTPBearer(auto_error=False)


async def verify_api_key(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> None:
    """Verify API key if IMPACT_VISION_API_KEY env var is set."""
    if not _API_KEY:
        return
    if request.url.path == "/api/v1/health":
        return
    token = credentials.credentials if credentials else request.headers.get("x-api-key", "")
    if not token or not secrets.compare_digest(token, _API_KEY):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


# ---------------------------------------------------------------------------
# Request/Response Models
# ---------------------------------------------------------------------------


class CompanyRequest(BaseModel):
    company_name: str
    company_description: str = ""
    sector: str = ""
    geography: str = ""
    impact_themes: list[str] = Field(default_factory=list)
    reported_metrics: dict[str, str] = Field(default_factory=dict)
    sdg_claims: list[int] = Field(default_factory=list)


class FrameworkRequest(BaseModel):
    framework: str = Field(description="Framework ID: gri, sasb, tcfd, sfdr, edci, unpri, issb_s1, issb_s2, esrs, opim, all")
    company_name: str = ""
    company_description: str = ""
    sector: str = ""
    reported_metrics: dict[str, str] = Field(default_factory=dict)


class CrossReferenceRequest(BaseModel):
    action: str = "lookup"
    metric_id: str = ""
    standard: str = "any"
    framework: str = ""
    concept: str = ""


class ReportRequest(CompanyRequest):
    impact_targets: dict[str, str] | list[dict[str, Any]] = Field(default_factory=dict)
    metric_history: list[dict[str, Any]] = Field(default_factory=list)
    impact_claims: list[dict[str, Any]] = Field(default_factory=list)
    output_format: str = Field(default="json", description="Output format: text, html, csv, json, xlsx, pdf")
    report_type: str = Field(default="full", description="Report type: full, target_progress, lp_ready")


class PipelineRequest(BaseModel):
    action: str = Field(description="Action: add, update, list, get, delete, transition, history, summary")
    company_name: str = ""
    stage: str = ""
    sector: str = ""
    notes: str = ""
    priority: str = "medium"
    sdg_focus: list[int] = Field(default_factory=list)


class MonitoringRequest(BaseModel):
    action: str = Field(description="Action: set_schedule, get_schedule, list_due, record_metric, check_alerts, reassess, dashboard")
    company_name: str = ""
    metric_id: str = ""
    value: float | str | None = None
    frequency: str = "quarterly"


class MetricValidationRequest(BaseModel):
    metrics: dict[str, Any] = Field(description="Metric ID -> value mapping to validate")
    sector: str = ""


class NarrativeRequest(BaseModel):
    section: str = Field(default="executive_summary", description="Section: executive_summary, key_findings, impact_narrative, case_study, full")
    company_name: str = ""
    company_description: str = ""
    sector: str = ""
    reported_metrics: dict[str, str] = Field(default_factory=dict)
    audience: str = "investor"


class BatchRequest(BaseModel):
    companies: list[CompanyRequest]
    analyses: list[str] = Field(
        default_factory=lambda: ["score"],
        description="Analyses to run: score, sdg_map, greenwashing, gap_analysis, risk_opportunity",
    )


class WebhookRegistration(BaseModel):
    url: str = Field(description="Webhook callback URL")
    events: list[str] = Field(
        default_factory=lambda: ["metric_update"],
        description="Events: metric_update, score_change, threshold_breach, assessment_complete, alert_fired",
    )
    company_name: str = ""
    secret: str = Field(default="", description="Optional HMAC secret for webhook signature verification")


_webhooks: list[dict] = []
_batch_jobs: dict[str, dict] = {}


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


def _get_tool_context():
    from openharness.tools.base import ToolExecutionContext
    return ToolExecutionContext(cwd=Path.cwd())


def _coerce_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


async def _fire_webhooks(event: str, payload: dict) -> None:
    """Fire registered webhooks for an event (best-effort, non-blocking)."""
    try:
        import httpx
    except ImportError:
        return
    for wh in _webhooks:
        if event not in wh["events"]:
            continue
        if wh.get("company_name") and wh["company_name"] != payload.get("company", ""):
            continue
        body = {"event": event, "timestamp": time.time(), "data": payload}
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if wh.get("secret"):
            import json as _json
            sig = hashlib.sha256((wh["secret"] + _json.dumps(body, sort_keys=True)).encode()).hexdigest()
            headers["X-Webhook-Signature"] = sig
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                await client.post(wh["url"], json=body, headers=headers)
        except Exception as exc:
            logger.warning("Webhook delivery failed for %s: %s", wh["url"], exc)


# ---------------------------------------------------------------------------
# Core Endpoints
# ---------------------------------------------------------------------------


@app.get("/api/v1/health")
async def health():
    return {"status": "ok", "version": "0.14.0", "engine": "impact-vision", "tools": 26}


@app.post("/api/v1/score", dependencies=[Depends(verify_api_key)])
async def score_company(req: CompanyRequest):
    try:
        store = get_metric_store()
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))

    company = _build_company(req)
    result = assess_five_dimensions(company, store)
    payload = {
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
    await _fire_webhooks("score_change", payload)
    return payload


@app.post("/api/v1/sdg-map", dependencies=[Depends(verify_api_key)])
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


@app.post("/api/v1/data-quality", dependencies=[Depends(verify_api_key)])
async def data_quality(req: CompanyRequest):
    try:
        store = get_metric_store()
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))

    metrics = req.reported_metrics
    unknown_ids = [mid for mid in metrics if store.get(mid) is None]
    placeholder_values = [
        mid for mid, val in metrics.items()
        if str(val).strip().lower() in ("tbd", "n/a", "na", "pending", "")
    ]

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


@app.post("/api/v1/greenwashing", dependencies=[Depends(verify_api_key)])
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


@app.post("/api/v1/gap-analysis", dependencies=[Depends(verify_api_key)])
async def gap_analysis_endpoint(req: CompanyRequest):
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


@app.post("/api/v1/validate", dependencies=[Depends(verify_api_key)])
async def validate_metrics(req: MetricValidationRequest):
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


# ---------------------------------------------------------------------------
# New Endpoints (Phase 10)
# ---------------------------------------------------------------------------


@app.post("/api/v1/framework", dependencies=[Depends(verify_api_key)])
async def framework_assess(req: FrameworkRequest):
    from openharness.tools.impact.framework_tool import FrameworkInput, FrameworkTool

    tool = FrameworkTool()
    args = FrameworkInput(
        framework=req.framework,
        company_name=req.company_name,
        description=req.company_description,
        sector=req.sector,
        reported_metrics=req.reported_metrics,
    )
    result = await tool.execute(args, _get_tool_context())
    if result.is_error:
        raise HTTPException(status_code=400, detail=result.output)
    return {"result": result.output, "metadata": result.metadata}


@app.post("/api/v1/cross-reference", dependencies=[Depends(verify_api_key)])
async def cross_reference_endpoint(req: CrossReferenceRequest):
    from openharness.tools.impact.cross_reference_tool import CrossReferenceInput, CrossReferenceTool

    tool = CrossReferenceTool()
    normalized_action = req.action
    if req.concept and not req.metric_id and req.action == "lookup":
        normalized_action = "search"
    args = CrossReferenceInput(
        action=normalized_action,
        metric_id=req.metric_id,
        standard=req.standard if req.standard != "any" else req.framework or "any",
        query=req.concept,
    )
    result = await tool.execute(args, _get_tool_context())
    return {"result": result.output}


@app.post("/api/v1/risk-opportunity", dependencies=[Depends(verify_api_key)])
async def risk_opportunity(req: CompanyRequest):
    from openharness.tools.impact.impact_risk_opportunity_tool import (
        ImpactRiskOpportunityInput,
        ImpactRiskOpportunityTool,
    )

    tool = ImpactRiskOpportunityTool()
    args = ImpactRiskOpportunityInput(
        company_name=req.company_name,
        company_description=req.company_description,
        sector=req.sector,
        reported_metrics=req.reported_metrics,
    )
    result = await tool.execute(args, _get_tool_context())
    return {"result": result.output}


@app.post("/api/v1/metric-recommend", dependencies=[Depends(verify_api_key)])
async def metric_recommend(req: CompanyRequest):
    from openharness.tools.impact.metric_recommender_tool import MetricRecommenderInput, MetricRecommenderTool

    tool = MetricRecommenderTool()
    args = MetricRecommenderInput(
        company_name=req.company_name,
        company_description=req.company_description,
        sector=req.sector,
        impact_themes=req.impact_themes,
        reported_metrics=req.reported_metrics,
        sdg_claims=req.sdg_claims,
    )
    result = await tool.execute(args, _get_tool_context())
    return {"result": result.output}


@app.post("/api/v1/exclusion-screen", dependencies=[Depends(verify_api_key)])
async def exclusion_screen(req: CompanyRequest):
    from openharness.tools.impact.exclusion_screening_tool import ExclusionScreeningInput, ExclusionScreeningTool

    tool = ExclusionScreeningTool()
    args = ExclusionScreeningInput(
        company_name=req.company_name,
        company_description=req.company_description,
        sector=req.sector,
        reported_metrics=req.reported_metrics,
    )
    result = await tool.execute(args, _get_tool_context())
    return {"result": result.output}


@app.post("/api/v1/report", dependencies=[Depends(verify_api_key)])
async def generate_report(req: ReportRequest):
    from openharness.tools.impact.impact_report_tool import ImpactReportInput, ImpactReportTool

    tool = ImpactReportTool()
    args = ImpactReportInput(
        company_name=req.company_name,
        company_description=req.company_description,
        sector=req.sector,
        geography=req.geography,
        impact_themes=req.impact_themes,
        reported_metrics=req.reported_metrics,
        sdg_claims=req.sdg_claims,
        impact_targets=req.impact_targets,
        metric_history=req.metric_history,
        impact_claims=req.impact_claims,
        output_format=req.output_format,
        report_type=req.report_type,
    )
    result = await tool.execute(args, _get_tool_context())
    payload = {"result": result.output, "format": req.output_format, "report_type": req.report_type}
    await _fire_webhooks("assessment_complete", {"company": req.company_name, "report_type": req.report_type})
    return payload


@app.post("/api/v1/pitch-deck", dependencies=[Depends(verify_api_key)])
async def analyze_pitch_deck(req: dict[str, Any]):
    from openharness.tools.impact.pitch_deck_analyze_tool import PitchDeckAnalyzeInput, PitchDeckAnalyzeTool

    tool = PitchDeckAnalyzeTool()
    args = PitchDeckAnalyzeInput(
        file_path=req.get("file_path", ""),
        text=req.get("text", ""),
        url=req.get("url", ""),
    )
    result = await tool.execute(args, _get_tool_context())
    return {"result": result.output}


@app.post("/api/v1/ddq-export", dependencies=[Depends(verify_api_key)])
async def ddq_export(req: CompanyRequest):
    from openharness.tools.impact.lp_ddq_export_tool import LpDdqExportInput, LpDdqExportTool

    tool = LpDdqExportTool()
    args = LpDdqExportInput(
        company_name=req.company_name,
        company_description=req.company_description,
        sector=req.sector,
        geography=req.geography,
        impact_themes=req.impact_themes,
        reported_metrics=req.reported_metrics,
        sdg_claims=req.sdg_claims,
    )
    result = await tool.execute(args, _get_tool_context())
    return {"result": result.output}


@app.post("/api/v1/pipeline", dependencies=[Depends(verify_api_key)])
async def pipeline_endpoint(req: PipelineRequest):
    from openharness.tools.impact.pipeline_tool import PipelineInput, PipelineTool

    tool = PipelineTool()
    args = PipelineInput(
        action=req.action,
        company_name=req.company_name,
        pipeline_stage=req.stage or "sourcing",
        sector=req.sector,
        notes=req.notes,
        priority=req.priority,
        sdg_focus=req.sdg_focus,
    )
    result = await tool.execute(args, _get_tool_context())
    return {"result": result.output}


@app.post("/api/v1/monitoring", dependencies=[Depends(verify_api_key)])
async def monitoring_endpoint(req: MonitoringRequest):
    from openharness.tools.impact.monitoring_tool import MonitoringInput, MonitoringTool

    tool = MonitoringTool()
    args = MonitoringInput(
        action=req.action,
        company_name=req.company_name,
        metric_id=req.metric_id,
        metric_value=_coerce_float(req.value),
        frequency=req.frequency,
    )
    result = await tool.execute(args, _get_tool_context())
    if req.action == "record_metric" and "alert" in result.output.lower():
        await _fire_webhooks("alert_fired", {"company": req.company_name, "metric_id": req.metric_id})
    return {"result": result.output}


@app.post("/api/v1/improvement-advisor", dependencies=[Depends(verify_api_key)])
async def improvement_advisor_endpoint(req: CompanyRequest):
    from openharness.tools.impact.improvement_advisor_tool import ImprovementAdvisorInput, ImprovementAdvisorTool

    tool = ImprovementAdvisorTool()
    args = ImprovementAdvisorInput(
        action="recommend",
        company_name=req.company_name,
        company_description=req.company_description,
        sector=req.sector,
        geography=req.geography,
        reported_metrics=req.reported_metrics,
        sdg_claims=req.sdg_claims,
    )
    result = await tool.execute(args, _get_tool_context())
    return {"result": result.output}


@app.post("/api/v1/narrative", dependencies=[Depends(verify_api_key)])
async def narrative_endpoint(req: NarrativeRequest):
    from openharness.tools.impact.narrative_tool import NarrativeInput, NarrativeTool

    tool = NarrativeTool()
    normalized_action = "full_narrative" if req.section == "full" else req.section
    normalized_audience = "lp" if req.audience == "investor" else req.audience
    args = NarrativeInput(
        action=normalized_action,
        company_name=req.company_name,
        company_description=req.company_description,
        sector=req.sector,
        reported_metrics=req.reported_metrics,
        audience=normalized_audience,
    )
    result = await tool.execute(args, _get_tool_context())
    return {"result": result.output}


# ---------------------------------------------------------------------------
# Batch API (10.3.3)
# ---------------------------------------------------------------------------


@app.post("/api/v1/batch", dependencies=[Depends(verify_api_key)])
async def batch_assess(req: BatchRequest):
    """Submit multiple companies for assessment. Returns a job ID for async processing."""
    job_id = str(uuid.uuid4())
    _batch_jobs[job_id] = {"status": "processing", "total": len(req.companies), "completed": 0, "results": []}

    async def _run_batch():
        for company_req in req.companies:
            entry: dict[str, Any] = {"company": company_req.company_name}
            try:
                company = _build_company(company_req)
                store = get_metric_store()

                if "score" in req.analyses:
                    r = assess_five_dimensions(company, store)
                    entry["score"] = {
                        "overall_score": r.overall_score,
                        "overall_grade": r.overall_grade,
                        "dimensions": {
                            d: {"score": getattr(r, d).score}
                            for d in ("what", "who", "how_much", "contribution", "risk")
                        },
                    }
                if "sdg_map" in req.analyses:
                    alignments = map_sdg_alignment(company, store)
                    entry["sdg_map"] = [
                        {"goal": a.goal, "score": a.score}
                        for a in alignments if a.score > 0
                    ]
                if "greenwashing" in req.analyses:
                    gw = assess_greenwashing(company)
                    entry["greenwashing"] = {
                        "score": gw.overall_score,
                        "classification": gw.classification,
                    }
                if "gap_analysis" in req.analyses:
                    gaps = analyze_gaps(company, store)
                    entry["gap_analysis"] = {
                        "coverage": gaps["coverage_percentage"],
                        "missing": len(gaps["metrics_missing"]),
                    }
            except Exception as exc:
                entry["error"] = str(exc)

            _batch_jobs[job_id]["results"].append(entry)
            _batch_jobs[job_id]["completed"] += 1

        _batch_jobs[job_id]["status"] = "complete"
        await _fire_webhooks("assessment_complete", {
            "batch_job_id": job_id,
            "total": len(req.companies),
        })

    asyncio.create_task(_run_batch())
    return {"job_id": job_id, "status": "processing", "total": len(req.companies)}


@app.get("/api/v1/batch/{job_id}", dependencies=[Depends(verify_api_key)])
async def batch_status(job_id: str):
    job = _batch_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Batch job not found")
    return job


# ---------------------------------------------------------------------------
# Webhook Management (10.3.4)
# ---------------------------------------------------------------------------


@app.post("/api/v1/webhook", dependencies=[Depends(verify_api_key)])
async def register_webhook(reg: WebhookRegistration):
    webhook_id = str(uuid.uuid4())
    _webhooks.append({
        "id": webhook_id,
        "url": reg.url,
        "events": reg.events,
        "company_name": reg.company_name,
        "secret": reg.secret,
    })
    return {
        "status": "registered",
        "webhook_id": webhook_id,
        "url": reg.url,
        "events": reg.events,
        "note": "Webhooks trigger on: assessment_complete, score_change, alert_fired, metric_update, threshold_breach",
    }


@app.get("/api/v1/webhooks", dependencies=[Depends(verify_api_key)])
async def list_webhooks():
    return {
        "webhooks": [
            {"id": w["id"], "url": w["url"], "events": w["events"], "company_name": w.get("company_name", "")}
            for w in _webhooks
        ]
    }


@app.delete("/api/v1/webhook/{webhook_id}", dependencies=[Depends(verify_api_key)])
async def delete_webhook(webhook_id: str):
    global _webhooks
    before = len(_webhooks)
    _webhooks = [w for w in _webhooks if w.get("id") != webhook_id]
    if len(_webhooks) == before:
        raise HTTPException(status_code=404, detail="Webhook not found")
    return {"status": "deleted", "webhook_id": webhook_id}
