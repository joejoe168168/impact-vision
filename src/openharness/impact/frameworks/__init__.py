"""Sustainability and impact reporting frameworks.

Includes: SASB, GRI, TCFD/IFRS S2, SFDR PAI, EDCI, UNPRI, Theory of Change,
and cross-reference mappings between all frameworks.
"""

from openharness.impact.frameworks.sasb import SASBStandard, get_sasb_industries, match_sasb_industry
from openharness.impact.frameworks.gri import GRIStandard, get_gri_standards, match_gri_topics
from openharness.impact.frameworks.tcfd import TCFDFramework, assess_tcfd_alignment, get_tcfd_framework
from openharness.impact.frameworks.sfdr_pai import SFDRIndicator, get_pai_indicators, assess_sfdr_compliance
from openharness.impact.frameworks.edci import EDCIMetric, get_edci_metrics, assess_edci_coverage
from openharness.impact.frameworks.unpri import UNPRIPrinciple, get_unpri_principles, assess_unpri_alignment
from openharness.impact.frameworks.theory_of_change import (
    TheoryOfChange, ToCPrinciple, get_rs_group_principles, get_giin_toc_checklist,
    assess_toc_alignment, assess_toc_completeness,
)
from openharness.impact.frameworks.cross_reference import (
    CrossReference, lookup_by_iris, lookup_by_gri, lookup_by_edci, lookup_by_sfdr,
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

__all__ = [
    "SASBStandard", "get_sasb_industries", "match_sasb_industry",
    "GRIStandard", "get_gri_standards", "match_gri_topics",
    "TCFDFramework", "assess_tcfd_alignment", "get_tcfd_framework",
    "SFDRIndicator", "get_pai_indicators", "assess_sfdr_compliance",
    "EDCIMetric", "get_edci_metrics", "assess_edci_coverage",
    "UNPRIPrinciple", "get_unpri_principles", "assess_unpri_alignment",
    "TheoryOfChange", "ToCPrinciple", "get_rs_group_principles",
    "get_giin_toc_checklist", "assess_toc_alignment", "assess_toc_completeness",
    "CrossReference", "lookup_by_iris", "lookup_by_gri", "lookup_by_edci",
    "lookup_by_sfdr", "search_cross_references", "get_all_cross_references",
    "format_cross_reference",
    # Phase 13 frameworks
    "FinancedEmissionsInput", "FinancedEmissionsResult", "PCAFRollup",
    "calculate_financed_emissions", "rollup_pcaf",
    "SBTiClaim", "SBTiAlignmentCheck", "check_sbti_alignment",
    "EconomicActivity", "TaxonomyAlignmentResult", "assess_taxonomy_alignment",
    "TNFDDisclosure", "TNFDInput", "TNFDAssessmentResult", "TNFD_DISCLOSURES", "assess_tnfd",
    "CDPResponse", "CDPIntakeResult", "parse_cdp_responses",
]
