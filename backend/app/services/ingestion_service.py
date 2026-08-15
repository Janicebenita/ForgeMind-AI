from __future__ import annotations

import csv
import hashlib
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pandas as pd

if TYPE_CHECKING:
    from fastapi import UploadFile

from app.core.config import get_settings
from app.core.document_access import can_access_document
from app.database import UPLOAD_DIR, connect, dumps, execute, init_db, query
from app.rag.azure_search import AzureSearchStore
from app.rag.providers import provider_for
from app.services.embedding_service import embed_text
from app.services.extraction_service import extract_entities, infer_relationships
from app.storage.azure_blob import AzureBlobStore, BlobReceipt


def chunk_text(text: str, max_chars: int = 900) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []
    current = ""
    section = "General"
    page = 1
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            section = line.lstrip("# ").strip() or section
        if len(current) + len(line) > max_chars and current:
            sections.append({"text": current.strip(), "section": section, "page_number": page})
            current = ""
            page += 1
        current += line + "\n"
    if current.strip():
        sections.append({"text": current.strip(), "section": section, "page_number": page})
    return sections or [{"text": text[:max_chars], "section": "General", "page_number": 1}]


def read_document(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".txt", ".md", ".log"}:
        return path.read_text(encoding="utf-8", errors="ignore")
    if suffix == ".csv":
        rows = []
        with path.open("r", encoding="utf-8", errors="ignore", newline="") as handle:
            for row in csv.DictReader(handle):
                rows.append("; ".join(f"{key}: {value}" for key, value in row.items()))
        return "\n".join(rows)
    if suffix in {".xlsx", ".xls"}:
        frames = pd.read_excel(path, sheet_name=None)
        lines = []
        for sheet, frame in frames.items():
            lines.append(f"# Sheet {sheet}")
            lines.append(frame.fillna("").to_csv(index=False))
        return "\n".join(lines)
    if suffix == ".pdf":
        try:
            from pypdf import PdfReader

            reader = PdfReader(str(path))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception as exc:
            return f"OCR_REQUIRED: Could not extract PDF text locally. Error: {exc}"
    if suffix in {".png", ".jpg", ".jpeg", ".tif", ".tiff"}:
        companion = path.with_suffix(".txt")
        if companion.exists():
            return companion.read_text(encoding="utf-8", errors="ignore")
        return f"OCR_REQUIRED: Image document {path.name} requires OCR or a companion extracted text file."
    return path.read_text(encoding="utf-8", errors="ignore")


def infer_doc_type(filename: str, text: str) -> str:
    lower = f"{filename} {text[:500]}".lower()
    if "sop" in lower or "procedure" in lower:
        return "SOP"
    if "inspection" in lower or "insp-" in lower:
        return "InspectionReport"
    if "work order" in lower or "wo-" in lower:
        return "MaintenanceWorkOrder"
    if "qa/qc" in lower or "inspection and test plan" in lower or "quality assurance" in lower or "quality control manual" in lower:
        return "QAQCManual"
    if "tender" in lower or "bill of quantities" in lower or "scope of work" in lower or "contract" in lower:
        return "TenderContractDocument"
    if "nonconformity" in lower or "ncr" in lower or "iso 9001" in lower:
        return "QualityNonconformance"
    if "method statement" in lower or "construction method" in lower or "constructionmethods" in lower:
        return "ConstructionMethodStatement"
    if "checklist" in lower or "regulation" in lower or "osha" in lower or "api" in lower:
        return "RegulatoryChecklist"
    if "incident" in lower:
        return "IncidentReport"
    if "metadata" in lower or "drawing" in lower or "p&id" in lower:
        return "EngineeringMetadata"
    return "IndustrialDocument"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def ingest_path(
    path: Path,
    owner_role: str = "operations",
    permission_level: str = "plant",
) -> dict[str, Any]:
    init_db()
    content_hash = sha256_file(path)
    existing = query(
        """
        SELECT id, filename, doc_type, storage_backend, blob_uri, indexing_status
        FROM documents WHERE content_hash = ? LIMIT 1
        """,
        (content_hash,),
    )
    if existing:
        return {
            "status": "duplicate",
            "document_id": existing[0]["id"],
            "filename": existing[0]["filename"],
            "doc_type": existing[0]["doc_type"],
            "content_hash": content_hash,
            "storage_backend": existing[0]["storage_backend"],
            "blob_uri": existing[0]["blob_uri"],
            "indexing_status": existing[0]["indexing_status"],
            "azure_indexed_chunks": 0,
        }

    settings = get_settings()
    blob_receipt = _store_document(path, content_hash, owner_role, permission_level)
    text = read_document(path)
    doc_type = infer_doc_type(path.name, text)
    chunks = chunk_text(text)
    all_entities: list[dict[str, Any]] = []
    search_chunks: list[dict[str, Any]] = []

    with connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO documents(
                filename, doc_type, source_path, text, owner_role, permission_level,
                content_hash, storage_backend, blob_uri, blob_etag, indexing_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                path.name,
                doc_type,
                str(path),
                text,
                owner_role,
                permission_level,
                content_hash,
                settings.document_storage_backend,
                blob_receipt.uri if blob_receipt else None,
                blob_receipt.etag if blob_receipt else None,
                "pending" if settings.retrieval_backend == "azure_search" else "local_indexed",
            ),
        )
        document_id = cursor.lastrowid
        for index, chunk in enumerate(chunks):
            embedding = dumps(embed_text(chunk["text"]))
            chunk_cursor = conn.execute(
                "INSERT INTO chunks(document_id, chunk_index, page_number, section, text, embedding) VALUES (?, ?, ?, ?, ?, ?)",
                (document_id, index, chunk["page_number"], chunk["section"], chunk["text"], embedding),
            )
            chunk_id = chunk_cursor.lastrowid
            search_chunks.append(
                {
                    "id": f"doc-{document_id}-chunk-{chunk_id}",
                    "document_id": document_id,
                    "chunk_id": chunk_id,
                    "filename": path.name,
                    "doc_type": doc_type,
                    "page_number": chunk["page_number"],
                    "section": chunk["section"],
                    "content": chunk["text"],
                    "owner_role": owner_role,
                    "permission_level": permission_level,
                    "created_at": "",
                }
            )
            entities = extract_entities(chunk["text"])
            all_entities.extend(entities)
            inserted: dict[tuple[str, str], int] = {}
            for entity in entities:
                entity_cursor = conn.execute(
                    "INSERT INTO entities(document_id, chunk_id, entity_type, name, metadata, confidence) VALUES (?, ?, ?, ?, ?, ?)",
                    (document_id, chunk_id, entity["type"], entity["name"], dumps(entity.get("metadata", {})), entity.get("confidence", 0.84)),
                )
                inserted[(entity["type"], entity["name"])] = entity_cursor.lastrowid
            for rel in infer_relationships(chunk["text"], entities):
                conn.execute(
                    """
                    INSERT INTO entity_relationships(
                        source_entity_id, source_type, source_name, relationship, target_entity_id,
                        target_type, target_name, document_id, evidence, confidence
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        inserted.get((rel["source_type"], rel["source_name"])),
                        rel["source_type"],
                        rel["source_name"],
                        rel["relationship"],
                        inserted.get((rel["target_type"], rel["target_name"])),
                        rel["target_type"],
                        rel["target_name"],
                        document_id,
                        chunk["text"][:420],
                        0.82,
                    ),
                )
        conn.execute(
            "INSERT INTO audit_logs(actor, action, target, detail) VALUES (?, ?, ?, ?)",
            (
                owner_role,
                "ingest",
                path.name,
                f"Processed {len(chunks)} chunks; sha256={content_hash}; storage={settings.document_storage_backend}",
            ),
        )
        conn.commit()

    try:
        azure_indexed_chunks = _sync_chunks_to_azure(search_chunks)
        indexing_status = "azure_indexed" if settings.retrieval_backend == "azure_search" else "local_indexed"
        execute(
            "UPDATE documents SET indexing_status = ?, ingestion_error = NULL WHERE id = ?",
            (indexing_status, document_id),
        )
    except Exception as exc:
        execute(
            "UPDATE documents SET indexing_status = 'failed', ingestion_error = ? WHERE id = ?",
            (str(exc)[:1000], document_id),
        )
        raise

    return {
        "status": "indexed",
        "document_id": document_id,
        "filename": path.name,
        "doc_type": doc_type,
        "chunks": len(chunks),
        "entities": all_entities,
        "content_hash": content_hash,
        "storage_backend": settings.document_storage_backend,
        "blob_uri": blob_receipt.uri if blob_receipt else None,
        "blob_etag": blob_receipt.etag if blob_receipt else None,
        "retrieval_backend": settings.retrieval_backend,
        "indexing_status": indexing_status,
        "azure_indexed_chunks": azure_indexed_chunks,
    }


@lru_cache(maxsize=1)
def _azure_blob_store() -> AzureBlobStore:
    return AzureBlobStore(settings=get_settings())


def _store_document(
    path: Path,
    content_hash: str,
    owner_role: str,
    permission_level: str,
) -> BlobReceipt | None:
    if get_settings().document_storage_backend != "azure_blob":
        return None
    return _azure_blob_store().upload_file(
        path,
        content_hash=content_hash,
        owner_role=owner_role,
        permission_level=permission_level,
    )


@lru_cache(maxsize=1)
def _azure_search_store() -> AzureSearchStore:
    store = AzureSearchStore(settings=get_settings())
    store.ensure_index()
    return store


def _sync_chunks_to_azure(search_chunks: list[dict[str, Any]]) -> int:
    settings = get_settings()
    if settings.retrieval_backend != "azure_search":
        return 0

    provider = provider_for("azure", settings=settings)
    vectors = provider.embed_many([item["content"] for item in search_chunks])
    for item, vector in zip(search_chunks, vectors, strict=True):
        if not isinstance(vector, list):
            raise TypeError("Azure AI Search requires dense embedding vectors.")
        item["content_vector"] = vector
    return _azure_search_store().upload_chunks(search_chunks)


def delete_document(document_id: int, user_role: str) -> dict[str, Any]:
    rows = query(
        """
        SELECT id, filename, source_path, owner_role, permission_level, storage_backend, blob_uri
        FROM documents WHERE id = ?
        """,
        (document_id,),
    )
    if not rows:
        raise FileNotFoundError("Document not found.")
    document = rows[0]
    if not can_access_document(
        user_role,
        document["owner_role"],
        document["permission_level"],
    ):
        raise PermissionError("Document access denied.")

    settings = get_settings()
    deleted_search_chunks = 0
    if settings.retrieval_backend == "azure_search":
        deleted_search_chunks = _azure_search_store().delete_document(document_id)
    if document["storage_backend"] == "azure_blob" and document["blob_uri"]:
        _azure_blob_store().delete(document["blob_uri"])
    elif document["source_path"]:
        # Only remove files that were created in ForgeMind's upload directory.
        # Seed/reference documents can live elsewhere and must never be deleted.
        source_path = Path(document["source_path"]).resolve()
        upload_root = UPLOAD_DIR.resolve()
        if source_path.is_relative_to(upload_root):
            source_path.unlink(missing_ok=True)

    execute("DELETE FROM documents WHERE id = ?", (document_id,))
    execute(
        "INSERT INTO audit_logs(actor, action, target, detail) VALUES (?, ?, ?, ?)",
        (user_role, "delete", document["filename"], f"Removed document {document_id}"),
    )
    return {
        "status": "deleted",
        "document_id": document_id,
        "filename": document["filename"],
        "deleted_search_chunks": deleted_search_chunks,
    }


async def ingest_upload(file: "UploadFile", owner_role: str = "operations") -> dict[str, Any]:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    safe_filename = Path(file.filename or "upload.bin").name
    if not safe_filename or safe_filename in {".", ".."}:
        raise ValueError("The uploaded document must have a valid filename.")
    target = UPLOAD_DIR / safe_filename
    max_upload_bytes = get_settings().max_upload_bytes
    written = 0
    with target.open("wb") as handle:
        while block := file.file.read(1024 * 1024):
            written += len(block)
            if written > max_upload_bytes:
                handle.close()
                target.unlink(missing_ok=True)
                raise ValueError(f"Upload exceeds MAX_UPLOAD_BYTES ({max_upload_bytes}).")
            handle.write(block)
    try:
        return ingest_path(target, owner_role=owner_role)
    finally:
        if get_settings().document_storage_backend == "azure_blob":
            target.unlink(missing_ok=True)
