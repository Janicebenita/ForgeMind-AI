from __future__ import annotations

from typing import Any

from app.core.config import Settings, get_settings
from app.core.document_access import azure_document_filter
from app.services.embedding_service import tokenize


class AzureSearchConfigurationError(RuntimeError):
    """Raised when Azure AI Search is selected without a usable endpoint."""


class AzureSearchStore:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        if not self.settings.azure_search_endpoint:
            raise AzureSearchConfigurationError(
                "AZURE_SEARCH_ENDPOINT is required when RETRIEVAL_BACKEND=azure_search."
            )

    def _credential(self) -> Any:
        if self.settings.azure_search_api_key:
            from azure.core.credentials import AzureKeyCredential

            return AzureKeyCredential(self.settings.azure_search_api_key)

        from azure.identity import DefaultAzureCredential

        return DefaultAzureCredential()

    def _search_client(self) -> Any:
        from azure.search.documents import SearchClient

        return SearchClient(
            endpoint=self.settings.azure_search_endpoint,
            index_name=self.settings.azure_search_index_name,
            credential=self._credential(),
        )

    def ensure_index(self) -> None:
        from azure.search.documents.indexes import SearchIndexClient
        from azure.search.documents.indexes.models import (
            HnswAlgorithmConfiguration,
            SearchField,
            SearchFieldDataType,
            SearchIndex,
            SearchableField,
            SimpleField,
            VectorSearch,
            VectorSearchProfile,
        )

        fields = [
            SimpleField(name="id", type=SearchFieldDataType.String, key=True, filterable=True),
            SimpleField(name="document_id", type=SearchFieldDataType.Int64, filterable=True),
            SimpleField(name="chunk_id", type=SearchFieldDataType.Int64, filterable=True),
            SearchableField(name="filename", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="doc_type", type=SearchFieldDataType.String, filterable=True, facetable=True),
            SimpleField(name="page_number", type=SearchFieldDataType.Int32, filterable=True),
            SearchableField(name="section", type=SearchFieldDataType.String),
            SearchableField(name="content", type=SearchFieldDataType.String),
            SimpleField(name="owner_role", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="permission_level", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="created_at", type=SearchFieldDataType.String, filterable=True),
            SearchField(
                name="content_vector",
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True,
                vector_search_dimensions=self.settings.azure_search_vector_dimensions,
                vector_search_profile_name="industrial-vector-profile",
            ),
        ]
        vector_search = VectorSearch(
            algorithms=[HnswAlgorithmConfiguration(name="industrial-hnsw")],
            profiles=[
                VectorSearchProfile(
                    name="industrial-vector-profile",
                    algorithm_configuration_name="industrial-hnsw",
                )
            ],
        )
        index = SearchIndex(
            name=self.settings.azure_search_index_name,
            fields=fields,
            vector_search=vector_search,
        )
        client = SearchIndexClient(
            endpoint=self.settings.azure_search_endpoint,
            credential=self._credential(),
        )
        client.create_or_update_index(index)

    def upload_chunks(self, chunks: list[dict[str, Any]]) -> int:
        if not chunks:
            return 0
        for chunk in chunks:
            vector = chunk.get("content_vector", [])
            if len(vector) != self.settings.azure_search_vector_dimensions:
                raise ValueError(
                    "Embedding dimension mismatch: "
                    f"expected {self.settings.azure_search_vector_dimensions}, got {len(vector)}."
                )
        results = self._search_client().upload_documents(documents=chunks)
        failed = [result.key for result in results if not result.succeeded]
        if failed:
            raise RuntimeError(f"Azure AI Search rejected chunk keys: {', '.join(failed)}")
        return len(results)

    def clear_documents_for_evaluation(self) -> int:
        """Clear a dedicated evaluation index while refusing production-like names."""
        index_name = self.settings.azure_search_index_name.lower()
        if "eval" not in index_name and "benchmark" not in index_name:
            raise ValueError(
                "Azure benchmark reset is permitted only when AZURE_SEARCH_INDEX_NAME "
                "contains 'eval' or 'benchmark'."
            )
        client = self._search_client()
        documents = [
            {"id": item["id"]}
            for item in client.search(search_text="*", select=["id"], top=1000)
        ]
        if not documents:
            return 0
        results = client.delete_documents(documents=documents)
        failed = [result.key for result in results if not result.succeeded]
        if failed:
            raise RuntimeError(f"Azure AI Search rejected deletion keys: {', '.join(failed)}")
        return len(results)

    def delete_document(self, document_id: int) -> int:
        client = self._search_client()
        matches = client.search(
            search_text="*",
            filter=f"document_id eq {int(document_id)}",
            select=["id"],
            top=1000,
        )
        documents = [{"id": item["id"]} for item in matches]
        if not documents:
            return 0
        results = client.delete_documents(documents=documents)
        failed = [result.key for result in results if not result.succeeded]
        if failed:
            raise RuntimeError(f"Azure AI Search rejected deletion keys: {', '.join(failed)}")
        return len(results)

    def search(
        self,
        question: str,
        vector: list[float],
        limit: int = 6,
        user_role: str = "plant_manager",
    ) -> list[dict[str, Any]]:
        from azure.search.documents.models import VectorizedQuery

        vector_query = VectorizedQuery(
            vector=vector,
            k_nearest_neighbors=max(limit, 10),
            fields="content_vector",
        )
        response = self._search_client().search(
            search_text=question,
            vector_queries=[vector_query],
            search_fields=["content", "filename", "section"],
            filter=azure_document_filter(user_role),
            select=[
                "document_id",
                "chunk_id",
                "filename",
                "doc_type",
                "page_number",
                "section",
                "content",
                "owner_role",
                "permission_level",
                "created_at",
            ],
            top=limit,
        )
        question_terms = set(tokenize(question))
        results: list[dict[str, Any]] = []
        for item in response:
            text = item.get("content", "")
            text_terms = set(tokenize(text))
            matched_terms = sorted(question_terms & text_terms)
            raw_score = max(0.0, float(item.get("@search.score", 0.0)))
            normalized_score = raw_score / (1.0 + raw_score)
            results.append(
                {
                    "document_id": item.get("document_id", 0),
                    "chunk_id": item.get("chunk_id", 0),
                    "filename": item.get("filename", "unknown"),
                    "doc_type": item.get("doc_type", "IndustrialDocument"),
                    "page_number": item.get("page_number", 1),
                    "section": item.get("section", "General"),
                    "text": text,
                    "owner_role": item.get("owner_role", "operations"),
                    "permission_level": item.get("permission_level", "plant"),
                    "created_at": item.get("created_at", ""),
                    "score": round(normalized_score, 4),
                    "raw_search_score": round(raw_score, 4),
                    "token_overlap": round(len(matched_terms) / max(len(question_terms), 1), 4),
                    "matched_terms": matched_terms,
                    "retrieval_backend": "azure_search",
                }
            )
        return results
