from __future__ import annotations

import argparse
import base64
import hashlib
import json
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DATA_DIRECTORIES = (
    Path("demo-data"),
    Path("backend/storage/documents"),
    Path("sample_data/documents"),
    Path("backend/app/uploads"),
    Path("backend/app/reports"),
)


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def json_value(value: Any) -> Any:
    if isinstance(value, bytes):
        return {"encoding": "base64", "value": base64.b64encode(value).decode("ascii")}
    return value


def database_inventory(database: Path) -> dict[str, Any]:
    connection = sqlite3.connect(f"{database.as_uri()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        tables = [
            row[0]
            for row in connection.execute(
                """
                SELECT name FROM sqlite_master
                WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
                ORDER BY name
                """
            )
        ]
        counts = {
            table: connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
            for table in tables
        }
        rows = {
            table: [
                {key: json_value(value) for key, value in dict(row).items()}
                for row in connection.execute(f'SELECT * FROM "{table}"')
            ]
            for table in tables
        }
        return {"tables": tables, "counts": counts, "rows": rows}
    finally:
        connection.close()


def copy_data_directories(source_root: Path, destination_root: Path) -> dict[str, Any]:
    copied = 0
    identical = 0
    conflicts: list[str] = []
    for relative in DATA_DIRECTORIES:
        source = source_root / relative
        if not source.exists():
            continue
        for source_file in source.rglob("*"):
            if not source_file.is_file():
                continue
            local = source_file.relative_to(source)
            destination = destination_root / relative / local
            destination.parent.mkdir(parents=True, exist_ok=True)
            if not destination.exists():
                shutil.copy2(source_file, destination)
                copied += 1
                continue
            if file_hash(source_file) == file_hash(destination):
                identical += 1
                continue
            conflict = destination_root / "backend/migration/legacy-conflicts" / relative / local
            conflict.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_file, conflict)
            conflicts.append(str(conflict.relative_to(destination_root)))
    return {"copied": copied, "identical": identical, "conflicts": conflicts}


def ensure_document_columns(connection: sqlite3.Connection) -> None:
    columns = {
        row[1] for row in connection.execute("PRAGMA table_info(documents)").fetchall()
    }
    additions = {
        "content_hash": "TEXT",
        "storage_backend": "TEXT NOT NULL DEFAULT 'local'",
        "blob_uri": "TEXT",
        "blob_etag": "TEXT",
        "indexing_status": "TEXT NOT NULL DEFAULT 'local_indexed'",
        "ingestion_error": "TEXT",
    }
    for column, definition in additions.items():
        if column not in columns:
            connection.execute(f"ALTER TABLE documents ADD COLUMN {column} {definition}")
    connection.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_documents_content_hash
        ON documents(content_hash) WHERE content_hash IS NOT NULL
        """
    )


def relink_documents(connection: sqlite3.Connection, destination_root: Path) -> dict[str, int]:
    connection.row_factory = sqlite3.Row
    candidates = (
        destination_root / "sample_data/documents",
        destination_root / "backend/storage/documents",
        destination_root / "demo-data",
        destination_root / "backend/app/uploads",
    )
    relinked = 0
    unresolved = 0
    for document in connection.execute(
        "SELECT id, filename, source_path, text, content_hash FROM documents"
    ).fetchall():
        matched = next(
            (directory / document["filename"] for directory in candidates if (directory / document["filename"]).is_file()),
            None,
        )
        if matched is None:
            unresolved += 1
            continue
        content_hash = document["content_hash"]
        if not content_hash:
            content_hash = hashlib.sha256(matched.read_bytes()).hexdigest()
        connection.execute(
            """
            UPDATE documents
            SET source_path = ?, content_hash = ?, storage_backend = 'local',
                indexing_status = 'local_indexed', ingestion_error = NULL
            WHERE id = ?
            """,
            (str(matched.resolve()), content_hash, document["id"]),
        )
        relinked += 1
    return {"relinked": relinked, "unresolved": unresolved}


def migrate(source_root: Path, destination_root: Path, *, force: bool, dry_run: bool) -> dict[str, Any]:
    source_root = source_root.resolve()
    destination_root = destination_root.resolve()
    if source_root == destination_root:
        raise ValueError("Source and destination must be separate directories.")

    source_database = source_root / "backend/app/data/industrial_brain.db"
    if not source_database.is_file():
        raise FileNotFoundError(f"Legacy database not found: {source_database}")

    source_inventory = database_inventory(source_database)
    summary: dict[str, Any] = {
        "source_root": str(source_root),
        "destination_root": str(destination_root),
        "source_database": str(source_database),
        "source_database_sha256": file_hash(source_database),
        "source_counts": source_inventory["counts"],
        "dry_run": dry_run,
    }
    if dry_run:
        return summary

    target_database = destination_root / "backend/app/data/forgemind.db"
    if target_database.exists() and not force:
        raise FileExistsError(
            f"ForgeMind database already exists: {target_database}. Use --force to replace it."
        )

    file_result = copy_data_directories(source_root, destination_root)
    target_database.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_database, target_database)
    connection = sqlite3.connect(target_database)
    try:
        ensure_document_columns(connection)
        link_result = relink_documents(connection, destination_root)
        connection.execute(
            """
            INSERT INTO audit_logs(actor, action, target, detail)
            VALUES (?, ?, ?, ?)
            """,
            (
                "migration",
                "legacy_import",
                "ForgeMind AI",
                f"Migrated from {source_root.name} at {datetime.now(timezone.utc).isoformat()}",
            ),
        )
        connection.commit()
    finally:
        connection.close()

    migrated_inventory = database_inventory(target_database)
    snapshot = {
        "format": "forgemind-legacy-snapshot-v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_database_sha256": summary["source_database_sha256"],
        "tables": migrated_inventory["rows"],
    }
    snapshot_path = destination_root / "backend/app/data/legacy_snapshot.json"
    snapshot_path.write_text(json.dumps(snapshot, ensure_ascii=False), encoding="utf-8")

    manifest = {
        **summary,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "target_database": str(target_database),
        "target_database_sha256": file_hash(target_database),
        "target_counts": migrated_inventory["counts"],
        "files": file_result,
        "documents": link_result,
        "snapshot": str(snapshot_path),
    }
    manifest_path = destination_root / "backend/migration/legacy_migration_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Copy the preserved Intelligence Brain data into a separate ForgeMind AI project."
    )
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--destination-root", type=Path, required=True)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    print(
        json.dumps(
            migrate(
                args.source_root,
                args.destination_root,
                force=args.force,
                dry_run=args.dry_run,
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
