"""Who is acting, and for which tenant (roadmap v8 W5.3).

Every request runs as one :class:`Identity`, held in a context variable so it
follows the request into tools, background tasks and the state store without
being threaded through every call.

* **Local mode** (default): one user, tenant ``default``, all permissions,
  exactly as before. Nothing changes for a single analyst on a laptop.
* **OIDC mode** (``IMPACT_VISION_OIDC_ISSUER`` set): the web app signs people
  in with the identity provider; their tenant and roles come from the ID
  token (see ``api_gateway/oidc.py``).

Tenant isolation is enforced where data lives, not in each route:
:func:`tenant_home` gives each tenant its own folder for chat transcripts,
uploads, reports and the assessment database, and :class:`TenantGuard` makes
the state store refuse another tenant's rows.
"""
from __future__ import annotations

import re
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

from impact_vision.impact.tenancy import BUILTIN_ROLES

DEFAULT_TENANT = "default"
_TENANT_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")


@dataclass(frozen=True)
class Identity:
    sub: str
    tenant_id: str = DEFAULT_TENANT
    roles: tuple[str, ...] = ("tenant_admin",)
    email: str = ""
    name: str = ""
    auth: str = "local"  # local | oidc | api_key
    claims: dict[str, Any] = field(default_factory=dict, compare=False, hash=False)

    @property
    def permissions(self) -> frozenset[str]:
        return frozenset(p for r in self.roles for p in BUILTIN_ROLES.get(r, []))

    def can(self, permission: str) -> bool:
        return permission in self.permissions

    @property
    def is_admin(self) -> bool:
        return "tenant_admin" in self.roles


LOCAL = Identity(sub="local", name="Local user")
_CURRENT: ContextVar[Identity] = ContextVar("impact_vision_identity", default=LOCAL)


def current_identity() -> Identity:
    return _CURRENT.get()


def current_tenant() -> str:
    return _CURRENT.get().tenant_id


@contextmanager
def acting_as(identity: Identity) -> Iterator[Identity]:
    """Run a block as ``identity`` (requests, share links, tests)."""
    token = _CURRENT.set(identity)
    try:
        yield identity
    finally:
        _CURRENT.reset(token)


def valid_tenant_id(tenant_id: str) -> bool:
    return bool(_TENANT_RE.match(tenant_id or ""))


def tenant_home(root: Path, tenant_id: str | None = None) -> Path:
    """``root`` for the default tenant, ``root/tenants/<id>`` for any other."""
    tenant = tenant_id or current_tenant()
    if tenant == DEFAULT_TENANT:
        return root
    if not valid_tenant_id(tenant):
        raise PermissionError(f"invalid tenant id {tenant!r}")
    return root / "tenants" / tenant


class TenantGuard:
    """State-store view for one tenant.

    Code written before tenancy passes ``"default"``; it is mapped to the
    current tenant. Asking for any other tenant is refused.
    """

    def __init__(self, store: Any, tenant_id: str) -> None:
        self._store, self._tenant = store, tenant_id

    def _t(self, tenant_id: str) -> str:
        if tenant_id in (DEFAULT_TENANT, "", self._tenant):
            return self._tenant
        raise PermissionError(f"tenant {self._tenant!r} may not access tenant {tenant_id!r}")

    def get(self, tenant_id: str, kind: str, key: str) -> dict[str, Any] | None:
        result: dict[str, Any] | None = self._store.get(self._t(tenant_id), kind, key)
        return result

    def put(self, tenant_id: str, kind: str, key: str, payload: dict[str, Any]) -> None:
        self._store.put(self._t(tenant_id), kind, key, payload)

    def delete(self, tenant_id: str, kind: str, key: str) -> None:
        self._store.delete(self._t(tenant_id), kind, key)

    def keys(self, tenant_id: str, kind: str) -> list[str]:
        result: list[str] = self._store.keys(self._t(tenant_id), kind)
        return result

    def __getattr__(self, name: str) -> Any:  # close(), schema_version, …
        return getattr(self._store, name)


__all__ = ["DEFAULT_TENANT", "LOCAL", "Identity", "TenantGuard", "acting_as", "current_identity",
           "current_tenant", "tenant_home", "valid_tenant_id"]
