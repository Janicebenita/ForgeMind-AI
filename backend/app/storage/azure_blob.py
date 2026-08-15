from __future__ import annotations

import mimetypes
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
from urllib.parse import unquote, urlparse

from app.core.config import Settings, get_settings


class AzureBlobConfigurationError(RuntimeError):
    """Raised when Azure Blob Storage is selected without usable configuration."""


@dataclass(frozen=True)
class BlobReceipt:
    uri: str
    etag: str
    blob_name: str
    content_type: str


class AzureBlobStore:
    def __init__(
        self,
        settings: Settings | None = None,
        service_client: Any | None = None,
        content_settings_factory: Callable[..., Any] | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        if not self.settings.azure_storage_connection_string and not self.settings.azure_storage_account_url:
            raise AzureBlobConfigurationError(
                "AZURE_STORAGE_CONNECTION_STRING or AZURE_STORAGE_ACCOUNT_URL is required "
                "when DOCUMENT_STORAGE_BACKEND=azure_blob."
            )
        self._service_client = service_client
        self._content_settings_factory = content_settings_factory

    def _service(self) -> Any:
        if self._service_client is not None:
            return self._service_client

        from azure.storage.blob import BlobServiceClient

        if self.settings.azure_storage_connection_string:
            self._service_client = BlobServiceClient.from_connection_string(
                self.settings.azure_storage_connection_string
            )
        else:
            from azure.identity import DefaultAzureCredential

            self._service_client = BlobServiceClient(
                account_url=self.settings.azure_storage_account_url,
                credential=DefaultAzureCredential(),
            )
        return self._service_client

    def _content_settings(self, content_type: str) -> Any:
        if self._content_settings_factory:
            return self._content_settings_factory(content_type=content_type)
        from azure.storage.blob import ContentSettings

        return ContentSettings(content_type=content_type)

    def _container(self) -> Any:
        container = self._service().get_container_client(self.settings.azure_storage_container)
        try:
            container.create_container()
        except Exception as exc:
            if exc.__class__.__name__ not in {"ResourceExistsError", "ContainerAlreadyExists"}:
                raise
        return container

    def upload_file(
        self,
        path: Path,
        content_hash: str,
        owner_role: str,
        permission_level: str,
    ) -> BlobReceipt:
        safe_filename = Path(path.name).name
        blob_name = f"documents/{content_hash[:2]}/{content_hash}/{safe_filename}"
        content_type = mimetypes.guess_type(safe_filename)[0] or "application/octet-stream"
        blob = self._container().get_blob_client(blob_name)
        with path.open("rb") as stream:
            result = blob.upload_blob(
                stream,
                overwrite=True,
                metadata={
                    "sha256": content_hash,
                    "owner_role": owner_role,
                    "permission_level": permission_level,
                },
                content_settings=self._content_settings(content_type),
            )
        etag = result.get("etag", "") if isinstance(result, dict) else getattr(result, "etag", "")
        return BlobReceipt(
            uri=blob.url,
            etag=str(etag).strip('"'),
            blob_name=blob_name,
            content_type=content_type,
        )

    def download_bytes(self, blob_uri: str) -> tuple[bytes, str]:
        parsed = urlparse(blob_uri)
        marker = f"/{self.settings.azure_storage_container}/"
        if marker not in parsed.path:
            raise ValueError("Blob URI does not belong to the configured document container.")
        blob_name = unquote(parsed.path.split(marker, maxsplit=1)[1])
        blob = self._container().get_blob_client(blob_name)
        payload = blob.download_blob().readall()
        properties = blob.get_blob_properties()
        content_settings = getattr(properties, "content_settings", None)
        content_type = getattr(content_settings, "content_type", None) or "application/octet-stream"
        return payload, content_type

    def delete(self, blob_uri: str) -> None:
        parsed = urlparse(blob_uri)
        marker = f"/{self.settings.azure_storage_container}/"
        if marker not in parsed.path:
            raise ValueError("Blob URI does not belong to the configured document container.")
        blob_name = unquote(parsed.path.split(marker, maxsplit=1)[1])
        self._container().get_blob_client(blob_name).delete_blob(delete_snapshots="include")
