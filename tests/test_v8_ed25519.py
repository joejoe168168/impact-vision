"""v8 W5.5: Ed25519-signed assurance manifests verify with the public key alone."""
from __future__ import annotations

import pytest

pytest.importorskip("cryptography")

from openharness.impact.signed_feed import Ed25519Signer, verify_ed25519  # noqa: E402


def _bundle():
    from openharness.impact.engagements.verification_bundle import (
        MandatePack,
        PracticePack,
        ReportingPack,
        build_assurance_bundle,
    )

    return build_assurance_bundle(engagement_id="eng-1", mandate=MandatePack(), practice=PracticePack(),
                                  reporting=ReportingPack())


def test_signer_round_trip_and_tamper():
    signer = Ed25519Signer.generate()
    sig = signer.sign(b"manifest")
    assert verify_ed25519(b"manifest", sig, signer.public_key_pem())
    assert not verify_ed25519(b"manifest!", sig, signer.public_key_pem())
    other = Ed25519Signer.generate()
    assert not verify_ed25519(b"manifest", sig, other.public_key_pem())


def test_seed_and_pem_material():
    signer = Ed25519Signer.generate()
    again = Ed25519Signer.from_material(signer.private_key_pem())
    assert again.public_key_pem() == signer.public_key_pem()
    seed_signer = Ed25519Signer.from_material("11" * 32)
    assert seed_signer.public_key_pem() == Ed25519Signer.from_material("11" * 32).public_key_pem()


def test_assurance_bundle_signed_with_ed25519(monkeypatch):
    from openharness.impact.engagements.verification_bundle import verify_assurance_bundle

    signer = Ed25519Signer.generate()
    monkeypatch.setenv("IMPACT_VISION_ASSURANCE_ED25519_KEY", signer.private_key_pem())
    bundle = _bundle()
    assert bundle.manifest.signature_algorithm == "ed25519"
    assert bundle.manifest.public_key_pem == signer.public_key_pem()
    monkeypatch.delenv("IMPACT_VISION_ASSURANCE_ED25519_KEY")
    # A verifier with no secret at all can check it ...
    assert verify_assurance_bundle(bundle, public_key_pem=signer.public_key_pem())
    # ... but a forged signature or a swapped key fails.
    other = Ed25519Signer.generate()
    assert not verify_assurance_bundle(bundle, public_key_pem=other.public_key_pem())
    sig = bundle.manifest.signature
    bundle.manifest.signature = ("0" if sig[0] != "0" else "1") + sig[1:]
    assert not verify_assurance_bundle(bundle)


def test_hmac_still_default_without_ed25519_key(monkeypatch):
    monkeypatch.delenv("IMPACT_VISION_ASSURANCE_ED25519_KEY", raising=False)
    monkeypatch.delenv("IMPACT_VISION_ED25519_KEY", raising=False)
    from openharness.impact.engagements.verification_bundle import verify_assurance_bundle

    bundle = _bundle()
    assert bundle.manifest.signature_algorithm == "sha256"
    assert verify_assurance_bundle(bundle)
