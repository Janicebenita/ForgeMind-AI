from __future__ import annotations

from typing import Any

from app.core.config import get_settings
from app.core.document_access import allowed_owner_roles
from app.database import loads, query
from app.rag.azure_search import AzureSearchStore
from app.rag.providers import provider_for
from app.services.embedding_service import cosine, embed_text, tokenize

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "before",
    "by",
    "for",
    "from",
    "has",
    "have",
    "how",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "show",
    "the",
    "to",
    "what",
    "when",
    "where",
    "which",
    "why",
    "with",
}


def signal_terms(text: str) -> set[str]:
    return {token for token in set(tokenize(text)) if token not in STOPWORDS and len(token) > 2}


def retrieve(
    question: str,
    limit: int = 6,
    user_role: str = "plant_manager",
) -> list[dict[str, Any]]:
    settings = get_settings()
    if settings.retrieval_backend == "azure_search":
        provider = provider_for("azure", settings=settings)
        vector = provider.embed(question)
        if not isinstance(vector, list):
            raise TypeError("Azure AI Search requires a dense embedding vector.")
        return AzureSearchStore(settings=settings).search(
            question,
            vector,
            limit=limit,
            user_role=user_role,
        )
    return retrieve_local(question, limit=limit, user_role=user_role)


def retrieve_local(
    question: str,
    limit: int = 6,
    user_role: str = "plant_manager",
) -> list[dict[str, Any]]:
    q_emb = embed_text(question)
    q_tokens = set(tokenize(question))
    q_signal_tokens = signal_terms(question)
    scopes = allowed_owner_roles(user_role)
    access_clause = ""
    parameters: tuple[Any, ...] = ()
    if scopes is not None:
        if scopes:
            placeholders = ", ".join("?" for _ in scopes)
            access_clause = (
                "WHERE d.permission_level = 'public' "
                f"OR (d.permission_level = 'plant' AND d.owner_role IN ({placeholders}))"
            )
            parameters = tuple(sorted(scopes))
        else:
            access_clause = "WHERE d.permission_level = 'public'"
    rows = query(
        f"""
        SELECT c.id AS chunk_id, c.document_id, c.page_number, c.section, c.text, c.embedding,
               d.filename, d.doc_type, d.owner_role, d.permission_level, d.created_at
        FROM chunks c
        JOIN documents d ON d.id = c.document_id
        {access_clause}
        """,
        parameters,
    )
    scored = []
    for row in rows:
        emb_score = cosine(q_emb, loads(row["embedding"], {}))
        text_tokens = set(tokenize(row["text"]))
        overlap = len(q_tokens & text_tokens) / max(len(q_tokens), 1)
        signal_overlap = len(q_signal_tokens & text_tokens) / max(len(q_signal_tokens), 1)
        score = round((0.72 * emb_score) + (0.28 * overlap), 4)
        row["score"] = score
        row["token_overlap"] = round(signal_overlap, 4)
        row["matched_terms"] = sorted(q_signal_tokens & text_tokens)
        row["retrieval_backend"] = "local"
        row.pop("embedding", None)
        scored.append(row)
    return sorted(scored, key=lambda item: item["score"], reverse=True)[:limit]


def evidence_is_sufficient(results: list[dict[str, Any]], threshold: float = 0.08, overlap_threshold: float = 0.18) -> bool:
    if not results:
        return False
    top = results[0]
    return top["score"] >= threshold and top.get("token_overlap", 0) >= overlap_threshold
