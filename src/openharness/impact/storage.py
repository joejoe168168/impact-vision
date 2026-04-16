"""SQLite-based persistence layer for Impact Vision assessments.

Stores company assessment snapshots and tool invocation history
so state can be preserved across sessions.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


_DEFAULT_DB_PATH = Path("data/impact_vision.db")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS assessments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_name TEXT NOT NULL,
    company_json TEXT NOT NULL,
    five_dimensions_json TEXT,
    sdg_alignments_json TEXT,
    gap_analysis_json TEXT,
    greenwashing_json TEXT,
    metadata_json TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_assessments_company ON assessments(company_name);
CREATE INDEX IF NOT EXISTS idx_assessments_created ON assessments(created_at);

CREATE TABLE IF NOT EXISTS session_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    company_name TEXT NOT NULL,
    tool_name TEXT NOT NULL,
    input_json TEXT,
    output_summary TEXT,
    metadata_json TEXT,
    timestamp TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_session_company ON session_history(company_name);
CREATE INDEX IF NOT EXISTS idx_session_session ON session_history(session_id);
CREATE INDEX IF NOT EXISTS idx_session_ts ON session_history(timestamp);
"""


class AssessmentStore:
    """SQLite-backed store for company assessments and session history."""

    def __init__(self, db_path: str | Path | None = None) -> None:
        self._db_path = str(db_path or _DEFAULT_DB_PATH)
        self._local = threading.local()
        self._ensure_schema()

    def _get_conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
            self._local.conn = sqlite3.connect(self._db_path)
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn

    def _ensure_schema(self) -> None:
        conn = self._get_conn()
        conn.executescript(_SCHEMA)
        conn.commit()

    def save_assessment(
        self,
        company_name: str,
        company_data: dict,
        five_dimensions: dict | None = None,
        sdg_alignments: list | None = None,
        gap_analysis: dict | None = None,
        greenwashing: dict | None = None,
        metadata: dict | None = None,
    ) -> int:
        """Save or update a company assessment. Returns the row ID."""
        now = datetime.now(timezone.utc).isoformat()
        conn = self._get_conn()

        existing = conn.execute(
            "SELECT id FROM assessments WHERE company_name = ? ORDER BY created_at DESC LIMIT 1",
            (company_name,),
        ).fetchone()

        if existing:
            conn.execute(
                """UPDATE assessments
                   SET company_json = ?, five_dimensions_json = ?, sdg_alignments_json = ?,
                       gap_analysis_json = ?, greenwashing_json = ?, metadata_json = ?, updated_at = ?
                   WHERE id = ?""",
                (
                    json.dumps(company_data),
                    json.dumps(five_dimensions) if five_dimensions else None,
                    json.dumps(sdg_alignments) if sdg_alignments else None,
                    json.dumps(gap_analysis) if gap_analysis else None,
                    json.dumps(greenwashing) if greenwashing else None,
                    json.dumps(metadata) if metadata else None,
                    now,
                    existing["id"],
                ),
            )
            conn.commit()
            return existing["id"]

        cursor = conn.execute(
            """INSERT INTO assessments
               (company_name, company_json, five_dimensions_json, sdg_alignments_json,
                gap_analysis_json, greenwashing_json, metadata_json, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                company_name,
                json.dumps(company_data),
                json.dumps(five_dimensions) if five_dimensions else None,
                json.dumps(sdg_alignments) if sdg_alignments else None,
                json.dumps(gap_analysis) if gap_analysis else None,
                json.dumps(greenwashing) if greenwashing else None,
                json.dumps(metadata) if metadata else None,
                now,
                now,
            ),
        )
        conn.commit()
        return cursor.lastrowid  # type: ignore[return-value]

    def get_assessment(self, company_name: str) -> dict | None:
        """Retrieve the latest assessment for a company."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM assessments WHERE company_name = ? ORDER BY updated_at DESC LIMIT 1",
            (company_name,),
        ).fetchone()
        if not row:
            return None
        return _row_to_assessment(row)

    def list_assessments(self, limit: int = 50) -> list[dict]:
        """List recent assessments (summary only)."""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT id, company_name, created_at, updated_at FROM assessments ORDER BY updated_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [
            {"id": r["id"], "company_name": r["company_name"],
             "created_at": r["created_at"], "updated_at": r["updated_at"]}
            for r in rows
        ]

    def delete_assessment(self, company_name: str) -> bool:
        """Delete all assessments for a company."""
        conn = self._get_conn()
        cursor = conn.execute("DELETE FROM assessments WHERE company_name = ?", (company_name,))
        conn.commit()
        return cursor.rowcount > 0

    def log_tool_invocation(
        self,
        session_id: str,
        company_name: str,
        tool_name: str,
        input_data: dict | None = None,
        output_summary: str = "",
        metadata: dict | None = None,
    ) -> int:
        """Log a tool invocation to session history."""
        now = datetime.now(timezone.utc).isoformat()
        conn = self._get_conn()
        cursor = conn.execute(
            """INSERT INTO session_history
               (session_id, company_name, tool_name, input_json, output_summary, metadata_json, timestamp)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                session_id,
                company_name,
                tool_name,
                json.dumps(input_data) if input_data else None,
                output_summary,
                json.dumps(metadata) if metadata else None,
                now,
            ),
        )
        conn.commit()
        return cursor.lastrowid  # type: ignore[return-value]

    def get_session_history(
        self,
        company_name: str | None = None,
        session_id: str | None = None,
        limit: int = 100,
    ) -> list[dict]:
        """Retrieve session history, optionally filtered by company or session."""
        conn = self._get_conn()
        query = "SELECT * FROM session_history"
        params: list[Any] = []

        conditions = []
        if company_name:
            conditions.append("company_name = ?")
            params.append(company_name)
        if session_id:
            conditions.append("session_id = ?")
            params.append(session_id)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(query, params).fetchall()
        return [
            {
                "id": r["id"],
                "session_id": r["session_id"],
                "company_name": r["company_name"],
                "tool_name": r["tool_name"],
                "input": json.loads(r["input_json"]) if r["input_json"] else None,
                "output_summary": r["output_summary"],
                "metadata": json.loads(r["metadata_json"]) if r["metadata_json"] else None,
                "timestamp": r["timestamp"],
            }
            for r in rows
        ]

    def close(self) -> None:
        """Close the database connection."""
        if hasattr(self._local, "conn") and self._local.conn:
            self._local.conn.close()
            self._local.conn = None


def _row_to_assessment(row: sqlite3.Row) -> dict:
    """Convert a database row to an assessment dict."""
    result: dict[str, Any] = {
        "id": row["id"],
        "company_name": row["company_name"],
        "company": json.loads(row["company_json"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }
    for field in ("five_dimensions", "sdg_alignments", "gap_analysis", "greenwashing", "metadata"):
        json_field = f"{field}_json"
        val = row[json_field]
        result[field] = json.loads(val) if val else None
    return result


_global_store: AssessmentStore | None = None


def get_assessment_store(db_path: str | Path | None = None) -> AssessmentStore:
    """Get the global AssessmentStore singleton (lazy-initialized)."""
    global _global_store
    if _global_store is None:
        _global_store = AssessmentStore(db_path)
    return _global_store
