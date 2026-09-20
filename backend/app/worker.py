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

from .config import get_settings
from .queue import dispatch_pending_document_jobs, recover_stale_document_jobs
from .tasks.document_tasks import cleanup_deleted_document_objects, process_document
from .tasks.auth_tasks import cleanup_refresh_tokens


class WorkerSettings:
    functions = [process_document]
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
    max_jobs = 4
    job_timeout = get_settings().document_job_timeout_seconds
    max_tries = get_settings().document_job_max_attempts
    cron_jobs = [
        cron(dispatch_pending_document_jobs, second={0, 30}, unique=True),
        cron(recover_stale_document_jobs, second=15, unique=True),
        cron(cleanup_deleted_document_objects, minute={0, 15, 30, 45}, unique=True),
        cron(cleanup_refresh_tokens, hour={3}, minute=0, unique=True),
        cron(cleanup_refresh_tokens, minute=10, unique=True),
    ]
