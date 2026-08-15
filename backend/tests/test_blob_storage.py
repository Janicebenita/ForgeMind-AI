from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from app.core.config import Settings
from app.storage.azure_blob import AzureBlobStore


class FakeBlob:
    def __init__(self, name: str) -> None:
        self.name = name
        self.url = f"https://example.blob.core.windows.net/documents/{name}"
        self.payload = b""
        self.metadata = {}
        self.content_settings = SimpleNamespace(content_type="application/octet-stream")

    def upload_blob(self, stream, **kwargs):
        self.payload = stream.read()
        self.metadata = kwargs["metadata"]
        self.content_settings = kwargs["content_settings"]
        return {"etag": '"phase-2-etag"'}

    def download_blob(self):
        return SimpleNamespace(readall=lambda: self.payload)

    def get_blob_properties(self):
        return SimpleNamespace(content_settings=self.content_settings)


class FakeContainer:
    def __init__(self) -> None:
        self.blobs: dict[str, FakeBlob] = {}

    def create_container(self) -> None:
        return None

    def get_blob_client(self, name: str) -> FakeBlob:
        self.blobs.setdefault(name, FakeBlob(name))
        return self.blobs[name]


class FakeService:
    def __init__(self, container: FakeContainer) -> None:
        self.container = container

    def get_container_client(self, _name: str) -> FakeContainer:
        return self.container


class BlobStorageTests(unittest.TestCase):
    def test_content_addressed_upload_preserves_lineage_and_downloads(self) -> None:
        container = FakeContainer()
        settings = Settings(
            azure_storage_connection_string="UseDevelopmentStorage=true",
            azure_storage_container="documents",
        )
        store = AzureBlobStore(
            settings=settings,
            service_client=FakeService(container),
            content_settings_factory=lambda **values: SimpleNamespace(**values),
        )

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "inspection report.txt"
            path.write_bytes(b"inspection evidence")
            receipt = store.upload_file(
                path,
                content_hash="a" * 64,
                owner_role="compliance",
                permission_level="plant",
            )

        payload, content_type = store.download_bytes(receipt.uri)
        self.assertEqual(payload, b"inspection evidence")
        self.assertEqual(content_type, "text/plain")
        self.assertEqual(receipt.etag, "phase-2-etag")
        self.assertIn("documents/aa/" + ("a" * 64), receipt.blob_name)
        self.assertEqual(container.blobs[receipt.blob_name].metadata["sha256"], "a" * 64)


if __name__ == "__main__":
    unittest.main()
