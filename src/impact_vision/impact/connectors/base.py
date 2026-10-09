"""Connector interface and registry (roadmap v8 W3.5)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Callable, Protocol, runtime_checkable

import httpx

SUPPORTED_SUFFIXES = (".pdf", ".docx", ".pptx", ".txt", ".md", ".xlsx", ".csv")


@dataclass(frozen=True)
class DocumentRef:
    id: str
    name: str
    modified: str = ""
    size: int | None = None
    company: str = ""  # from the folder it sits in, when the source has one per company
    source: str = ""


@dataclass
class Deal:
    name: str
    stage: str = ""
    sector: str = ""
    geography: str = ""
    owner: str = ""
    source_id: str = ""
    fields: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class DocumentSource(Protocol):
    id: str

    def list_documents(self) -> list[DocumentRef]: ...

    def fetch(self, doc: DocumentRef) -> bytes: ...


@runtime_checkable
class DealSource(Protocol):
    id: str

    def list_deals(self) -> list[Deal]: ...


def env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is not set")
    return value


def http_client(transport: httpx.BaseTransport | None = None) -> httpx.Client:
    """No redirects to other hosts: connectors only talk to their fixed API host."""
    return httpx.Client(timeout=30, transport=transport, follow_redirects=False)


def supported(name: str) -> bool:
    return name.lower().endswith(SUPPORTED_SUFFIXES)


def _registry() -> dict[str, Callable[..., Any]]:
    from impact_vision.impact.connectors.crm import AffinitySource, DealCloudSource
    from impact_vision.impact.connectors.documents import FolderSource, GoogleDriveSource, SharePointSource

    return {"folder": FolderSource, "gdrive": GoogleDriveSource, "sharepoint": SharePointSource,
            "affinity": AffinitySource, "dealcloud": DealCloudSource}


CONNECTORS = ("folder", "gdrive", "sharepoint", "affinity", "dealcloud")


def get_connector(name: str, **config: Any) -> Any:
    try:
        return _registry()[name](**config)
    except KeyError:
        raise ValueError(f"unknown connector {name!r}; choose from {', '.join(CONNECTORS)}") from None


__all__ = ["CONNECTORS", "Deal", "DealSource", "DocumentRef", "DocumentSource", "env", "get_connector",
           "http_client", "supported"]
