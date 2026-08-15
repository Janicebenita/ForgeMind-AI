from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.core.config import get_settings
from app.database import clear_demo_data, init_db
from app.services.ingestion_service import (
    _azure_blob_store,
    _azure_search_store,
    delete_document,
    ingest_path,
)


class DocumentDeletionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.environment = {
            "AI_PROVIDER": "local",
            "RETRIEVAL_BACKEND": "local",
            "DOCUMENT_STORAGE_BACKEND": "local",
        }

    def tearDown(self) -> None:
        get_settings.cache_clear()
        _azure_blob_store.cache_clear()
        _azure_search_store.cache_clear()

    def test_deletion_preserves_reference_file_outside_upload_root(self) -> None:
        with patch.dict(os.environ, self.environment), tempfile.TemporaryDirectory() as directory:
            get_settings.cache_clear()
            _azure_blob_store.cache_clear()
            _azure_search_store.cache_clear()
            init_db()
            clear_demo_data()
            root = Path(directory)
            upload_root = root / "uploads"
            upload_root.mkdir()
            reference = root / "conference-reference.txt"
            reference.write_text("Asset: P-101\nReference evidence.", encoding="utf-8")

            with patch("app.services.ingestion_service.UPLOAD_DIR", upload_root):
                receipt = ingest_path(reference, owner_role="operations")
                delete_document(receipt["document_id"], user_role="plant_manager")

            self.assertTrue(reference.exists())

    def test_deletion_removes_file_created_inside_upload_root(self) -> None:
        with patch.dict(os.environ, self.environment), tempfile.TemporaryDirectory() as directory:
            get_settings.cache_clear()
            _azure_blob_store.cache_clear()
            _azure_search_store.cache_clear()
            init_db()
            clear_demo_data()
            upload_root = Path(directory) / "uploads"
            upload_root.mkdir()
            uploaded = upload_root / "uploaded-evidence.txt"
            uploaded.write_text("Asset: P-101\nUploaded evidence.", encoding="utf-8")

            with patch("app.services.ingestion_service.UPLOAD_DIR", upload_root):
                receipt = ingest_path(uploaded, owner_role="operations")
                delete_document(receipt["document_id"], user_role="plant_manager")

            self.assertFalse(uploaded.exists())

if __name__ == "__main__":
    unittest.main()
