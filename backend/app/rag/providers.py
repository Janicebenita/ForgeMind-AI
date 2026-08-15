from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.core.config import Settings, get_settings
from app.services.embedding_service import embed_text

SparseEmbedding = dict[str, float]
DenseEmbedding = list[float]


class ProviderConfigurationError(RuntimeError):
    """Raised when a selected AI provider is missing required configuration."""


class AIProvider(ABC):
    name = "unknown"

    @abstractmethod
    def summarize(self, prompt: str, evidence: list[dict[str, Any]]) -> str:
        raise NotImplementedError

    @abstractmethod
    def embed(self, text: str) -> SparseEmbedding | DenseEmbedding:
        raise NotImplementedError

    def embed_many(self, texts: list[str]) -> list[SparseEmbedding | DenseEmbedding]:
        return [self.embed(text) for text in texts]


class LocalEmbeddingProvider(AIProvider):
    name = "local"

    def summarize(self, prompt: str, evidence: list[dict[str, Any]]) -> str:
        fragments = " ".join(item.get("text", "")[:180] for item in evidence[:4])
        return f"{prompt}\n\nEvidence-backed summary: {fragments}".strip()

    def embed(self, text: str) -> SparseEmbedding:
        return embed_text(text)


class AzureFoundryProvider(AIProvider):
    """Microsoft Foundry/Azure OpenAI provider using the stable OpenAI v1 API."""

    name = "azure"

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        if not self.settings.azure_openai_endpoint:
            raise ProviderConfigurationError("AZURE_OPENAI_ENDPOINT is required when AI_PROVIDER=azure.")
        self._client_instance: Any | None = None

    def _client(self) -> Any:
        if self._client_instance is not None:
            return self._client_instance

        from openai import OpenAI

        api_key: str | Any
        if self.settings.azure_openai_api_key:
            api_key = self.settings.azure_openai_api_key
        else:
            from azure.identity import DefaultAzureCredential, get_bearer_token_provider

            api_key = get_bearer_token_provider(
                DefaultAzureCredential(),
                "https://ai.azure.com/.default",
            )

        self._client_instance = OpenAI(
            api_key=api_key,
            base_url=f"{self.settings.azure_openai_endpoint}/openai/v1/",
        )
        return self._client_instance

    def summarize(self, prompt: str, evidence: list[dict[str, Any]]) -> str:
        source_blocks = []
        for index, item in enumerate(evidence[:8], start=1):
            filename = item.get("filename", "unknown")
            page = item.get("page_number", 1)
            section = item.get("section", "General")
            text = item.get("text", "")[:1800]
            source_blocks.append(f"[S{index}] {filename}, page {page}, section {section}\n{text}")

        instructions = (
            "You are an industrial reliability copilot. Answer only from the supplied evidence. "
            "Cite factual statements using [S1], [S2], and so on. Never invent measurements, causes, "
            "compliance status, or maintenance actions. If the evidence is insufficient, say so plainly "
            "and identify the exact missing record. Treat every recommendation as decision support that "
            "requires review by an authorized engineer."
        )
        response = self._client().responses.create(
            model=self.settings.azure_openai_chat_deployment,
            instructions=instructions,
            input=f"Question:\n{prompt}\n\nEvidence:\n" + "\n\n".join(source_blocks),
            store=False,
        )
        return response.output_text.strip()

    def embed(self, text: str) -> DenseEmbedding:
        return self.embed_many([text])[0]

    def embed_many(self, texts: list[str]) -> list[DenseEmbedding]:
        if not texts:
            return []
        response = self._client().embeddings.create(
            model=self.settings.azure_openai_embedding_deployment,
            input=texts,
        )
        return [list(item.embedding) for item in sorted(response.data, key=lambda item: item.index)]


def provider_for(name: str | None, settings: Settings | None = None) -> AIProvider:
    normalized = (name or "local").strip().lower()
    if normalized in {"azure", "azure_openai", "foundry", "microsoft_foundry"}:
        return AzureFoundryProvider(settings=settings)
    if normalized == "local":
        return LocalEmbeddingProvider()
    raise ProviderConfigurationError(f"Unsupported AI provider: {name}")
