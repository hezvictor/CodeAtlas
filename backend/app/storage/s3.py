import asyncio
import re
from functools import partial
from pathlib import PurePath

import boto3

from ..config import get_settings


def object_key_for(user_id: str, group_id: str, document_id: str, version_no: int, filename: str) -> str:
    safe_name = PurePath(filename).name
    safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", safe_name)[:180] or "document"
    return f"users/{user_id}/groups/{group_id}/documents/{document_id}/versions/{version_no}/{safe_name}"


class S3Storage:
    def __init__(self, settings=None):
        settings = settings or get_settings()
        self.bucket = settings.s3_bucket
        credentials = {
            "aws_access_key_id": settings.minio_root_user,
            "aws_secret_access_key": settings.minio_root_password,
            "region_name": settings.s3_region,
        }
        self.client = boto3.client("s3", endpoint_url=settings.s3_endpoint, **credentials)
        browser_endpoint = getattr(settings, "browser_s3_endpoint", "") or settings.s3_endpoint
        self.browser_client = (
            self.client
            if browser_endpoint == settings.s3_endpoint
            else boto3.client("s3", endpoint_url=browser_endpoint, **credentials)
        )

    async def ensure_bucket(self) -> None:
        try:
            await asyncio.to_thread(partial(self.client.head_bucket, Bucket=self.bucket))
        except self.client.exceptions.ClientError:
            await asyncio.to_thread(partial(self.client.create_bucket, Bucket=self.bucket))

    async def put_bytes(self, key: str, data: bytes, content_type: str) -> None:
        await self.ensure_bucket()
        await asyncio.to_thread(partial(self.client.put_object, Bucket=self.bucket, Key=key, Body=data, ContentType=content_type))

    async def get_bytes(self, key: str) -> bytes:
        response = await asyncio.to_thread(partial(self.client.get_object, Bucket=self.bucket, Key=key))
        return await asyncio.to_thread(response["Body"].read)

    async def delete(self, key: str) -> None:
        await asyncio.to_thread(partial(self.client.delete_object, Bucket=self.bucket, Key=key))

    async def presigned_get(self, key: str, expires: int = 300) -> str:
        return await asyncio.to_thread(partial(self.browser_client.generate_presigned_url, "get_object", Params={"Bucket": self.bucket, "Key": key}, ExpiresIn=expires))
