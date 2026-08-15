from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.core.config import get_settings
from app.database import clear_demo_data, init_db, query
from app.services.ingestion_service import _azure_blob_store, _azure_search_store, ingest_path


class IngestionLineageTests(unittest.TestCase):
    def test_same_content_is_indexed_once(self) -> None:
        environment = {
            "AI_PROVIDER": "local",
            "RETRIEVAL_BACKEND": "local",
            "DOCUMENT_STORAGE_BACKEND": "local",
        }
        with patch.dict(os.environ, environment):
            get_settings.cache_clear()
            _azure_blob_store.cache_clear()
            _azure_search_store.cache_clear()
            init_db()
            clear_demo_data()
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "SOP-lineage.txt"
                path.write_text("# SOP\nAsset: P-101\nVerify isolation.", encoding="utf-8")
                first = ingest_path(path, owner_role="operations")
                second = ingest_path(path, owner_role="operations")

            rows = query(
                "SELECT id, content_hash, storage_backend, indexing_status FROM documents"
            )

        get_settings.cache_clear()
        _azure_blob_store.cache_clear()
        _azure_search_store.cache_clear()
        self.assertEqual(first["status"], "indexed")
        self.assertEqual(second["status"], "duplicate")
        self.assertEqual(first["document_id"], second["document_id"])
        self.assertEqual(len(rows), 1)
        self.assertEqual(len(rows[0]["content_hash"]), 64)
        self.assertEqual(rows[0]["storage_backend"], "local")
        self.assertEqual(rows[0]["indexing_status"], "local_indexed")


if __name__ == "__main__":
    unittest.main()
