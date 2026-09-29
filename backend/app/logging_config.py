import logging
import logging.config
from contextvars import ContextVar

request_id: ContextVar[str] = ContextVar("request_id", default="-")


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id.get()
        return True


class TemporaryAccessFilter(logging.Filter):
    def filter(self, record):
        # Access URLs may contain an ephemeral file ID. Do not persist them.
        return "/temporary-files" not in record.getMessage()


def configure_logging(level: str) -> None:
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "filters": {"request_id": {"()": "app.logging_config.RequestIdFilter"}},
            "formatters": {"default": {"format": "%(asctime)s %(levelname)s [%(request_id)s] %(name)s %(message)s"}},
            "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "default", "filters": ["request_id"]}},
            "root": {"level": level, "handlers": ["console"]},
        }
    )
    logging.getLogger("uvicorn.access").addFilter(TemporaryAccessFilter())
