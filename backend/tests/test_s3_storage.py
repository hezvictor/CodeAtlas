from types import SimpleNamespace

import pytest


class _FakeClient:
    class exceptions:
        ClientError = Exception

    def __init__(self, endpoint):
        self.endpoint = endpoint

    def generate_presigned_url(self, *_args, **_kwargs):
        return f"{self.endpoint}/codeatlas-documents/key"


@pytest.mark.asyncio
async def test_presigned_download_uses_browser_reachable_endpoint(monkeypatch):
    import app.storage.s3 as s3_module

    clients = []

    def fake_client(_service, **kwargs):
        client = _FakeClient(kwargs["endpoint_url"])
        clients.append(client)
        return client

    monkeypatch.setattr(s3_module.boto3, "client", fake_client)
    settings = SimpleNamespace(
        s3_bucket="codeatlas-documents",
        s3_endpoint="http://minio:9000",
        browser_s3_endpoint="http://localhost:9000",
        minio_root_user="user",
        minio_root_password="password",
        s3_region="us-east-1",
    )

    url = await s3_module.S3Storage(settings).presigned_get("key")

    assert url.startswith("http://localhost:9000/")
    assert [client.endpoint for client in clients] == ["http://minio:9000", "http://localhost:9000"]
