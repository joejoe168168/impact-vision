"""Read-only connectors: documents and deals from where funds keep them (roadmap v8 W3.5).

* Documents: a data-room export folder, Google Drive, SharePoint / OneDrive.
* Deals: Affinity and DealCloud lists, synced into the pipeline.

Every connector only reads. Tokens come from environment variables and are
never logged or stored. Hosts are fixed (Google, Microsoft Graph, Affinity,
your DealCloud tenant), so a document can't redirect a request elsewhere.
:mod:`.sync` copies new or changed documents into the uploads folder (and can
assess them) and upserts deals into the pipeline, remembering what it has seen.
"""
from __future__ import annotations

from impact_vision.impact.connectors.base import Deal, DealSource, DocumentRef, DocumentSource, get_connector, CONNECTORS

__all__ = ["CONNECTORS", "Deal", "DealSource", "DocumentRef", "DocumentSource", "get_connector"]
