from arq import cron
from arq.connections import RedisSettings

from .config import get_settings
from .queue import dispatch_pending_document_jobs, recover_stale_document_jobs
from .tasks.document_tasks import process_document


class WorkerSettings:
    functions = [process_document]
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
    max_jobs = 4
    job_timeout = get_settings().document_job_timeout_seconds
    max_tries = get_settings().document_job_max_attempts
    cron_jobs = [
        cron(dispatch_pending_document_jobs, second={0, 30}, unique=True),
        cron(recover_stale_document_jobs, second=15, unique=True),
    ]
