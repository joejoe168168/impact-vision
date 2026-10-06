"""W0.8: signing keys come from the environment; production refuses dev keys."""

from __future__ import annotations

import pytest

from openharness.impact.audit_trail import AuditTrail
from openharness.impact.engagements.verification_bundle import (
    MandatePack,
    PracticePack,
    ReportingPack,
    build_assurance_bundle,
    verify_assurance_bundle,
)
from openharness.impact.signed_feed import SigningKeyError, get_signer, resolve_signing_key


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for var in ("IMPACT_VISION_ENV", "IMPACT_VISION_ALLOW_DEV_KEYS", "IMPACT_VISION_HMAC_KEY",
                "IMPACT_VISION_AUDIT_HMAC_KEY", "IMPACT_VISION_ASSURANCE_HMAC_KEY"):
        monkeypatch.delenv(var, raising=False)


def test_dev_key_is_labelled():
    assert get_signer("audit").id == "hmac-sha256-dev"
    assert AuditTrail().signer.id == "hmac-sha256-dev"


def test_env_key_is_used(monkeypatch):
    monkeypatch.setenv("IMPACT_VISION_AUDIT_HMAC_KEY", "s3cret")
    key, is_dev = resolve_signing_key("audit")
    assert key == b"s3cret" and not is_dev
    assert get_signer("audit").id == "hmac-sha256"


@pytest.mark.parametrize("env", [("IMPACT_VISION_ENV", "production"), ("IMPACT_VISION_ALLOW_DEV_KEYS", "0")])
def test_production_refuses_dev_keys(monkeypatch, env):
    monkeypatch.setenv(*env)
    with pytest.raises(SigningKeyError):
        get_signer("audit")
    trail = AuditTrail()  # constructing is fine; signing fails closed
    with pytest.raises(SigningKeyError):
        trail.record_event(event_type="x", payload={})


def _packs():
    return MandatePack(), PracticePack(), ReportingPack()


def test_assurance_manifest_discloses_key_and_verifies(monkeypatch):
    m, p, r = _packs()
    dev = build_assurance_bundle(engagement_id="e1", mandate=m, practice=p, reporting=r)
    assert dev.manifest.key_id == "development-default"
    assert verify_assurance_bundle(dev)

    monkeypatch.setenv("IMPACT_VISION_ASSURANCE_HMAC_KEY", "kms-issued")
    real = build_assurance_bundle(engagement_id="e1", mandate=m, practice=p, reporting=r)
    assert real.manifest.key_id == "env:IMPACT_VISION_ASSURANCE_HMAC_KEY"
    assert verify_assurance_bundle(real)
    assert not verify_assurance_bundle(real, secret_key=b"impact-vision-assurance")


def test_tool_registry_loads_in_production_without_keys(monkeypatch):
    from openharness.tools import create_default_tool_registry

    monkeypatch.setenv("IMPACT_VISION_ENV", "production")
    assert len(create_default_tool_registry().list_tools()) > 50
