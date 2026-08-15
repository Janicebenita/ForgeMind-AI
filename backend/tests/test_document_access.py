from __future__ import annotations

import unittest
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from app.core.config import get_settings
from app.core.document_access import (
    allowed_owner_roles,
    azure_document_filter,
    can_access_document,
)
from app.database import clear_demo_data, init_db
from app.services.ingestion_service import _azure_blob_store, _azure_search_store, ingest_path
from app.services.retrieval_service import retrieve_local


class DocumentAccessTests(unittest.TestCase):
    def test_plant_manager_has_plant_wide_access(self) -> None:
        self.assertIsNone(allowed_owner_roles("plant_manager"))
        self.assertIsNone(azure_document_filter("plant_manager"))
        self.assertTrue(can_access_document("plant_manager", "safety", "plant"))

    def test_auditor_filter_contains_only_allowed_scopes(self) -> None:
        result = azure_document_filter("compliance_auditor")

        self.assertIn("permission_level eq 'public'", result)
        self.assertIn("compliance", result)
        self.assertIn("quality", result)
        self.assertNotIn("reliability", result)
        self.assertFalse(
            can_access_document("compliance_auditor", "reliability", "plant")
        )

    def test_unknown_role_can_read_only_public_documents(self) -> None:
        self.assertEqual(azure_document_filter("unknown"), "permission_level eq 'public'")
        self.assertTrue(can_access_document("unknown", "operations", "public"))
        self.assertFalse(can_access_document("unknown", "operations", "plant"))

    def test_local_retrieval_excludes_disallowed_owner_scope(self) -> None:
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
                root = Path(directory)
                operations = root / "operations.txt"
                safety = root / "safety.txt"
                operations.write_text("pump schedule operations", encoding="utf-8")
                safety.write_text("restricted zephyr safety finding", encoding="utf-8")
                ingest_path(operations, owner_role="operations")
                ingest_path(safety, owner_role="safety")

            auditor_results = retrieve_local(
                "restricted zephyr safety finding",
                user_role="compliance_auditor",
            )
            manager_results = retrieve_local(
                "restricted zephyr safety finding",
                user_role="plant_manager",
            )

        get_settings.cache_clear()
        _azure_blob_store.cache_clear()
        _azure_search_store.cache_clear()
        self.assertNotIn("safety.txt", {item["filename"] for item in auditor_results})
        self.assertIn("safety.txt", {item["filename"] for item in manager_results})


if __name__ == "__main__":
    unittest.main()
