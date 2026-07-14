from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sqlite3
import uuid
import json
from typing import Any
from contextlib import contextmanager
from collections.abc import Iterator


SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    agent TEXT NOT NULL,
    objective TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at TEXT NOT NULL,
    closed_at TEXT,
    next_action TEXT
);
CREATE INDEX IF NOT EXISTS idx_sessions_workspace_started
ON sessions(workspace_id, started_at DESC);

CREATE TABLE IF NOT EXISTS failures (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workspace_id TEXT NOT NULL,
    command TEXT NOT NULL,
    error_signature TEXT NOT NULL,
    root_cause TEXT,
    replacement_action TEXT,
    status TEXT NOT NULL DEFAULT 'known_failure',
    created_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    UNIQUE(workspace_id, command, error_signature)
);

CREATE TABLE IF NOT EXISTS command_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workspace_id TEXT NOT NULL,
    fingerprint TEXT NOT NULL,
    command TEXT NOT NULL,
    exit_code INTEGER NOT NULL,
    error_signature TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_command_runs_lookup
ON command_runs(workspace_id, fingerprint, command, created_at DESC);

CREATE TABLE IF NOT EXISTS validation_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workspace_id TEXT NOT NULL,
    fingerprint TEXT NOT NULL,
    command_name TEXT NOT NULL,
    command TEXT NOT NULL,
    exit_code INTEGER NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workspace_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_workspace_created
ON events(workspace_id, created_at DESC);
"""


class StateStore:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(SCHEMA)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def open_session(self, workspace_id: str, agent: str, objective: str) -> str:
        session_id = f"ses_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO sessions(id, workspace_id, agent, objective, status, started_at) VALUES (?, ?, ?, ?, ?, ?)",
                (session_id, workspace_id, agent, objective, "in_progress", _now()),
            )
        return session_id

    def close_session(self, session_id: str, status: str, next_action: str | None) -> None:
        with self._connect() as conn:
            result = conn.execute(
                "UPDATE sessions SET status=?, closed_at=?, next_action=? WHERE id=?",
                (status, _now(), next_action, session_id),
            )
            if result.rowcount == 0:
                raise KeyError(f"Unknown session: {session_id}")

    def latest_session(self, workspace_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM sessions WHERE workspace_id=? ORDER BY started_at DESC LIMIT 1",
                (workspace_id,),
            ).fetchone()
        return dict(row) if row else None

    def active_session(self, workspace_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM sessions WHERE workspace_id=? AND status='in_progress' ORDER BY started_at DESC LIMIT 1",
                (workspace_id,),
            ).fetchone()
        return dict(row) if row else None

    def record_failure(
        self,
        workspace_id: str,
        command: str,
        error_signature: str,
        root_cause: str | None = None,
        replacement_action: str | None = None,
    ) -> None:
        now = _now()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO failures(workspace_id, command, error_signature, root_cause, replacement_action, created_at, last_seen_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(workspace_id, command, error_signature)
                DO UPDATE SET root_cause=excluded.root_cause,
                              replacement_action=excluded.replacement_action,
                              last_seen_at=excluded.last_seen_at
                """,
                (workspace_id, command, error_signature, root_cause, replacement_action, now, now),
            )

    def list_failures(self, workspace_id: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM failures WHERE workspace_id=? ORDER BY last_seen_at DESC",
                (workspace_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def record_command_run(
        self,
        workspace_id: str,
        fingerprint: str,
        command: str,
        exit_code: int,
        error_signature: str | None,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO command_runs(workspace_id, fingerprint, command, exit_code, error_signature, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (workspace_id, fingerprint, command, exit_code, error_signature, _now()),
            )

    def latest_command_run(self, workspace_id: str, fingerprint: str, command: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM command_runs
                WHERE workspace_id=? AND fingerprint=? AND command=?
                ORDER BY created_at DESC LIMIT 1
                """,
                (workspace_id, fingerprint, command),
            ).fetchone()
        return dict(row) if row else None

    def record_validation(
        self,
        workspace_id: str,
        fingerprint: str,
        command_name: str,
        command: str,
        exit_code: int,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO validation_runs(workspace_id, fingerprint, command_name, command, exit_code, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (workspace_id, fingerprint, command_name, command, exit_code, _now()),
            )


    def latest_validations(self, workspace_id: str, fingerprint: str) -> dict[str, dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT v.* FROM validation_runs v
                JOIN (
                    SELECT command_name, MAX(id) AS max_id
                    FROM validation_runs
                    WHERE workspace_id=? AND fingerprint=?
                    GROUP BY command_name
                ) latest ON latest.max_id = v.id
                ORDER BY v.command_name
                """,
                (workspace_id, fingerprint),
            ).fetchall()
        return {row["command_name"]: dict(row) for row in rows}

    def record_event(self, workspace_id: str, event_type: str, payload: dict[str, Any]) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO events(workspace_id, event_type, payload_json, created_at) VALUES (?, ?, ?, ?)",
                (workspace_id, event_type, json.dumps(payload, sort_keys=True), _now()),
            )

    def list_events(self, workspace_id: str, limit: int = 20) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM events WHERE workspace_id=? ORDER BY id DESC LIMIT ?",
                (workspace_id, limit),
            ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["payload"] = json.loads(item.pop("payload_json"))
            result.append(item)
        return result


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
