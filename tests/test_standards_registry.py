"""Tests for the versioned standards registry."""

from __future__ import annotations

import pytest

from openharness.impact.standards_registry import (
    StandardVersion,
    StandardsRegistry,
    default_standards_registry,
    get_default_standard,
)


def test_default_registry_contains_core_v2_standards() -> None:
    registry = default_standards_registry()
    ids = {item.standard_id for item in registry.list_standards()}

    assert {
        "IRIS_PLUS",
        "EDCI",
        "ISSB",
        "ESRS",
        "SFDR",
        "GHG_PROTOCOL",
        "GHG_PROTOCOL_SCOPE2",
        "PCAF",
        "OPIM",
    } <= ids
    assert registry.summary()["total"] >= 10


def test_registry_lookup_supports_aliases_and_versions() -> None:
    registry = default_standards_registry()

    assert registry.get("IRIS+").key == "IRIS_PLUS@5.3c"
    assert registry.get("IFRS S2").standard_id == "ISSB"
    assert registry.get("ESRS", version="2025-exposure-draft").status == "draft"
    assert get_default_standard("SFDR PAI").standard_id == "SFDR"


def test_active_rule_packs_include_under_revision_climate_methods() -> None:
    active = default_standards_registry().active_rule_packs()
    keys = {item.key for item in active}

    assert "GHG_PROTOCOL@corporate-2004" in keys
    assert "ESRS@2025-exposure-draft" not in keys


def test_registry_rejects_duplicate_standard_versions() -> None:
    with pytest.raises(ValueError, match="Duplicate standard versions"):
        StandardsRegistry(standards=[
            StandardVersion(standard_id="IRIS+", name="IRIS+", version="5.3c"),
            StandardVersion(standard_id="IRIS_PLUS", name="IRIS duplicate", version="5.3c"),
        ])


def test_registry_raises_for_unknown_standard() -> None:
    with pytest.raises(KeyError, match="Unknown standard"):
        default_standards_registry().get("NOPE")
