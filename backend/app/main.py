import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .logging_config import configure_logging
from .routers.auth import router as auth_router

settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("CodeAtlas backend starting in %s environment", settings.app_env)
    yield
    logger.info("CodeAtlas backend stopped")


app = FastAPI(title="CodeAtlas API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router, prefix="/api/v1")


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "codeatlas-backend"}


@app.get("/api/v1/health", tags=["system"])
async def api_health() -> dict[str, str]:
    return {"status": "ok", "service": "codeatlas-api"}
