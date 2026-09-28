"""Isolated browser smoke harness: real API/Postgres, fake external storage/provider.

Only run against a disposable database. Production imports never load this file.
Run: python -m uvicorn tests.lifecycle_smoke_server:app --port 8000
"""
import asyncio
from contextlib import asynccontextmanager
from urllib.parse import quote

from fastapi import Response
from sqlalchemy import select

from app.db import session_factory
from app.main import app
from app.models import DocumentJob
from app.routers import attachments, knowledge_documents
from app.tasks import document_tasks


class SmokeStorage:
    objects = {}

    async def put_bytes(self, key, data, content_type):
        await asyncio.sleep(0.5)
        self.objects[key] = (data, content_type)

    async def get_bytes(self, key):
        return self.objects[key][0]

    async def delete(self, key):
        self.objects.pop(key, None)

    async def presigned_get(self, key, filename=None):
        return "http://127.0.0.1:8000/smoke-download?key=" + quote(key, safe="")


class SmokeProvider:
    async def embed_documents(self, texts):
        await asyncio.sleep(1)
        return [[0.1] * 1024 for _ in texts]


async def no_dispatch(_):
    pass


async def poll():
    while True:
        await asyncio.sleep(1)
        async with session_factory() as session:
            ids = (await session.scalars(select(DocumentJob.id).where(DocumentJob.status == "queued"))).all()
        for job_id in ids:
            await document_tasks.process_document(None, str(job_id))
        await document_tasks.cleanup_deleted_document_objects()


original_lifespan = app.router.lifespan_context


@asynccontextmanager
async def lifespan(application):
    knowledge_documents.S3Storage = SmokeStorage
    attachments.S3Storage = SmokeStorage
    document_tasks.S3Storage = SmokeStorage
    document_tasks.UserEmbeddingProvider = lambda *_: SmokeProvider()
    knowledge_documents.dispatch_document_job = no_dispatch
    attachments.dispatch_document_job = no_dispatch
    document_tasks.project_embedding_is_configured = lambda: True
    async with original_lifespan(application):
        task = asyncio.create_task(poll())
        try:
            yield
        finally:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)


app.router.lifespan_context = lifespan


@app.get("/smoke-download")
async def download(key: str):
    data, mime = SmokeStorage.objects[key]
    return Response(data, media_type=mime)
