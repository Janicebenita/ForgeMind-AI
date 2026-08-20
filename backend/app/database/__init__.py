from __future__ import annotations

import json
import os
import re
import sqlite3
from pathlib import Path
from typing import Any, Iterable, Iterator

from app.core.config import get_settings

ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = Path(os.getenv("FORGEMIND_DATA_DIR", str(ROOT / "backend" / "app" / "data")))
UPLOAD_DIR = Path(os.getenv("FORGEMIND_UPLOAD_DIR", str(ROOT / "backend" / "app" / "uploads")))
DB_PATH = DATA_DIR / "forgemind.db"


class DatabaseRow(dict[str, Any]):
    """Mapping row that also preserves sqlite-style numeric access."""

    def __getitem__(self, key: str | int) -> Any:
        if isinstance(key, int):
            return list(self.values())[key]
        return super().__getitem__(key)


class CursorAdapter:
    def __init__(self, cursor: Any, lastrowid: int | None = None) -> None:
        self._cursor = cursor
        self.lastrowid = lastrowid

    def _row(self, row: Any) -> DatabaseRow | None:
        if row is None:
            return None
        if isinstance(row, dict):
            return DatabaseRow(row)
        if isinstance(row, sqlite3.Row):
            return DatabaseRow(dict(row))
        names = [column[0] for column in (self._cursor.description or [])]
        return DatabaseRow(zip(names, row, strict=False))

    def fetchone(self) -> DatabaseRow | None:
        return self._row(self._cursor.fetchone())

    def fetchall(self) -> list[DatabaseRow]:
        rows: list[DatabaseRow] = []
        for row in self._cursor.fetchall():
            converted = self._row(row)
            if converted is not None:
                rows.append(converted)
        return rows

    def __iter__(self) -> Iterator[DatabaseRow]:
        for row in self._cursor:
            converted = self._row(row)
            if converted is not None:
                yield converted


class ConnectionAdapter:
    def __init__(self, connection: Any, backend: str) -> None:
        self._connection = connection
        self.backend = backend

    def __enter__(self) -> "ConnectionAdapter":
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        try:
            if exc_type is None:
                self._connection.commit()
            else:
                self._connection.rollback()
        finally:
            self._connection.close()

    def execute(self, sql: str, params: Iterable[Any] = ()) -> CursorAdapter:
        if self.backend == "sqlite":
            cursor = self._connection.execute(sql, tuple(params))
            return CursorAdapter(cursor, lastrowid=cursor.lastrowid)

        statement, returns_id = _postgres_statement(sql, return_insert_id=True)
        cursor = self._connection.cursor()
        cursor.execute(statement, tuple(params))
        lastrowid = None
        if returns_id:
            row = cursor.fetchone()
            if row:
                lastrowid = int(row[0])
        return CursorAdapter(cursor, lastrowid=lastrowid)

    def executemany(self, sql: str, params: Iterable[Iterable[Any]]) -> CursorAdapter:
        if self.backend == "sqlite":
            return CursorAdapter(self._connection.executemany(sql, params))
        statement, _ = _postgres_statement(sql, return_insert_id=False)
        cursor = self._connection.cursor()
        cursor.executemany(statement, [tuple(row) for row in params])
        return CursorAdapter(cursor)

    def executescript(self, sql: str) -> None:
        if self.backend != "sqlite":
            raise RuntimeError("executescript is available only for SQLite development.")
        self._connection.executescript(sql)

    def commit(self) -> None:
        self._connection.commit()


def _postgres_statement(sql: str, return_insert_id: bool) -> tuple[str, bool]:
    statement = sql.strip().rstrip(";")
    ignore_conflicts = bool(re.match(r"INSERT\s+OR\s+IGNORE\s+INTO", statement, re.I))
    if ignore_conflicts:
        statement = re.sub(
            r"INSERT\s+OR\s+IGNORE\s+INTO",
            "INSERT INTO",
            statement,
            count=1,
            flags=re.I,
        )
        statement += " ON CONFLICT DO NOTHING"
    statement = statement.replace("?", "%s")
    is_insert = bool(re.match(r"INSERT\s+INTO", statement, re.I))
    returns_id = return_insert_id and is_insert and "RETURNING" not in statement.upper()
    if returns_id:
        statement += " RETURNING id"
    return statement, returns_id


def database_backend() -> str:
    url = get_settings().database_url
    return "postgresql" if url.startswith(("postgres://", "postgresql://", "postgresql+psycopg://")) else "sqlite"


def connect() -> ConnectionAdapter:
    backend = database_backend()
    if backend == "postgresql":
        try:
            import psycopg
        except ImportError as exc:
            raise RuntimeError("psycopg is required when DATABASE_URL selects PostgreSQL.") from exc
        connection_url = get_settings().database_url.replace(
            "postgresql+psycopg://", "postgresql://", 1
        )
        return ConnectionAdapter(psycopg.connect(connection_url), "postgresql")

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return ConnectionAdapter(connection, "sqlite")


def execute(sql: str, params: Iterable[Any] = ()) -> None:
    with connect() as conn:
        conn.execute(sql, tuple(params))


def query(sql: str, params: Iterable[Any] = ()) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(sql, tuple(params)).fetchall()
    return [dict(row) for row in rows]


def scalar(sql: str, params: Iterable[Any] = ()) -> Any:
    with connect() as conn:
        row = conn.execute(sql, tuple(params)).fetchone()
    if row is None:
        return None
    return row[0]


def dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True)


def loads(value: str | None, fallback: Any = None) -> Any:
    if not value:
        return fallback
    return json.loads(value)


SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    doc_type TEXT NOT NULL,
    source_path TEXT NOT NULL,
    text TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    owner_role TEXT NOT NULL DEFAULT 'operations',
    permission_level TEXT NOT NULL DEFAULT 'plant',
    content_hash TEXT,
    storage_backend TEXT NOT NULL DEFAULT 'local',
    blob_uri TEXT,
    blob_etag TEXT,
    indexing_status TEXT NOT NULL DEFAULT 'local_indexed',
    ingestion_error TEXT
);
CREATE TABLE IF NOT EXISTS chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER NOT NULL,
    chunk_index INTEGER NOT NULL,
    page_number INTEGER NOT NULL,
    section TEXT NOT NULL,
    text TEXT NOT NULL,
    embedding TEXT NOT NULL,
    FOREIGN KEY(document_id) REFERENCES documents(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS entities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER NOT NULL,
    chunk_id INTEGER,
    entity_type TEXT NOT NULL,
    name TEXT NOT NULL,
    value TEXT,
    metadata TEXT NOT NULL DEFAULT '{}',
    confidence REAL NOT NULL DEFAULT 0.82,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(document_id) REFERENCES documents(id) ON DELETE CASCADE,
    FOREIGN KEY(chunk_id) REFERENCES chunks(id) ON DELETE SET NULL
);
CREATE TABLE IF NOT EXISTS entity_relationships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_entity_id INTEGER,
    source_type TEXT NOT NULL,
    source_name TEXT NOT NULL,
    relationship TEXT NOT NULL,
    target_entity_id INTEGER,
    target_type TEXT NOT NULL,
    target_name TEXT NOT NULL,
    document_id INTEGER,
    evidence TEXT NOT NULL,
    confidence REAL NOT NULL DEFAULT 0.8,
    FOREIGN KEY(document_id) REFERENCES documents(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS assets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tag TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    asset_type TEXT NOT NULL,
    location TEXT NOT NULL,
    criticality TEXT NOT NULL,
    risk_score INTEGER NOT NULL DEFAULT 50,
    status TEXT NOT NULL DEFAULT 'Monitored'
);
CREATE TABLE IF NOT EXISTS failures (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_tag TEXT NOT NULL,
    failure_mode TEXT NOT NULL,
    root_cause TEXT,
    occurred_on TEXT NOT NULL,
    severity TEXT NOT NULL,
    work_order TEXT,
    document_id INTEGER,
    FOREIGN KEY(document_id) REFERENCES documents(id) ON DELETE SET NULL
);
CREATE TABLE IF NOT EXISTS work_orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    work_order TEXT NOT NULL UNIQUE,
    asset_tag TEXT NOT NULL,
    action TEXT NOT NULL,
    performed_on TEXT NOT NULL,
    role TEXT NOT NULL,
    status TEXT NOT NULL,
    document_id INTEGER
);
CREATE TABLE IF NOT EXISTS inspections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    inspection_id TEXT NOT NULL UNIQUE,
    asset_tag TEXT NOT NULL,
    finding TEXT NOT NULL,
    inspected_on TEXT NOT NULL,
    severity TEXT NOT NULL,
    next_due TEXT NOT NULL,
    document_id INTEGER
);
CREATE TABLE IF NOT EXISTS regulations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    clause TEXT NOT NULL UNIQUE,
    requirement TEXT NOT NULL,
    applies_to TEXT NOT NULL,
    evidence_status TEXT NOT NULL DEFAULT 'unmapped'
);
CREATE TABLE IF NOT EXISTS procedures (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    procedure_id TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    applies_to TEXT NOT NULL,
    revision TEXT NOT NULL,
    document_id INTEGER
);
CREATE TABLE IF NOT EXISTS chat_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    user_role TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS citations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    answer_id TEXT NOT NULL,
    document_id INTEGER NOT NULL,
    chunk_id INTEGER NOT NULL,
    quote TEXT NOT NULL,
    page_number INTEGER NOT NULL,
    confidence REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    actor TEXT NOT NULL,
    action TEXT NOT NULL,
    target TEXT NOT NULL,
    detail TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- New table for asset usage metrics
CREATE TABLE IF NOT EXISTS asset_usage (
    usage_id TEXT PRIMARY KEY,
    asset_tag TEXT NOT NULL,
    period TEXT NOT NULL,
    metric TEXT NOT NULL,
    value REAL NOT NULL,
    unit TEXT NOT NULL,
    FOREIGN KEY(asset_tag) REFERENCES assets(tag) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_asset_usage_asset_tag ON asset_usage(asset_tag);
CREATE INDEX IF NOT EXISTS idx_asset_usage_period ON asset_usage(period);
"""


POSTGRES_SCHEMA = SQLITE_SCHEMA.replace(
    "INTEGER PRIMARY KEY AUTOINCREMENT", "BIGSERIAL PRIMARY KEY"
).replace(" REAL ", " DOUBLE PRECISION ")


def _ensure_sqlite_columns(conn: ConnectionAdapter) -> None:
    existing = {row[1] for row in conn.execute("PRAGMA table_info(documents)").fetchall()}
    columns = {
        "content_hash": "TEXT",
        "storage_backend": "TEXT NOT NULL DEFAULT 'local'",
        "blob_uri": "TEXT",
        "blob_etag": "TEXT",
        "indexing_status": "TEXT NOT NULL DEFAULT 'local_indexed'",
        "ingestion_error": "TEXT",
    }
    for column, definition in columns.items():
        if column not in existing:
            conn.execute(f"ALTER TABLE documents ADD COLUMN {column} {definition}")


def init_db() -> None:
    with connect() as conn:
        if conn.backend == "sqlite":
            conn.executescript(SQLITE_SCHEMA)
            _ensure_sqlite_columns(conn)
        else:
            for statement in POSTGRES_SCHEMA.split(";"):
                if statement.strip():
                    conn.execute(statement)
            for column, definition in {
                "content_hash": "TEXT",
                "storage_backend": "TEXT NOT NULL DEFAULT 'local'",
                "blob_uri": "TEXT",
                "blob_etag": "TEXT",
                "indexing_status": "TEXT NOT NULL DEFAULT 'local_indexed'",
                "ingestion_error": "TEXT",
            }.items():
                conn.execute(
                    f"ALTER TABLE documents ADD COLUMN IF NOT EXISTS {column} {definition}"
                )
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_documents_content_hash "
            "ON documents(content_hash) WHERE content_hash IS NOT NULL"
        )


def clear_demo_data() -> None:
    with connect() as conn:
        for table in [
            "citations",
            "chat_sessions",
            "entity_relationships",
            "entities",
            "chunks",
            "failures",
            "work_orders",
            "inspections",
            "regulations",
            "procedures",
            "assets",
            "documents",
            "audit_logs",
        ]:
            conn.execute(f"DELETE FROM {table}")
