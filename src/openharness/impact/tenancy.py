"""Multi-tenant + role-based access control (RBAC) for Impact Vision.

This is the *model layer* — it does not by itself enforce auth on FastAPI
routes (that lives in `api_gateway`). It defines:

  * `Tenant`       — a GP / fund family (data isolation boundary).
  * `User`         — a person inside a Tenant.
  * `Role`         — a named bundle of `Permission`s.
  * `Permission`   — a fine-grained capability (e.g. ``deal:write``).
  * `RBACPolicy`   — pure, in-memory authorisation evaluator.

Persistence is intentionally pluggable: the default `InMemoryRBACStore`
keeps everything in a dict (perfect for tests / single-tenant deploys); a
production deployment swaps it for Postgres / OIDC / Auth0 by writing a
class that satisfies the same `RBACStore` Protocol.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Permission catalogue — kept as constants so typos surface at import time.
# ---------------------------------------------------------------------------

PERM_DEAL_READ = "deal:read"
PERM_DEAL_WRITE = "deal:write"
PERM_DEAL_DELETE = "deal:delete"
PERM_THESIS_READ = "thesis:read"
PERM_THESIS_WRITE = "thesis:write"
PERM_PORTFOLIO_READ = "portfolio:read"
PERM_PORTFOLIO_WRITE = "portfolio:write"
PERM_REPORT_GENERATE = "report:generate"
PERM_REPORT_PUBLISH_LP = "report:publish_lp"
PERM_USER_ADMIN = "user:admin"
PERM_TENANT_ADMIN = "tenant:admin"

ALL_PERMISSIONS: tuple[str, ...] = (
    PERM_DEAL_READ, PERM_DEAL_WRITE, PERM_DEAL_DELETE,
    PERM_THESIS_READ, PERM_THESIS_WRITE,
    PERM_PORTFOLIO_READ, PERM_PORTFOLIO_WRITE,
    PERM_REPORT_GENERATE, PERM_REPORT_PUBLISH_LP,
    PERM_USER_ADMIN, PERM_TENANT_ADMIN,
)


# Built-in role presets — GPs typically use these as a starting point.
BUILTIN_ROLES: dict[str, list[str]] = {
    "viewer": [PERM_DEAL_READ, PERM_THESIS_READ, PERM_PORTFOLIO_READ],
    "analyst": [
        PERM_DEAL_READ, PERM_DEAL_WRITE,
        PERM_THESIS_READ, PERM_PORTFOLIO_READ,
        PERM_REPORT_GENERATE,
    ],
    "ic_member": [
        PERM_DEAL_READ, PERM_DEAL_WRITE,
        PERM_THESIS_READ, PERM_THESIS_WRITE,
        PERM_PORTFOLIO_READ, PERM_PORTFOLIO_WRITE,
        PERM_REPORT_GENERATE,
    ],
    "lp_relations": [
        PERM_DEAL_READ, PERM_THESIS_READ, PERM_PORTFOLIO_READ,
        PERM_REPORT_GENERATE, PERM_REPORT_PUBLISH_LP,
    ],
    "tenant_admin": list(ALL_PERMISSIONS),
}


class Tenant(BaseModel):
    id: str
    name: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    settings: dict = Field(default_factory=dict)


class Role(BaseModel):
    name: str
    permissions: list[str] = Field(default_factory=list)

    @field_validator("permissions")
    @classmethod
    def _validate_perms(cls, v: list[str]) -> list[str]:
        unknown = [p for p in v if p not in ALL_PERMISSIONS]
        if unknown:
            raise ValueError(f"Unknown permissions: {unknown}. Valid: {ALL_PERMISSIONS}")
        return v


class User(BaseModel):
    id: str
    tenant_id: str
    email: str
    display_name: str = ""
    role_names: list[str] = Field(default_factory=list)
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class AuthorizationDecision:
    allowed: bool
    reason: str
    user_id: str | None = None
    permission: str | None = None
    resource_tenant_id: str | None = None


# ---------------------------------------------------------------------------
# Pluggable persistence layer
# ---------------------------------------------------------------------------

@runtime_checkable
class RBACStore(Protocol):
    def get_tenant(self, tenant_id: str) -> Tenant | None: ...
    def get_user(self, user_id: str) -> User | None: ...
    def get_role(self, tenant_id: str, role_name: str) -> Role | None: ...
    def list_roles(self, tenant_id: str) -> list[Role]: ...
    def upsert_tenant(self, tenant: Tenant) -> None: ...
    def upsert_user(self, user: User) -> None: ...
    def upsert_role(self, tenant_id: str, role: Role) -> None: ...


class InMemoryRBACStore:
    """Default in-memory store. Thread-safety is the caller's responsibility."""
    def __init__(self) -> None:
        self._tenants: dict[str, Tenant] = {}
        self._users: dict[str, User] = {}
        self._roles: dict[tuple[str, str], Role] = {}

    def get_tenant(self, tenant_id: str) -> Tenant | None:
        return self._tenants.get(tenant_id)

    def get_user(self, user_id: str) -> User | None:
        return self._users.get(user_id)

    def get_role(self, tenant_id: str, role_name: str) -> Role | None:
        if (tenant_id, role_name) in self._roles:
            return self._roles[(tenant_id, role_name)]
        if role_name in BUILTIN_ROLES:
            return Role(name=role_name, permissions=BUILTIN_ROLES[role_name])
        return None

    def list_roles(self, tenant_id: str) -> list[Role]:
        explicit = [v for (tid, _), v in self._roles.items() if tid == tenant_id]
        builtins = [Role(name=n, permissions=p) for n, p in BUILTIN_ROLES.items()]
        return builtins + explicit

    def upsert_tenant(self, tenant: Tenant) -> None:
        self._tenants[tenant.id] = tenant

    def upsert_user(self, user: User) -> None:
        self._users[user.id] = user

    def upsert_role(self, tenant_id: str, role: Role) -> None:
        self._roles[(tenant_id, role.name)] = role


# ---------------------------------------------------------------------------
# Authorisation evaluator
# ---------------------------------------------------------------------------

class RBACPolicy:
    """Pure-function authorisation evaluator.

    Always denies by default. Evaluates:
      1. user is active
      2. user belongs to the same tenant as the resource
      3. one of the user's roles grants the required permission
    """
    def __init__(self, store: RBACStore) -> None:
        self.store = store

    def is_allowed(
        self,
        user_id: str,
        permission: str,
        *,
        resource_tenant_id: str | None = None,
    ) -> AuthorizationDecision:
        if permission not in ALL_PERMISSIONS:
            return AuthorizationDecision(False, f"Unknown permission '{permission}'.",
                                         user_id, permission, resource_tenant_id)

        user = self.store.get_user(user_id)
        if not user:
            return AuthorizationDecision(False, f"User '{user_id}' not found.",
                                         user_id, permission, resource_tenant_id)
        if not user.is_active:
            return AuthorizationDecision(False, "User is inactive.",
                                         user_id, permission, resource_tenant_id)
        if resource_tenant_id and user.tenant_id != resource_tenant_id:
            return AuthorizationDecision(False, "Cross-tenant access denied.",
                                         user_id, permission, resource_tenant_id)

        for role_name in user.role_names:
            role = self.store.get_role(user.tenant_id, role_name)
            if role and permission in role.permissions:
                return AuthorizationDecision(True, f"Granted via role '{role_name}'.",
                                             user_id, permission, resource_tenant_id)

        return AuthorizationDecision(False, "No role grants this permission.",
                                     user_id, permission, resource_tenant_id)

    def require(
        self,
        user_id: str,
        permission: str,
        *,
        resource_tenant_id: str | None = None,
    ) -> None:
        """Raise `PermissionError` if not allowed — convenience for service code."""
        d = self.is_allowed(user_id, permission, resource_tenant_id=resource_tenant_id)
        if not d.allowed:
            raise PermissionError(f"{permission}: {d.reason}")

    def visible_tenants(self, user_id: str) -> list[str]:
        """Return the set of tenant IDs the user may see — usually just their own."""
        user = self.store.get_user(user_id)
        return [user.tenant_id] if user and user.is_active else []


def make_tenant_id(name: str) -> str:
    """Stable, URL-safe ID derived from a tenant name."""
    h = hashlib.sha256(name.encode("utf-8")).hexdigest()[:10]
    slug = "".join(c if c.isalnum() else "-" for c in name.lower()).strip("-")
    return f"{slug}-{h}"


def bootstrap_tenant(store: RBACStore, name: str, admin_email: str) -> tuple[Tenant, User]:
    """Provision a brand-new tenant with one tenant_admin user.

    Returns the created `(Tenant, User)`. The caller is responsible for
    storing the admin's authentication credential — RBAC here is purely
    authorisation, not authentication.
    """
    tenant_id = make_tenant_id(name)
    tenant = Tenant(id=tenant_id, name=name)
    store.upsert_tenant(tenant)

    user_id = f"{tenant_id}::admin"
    user = User(
        id=user_id, tenant_id=tenant_id, email=admin_email,
        display_name="Tenant Admin", role_names=["tenant_admin"],
    )
    store.upsert_user(user)
    return tenant, user
