"""Sync from connectors into Impact Vision (roadmap v8 W3.5).

* :func:`sync_documents` copies new or changed documents into the uploads
  folder (``<uploads>/<connector>/<company>/<file>``) and, with
  ``assess=True``, assesses each new deck or memo and files it on the company
  record. What was seen (id → modified time) is kept in the state store, so a
  re-run only touches what changed.
* :func:`sync_deals` upserts CRM rows into the pipeline: new companies are
  added at their mapped stage; a changed stage is a logged transition. Nothing
  is ever written back to the CRM.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from impact_vision.impact.connectors.base import DealSource, DocumentSource

_SAFE = re.compile(r"[^A-Za-z0-9._ -]+")
_ASSESSABLE = (".pdf", ".docx", ".pptx", ".txt", ".md")


def _safe(part: str) -> str:
    return (_SAFE.sub("_", part).strip("._ ") or "untitled")[:120]


def _seen_store() -> Any:
    from impact_vision.impact.state_store import get_state_store

    return get_state_store()


def sync_documents(source: DocumentSource, *, assess: bool = False, target: Path | None = None,
                   limit: int = 200) -> dict[str, Any]:
    from impact_vision.web.chat_api import uploads_dir

    root = Path(target) if target else uploads_dir() / source.id
    store = _seen_store()
    seen: dict[str, str] = store.get("default", "connector_seen", source.id) or {}
    copied, assessed, skipped, errors = [], [], 0, []
    for doc in source.list_documents()[:limit]:
        if seen.get(doc.id) == (doc.modified or "?"):
            skipped += 1
            continue
        folder = root / _safe(doc.company) if doc.company else root
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / _safe(doc.name)
        try:
            path.write_bytes(source.fetch(doc))
        except Exception as exc:  # noqa: BLE001 - one bad file must not stop the sync
            errors.append({"document": doc.name, "error": str(exc)[:200]})
            continue
        copied.append(str(path))
        seen[doc.id] = doc.modified or "?"
        if assess and path.suffix.lower() in _ASSESSABLE:
            try:
                from impact_vision.impact.pipeline import assess_file, save_bundle

                bundle = assess_file(path)
                if doc.company and bundle.company.name in {"", "Company"}:
                    bundle.company.name = doc.company
                assessed.append({"document": doc.name, "company": bundle.company.name,
                                 "assessment_id": save_bundle(bundle, source_label=f"{source.id}: {doc.name}")})
            except Exception as exc:  # noqa: BLE001
                errors.append({"document": doc.name, "error": f"assessment failed: {str(exc)[:200]}"})
        store.put("default", "connector_seen", source.id, seen)
    return {"source": source.id, "copied": copied, "assessed": assessed, "unchanged": skipped, "errors": errors,
            "folder": str(root)}


def sync_deals(source: DealSource, *, actor: str = "") -> dict[str, Any]:
    from impact_vision.impact.storage import get_assessment_store

    store = get_assessment_store()
    added, moved, unchanged, unmapped = [], [], 0, []
    for deal in source.list_deals():
        entry = store.get_pipeline_entry(deal.name)
        if entry is None:
            store.upsert_pipeline_entry(deal.name, pipeline_stage=deal.stage or "sourcing", sector=deal.sector,
                                        geography=deal.geography, assigned_to=deal.owner,
                                        notes=f"Imported from {source.id} ({deal.source_id})")
            added.append(deal.name)
        elif deal.stage and deal.stage != entry.get("pipeline_stage"):
            store.transition_stage(deal.name, deal.stage, actor=actor or f"{source.id} sync",
                                   rationale=f"Stage changed in {source.id}")
            moved.append({"company": deal.name, "from": entry.get("pipeline_stage"), "to": deal.stage})
        else:
            unchanged += 1
        if not deal.stage:
            unmapped.append(deal.name)
    return {"source": source.id, "added": added, "moved": moved, "unchanged": unchanged,
            "stage_not_mapped": unmapped}


__all__ = ["sync_deals", "sync_documents"]
