from __future__ import annotations

import os
from functools import lru_cache
from typing import Literal
from urllib.parse import quote

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Settings(BaseModel):
    model_config = ConfigDict(extra="ignore")

    app_name: str = "ForgeMind AI"
    environment: str = "development"
    seed_demo_on_startup: bool = True
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    database_url: str = "sqlite:///./app/data/forgemind.db"
    postgres_url: str = "postgresql+psycopg://forgemind:forgemind@postgres:5432/forgemind"
    postgres_host: str | None = None
    postgres_port: int = 5432
    postgres_database: str = "forgemind"
    postgres_user: str | None = None
    postgres_password: str | None = None
    postgres_sslmode: str = "require"
    redis_url: str = "redis://redis:6379/0"
    chroma_url: str = "http://chromadb:8000"
    jwt_secret: str = Field(default="change-me-for-production", min_length=16)
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 480

    ai_provider: Literal["local", "azure"] = "local"
    retrieval_backend: Literal["local", "azure_search"] = "local"
    document_storage_backend: Literal["local", "azure_blob"] = "local"
    max_upload_bytes: int = 25_000_000

    openai_api_key: str | None = None
    gemini_api_key: str | None = None

    azure_openai_endpoint: str | None = None
    azure_openai_api_key: str | None = None
    azure_openai_chat_deployment: str = "gpt-4.1-mini"
    azure_openai_embedding_deployment: str = "text-embedding-3-small"

    azure_search_endpoint: str | None = None
    azure_search_api_key: str | None = None
    azure_search_index_name: str = "forgemind-chunks"
    azure_search_vector_dimensions: int = 1536

    azure_storage_connection_string: str | None = None
    azure_storage_account_url: str | None = None
    azure_storage_container: str = "forgemind-documents"

    @classmethod
    def from_environment(cls) -> "Settings":
        values = {
            field_name: os.environ[field_name.upper()]
            for field_name in cls.model_fields
            if field_name.upper() in os.environ
        }
        return cls.model_validate(values)

    @field_validator("azure_openai_endpoint", "azure_search_endpoint", "azure_storage_account_url")
    @classmethod
    def strip_trailing_slash(cls, value: str | None) -> str | None:
        return value.rstrip("/") if value else value

    @model_validator(mode="after")
    def reject_default_production_secret(self) -> "Settings":
        if self.postgres_host and self.postgres_user and self.postgres_password:
            user = quote(self.postgres_user, safe="")
            password = quote(self.postgres_password, safe="")
            database = quote(self.postgres_database, safe="")
            self.database_url = (
                f"postgresql://{user}:{password}@{self.postgres_host}:"
                f"{self.postgres_port}/{database}?sslmode={quote(self.postgres_sslmode, safe='')}"
            )
        if self.environment.lower() == "production" and self.jwt_secret == "change-me-for-production":
            raise ValueError("JWT_SECRET must be replaced in production.")
        return self

    @property
    def cors_allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    def azure_readiness(self) -> dict[str, object]:
        foundry_ready = bool(self.azure_openai_endpoint and self.azure_openai_chat_deployment and self.azure_openai_embedding_deployment)
        search_ready = bool(self.azure_search_endpoint and self.azure_search_index_name)
        storage_ready = bool(self.azure_storage_connection_string or self.azure_storage_account_url)
        return {
            "ai_provider": self.ai_provider,
            "retrieval_backend": self.retrieval_backend,
            "document_storage_backend": self.document_storage_backend,
            "foundry_configured": foundry_ready,
            "search_configured": search_ready,
            "storage_configured": storage_ready,
            "foundry_authentication": "api_key" if self.azure_openai_api_key else "managed_identity",
            "search_authentication": "api_key" if self.azure_search_api_key else "managed_identity",
            "storage_authentication": "connection_string" if self.azure_storage_connection_string else "managed_identity",
        }


@lru_cache
def get_settings() -> Settings:
    return Settings.from_environment()
