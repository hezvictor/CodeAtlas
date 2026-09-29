import asyncio
import logging
import time

import httpx
from botocore.exceptions import BotoCoreError, ClientError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..models import EmbeddingConfig

logger = logging.getLogger(__name__)


def embedding_batch_limit(model: str, configured: int) -> int:
    limit = 10 if model in {"text-embedding-v3", "text-embedding-v4"} else 25
    return min(limit, max(1, configured))


def processing_error(error: Exception) -> tuple[str, str, bool]:
    """Classify failures without persisting credentials, URLs or document input."""
    if isinstance(error, httpx.HTTPStatusError):
        status = error.response.status_code
        try:
            data = error.response.json()
            provider = data.get("error") or data
            code = str(provider.get("code", ""))[:80]
            detail = str(provider.get("message", "")).lower()
        except (ValueError, AttributeError, TypeError):
            code, detail = "", ""
        label = "向量服务请求失败"
        if status in {401, 403}:
            label = "Embedding 配置或权限无效，请检查模型配置"
        elif status == 429:
            label = "向量服务限流，等待自动重试"
        elif status >= 500:
            label = "向量服务暂时不可用，等待自动重试"
        elif "batch" in detail:
            label = "向量请求批次超出模型限制"
        elif "length" in detail or "token" in detail:
            label = "文本切块超出模型输入长度限制"
        # Provider codes are identifiers, not arbitrary response content.
        safe_code = "".join(char for char in code if char.isalnum() or char in "_-.")
        return f"EMBEDDING_HTTP_{status}", f"{label}（HTTP {status}{' · ' + safe_code if safe_code else ''}）", status == 429 or status >= 500
    if isinstance(error, (httpx.TimeoutException, httpx.TransportError, TimeoutError, ConnectionError)):
        return "SERVICE_UNAVAILABLE", "网络或服务暂时不可用，等待自动重试", True
    if isinstance(error, ClientError):
        status = error.response.get("ResponseMetadata", {}).get("HTTPStatusCode", 0)
        if status == 404:
            return "SOURCE_FILE_MISSING", "原文件不存在，请删除此记录后重新上传", False
        return "SOURCE_STORAGE_ERROR", "原文件存储服务访问失败，请检查服务和权限", status >= 500 or status == 429
    if isinstance(error, BotoCoreError):
        return "SOURCE_STORAGE_UNAVAILABLE", "原文件存储服务暂时不可用，等待自动重试", True
    if isinstance(error, ValueError):
        message = str(error)
        if message.startswith("embedding dimension mismatch"):
            message = "向量维度与数据库配置不一致，请检查 Embedding 模型和维度配置"
        elif message.startswith("embedding count mismatch"):
            message = "向量服务返回数量与文本块数量不一致，索引未启用"
        elif message.startswith("embedding input"):
            message = "文本块为空或超出模型输入长度限制，请检查文件内容和切块配置"
        return "INVALID_DOCUMENT", message[:300], False
    return "DOCUMENT_PROCESSING_FAILED", "文档处理失败，请重试或联系管理员", False


def project_embedding_is_configured(settings=None) -> bool:
    settings = settings or get_settings()
    return bool(getattr(settings, "dashscope_api_key", "") and getattr(settings, "embedding_model", ""))


def validate_embedding_vectors(vectors: list[list[float]], expected_count: int, dimensions: int) -> list[list[float]]:
    if len(vectors) != expected_count:
        raise ValueError(f"embedding count mismatch: expected {expected_count}, got {len(vectors)}")
    if any(len(vector) != dimensions for vector in vectors):
        raise ValueError(f"embedding dimension mismatch: expected {dimensions}")
    return vectors


def _batches(values: list[str], size: int):
    for start in range(0, len(values), size):
        yield start, values[start:start + size]


class EmbeddingProvider:
    async def _embed_batches(self, texts: list[str], *, api_key: str, model: str, settings) -> list[list[float]]:
        if not texts:
            return []
        max_chars = max(1, int(getattr(settings, "embedding_max_input_chars", 12000)))
        for index, text in enumerate(texts):
            if not text.strip():
                raise ValueError(f"embedding input {index} is empty")
            if len(text) > max_chars:
                raise ValueError(f"embedding input {index} exceeds {max_chars} characters")
        batch_size = embedding_batch_limit(model, int(getattr(settings, "embedding_batch_size", 10)))
        vectors: list[list[float]] = []
        timeout = httpx.Timeout(120, connect=10)
        async with httpx.AsyncClient(timeout=timeout) as client:
            for offset, batch in _batches(texts, batch_size):
                body = {"model": model, "input": batch}
                response = None
                for attempt in range(int(getattr(settings, "embedding_max_retries", 2)) + 1):
                    started = time.monotonic()
                    try:
                        response = await client.post(
                            settings.dashscope_base_url.rstrip("/") + "/embeddings",
                            headers={"Authorization": f"Bearer {api_key}"},
                            json=body,
                        )
                        response.raise_for_status()
                        break
                    except (httpx.TimeoutException, httpx.TransportError, httpx.HTTPStatusError) as error:
                        status = getattr(getattr(error, "response", None), "status_code", None)
                        retryable = status == 429 or (status is not None and status >= 500) or not status
                        if not retryable or attempt >= int(getattr(settings, "embedding_max_retries", 2)):
                            raise
                        delay = min(
                            float(getattr(settings, "embedding_retry_max_delay_seconds", 8.0)),
                            float(getattr(settings, "embedding_retry_base_delay_seconds", 0.5)) * (2 ** attempt),
                        )
                        logger.warning(
                            "embedding request retry",
                            extra={"batch_offset": offset, "batch_size": len(batch), "status_code": status, "attempt": attempt + 1, "elapsed_ms": round((time.monotonic() - started) * 1000), "delay_seconds": delay},
                        )
                        await asyncio.sleep(delay)
                if response is None:
                    raise RuntimeError(f"embedding batch {offset} did not return a response")
                data = response.json().get("data") or []
                batch_vectors = [item.get("embedding") for item in sorted(data, key=lambda item: item.get("index", 0))]
                vectors.extend(validate_embedding_vectors(batch_vectors, len(batch), settings.embedding_dimensions))
        return vectors

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        settings = get_settings()
        if not settings.dashscope_api_key or not settings.embedding_model:
            raise RuntimeError("embedding provider is not configured")
        return await self._embed_batches(texts, api_key=settings.dashscope_api_key, model=settings.embedding_model, settings=settings)

    async def embed_query(self, text: str) -> list[float]:
        vectors = await self.embed_documents([text])
        return vectors[0]


class UserEmbeddingProvider(EmbeddingProvider):
    def __init__(self, session: AsyncSession, user_id):
        self.session = session
        self.user_id = user_id

    async def _config(self) -> EmbeddingConfig | None:
        config = await self.session.scalar(select(EmbeddingConfig).where(EmbeddingConfig.user_id == self.user_id))
        return config

    async def embed_query(self, text: str) -> list[float]:
        # Chat/tool retry budgets are owned by the runtime, never nested here.
        settings = get_settings().model_copy(update={"embedding_max_retries": 0})
        config = await self._config()
        if config:
            from ..security.provider_credentials import decrypt_secret
            key = decrypt_secret(config.api_key_ciphertext, config.api_key_nonce)
            model = config.model_name or settings.embedding_model
        else:
            key, model = settings.dashscope_api_key, settings.embedding_model
        if not key or not model:
            raise RuntimeError("embedding provider is not configured")
        return (await self._embed_batches([text], api_key=key, model=model, settings=settings))[0]

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        config = await self._config()
        settings = get_settings()
        if not config:
            return await super().embed_documents(texts)
        from ..security.provider_credentials import decrypt_secret

        key = decrypt_secret(config.api_key_ciphertext, config.api_key_nonce)
        model = config.model_name or settings.embedding_model
        return await self._embed_batches(texts, api_key=key, model=model, settings=settings)
