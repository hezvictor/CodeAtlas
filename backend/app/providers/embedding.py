import asyncio
import logging
import time

import httpx

from ..config import get_settings

logger = logging.getLogger(__name__)


def validate_embedding_vectors(vectors: list[list[float]], expected_count: int, dimensions: int) -> list[list[float]]:
    if len(vectors) != expected_count:
        raise ValueError(f"embedding count mismatch: expected {expected_count}, got {len(vectors)}")
    if any(len(vector) != dimensions for vector in vectors):
        raise ValueError(f"embedding dimension mismatch: expected {dimensions}")
    return vectors


class EmbeddingProvider:
    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        settings = get_settings()
        if not settings.dashscope_api_key or not settings.embedding_model:
            raise RuntimeError("embedding provider is not configured")
        body = {"model": settings.embedding_model, "input": texts}
        timeout = httpx.Timeout(120, connect=10)
        async with httpx.AsyncClient(timeout=timeout) as client:
            for attempt in range(settings.embedding_max_retries + 1):
                started = time.monotonic()
                try:
                    response = await client.post(
                        settings.dashscope_base_url.rstrip("/") + "/embeddings",
                        headers={"Authorization": f"Bearer {settings.dashscope_api_key}"}, json=body,
                    )
                    response.raise_for_status()
                    break
                except (httpx.TimeoutException, httpx.TransportError, httpx.HTTPStatusError) as error:
                    status = getattr(getattr(error, "response", None), "status_code", None)
                    retryable = status == 429 or (status is not None and status >= 500) or not status
                    if not retryable or attempt >= settings.embedding_max_retries:
                        raise
                    delay = min(settings.embedding_retry_max_delay_seconds, settings.embedding_retry_base_delay_seconds * (2 ** attempt))
                    logger.warning("embedding request retry", extra={"status_code": status, "attempt": attempt + 1, "elapsed_ms": round((time.monotonic() - started) * 1000), "delay_seconds": delay})
                    await asyncio.sleep(delay)
        data = response.json().get("data") or []
        vectors = [item.get("embedding") for item in sorted(data, key=lambda item: item.get("index", 0))]
        return validate_embedding_vectors(vectors, len(texts), settings.embedding_dimensions)

    async def embed_query(self, text: str) -> list[float]:
        vectors = await self.embed_documents([text])
        return vectors[0]
