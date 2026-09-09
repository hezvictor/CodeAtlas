import asyncio
import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .db import engine
from .logging_config import configure_logging, request_id
from .routers.auth import router as auth_router
from .routers.conversations import router as conversations_router
from .routers.users import router as users_router

settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger(__name__)


async def _cleanup_runs(registry):
    while True:
        await asyncio.sleep(60)
        await registry.cleanup()


@asynccontextmanager
async def lifespan(_: FastAPI):
    from .routers.conversations import runs
    cleanup_task = asyncio.create_task(_cleanup_runs(runs))
    logger.info("CodeAtlas backend starting in %s environment", settings.app_env)
    try:
        yield
    finally:
        cleanup_task.cancel()
        await asyncio.gather(cleanup_task, return_exceptions=True)
        logger.info("CodeAtlas backend stopped")


app = FastAPI(title="CodeAtlas API", version="0.1.0", lifespan=lifespan)

@app.exception_handler(HTTPException)
async def http_error_handler(_: Request, exc: HTTPException):
    code = "INVALID_CREDENTIALS" if exc.status_code == 401 and "password" in str(exc.detail).lower() else "REQUEST_FAILED"
    return JSONResponse(status_code=exc.status_code, content={"code": code, "message": str(exc.detail), "details": {}})

@app.exception_handler(RequestValidationError)
async def validation_error_handler(_: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"code": "VALIDATION_ERROR", "message": "请求参数不合法", "details": exc.errors()})


@app.middleware("http")
async def request_logging(request, call_next):
    token = request_id.set(request.headers.get("X-Request-ID", str(uuid.uuid4())))
    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id.get()
        return response
    finally:
        request_id.reset(token)


app.add_middleware(CORSMiddleware, allow_origins=[settings.frontend_url], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(auth_router, prefix="/api/v1")
app.include_router(conversations_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "codeatlas-backend"}


@app.get("/api/v1/health", tags=["system"])
async def api_health() -> dict[str, str]:
    return {"status": "ok", "service": "codeatlas-api"}


@app.get("/ready", tags=["system"])
async def ready() -> dict[str, str]:
    from sqlalchemy import text
    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))
    return {"status": "ready", "service": "codeatlas-backend"}
