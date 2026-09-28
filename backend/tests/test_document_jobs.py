from types import SimpleNamespace
from uuid import uuid4

import pytest


class _FakePool:
    def __init__(self):
        self.calls = []

    async def enqueue_job(self, *args, **kwargs):
        self.calls.append((args, kwargs))

    async def aclose(self):
        pass


class _AsyncSessionContext:
    def __init__(self, session):
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, *_exc):
        return False


class _FakeSession:
    def __init__(self, job):
        self.job = job
        self.commits = 0

    async def get(self, _model, _job_id):
        return self.job

    async def commit(self):
        self.commits += 1


@pytest.mark.asyncio
async def test_repeated_delivery_is_not_suppressed_by_retained_arq_result(monkeypatch):
    import app.queue as queue_module

    pool = _FakePool()
    async def create_pool(_settings):
        return pool

    monkeypatch.setattr(queue_module, "create_pool", create_pool)
    monkeypatch.setattr(queue_module, "get_settings", lambda: SimpleNamespace(redis_url="redis://test"))

    job_id = str(uuid4())
    await queue_module.enqueue_document_job(job_id)
    await queue_module.enqueue_document_job(job_id)
    assert [call[0] for call in pool.calls] == [("process_document", job_id)] * 2
    assert pool.calls[0][1]["_job_id"] != pool.calls[1][1]["_job_id"]


@pytest.mark.asyncio
async def test_dispatch_failure_is_persisted_on_document_job(monkeypatch):
    import app.queue as queue_module

    job = SimpleNamespace(
        id=uuid4(), status="queued", dispatch_attempts=0,
        last_dispatch_at=None, last_dispatch_error=None,
    )
    session = _FakeSession(job)
    monkeypatch.setattr(queue_module, "session_factory", lambda: _AsyncSessionContext(session))

    async def fail_enqueue(_job_id):
        raise ConnectionError("redis unavailable")

    monkeypatch.setattr(queue_module, "enqueue_document_job", fail_enqueue)

    with pytest.raises(ConnectionError, match="redis unavailable"):
        await queue_module.dispatch_document_job(str(job.id))

    assert job.dispatch_attempts == 1
    assert job.last_dispatch_error == "redis unavailable"
    assert session.commits == 1


def _pool_context(pool):
    class _Context:
        async def __aenter__(self):
            return pool

        async def __aexit__(self, *_exc):
            return False

    return _Context()


def test_document_jobs_have_dispatch_fields_and_active_unique_index():
    from app.models import DocumentJob

    columns = DocumentJob.__table__.columns
    assert {"dispatch_attempts", "last_dispatch_at", "last_dispatch_error"}.issubset(columns.keys())
    indexes = {index.name: index for index in DocumentJob.__table__.indexes}
    assert indexes["uq_document_jobs_active_version"].unique is True


@pytest.mark.asyncio
async def test_completed_document_job_is_not_processed_again(monkeypatch):
    import app.tasks.document_tasks as tasks_module

    job = SimpleNamespace(id=uuid4(), status="completed", document_version_id=uuid4())

    class Session:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_exc):
            return False

        async def scalar(self, _statement):
            return job

    monkeypatch.setattr(tasks_module, "session_factory", lambda: Session())

    result = await tasks_module.process_document(None, str(job.id))

    assert result == {"status": "duplicate", "job_id": str(job.id), "job_status": "completed"}
