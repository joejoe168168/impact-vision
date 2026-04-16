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

CREATE TABLE IF NOT EXISTS pipeline (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_name TEXT NOT NULL UNIQUE,
    pipeline_stage TEXT NOT NULL DEFAULT 'sourcing',
    assigned_to TEXT DEFAULT '',
    priority TEXT DEFAULT 'medium',
    tags_json TEXT DEFAULT '[]',
    sector TEXT DEFAULT '',
    geography TEXT DEFAULT '',
    sdg_focus_json TEXT DEFAULT '[]',
    investment_size REAL,
    notes TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_pipeline_stage ON pipeline(pipeline_stage);
CREATE INDEX IF NOT EXISTS idx_pipeline_sector ON pipeline(sector);

CREATE TABLE IF NOT EXISTS stage_transitions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_name TEXT NOT NULL,
    from_stage TEXT DEFAULT '',
    to_stage TEXT NOT NULL,
    actor TEXT DEFAULT '',
    rationale TEXT DEFAULT '',
    notes TEXT DEFAULT '',
    timestamp TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_transitions_company ON stage_transitions(company_name);

CREATE TABLE IF NOT EXISTS monitoring_schedules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_name TEXT NOT NULL UNIQUE,
    frequency TEXT DEFAULT 'quarterly',
    next_review_date TEXT DEFAULT '',
    last_review_date TEXT DEFAULT '',
    alert_thresholds_json TEXT DEFAULT '{}',
    watch_metrics_json TEXT DEFAULT '[]',
    status TEXT DEFAULT 'active',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS monitoring_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_name TEXT NOT NULL,
    alert_type TEXT NOT NULL,
    severity TEXT DEFAULT 'warning',
    message TEXT DEFAULT '',
    metric_id TEXT DEFAULT '',
    current_value REAL,
    threshold_value REAL,
    created_at TEXT NOT NULL,
    acknowledged INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_alerts_company ON monitoring_alerts(company_name);
CREATE INDEX IF NOT EXISTS idx_alerts_ack ON monitoring_alerts(acknowledged);
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

    # --- Pipeline Management ---

    def upsert_pipeline_entry(
        self,
        company_name: str,
        pipeline_stage: str = "sourcing",
        assigned_to: str = "",
        priority: str = "medium",
        tags: list[str] | None = None,
        sector: str = "",
        geography: str = "",
        sdg_focus: list[int] | None = None,
        investment_size: float | None = None,
        notes: str = "",
    ) -> int:
        """Create or update a pipeline entry. Returns the row ID."""
        now = datetime.now(timezone.utc).isoformat()
        conn = self._get_conn()
        existing = conn.execute(
            "SELECT id, pipeline_stage FROM pipeline WHERE company_name = ?",
            (company_name,),
        ).fetchone()

        if existing:
            old_stage = existing["pipeline_stage"]
            conn.execute(
                """UPDATE pipeline SET pipeline_stage=?, assigned_to=?, priority=?,
                   tags_json=?, sector=?, geography=?, sdg_focus_json=?,
                   investment_size=?, notes=?, updated_at=?
                   WHERE id=?""",
                (
                    pipeline_stage, assigned_to, priority,
                    json.dumps(tags or []), sector, geography,
                    json.dumps(sdg_focus or []), investment_size, notes, now,
                    existing["id"],
                ),
            )
            if old_stage != pipeline_stage:
                self._log_transition(company_name, old_stage, pipeline_stage, "", "", now)
            conn.commit()
            return existing["id"]

        cursor = conn.execute(
            """INSERT INTO pipeline
               (company_name, pipeline_stage, assigned_to, priority, tags_json,
                sector, geography, sdg_focus_json, investment_size, notes,
                created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                company_name, pipeline_stage, assigned_to, priority,
                json.dumps(tags or []), sector, geography,
                json.dumps(sdg_focus or []), investment_size, notes, now, now,
            ),
        )
        conn.commit()
        return cursor.lastrowid  # type: ignore[return-value]

    def get_pipeline_entry(self, company_name: str) -> dict | None:
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM pipeline WHERE company_name = ?", (company_name,),
        ).fetchone()
        return _row_to_pipeline(row) if row else None

    def list_pipeline(
        self,
        stage: str | None = None,
        sector: str | None = None,
        sdg: int | None = None,
        priority: str | None = None,
        limit: int = 200,
    ) -> list[dict]:
        conn = self._get_conn()
        query = "SELECT * FROM pipeline"
        params: list[Any] = []
        conditions = []
        if stage:
            conditions.append("pipeline_stage = ?")
            params.append(stage)
        if sector:
            conditions.append("sector = ?")
            params.append(sector)
        if priority:
            conditions.append("priority = ?")
            params.append(priority)
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY updated_at DESC LIMIT ?"
        params.append(limit)
        rows = conn.execute(query, params).fetchall()
        results = [_row_to_pipeline(r) for r in rows]
        if sdg is not None:
            results = [r for r in results if sdg in r.get("sdg_focus", [])]
        return results

    def transition_stage(
        self,
        company_name: str,
        new_stage: str,
        actor: str = "",
        rationale: str = "",
        notes: str = "",
    ) -> bool:
        """Move a company to a new pipeline stage with a recorded transition."""
        now = datetime.now(timezone.utc).isoformat()
        conn = self._get_conn()
        row = conn.execute(
            "SELECT id, pipeline_stage FROM pipeline WHERE company_name = ?",
            (company_name,),
        ).fetchone()
        if not row:
            return False
        old_stage = row["pipeline_stage"]
        conn.execute(
            "UPDATE pipeline SET pipeline_stage=?, updated_at=? WHERE id=?",
            (new_stage, now, row["id"]),
        )
        self._log_transition(company_name, old_stage, new_stage, actor, rationale, now, notes)
        conn.commit()
        return True

    def _log_transition(
        self, company: str, from_s: str, to_s: str,
        actor: str, rationale: str, ts: str, notes: str = "",
    ) -> None:
        conn = self._get_conn()
        conn.execute(
            """INSERT INTO stage_transitions
               (company_name, from_stage, to_stage, actor, rationale, notes, timestamp)
               VALUES (?,?,?,?,?,?,?)""",
            (company, from_s, to_s, actor, rationale, notes, ts),
        )

    def get_transitions(self, company_name: str) -> list[dict]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM stage_transitions WHERE company_name = ? ORDER BY timestamp",
            (company_name,),
        ).fetchall()
        return [
            {
                "from_stage": r["from_stage"], "to_stage": r["to_stage"],
                "actor": r["actor"], "rationale": r["rationale"],
                "notes": r["notes"], "timestamp": r["timestamp"],
            }
            for r in rows
        ]

    def delete_pipeline_entry(self, company_name: str) -> bool:
        conn = self._get_conn()
        cursor = conn.execute("DELETE FROM pipeline WHERE company_name = ?", (company_name,))
        conn.execute("DELETE FROM stage_transitions WHERE company_name = ?", (company_name,))
        conn.commit()
        return cursor.rowcount > 0

    def pipeline_summary(self) -> dict:
        """Get pipeline funnel summary: count per stage."""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT pipeline_stage, COUNT(*) as cnt FROM pipeline GROUP BY pipeline_stage"
        ).fetchall()
        return {r["pipeline_stage"]: r["cnt"] for r in rows}

    # --- Monitoring ---

    def upsert_monitoring_schedule(
        self,
        company_name: str,
        frequency: str = "quarterly",
        next_review_date: str = "",
        alert_thresholds: dict | None = None,
        watch_metrics: list[str] | None = None,
        status: str = "active",
    ) -> int:
        now = datetime.now(timezone.utc).isoformat()
        conn = self._get_conn()
        existing = conn.execute(
            "SELECT id FROM monitoring_schedules WHERE company_name = ?",
            (company_name,),
        ).fetchone()
        if existing:
            conn.execute(
                """UPDATE monitoring_schedules SET frequency=?, next_review_date=?,
                   alert_thresholds_json=?, watch_metrics_json=?, status=?, updated_at=?
                   WHERE id=?""",
                (
                    frequency, next_review_date,
                    json.dumps(alert_thresholds or {}),
                    json.dumps(watch_metrics or []), status, now, existing["id"],
                ),
            )
            conn.commit()
            return existing["id"]
        cursor = conn.execute(
            """INSERT INTO monitoring_schedules
               (company_name, frequency, next_review_date, last_review_date,
                alert_thresholds_json, watch_metrics_json, status, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (
                company_name, frequency, next_review_date, "",
                json.dumps(alert_thresholds or {}),
                json.dumps(watch_metrics or []), status, now, now,
            ),
        )
        conn.commit()
        return cursor.lastrowid  # type: ignore[return-value]

    def get_monitoring_schedule(self, company_name: str) -> dict | None:
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM monitoring_schedules WHERE company_name = ?",
            (company_name,),
        ).fetchone()
        if not row:
            return None
        return {
            "company_name": row["company_name"],
            "frequency": row["frequency"],
            "next_review_date": row["next_review_date"],
            "last_review_date": row["last_review_date"],
            "alert_thresholds": json.loads(row["alert_thresholds_json"]),
            "watch_metrics": json.loads(row["watch_metrics_json"]),
            "status": row["status"],
        }

    def list_monitoring_due(self, as_of: str = "") -> list[dict]:
        """List companies with reviews due on or before the given date."""
        if not as_of:
            as_of = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM monitoring_schedules WHERE status='active' AND next_review_date <= ? AND next_review_date != ''",
            (as_of,),
        ).fetchall()
        return [
            {
                "company_name": r["company_name"],
                "frequency": r["frequency"],
                "next_review_date": r["next_review_date"],
                "last_review_date": r["last_review_date"],
            }
            for r in rows
        ]

    def create_alert(
        self,
        company_name: str,
        alert_type: str,
        message: str,
        severity: str = "warning",
        metric_id: str = "",
        current_value: float | None = None,
        threshold_value: float | None = None,
    ) -> int:
        now = datetime.now(timezone.utc).isoformat()
        conn = self._get_conn()
        cursor = conn.execute(
            """INSERT INTO monitoring_alerts
               (company_name, alert_type, severity, message, metric_id,
                current_value, threshold_value, created_at)
               VALUES (?,?,?,?,?,?,?,?)""",
            (company_name, alert_type, severity, message, metric_id,
             current_value, threshold_value, now),
        )
        conn.commit()
        return cursor.lastrowid  # type: ignore[return-value]

    def list_alerts(
        self,
        company_name: str | None = None,
        unacknowledged_only: bool = False,
        limit: int = 100,
    ) -> list[dict]:
        conn = self._get_conn()
        query = "SELECT * FROM monitoring_alerts"
        params: list[Any] = []
        conds = []
        if company_name:
            conds.append("company_name = ?")
            params.append(company_name)
        if unacknowledged_only:
            conds.append("acknowledged = 0")
        if conds:
            query += " WHERE " + " AND ".join(conds)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        rows = conn.execute(query, params).fetchall()
        return [
            {
                "id": r["id"], "company_name": r["company_name"],
                "alert_type": r["alert_type"], "severity": r["severity"],
                "message": r["message"], "metric_id": r["metric_id"],
                "current_value": r["current_value"],
                "threshold_value": r["threshold_value"],
                "created_at": r["created_at"],
                "acknowledged": bool(r["acknowledged"]),
            }
            for r in rows
        ]

    def acknowledge_alert(self, alert_id: int) -> bool:
        conn = self._get_conn()
        cursor = conn.execute(
            "UPDATE monitoring_alerts SET acknowledged = 1 WHERE id = ?", (alert_id,),
        )
        conn.commit()
        return cursor.rowcount > 0

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


def _row_to_pipeline(row: sqlite3.Row) -> dict:
    """Convert a pipeline database row to a dict."""
    return {
        "id": row["id"],
        "company_name": row["company_name"],
        "pipeline_stage": row["pipeline_stage"],
        "assigned_to": row["assigned_to"],
        "priority": row["priority"],
        "tags": json.loads(row["tags_json"]) if row["tags_json"] else [],
        "sector": row["sector"],
        "geography": row["geography"],
        "sdg_focus": json.loads(row["sdg_focus_json"]) if row["sdg_focus_json"] else [],
        "investment_size": row["investment_size"],
        "notes": row["notes"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


_global_store: AssessmentStore | None = None


def get_assessment_store(db_path: str | Path | None = None) -> AssessmentStore:
    """Get the global AssessmentStore singleton (lazy-initialized)."""
    global _global_store
    if _global_store is None:
        _global_store = AssessmentStore(db_path)
    return _global_store
