from __future__ import annotations

import unittest
from types import SimpleNamespace

from app.core.config import Settings
from app.rag.providers import AzureFoundryProvider, LocalEmbeddingProvider, ProviderConfigurationError, provider_for


class FakeResponses:
    def create(self, **kwargs):
        if kwargs["store"] is not False or "Evidence:" not in kwargs["input"]:
            raise AssertionError("The provider did not send a non-retained, grounded request.")
        return SimpleNamespace(output_text="Evidence-grounded answer [S1]")


class FakeEmbeddings:
    def create(self, **kwargs):
        rows = [SimpleNamespace(index=index, embedding=[float(index), 1.0]) for index, _ in enumerate(kwargs["input"])]
        return SimpleNamespace(data=list(reversed(rows)))


class ProviderTests(unittest.TestCase):
    def test_local_provider_remains_available(self) -> None:
        provider = provider_for("local")
        self.assertIsInstance(provider, LocalEmbeddingProvider)
        self.assertTrue(provider.embed("pump vibration"))

    def test_azure_provider_requires_endpoint(self) -> None:
        with self.assertRaisesRegex(ProviderConfigurationError, "AZURE_OPENAI_ENDPOINT"):
            AzureFoundryProvider(Settings())

    def test_azure_provider_uses_grounded_prompt_and_orders_embeddings(self) -> None:
        settings = Settings(
            azure_openai_endpoint="https://example.openai.azure.com",
            azure_openai_api_key="test-key",
        )
        provider = AzureFoundryProvider(settings)
        provider._client_instance = SimpleNamespace(responses=FakeResponses(), embeddings=FakeEmbeddings())

        answer = provider.summarize(
            "Why did P-101 fail?",
            [{"filename": "WO-1.txt", "page_number": 1, "section": "Failure", "text": "Seal damage."}],
        )
        vectors = provider.embed_many(["first", "second"])

        self.assertEqual(answer, "Evidence-grounded answer [S1]")
        self.assertEqual(vectors, [[0.0, 1.0], [1.0, 1.0]])


if __name__ == "__main__":
    unittest.main()
