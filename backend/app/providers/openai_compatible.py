from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncGenerator

import httpx

from .chat import ModelCandidate, ProviderTestResult


class OpenAICompatibleChatProvider:
    def __init__(self, base_url: str, api_key: str, timeout_seconds: float = 120):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = httpx.Timeout(timeout_seconds, connect=10)

    @property
    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    async def list_models(self) -> list[ModelCandidate]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{self.base_url}/models", headers=self.headers)
            response.raise_for_status()
            items = response.json().get("data") or []
        return [ModelCandidate(str(item["id"])) for item in items if item.get("id")]

    async def test_model(self, model: str) -> ProviderTestResult:
        body = {
            "model": model,
            "messages": [{"role": "user", "content": "Reply with OK."}],
            "stream": False,
            "max_tokens": 1,
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions", headers=self.headers, json=body
                )
                response.raise_for_status()
                data = response.json()
                if not data.get("choices"):
                    return ProviderTestResult(False, "provider returned no choices")
                return ProviderTestResult(True)
        except (httpx.HTTPError, ValueError, KeyError) as error:
            return ProviderTestResult(False, str(error))

    async def stream_chat(
        self, messages: list[dict], model: str, stop_event: asyncio.Event
    ) -> AsyncGenerator[str, None]:
        body = {"model": model, "messages": messages, "stream": True}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream(
                "POST", f"{self.base_url}/chat/completions", headers=self.headers, json=body
            ) as response:
                response.raise_for_status()
                lines = response.aiter_lines().__aiter__()
                while not stop_event.is_set():
                    next_line = asyncio.create_task(lines.__anext__())
                    stopped = asyncio.create_task(stop_event.wait())
                    done, pending = await asyncio.wait(
                        {next_line, stopped}, return_when=asyncio.FIRST_COMPLETED
                    )
                    for task in pending:
                        task.cancel()
                    if stopped in done:
                        break
                    try:
                        line = next_line.result()
                    except StopAsyncIteration:
                        break
                    if not line.startswith("data: ") or line[6:] == "[DONE]":
                        continue
                    choices = (json.loads(line[6:]).get("choices") or [])
                    if not choices:
                        continue
                    delta = (choices[0].get("delta") or {}).get("content") or ""
                    if isinstance(delta, list):
                        delta = "".join(
                            part.get("text", "") if isinstance(part, dict) else str(part)
                            for part in delta
                        )
                    if delta:
                        yield str(delta)
