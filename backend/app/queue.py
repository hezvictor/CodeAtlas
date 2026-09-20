import logging
from datetime import UTC, datetime, timedelta

try:
    from arq import create_pool
    from arq.connections import RedisSettings
except ImportError:  # Keep API imports usable when the optional worker runtime is absent.
    create_pool = None
    RedisSettings = None
from sqlalchemy import select, update

from .config import get_settings
from .db import session_factory
from .models import DocumentJob

logger = logging.getLogger(__name__)
_DISPATCH_LEASE_SECONDS = 30


async def enqueue_document_job(job_id: str) -> None:
    if create_pool is None:
        raise RuntimeError("document worker dependencies are not installed")
    settings = RedisSettings.from_dsn(get_settings().redis_url) if RedisSettings else get_settings().redis_url
    pool = await create_pool(settings)
    try:
        await pool.enqueue_job("process_document", job_id, _job_id=f"document-job:{job_id}")
    finally:
        await pool.aclose()


async def _record_dispatch(job_id: str, error: Exception | None = None) -> None:
    async with session_factory() as session:
        job = await session.get(DocumentJob, job_id)
        if not job:
            return
        job.dispatch_attempts += 1
        job.last_dispatch_at = datetime.now(UTC)
        job.last_dispatch_error = str(error)[:500] if error else None
        await session.commit()


async def dispatch_document_job(job_id: str) -> None:
    try:
        await enqueue_document_job(job_id)
    except Exception as error:
        await _record_dispatch(job_id, error)
        raise
    await _record_dispatch(job_id)


async def dispatch_pending_document_jobs(_ctx=None) -> dict[str, int]:
    now = datetime.now(UTC)
    cutoff = now - timedelta(seconds=_DISPATCH_LEASE_SECONDS)
    async with session_factory() as session:
        job_ids = (
            await session.scalars(
                select(DocumentJob.id).where(
                    DocumentJob.status == "queued",
                    DocumentJob.available_at <= now,
                    (DocumentJob.last_dispatch_at.is_(None) | (DocumentJob.last_dispatch_at < cutoff)),
                )
            )
        ).all()

    dispatched = 0
    failed = 0
    for job_id in job_ids:
        try:
            await dispatch_document_job(str(job_id))
            dispatched += 1
        except Exception:
            failed += 1
            logger.exception("document job dispatch failed", extra={"job_id": str(job_id)})
    return {"dispatched": dispatched, "failed": failed}


async def recover_stale_document_jobs(_ctx=None) -> int:
    timeout = get_settings().document_job_timeout_seconds
    cutoff = datetime.now(UTC) - timedelta(seconds=timeout)
    async with session_factory() as session:
        result = await session.execute(
            update(DocumentJob)
            .where(DocumentJob.status == "running", DocumentJob.locked_at < cutoff)
            .values(
                status="queued",
                available_at=datetime.now(UTC),
                locked_at=None,
                locked_by=None,
                last_dispatch_at=None,
            )
        )
        await session.commit()
        return result.rowcount or 0
