try:
    from arq import cron
    from arq.connections import RedisSettings
except ImportError:  # Worker commands still require arq; importing API settings should not.
    def cron(function, **_kwargs):
        return function

    class RedisSettings:
        @classmethod
        def from_dsn(cls, value):
            return value

from .chat_runtime.infrastructure import RuntimeResources
from .chat_runtime.service import cleanup_chat_runs, dispatch_chat_runs, process_chat_run
from .config import get_settings
from .queue import dispatch_pending_document_jobs, recover_stale_document_jobs
from .tasks.auth_tasks import cleanup_refresh_tokens
from .tasks.document_tasks import cleanup_deleted_document_objects, process_document


async def startup(ctx):
    runtime = RuntimeResources()
    try:
        ctx["chat_runtime"] = await runtime.open()
    except Exception:
        await runtime.close()
        raise


async def shutdown(ctx):
    await ctx["chat_runtime"].close()


class WorkerSettings:
    functions = [process_document, process_chat_run]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
    max_jobs = 4
    job_timeout = get_settings().document_job_timeout_seconds
    max_tries = get_settings().document_job_max_attempts
    cron_jobs = [
        cron(dispatch_chat_runs, second=set(range(0, 60, 5)), unique=True),
        cron(cleanup_chat_runs, minute=set(range(0, 60, 5)), second=5, unique=True),
        cron(dispatch_pending_document_jobs, second={0, 30}, unique=True),
        cron(recover_stale_document_jobs, second=15, unique=True),
        cron(cleanup_deleted_document_objects, second={10, 40}, unique=True),
        cron(cleanup_refresh_tokens, hour={3}, minute=0, unique=True),
        cron(cleanup_refresh_tokens, minute=10, unique=True),
    ]
