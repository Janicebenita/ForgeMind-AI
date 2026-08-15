from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from pydantic import ValidationError

from app.core.config import Settings


class SettingsTests(unittest.TestCase):
    def test_environment_variables_select_azure(self) -> None:
        variables = {
            "AI_PROVIDER": "azure",
            "RETRIEVAL_BACKEND": "azure_search",
            "DOCUMENT_STORAGE_BACKEND": "azure_blob",
            "AZURE_OPENAI_ENDPOINT": "https://example.openai.azure.com/",
            "AZURE_SEARCH_ENDPOINT": "https://example.search.windows.net/",
            "AZURE_STORAGE_ACCOUNT_URL": "https://example.blob.core.windows.net/",
        }
        with patch.dict(os.environ, variables, clear=True):
            settings = Settings.from_environment()

        self.assertEqual(settings.ai_provider, "azure")
        self.assertEqual(settings.retrieval_backend, "azure_search")
        self.assertEqual(settings.document_storage_backend, "azure_blob")
        self.assertEqual(settings.azure_openai_endpoint, "https://example.openai.azure.com")
        self.assertEqual(settings.azure_search_endpoint, "https://example.search.windows.net")
        self.assertEqual(settings.azure_storage_account_url, "https://example.blob.core.windows.net")
        self.assertTrue(settings.azure_readiness()["foundry_configured"])
        self.assertTrue(settings.azure_readiness()["search_configured"])
        self.assertTrue(settings.azure_readiness()["storage_configured"])

    def test_default_secret_is_rejected_in_production(self) -> None:
        with self.assertRaisesRegex(ValidationError, "JWT_SECRET must be replaced"):
            Settings(environment="production")

    def test_postgres_environment_builds_encoded_database_url(self) -> None:
        settings = Settings(
            postgres_host="forgemind.postgres.database.azure.com",
            postgres_user="forge admin",
            postgres_password="safe:/password",
        )

        self.assertEqual(
            settings.database_url,
            "postgresql://forge%20admin:safe%3A%2Fpassword@"
            "forgemind.postgres.database.azure.com:5432/forgemind?sslmode=require",
        )


if __name__ == "__main__":
    unittest.main()
