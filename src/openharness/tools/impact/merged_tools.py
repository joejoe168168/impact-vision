"""Merged agent tools (v7 W1.5): clear duplicates folded into one tool each.

| Kept tool            | Absorbed tool         | New actions                                      |
|----------------------|-----------------------|--------------------------------------------------|
| stakeholder_voice    | beneficiary_feedback  | feedback_import / feedback_analyze / feedback_summary |
| ddq_responder        | lp_ddq_export         | template_list / template_generate / template_preview |
| regulatory_calendar  | regulatory_radar      | radar_check / radar_findings / radar_confirm / radar_dismiss / radar_impact |
| pipeline             | guided_assessment     | guided_start / guided_status / guided_next_step / guided_submit / guided_templates |
| pitch_deck_analyze   | document_analysis     | compare_documents / detect_changes / verify_claims (default action: analyze) |

The absorbed tools stay registered for one release as deprecated aliases in
the ``developer`` profile only (see ``DEPRECATED_TOOLS``).
"""

from __future__ import annotations

from openharness.tools.impact.beneficiary_feedback_tool import BeneficiaryFeedbackTool
from openharness.tools.impact.ddq_responder_tool import DDQResponderTool as _DDQResponderTool
from openharness.tools.impact.document_analysis_tool import DocumentAnalysisTool
from openharness.tools.impact.guided_assessment_tool import GuidedAssessmentTool
from openharness.tools.impact.lp_ddq_export_tool import LpDdqExportTool
from openharness.tools.impact.merge import deprecated_alias, merge_tools
from openharness.tools.impact.pipeline_tool import PipelineTool as _PipelineTool
from openharness.tools.impact.pitch_deck_analyze_tool import (
    PitchDeckAnalyzeTool as _PitchDeckAnalyzeTool,
)
from openharness.tools.impact.regulatory_calendar_tool import (
    RegulatoryCalendarTool as _RegulatoryCalendarTool,
)
from openharness.tools.impact.regulatory_radar_tool import RegulatoryRadarTool
from openharness.tools.impact.stakeholder_voice_tool import (
    StakeholderVoiceTool as _StakeholderVoiceTool,
)

StakeholderVoiceTool = merge_tools(
    _StakeholderVoiceTool,
    BeneficiaryFeedbackTool,
    {"import": "feedback_import", "analyze": "feedback_analyze", "summary": "feedback_summary"},
    summary="beneficiary feedback import and analysis (60 Decibels Lean Data or manual surveys)",
)

DDQResponderTool = merge_tools(
    _DDQResponderTool,
    LpDdqExportTool,
    {"list_templates": "template_list", "generate": "template_generate", "preview": "template_preview"},
    rename_prefix="template_",
    summary="LP DDQ templates (ILPA ESG, GIIN/IRIS+, EDCI, SFDR) filled from company data",
)

RegulatoryCalendarTool = merge_tools(
    _RegulatoryCalendarTool,
    RegulatoryRadarTool,
    {
        "check": "radar_check",
        "list_findings": "radar_findings",
        "confirm": "radar_confirm",
        "dismiss": "radar_dismiss",
        "impact": "radar_impact",
    },
    summary="the regulatory radar (review-gated detection of standard changes)",
)

PipelineTool = merge_tools(
    _PipelineTool,
    GuidedAssessmentTool,
    {
        "start": "guided_start",
        "status": "guided_status",
        "next_step": "guided_next_step",
        "submit_data": "guided_submit",
        "list_templates": "guided_templates",
    },
    summary="guided step-by-step assessments (screening / DD / monitoring templates)",
)

PitchDeckAnalyzeTool = merge_tools(
    _PitchDeckAnalyzeTool,
    DocumentAnalysisTool,
    {
        "compare_documents": "compare_documents",
        "detect_changes": "detect_changes",
        "verify_claims": "verify_claims",
    },
    default_action="analyze",
    target_action_without_field="analyze",
    summary="multi-document comparison for one company",
)

# Old name -> replacement hint, kept for one release (developer profile only).
DEPRECATED_TOOLS: dict[str, tuple[type, str]] = {
    "beneficiary_feedback": (
        deprecated_alias(BeneficiaryFeedbackTool, "stakeholder_voice action='feedback_*'"),
        "stakeholder_voice",
    ),
    "lp_ddq_export": (
        deprecated_alias(LpDdqExportTool, "ddq_responder action='template_*'"),
        "ddq_responder",
    ),
    "regulatory_radar": (
        deprecated_alias(RegulatoryRadarTool, "regulatory_calendar action='radar_*'"),
        "regulatory_calendar",
    ),
    "guided_assessment": (
        deprecated_alias(GuidedAssessmentTool, "pipeline action='guided_*'"),
        "pipeline",
    ),
    "document_analysis": (
        deprecated_alias(DocumentAnalysisTool, "pitch_deck_analyze action='compare_documents'"),
        "pitch_deck_analyze",
    ),
}

__all__ = [
    "DDQResponderTool",
    "DEPRECATED_TOOLS",
    "PipelineTool",
    "PitchDeckAnalyzeTool",
    "RegulatoryCalendarTool",
    "StakeholderVoiceTool",
]
