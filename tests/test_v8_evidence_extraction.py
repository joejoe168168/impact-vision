"""Evidence-aware extraction (roadmap v8 W2.1)."""
from __future__ import annotations

from impact_vision.impact.doc_structure import tables_to_sentences
from impact_vision.impact.extractors.regex_extractor import evidence_signals
from impact_vision.impact.pipeline import assess_document

DECK = """# Afya Clinics — Series A

Afya runs primary-care clinics for low-income families in Nairobi.

## The problem
Kenya has 1.5 million people without access to a clinic within 5 km.

## Traction
| Metric | 2023 | 2024 |
|---|---|---|
| Patients treated | 18,000 | 31,000 |
| Clinics | 4 | 7 |

- Our clinics are SafeCare level 4 accredited.
- Lab results validated by SIRIM.
- We raised USD 3m from Acumen in 2023.

## Risks we manage
- Clinical quality: quarterly clinical governance audits.
- Medical waste: handled by a licensed contractor.

## Ask
USD 5m Series A.
"""


def test_table_rows_become_sentences():
    out = tables_to_sentences(DECK)
    assert "- 31,000 patients treated in 2024 (18,000 in 2023)." in out
    assert "- Clinics: 7 in 2024 (4 in 2023)." in out
    assert "|---|" not in out
    plain = "| Indicator | Value |\n|---|---|\n| Farmers reached | 4,200 |\n"
    assert tables_to_sentences(plain).strip() == "- 4,200 farmers reached."
    assert tables_to_sentences("no tables | here") == "no tables | here"


def test_table_reach_drives_expected_impact():
    people = assess_document(DECK, name="Afya", sector="healthcare").report_data["expected_impact"]["outcomes"][0]
    assert people["stakeholder"] == "patients"
    assert next(f["median"] for f in people["factors"] if f["name"] == "Reach") == 31_000


def test_context_sections_are_not_company_claims():
    claims = [c["text"] for c in assess_document(DECK, name="Afya").report_data["impact_claims"]]
    assert not any("1.5 million" in c for c in claims)      # the problem statement
    assert not any("USD 3m" in c or "USD 5m" in c for c in claims)  # funding is not an output


def test_accreditations_count_as_verification():
    assert "certified" in evidence_signals("Our clinics are SafeCare level 4 accredited.")
    assert "certified" in evidence_signals("Offsets are Gold Standard certified.")
    assert "third_party_verified" in evidence_signals("Lab results validated by SIRIM.")
    assert evidence_signals("Results were validated by the team internally.") == []


def test_risk_section_bullets_are_disclosed_risks():
    risks = assess_document(DECK, name="Afya", sector="healthcare").report_data["impact_analysis"]["risks"]
    disclosed = [r for r in risks if r.startswith("Disclosed:")]
    assert "Disclosed: Clinical quality: quarterly clinical governance audits." in disclosed
    assert "Disclosed: Medical waste: handled by a licensed contractor." in disclosed
