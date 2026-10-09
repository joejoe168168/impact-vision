"""Roadmap v7 W5.3 — consultant state survives a restart."""

from __future__ import annotations

import os

import pytest


@pytest.fixture()
def sqlite_store(tmp_path):
    from impact_vision.impact.state_store import SQLiteStateStore

    return lambda: SQLiteStateStore(tmp_path / "state.db")  # each call = a "new process"


def test_store_backends_round_trip_and_isolate_tenants(sqlite_store) -> None:
    from impact_vision.impact.state_store import MemoryStateStore

    for store in (MemoryStateStore(), sqlite_store()):
        store.put("fund-a", "k", "x", {"n": 1})
        store.put("fund-b", "k", "x", {"n": 2})
        store.put("fund-a", "k", "x", {"n": 3})  # upsert
        assert store.get("fund-a", "k", "x") == {"n": 3}
        assert store.get("fund-b", "k", "x") == {"n": 2}
        assert store.keys("fund-a", "k") == ["x"]
        store.delete("fund-a", "k", "x")
        assert store.get("fund-a", "k", "x") is None


def test_engagement_workspace_restores_after_restart(sqlite_store) -> None:
    from impact_vision.impact.engagements.workspace import EngagementWorkspace

    ws = EngagementWorkspace(tenant_id="acme", store=sqlite_store())
    eng = ws.create_engagement(name="DD", client_name="Fund I", bundle_id="dd_light")
    ws.add_note(eng.engagement_id, author="cl", text="Kick-off done")

    restarted = EngagementWorkspace(tenant_id="acme", store=sqlite_store())
    again = restarted.get_engagement(eng.engagement_id)
    assert again.name == "DD" and again.client_name == "Fund I"
    assert any(n.text == "Kick-off done" for n in again.notes)
    assert EngagementWorkspace(tenant_id="other", store=sqlite_store()).list_engagements() == []


def test_audit_chain_survives_restart_and_shared_writers(sqlite_store) -> None:
    from impact_vision.impact.audit_trail import AuditTrail
    from impact_vision.impact.signed_feed import HMACSigner

    signer = HMACSigner(key=b"k" * 32)
    a = AuditTrail(fund_id="f1", signer=signer, store=sqlite_store())
    b = AuditTrail(fund_id="f1", signer=signer, store=sqlite_store())
    a.record_event(event_type="score", payload={"n": 1})
    b.record_event(event_type="score", payload={"n": 2})  # appends after a's event
    a.record_event(event_type="score", payload={"n": 3})
    restarted = AuditTrail(fund_id="f1", signer=signer, store=sqlite_store())
    assert [r.payload["n"] for r in restarted.feed.reports] == [1, 2, 3]
    ok, problems = restarted.feed.verify(signer)
    assert ok, problems


def test_review_queues_and_rbac_persist(sqlite_store) -> None:
    from impact_vision.impact.evidence_workflow import load_review_queue, save_review_queue
    from impact_vision.impact.ai_review import AIExtractionReview
    from impact_vision.impact.tenancy import PersistentRBACStore, Role, Tenant, User

    q = load_review_queue("radar", store=sqlite_store())
    q.add(AIExtractionReview(item_id="i1", extracted_text="x", confidence=0.5, rationale="r", source_refs=[]))
    save_review_queue(q, "radar", store=sqlite_store())
    assert [i.review.item_id for i in load_review_queue("radar", store=sqlite_store()).items] == ["i1"]

    rbac = PersistentRBACStore(sqlite_store())
    rbac.upsert_tenant(Tenant(id="t1", name="Fund"))
    rbac.upsert_user(User(id="u1", tenant_id="t1", email="a@b.c", role_names=["analyst"]))
    rbac.upsert_role("t1", Role(name="auditor", permissions=["report:generate"]))
    fresh = PersistentRBACStore(sqlite_store())
    assert fresh.get_tenant("t1").name == "Fund" and fresh.get_user("u1").role_names == ["analyst"]
    assert fresh.get_role("t1", "auditor").permissions == ["report:generate"]


def test_default_store_follows_environment(monkeypatch, tmp_path) -> None:
    from impact_vision.impact import state_store

    monkeypatch.setenv("IMPACT_VISION_STATE_STORE", "sqlite")
    monkeypatch.setenv("IMPACT_VISION_STATE_DB", str(tmp_path / "s.db"))
    state_store.set_state_store(None)
    try:
        store = state_store.get_state_store()
        assert isinstance(store, state_store.SQLiteStateStore) and store.path == tmp_path / "s.db"
    finally:
        state_store.set_state_store(None)
        monkeypatch.setenv("IMPACT_VISION_STATE_STORE", "memory")


@pytest.mark.skipif(not os.environ.get("IMPACT_VISION_STATE_DSN"), reason="needs a Postgres DSN")
def test_postgres_backend_round_trip() -> None:  # pragma: no cover - optional
    from impact_vision.impact.state_store import PostgresStateStore

    store = PostgresStateStore()
    store.put("t", "k", "x", {"n": 1})
    assert store.get("t", "k", "x") == {"n": 1}
    store.delete("t", "k", "x")


def test_retired_module_shims_are_gone() -> None:
    """The roadmap_v2 / questionnaire_v2 / sfdr_v2 shims were removed in 0.18 (v8 W5.1)."""
    import importlib

    for old in ("impact_vision.impact.roadmap_v2", "impact_vision.impact.questionnaire_v2",
                "impact_vision.impact.frameworks.sfdr_v2"):
        with pytest.raises(ModuleNotFoundError):
            importlib.import_module(old)
