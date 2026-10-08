"""Impact-specific tools for IRIS+ metrics, SDG alignment, and impact assessment.

Tool classes are imported lazily (PEP 562): ``from openharness.tools.impact
import SdgMapperTool`` still works, but importing this package (or one helper
module such as ``tools.impact.common`` from the core engine) no longer loads
all 60 tool modules. That cut ``import openharness.impact`` from ~1.6 s.
"""

from __future__ import annotations

import importlib
from typing import Any

_TOOL_MODULES: dict[str, str] = {
    "ImpactAdvisorTool": "advisor_tool",
    "AIGovernanceTool": "ai_governance_tool",
    "ClimateScenarioTool": "climate_scenario_tool",
    "CarbonCreditIntegrityTool": "carbon_credit_tool",
    "ContributionTrackerTool": "contribution_tool",
    "CrossReferenceTool": "cross_reference_tool",
    "DataQualityTool": "data_quality_tool",
    "DecisionWorkflowTool": "decision_workflow_tool",
    "DdChecklistTool": "dd_checklist_tool",
    "DMRVEvidenceTool": "dmrv_tool",
    "AssessDealTool": "assess_deal_tool",
    "EmissionFactorsTool": "emission_factors_tool",
    "EngagementSuiteTool": "engagement_suite_tool",
    "EngagementWorkspaceTool": "engagement_workspace_tool",
    "EvidenceReviewTool": "evidence_review_tool",
    "ExclusionScreeningTool": "exclusion_screening_tool",
    "ExitImpactTool": "exit_impact_tool",
    "ESGToolboxTool": "esg_toolbox_tool",
    "DDQResponderTool": "merged_tools",
    "PipelineTool": "merged_tools",
    "PitchDeckAnalyzeTool": "merged_tools",
    "RegulatoryCalendarTool": "merged_tools",
    "StakeholderVoiceTool": "merged_tools",
    "FiveDimensionAssessTool": "five_dimension_assess_tool",
    "FrameworkTool": "framework_tool",
    "GapAnalysisTool": "gap_analysis_tool",
    "GreenwashingReviewerTool": "greenwashing_reviewer_tool",
    "GreenwashingDetectorTool": "greenwashing_tool",
    "HRDDTool": "hrdd_tool",
    "ImpactQuantifierTool": "impact_quantifier_tool",
    "ImpactRiskOpportunityTool": "impact_risk_opportunity_tool",
    "ImpactReportTool": "impact_report_tool",
    "ImpactValuationTool": "impact_valuation_tool",
    "ImpactLinkedFinanceTool": "impact_linked_finance_tool",
    "ImprovementAdvisorTool": "improvement_advisor_tool",
    "InvesteePortalTool": "investee_portal_tool",
    "IrisCatalogTool": "iris_catalog_tool",
    "LPNarrativeTool": "lp_narrative_tool",
    "LCAAssessmentTool": "lca_tool",
    "MetricRecommenderTool": "metric_recommender_tool",
    "MonitoringTool": "monitoring_tool",
    "NarrativeTool": "narrative_tool",
    "PortfolioQueryTool": "portfolio_query_tool",
    "PortfolioTool": "portfolio_tool",
    "ProductPassportTool": "product_passport_tool",
    "SdgMapperTool": "sdg_mapper_tool",
    "SurveyDeliveryTool": "survey_delivery_tool",
    "ToCBuilderTool": "toc_builder_tool",
    "TrendAnalysisTool": "trend_analysis_tool",
    "VerificationPrepTool": "verification_prep_tool",
    "VerificationWorkspaceTool": "verification_workspace_tool",
}


def __getattr__(name: str) -> Any:
    module = _TOOL_MODULES.get(name)
    if module is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(importlib.import_module(f"{__name__}.{module}"), name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(_TOOL_MODULES))


__all__ = [
    "AIGovernanceTool",
    "AssessDealTool",
    "ClimateScenarioTool",
    "CarbonCreditIntegrityTool",
    "ContributionTrackerTool",
    "CrossReferenceTool",
    "DataQualityTool",
    "DecisionWorkflowTool",
    "DdChecklistTool",
    "DDQResponderTool",
    "DMRVEvidenceTool",
    "EmissionFactorsTool",
    "EngagementSuiteTool",
    "EngagementWorkspaceTool",
    "EvidenceReviewTool",
    "ExclusionScreeningTool",
    "ExitImpactTool",
    "ESGToolboxTool",
    "FiveDimensionAssessTool",
    "FrameworkTool",
    "GapAnalysisTool",
    "GreenwashingDetectorTool",
    "HRDDTool",
    "ImpactAdvisorTool",
    "ImpactQuantifierTool",
    "ImpactRiskOpportunityTool",
    "ImpactReportTool",
    "ImpactValuationTool",
    "ImpactLinkedFinanceTool",
    "ImprovementAdvisorTool",
    "InvesteePortalTool",
    "IrisCatalogTool",
    "LPNarrativeTool",
    "LCAAssessmentTool",
    "MetricRecommenderTool",
    "MonitoringTool",
    "PipelineTool",
    "PitchDeckAnalyzeTool",
    "PortfolioQueryTool",
    "PortfolioTool",
    "ProductPassportTool",
    "RegulatoryCalendarTool",
    "SdgMapperTool",
    "StakeholderVoiceTool",
    "SurveyDeliveryTool",
    "ToCBuilderTool",
    "TrendAnalysisTool",
    "VerificationWorkspaceTool",
]
