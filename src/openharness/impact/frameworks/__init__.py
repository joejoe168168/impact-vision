"""Sustainability and impact reporting frameworks.

Includes: SASB, GRI, TCFD/IFRS S2, SFDR PAI, EDCI, UNPRI, Theory of Change,
and cross-reference mappings between all frameworks.
"""

from openharness.impact.frameworks.sasb import SASBStandard, get_sasb_industries, match_sasb_industry
from openharness.impact.frameworks.gri import GRIStandard, get_gri_standards, match_gri_topics
from openharness.impact.frameworks.tcfd import TCFDFramework, assess_tcfd_alignment, get_tcfd_framework
from openharness.impact.frameworks.sfdr_pai import SFDRIndicator, get_pai_indicators, assess_sfdr_compliance
from openharness.impact.frameworks.edci import (
    EDCICompletenessReport,
    EDCICompletenessRow,
    EDCIMetric,
    assess_edci_completeness,
    assess_edci_coverage,
    get_edci_metrics,
    portfolio_edci_completeness,
)
from openharness.impact.frameworks.unpri import UNPRIPrinciple, get_unpri_principles, assess_unpri_alignment
from openharness.impact.frameworks.theory_of_change import (
    TheoryOfChange, ToCPrinciple, get_rs_group_principles, get_giin_toc_checklist,
    assess_toc_alignment, assess_toc_completeness,
)
from openharness.impact.frameworks.cross_reference import (
    CrossReference, lookup_by_iris, lookup_by_gri, lookup_by_edci, lookup_by_sfdr,
    lookup_by_issb, lookup_by_esrs,
    search_cross_references, get_all_cross_references, format_cross_reference,
)
from openharness.impact.frameworks.pcaf import (
    FinancedEmissionsInput, FinancedEmissionsResult, PCAFRollup,
    calculate_financed_emissions, rollup_pcaf,
)
from openharness.impact.frameworks.sbti import (
    SBTiClaim, SBTiAlignmentCheck, check_sbti_alignment,
)
from openharness.impact.frameworks.eu_taxonomy import (
    EconomicActivity, TaxonomyAlignmentResult, assess_taxonomy_alignment,
)
from openharness.impact.frameworks.tnfd import (
    TNFDDisclosure, TNFDInput, TNFDAssessmentResult, TNFD_DISCLOSURES, assess_tnfd,
)
from openharness.impact.frameworks.cdp import (
    CDPResponse, CDPIntakeResult, parse_cdp_responses,
)
from openharness.impact.frameworks.vsme import (
    VSMEDisclosure, VSMEDisclosureResult, VSMEAssessmentResult,
    VSME_DISCLOSURES, get_vsme_disclosures, assess_vsme,
)
from openharness.impact.frameworks.two_x import (
    TwoXInput, TwoXDimensionResult, TwoXResult,
    assess_2x_criteria, screen_2x_from_text,
)
from openharness.impact.frameworks.tisfd import (
    TISFDDisclosure, TISFDAssessmentResult, TISFD_DISCLOSURES,
    get_tisfd_disclosures, assess_tisfd_readiness,
)

__all__ = [
    "SASBStandard", "get_sasb_industries", "match_sasb_industry",
    "GRIStandard", "get_gri_standards", "match_gri_topics",
    "TCFDFramework", "assess_tcfd_alignment", "get_tcfd_framework",
    "SFDRIndicator", "get_pai_indicators", "assess_sfdr_compliance",
    "EDCICompletenessReport", "EDCICompletenessRow", "EDCIMetric",
    "assess_edci_completeness", "get_edci_metrics", "assess_edci_coverage",
    "portfolio_edci_completeness",
    "UNPRIPrinciple", "get_unpri_principles", "assess_unpri_alignment",
    "TheoryOfChange", "ToCPrinciple", "get_rs_group_principles",
    "get_giin_toc_checklist", "assess_toc_alignment", "assess_toc_completeness",
    "CrossReference", "lookup_by_iris", "lookup_by_gri", "lookup_by_edci",
    "lookup_by_sfdr", "lookup_by_issb", "lookup_by_esrs", "search_cross_references",
    "get_all_cross_references", "format_cross_reference",
    # Phase 13 frameworks
    "FinancedEmissionsInput", "FinancedEmissionsResult", "PCAFRollup",
    "calculate_financed_emissions", "rollup_pcaf",
    "SBTiClaim", "SBTiAlignmentCheck", "check_sbti_alignment",
    "EconomicActivity", "TaxonomyAlignmentResult", "assess_taxonomy_alignment",
    "TNFDDisclosure", "TNFDInput", "TNFDAssessmentResult", "TNFD_DISCLOSURES", "assess_tnfd",
    "CDPResponse", "CDPIntakeResult", "parse_cdp_responses",
    "VSMEDisclosure", "VSMEDisclosureResult", "VSMEAssessmentResult",
    "VSME_DISCLOSURES", "get_vsme_disclosures", "assess_vsme",
    "TwoXInput", "TwoXDimensionResult", "TwoXResult",
    "assess_2x_criteria", "screen_2x_from_text",
    "TISFDDisclosure", "TISFDAssessmentResult", "TISFD_DISCLOSURES",
    "get_tisfd_disclosures", "assess_tisfd_readiness",
]
