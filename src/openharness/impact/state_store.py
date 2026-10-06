"""Pluggable, tenant-scoped persistence for consultant state (v7 W5.3).

Before W5.3 the engagement workspace, audit trail, review queues, RBAC and the
regulatory-radar queue lived only in memory, so a restart lost a consultant's
work. Each of them now saves a JSON document to a :class:`StateStore` keyed by
``(tenant_id, kind, key)`` and restores it on construction.

Backends, chosen by ``IMPACT_VISION_STATE_STORE``:

* ``sqlite`` (default): one table in ``IMPACT_VISION_STATE_DB``, defaulting to
  ``~/.impact-vision/state.db`` (next to the assessment store).
* ``postgres``: ``IMPACT_VISION_STATE_DSN`` (needs ``psycopg``; same table).
* ``memory``: per-process, nothing written to disk (tests, ephemeral demos).
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

_TABLE = """
CREATE TABLE IF NOT EXISTS iv_state (
    tenant_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    key TEXT NOT NULL,
    payload TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (tenant_id, kind, key)
)
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@runtime_checkable
class StateStore(Protocol):
    def get(self, tenant_id: str, kind: str, key: str) -> dict[str, Any] | None: ...
    def put(self, tenant_id: str, kind: str, key: str, payload: dict[str, Any]) -> None: ...
    def delete(self, tenant_id: str, kind: str, key: str) -> None: ...
    def keys(self, tenant_id: str, kind: str) -> list[str]: ...


class MemoryStateStore:
    """Per-process store (copies payloads so callers can't alias stored state)."""

    def __init__(self) -> None:
        self._data: dict[tuple[str, str, str], str] = {}

    def get(self, tenant_id: str, kind: str, key: str) -> dict[str, Any] | None:
        raw = self._data.get((tenant_id, kind, key))
        return json.loads(raw) if raw is not None else None

    def put(self, tenant_id: str, kind: str, key: str, payload: dict[str, Any]) -> None:
        self._data[(tenant_id, kind, key)] = json.dumps(payload, default=str)

    def delete(self, tenant_id: str, kind: str, key: str) -> None:
        self._data.pop((tenant_id, kind, key), None)

    def keys(self, tenant_id: str, kind: str) -> list[str]:
        return sorted(k for t, kd, k in self._data if t == tenant_id and kd == kind)


class SQLiteStateStore:
    """SQLite backend (default). Safe across threads; WAL for concurrent readers."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path else default_state_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(str(self.path), check_same_thread=False)
        with self._lock:
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute(_TABLE)
            self._conn.commit()

    def get(self, tenant_id: str, kind: str, key: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT payload FROM iv_state WHERE tenant_id=? AND kind=? AND key=?",
                (tenant_id, kind, key),
            ).fetchone()
        return json.loads(row[0]) if row else None

    def put(self, tenant_id: str, kind: str, key: str, payload: dict[str, Any]) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO iv_state (tenant_id, kind, key, payload, updated_at) VALUES (?,?,?,?,?) "
                "ON CONFLICT(tenant_id, kind, key) DO UPDATE SET payload=excluded.payload, "
                "updated_at=excluded.updated_at",
                (tenant_id, kind, key, json.dumps(payload, default=str), _now()),
            )
            self._conn.commit()

    def delete(self, tenant_id: str, kind: str, key: str) -> None:
        with self._lock:
            self._conn.execute(
                "DELETE FROM iv_state WHERE tenant_id=? AND kind=? AND key=?", (tenant_id, kind, key)
            )
            self._conn.commit()

    def keys(self, tenant_id: str, kind: str) -> list[str]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT key FROM iv_state WHERE tenant_id=? AND kind=? ORDER BY key", (tenant_id, kind)
            ).fetchall()
        return [r[0] for r in rows]

    def close(self) -> None:
        self._conn.close()


class PostgresStateStore:
    """Postgres backend (optional; ``pip install psycopg``). Same schema as SQLite."""

    def __init__(self, dsn: str | None = None, *, connection: Any | None = None) -> None:
        if connection is None:
            try:
                import psycopg  # type: ignore[import-not-found]
            except ImportError as exc:  # pragma: no cover - optional dependency
                raise RuntimeError(
                    "PostgresStateStore needs psycopg: pip install 'psycopg[binary]'"
                ) from exc
            connection = psycopg.connect(dsn or os.environ["IMPACT_VISION_STATE_DSN"])
        self._conn = connection
        self._lock = threading.Lock()
        with self._lock, self._conn.cursor() as cur:
            cur.execute(_TABLE)
        self._conn.commit()

    def _one(self, sql: str, params: tuple) -> Any:
        with self._lock, self._conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()

    def get(self, tenant_id: str, kind: str, key: str) -> dict[str, Any] | None:
        rows = self._one(
            "SELECT payload FROM iv_state WHERE tenant_id=%s AND kind=%s AND key=%s", (tenant_id, kind, key)
        )
        return json.loads(rows[0][0]) if rows else None

    def put(self, tenant_id: str, kind: str, key: str, payload: dict[str, Any]) -> None:
        with self._lock, self._conn.cursor() as cur:
            cur.execute(
                "INSERT INTO iv_state (tenant_id, kind, key, payload, updated_at) VALUES (%s,%s,%s,%s,%s) "
                "ON CONFLICT (tenant_id, kind, key) DO UPDATE SET payload=EXCLUDED.payload, "
                "updated_at=EXCLUDED.updated_at",
                (tenant_id, kind, key, json.dumps(payload, default=str), _now()),
            )
        self._conn.commit()

    def delete(self, tenant_id: str, kind: str, key: str) -> None:
        with self._lock, self._conn.cursor() as cur:
            cur.execute(
                "DELETE FROM iv_state WHERE tenant_id=%s AND kind=%s AND key=%s", (tenant_id, kind, key)
            )
        self._conn.commit()

    def keys(self, tenant_id: str, kind: str) -> list[str]:
        rows = self._one(
            "SELECT key FROM iv_state WHERE tenant_id=%s AND kind=%s ORDER BY key", (tenant_id, kind)
        )
        return [r[0] for r in rows]


def default_state_path() -> Path:
    env = os.environ.get("IMPACT_VISION_STATE_DB", "").strip()
    if env:
        return Path(env).expanduser()
    return Path.home() / ".impact-vision" / "state.db"


_STORE: StateStore | None = None
_STORE_LOCK = threading.Lock()


def get_state_store() -> StateStore:
    """Process-wide store selected by ``IMPACT_VISION_STATE_STORE``."""
    global _STORE
    with _STORE_LOCK:
        if _STORE is None:
            backend = os.environ.get("IMPACT_VISION_STATE_STORE", "sqlite").strip().lower()
            if backend == "memory":
                _STORE = MemoryStateStore()
            elif backend == "postgres":
                _STORE = PostgresStateStore()
            else:
                _STORE = SQLiteStateStore()
        return _STORE


def set_state_store(store: StateStore | None) -> None:
    """Install a store (or ``None`` to re-resolve from the environment)."""
    global _STORE
    with _STORE_LOCK:
        _STORE = store


__all__ = [
    "MemoryStateStore",
    "PostgresStateStore",
    "SQLiteStateStore",
    "StateStore",
    "default_state_path",
    "get_state_store",
    "set_state_store",
]
