"""Deprecated compatibility shim for the retired ``roadmap_v2`` module (v7 W5.4).

Its helpers moved to the modules they duplicated; import from there. This
shim re-exports every public name for one release and will be removed in
0.18. ``JURISDICTION_PROFILES`` here is the legacy disclosure-profile map,
now ``regulatory_calendar.DISCLOSURE_PROFILES``.
"""

from __future__ import annotations

import warnings

warnings.warn(
    "openharness.impact.roadmap_v2 is deprecated; import from the modules listed in its "
    "docstring (removed in 0.18).",
    DeprecationWarning,
    stacklevel=2,
)

from openharness.impact.investee_collection import (  # noqa: E402
    CollectionStatus,
    PublicCollectionLink,
    CollectionLinkIssue,
    hash_token,
    issue_collection_link,
    CollectionTrackerRow,
    build_collection_tracker,
    ImportPreviewRow,
    ImportPreview,
    preview_csv_metric_import,
)

from openharness.impact.ai_review import (  # noqa: E402
    ReviewDecision,
    ReviewQueueItem,
    build_review_queue,
    AIExtractionReview,
    decide_ai_extraction,
    AIMetricMapping,
    harmonize_uploaded_metrics,
    AIGovernanceLog,
)

from openharness.impact.climate_accounting import (  # noqa: E402
    EmissionFactorCatalog,
    Scope3ProxyEstimate,
    estimate_scope3_proxy,
    CarbonIntensity,
    calculate_carbon_intensity,
    ClimateCoverageRow,
    build_climate_coverage_dashboard,
)

from openharness.impact.frameworks.pcaf import (  # noqa: E402
    PCAFPosition,
    PCAFResult,
    calculate_pcaf_financed_emissions,
)

from openharness.impact.disclosure_packs import (  # noqa: E402
    DisclosureStatus,
    SourceLinkedAnswer,
    DisclosurePack,
    build_issb_disclosure_pack,
    build_esrs_disclosure_pack,
    autofill_sfdr_pai,
)

from openharness.impact.regulatory_calendar import (  # noqa: E402
    JurisdictionProfile,
    DISCLOSURE_PROFILES,
    select_jurisdiction_profile,
)

from openharness.impact.frameworks.cross_reference import (  # noqa: E402
    explore_framework_crosswalk,
)

from openharness.impact.standards_registry import (  # noqa: E402
    RulePackTestResult,
    run_rule_pack_tests,
)

from openharness.impact.report_governance import (  # noqa: E402
    PublicationState,
    LPExportBundle,
    build_lp_export_bundle,
    ReportPublication,
    transition_report_publication,
    FundBrandingProfile,
    ControlCheckResult,
    run_control_checks,
    ImmutableReportManifest,
    build_immutable_report_manifest,
    ExceptionRegisterEntry,
)

from openharness.impact.contribution import (  # noqa: E402
    ContributionAnalysis,
    run_contribution_analysis,
    generate_counterfactual_questions,
    EvidenceStrength,
    score_evidence_strength,
    calculate_difference_in_differences,
)

from openharness.impact.exit_impact import (  # noqa: E402
    ExitImpactAssessment,
    ImpactLearningLoop,
)

from openharness.impact.portfolio_nlq import (  # noqa: E402
    PortfolioQueryResult,
    answer_portfolio_query,
)

from openharness.impact.regulatory_radar import (  # noqa: E402
    RegulatoryChangeImpact,
    monitor_regulatory_change,
)

JURISDICTION_PROFILES = DISCLOSURE_PROFILES


__all__ = [
    "AIExtractionReview",
    "AIGovernanceLog",
    "AIMetricMapping",
    "CarbonIntensity",
    "ClimateCoverageRow",
    "CollectionLinkIssue",
    "CollectionStatus",
    "CollectionTrackerRow",
    "ContributionAnalysis",
    "ControlCheckResult",
    "DisclosurePack",
    "DisclosureStatus",
    "EmissionFactorCatalog",
    "EvidenceStrength",
    "ExceptionRegisterEntry",
    "ExitImpactAssessment",
    "FundBrandingProfile",
    "ImmutableReportManifest",
    "ImportPreview",
    "ImpactLearningLoop",
    "ImportPreviewRow",
    "JURISDICTION_PROFILES",
    "JurisdictionProfile",
    "LPExportBundle",
    "PCAFPosition",
    "PCAFResult",
    "PortfolioQueryResult",
    "PublicCollectionLink",
    "PublicationState",
    "ReportPublication",
    "ReviewDecision",
    "RegulatoryChangeImpact",
    "ReviewQueueItem",
    "RulePackTestResult",
    "Scope3ProxyEstimate",
    "SourceLinkedAnswer",
    "answer_portfolio_query",
    "autofill_sfdr_pai",
    "build_climate_coverage_dashboard",
    "build_collection_tracker",
    "build_esrs_disclosure_pack",
    "build_immutable_report_manifest",
    "build_issb_disclosure_pack",
    "build_lp_export_bundle",
    "build_review_queue",
    "calculate_carbon_intensity",
    "calculate_difference_in_differences",
    "calculate_pcaf_financed_emissions",
    "decide_ai_extraction",
    "estimate_scope3_proxy",
    "explore_framework_crosswalk",
    "generate_counterfactual_questions",
    "harmonize_uploaded_metrics",
    "hash_token",
    "issue_collection_link",
    "monitor_regulatory_change",
    "preview_csv_metric_import",
    "run_contribution_analysis",
    "run_control_checks",
    "run_rule_pack_tests",
    "score_evidence_strength",
    "select_jurisdiction_profile",
    "transition_report_publication",
]
