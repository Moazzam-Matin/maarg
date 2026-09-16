"""
SQLite implementation of the maarg storage backend.

Stores each Run as one row in a `runs` table. Complex fields (inputs,
metrics, artifacts, other) are stored as JSON-serialized text, since
SQLite has no native nested-object column type.

Connections are opened fresh for each method call rather than held
open for the lifetime of this object — simplest correct behavior for
v1, since we're not yet designing for concurrent/multi-process access.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from maarg.models import Run
from maarg.storage.base import StorageBackend

DEFAULT_DB_PATH = Path(".maarg") / "runs.db"

# Explicit column order, used consistently for CREATE TABLE, INSERT, and
# SELECT — avoids relying on "SELECT *" matching table order by accident.
_COLUMNS = (
    "run_id", "function", "experiment", "timestamp", "duration_sec",
    "inputs", "metrics", "artifacts", "other",
)

_CREATE_TABLE_SQL = f"""
CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY,
    function TEXT NOT NULL,
    experiment TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    duration_sec REAL NOT NULL,
    inputs TEXT NOT NULL,
    metrics TEXT NOT NULL,
    artifacts TEXT NOT NULL,
    other TEXT NOT NULL
)
"""

_SELECT_COLUMNS_SQL = ", ".join(_COLUMNS)


class SQLiteStorage(StorageBackend):
    """SQLite-backed implementation of StorageBackend."""

    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _init_schema(self) -> None:
        conn = self._connect()
        try:
            conn.execute(_CREATE_TABLE_SQL)
            conn.commit()
        finally:
            conn.close()

    # ── Serialization helpers ────────────────────────────────────────

    @staticmethod
    def _run_to_row(run: Run) -> tuple:
        return (
            run.run_id,
            run.function,
            run.experiment,
            run.timestamp,
            run.duration_sec,
            json.dumps(run.inputs),
            json.dumps(run.metrics),
            json.dumps(run.artifacts),
            json.dumps(run.other),
        )

    @staticmethod
    def _row_to_run(row: tuple) -> Run:
        (run_id, function, experiment, timestamp, duration_sec,
         inputs_json, metrics_json, artifacts_json, other_json) = row
        return Run(
            run_id=run_id,
            function=function,
            experiment=experiment,
            timestamp=timestamp,
            duration_sec=duration_sec,
            inputs=json.loads(inputs_json),
            metrics=json.loads(metrics_json),
            artifacts=json.loads(artifacts_json),
            other=json.loads(other_json),
        )

    # ── StorageBackend implementation ────────────────────────────────

    def save(self, run: Run) -> None:
        conn = self._connect()
        try:
            placeholders = ", ".join("?" * len(_COLUMNS))
            conn.execute(
                f"INSERT INTO runs ({_SELECT_COLUMNS_SQL}) VALUES ({placeholders})",
                self._run_to_row(run),
            )
            conn.commit()
        finally:
            conn.close()

    def get_by_id(self, run_id: str) -> Run | None:
        conn = self._connect()
        try:
            cursor = conn.execute(
                f"SELECT {_SELECT_COLUMNS_SQL} FROM runs WHERE run_id = ?",
                (run_id,),
            )
            row = cursor.fetchone()
        finally:
            conn.close()
        return self._row_to_run(row) if row is not None else None

    def list_by_function(self, function: str) -> list[Run]:
        conn = self._connect()
        try:
            cursor = conn.execute(
                f"SELECT {_SELECT_COLUMNS_SQL} FROM runs "
                f"WHERE function = ? ORDER BY timestamp DESC",
                (function,),
            )
            rows = cursor.fetchall()
        finally:
            conn.close()
        return [self._row_to_run(row) for row in rows]

    def list_by_experiment(self, experiment: str) -> list[Run]:
        conn = self._connect()
        try:
            cursor = conn.execute(
                f"SELECT {_SELECT_COLUMNS_SQL} FROM runs "
                f"WHERE experiment = ? ORDER BY timestamp DESC",
                (experiment,),
            )
            rows = cursor.fetchall()
        finally:
            conn.close()
        return [self._row_to_run(row) for row in rows]

    def list_all(self) -> list[Run]:
        conn = self._connect()
        try:
            cursor = conn.execute(
                f"SELECT {_SELECT_COLUMNS_SQL} FROM runs ORDER BY timestamp DESC"
            )
            rows = cursor.fetchall()
        finally:
            conn.close()
        return [self._row_to_run(row) for row in rows]