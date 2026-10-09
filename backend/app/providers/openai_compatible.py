from __future__ import annotations

import asyncio

import httpx

from .chat import ModelCandidate, ModelTurn, ProviderTestResult
from .url_validation import pin_provider_base_url


class OpenAICompatibleChatProvider:
    def __init__(self, base_url: str, api_key: str, timeout_seconds: float = 120):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = httpx.Timeout(timeout_seconds, connect=10)

    @property
    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    async def list_models(self) -> list[ModelCandidate]:
        base_url, host, extensions = pin_provider_base_url(self.base_url)
        async with httpx.AsyncClient(timeout=self.timeout, trust_env=False) as client:
            response = await client.get(f"{base_url}/models", headers={**self.headers, **host}, extensions=extensions)
            response.raise_for_status()
            items = response.json().get("data") or []
        return [ModelCandidate(str(item["id"])) for item in items if item.get("id")]

    async def complete(self, messages: list[dict], model: str, *, tools: list[dict] | None = None,
                       stop_event: asyncio.Event | None = None, max_tokens: int = 4096) -> ModelTurn:
        body = {"model": model, "messages": messages, "stream": False, "max_tokens": max_tokens}
        if tools:
            body["tools"] = tools
        base_url, host, extensions = pin_provider_base_url(self.base_url)
        async with httpx.AsyncClient(timeout=self.timeout, trust_env=False) as client:
            request = asyncio.create_task(client.post(f"{base_url}/chat/completions", headers={**self.headers, **host},
                                                      extensions=extensions, json=body))
            stopped = asyncio.create_task(stop_event.wait()) if stop_event else None
            try:
                if stopped:
                    done, _ = await asyncio.wait({request, stopped}, return_when=asyncio.FIRST_COMPLETED)
                    if stopped in done:
                        raise asyncio.CancelledError
                response = await request
                response.raise_for_status()
                data = response.json()
                choices = data.get("choices") or []
                if not choices or not isinstance(choices[0].get("message"), dict):
                    raise ValueError("provider returned no valid message")
                message = dict(choices[0]["message"])
                if message.get("role", "assistant") != "assistant":
                    raise ValueError("MODEL_TOOL_PROTOCOL_ERROR")
                message["role"] = "assistant"
                content = message.get("content")
                if isinstance(content, list):
                    if any(not isinstance(part, dict) or not isinstance(part.get("text"), str) for part in content):
                        raise ValueError("MODEL_TOOL_PROTOCOL_ERROR")
                    content = "".join(part["text"] for part in content)
                    message["content"] = content
                if content is not None and not isinstance(content, str):
                    raise ValueError("MODEL_TOOL_PROTOCOL_ERROR")
                calls = message.get("tool_calls") or []
                if not isinstance(calls, list): raise ValueError("MODEL_TOOL_PROTOCOL_ERROR")
                identifiers = set()
                for call in calls:
                    if not isinstance(call, dict): raise ValueError("MODEL_TOOL_PROTOCOL_ERROR")
                    function = call.get("function")
                    identifier = call.get("id")
                    if (not isinstance(identifier, str) or not identifier or identifier in identifiers
                            or call.get("type") != "function" or not isinstance(function, dict)
                            or not isinstance(function.get("name"), str) or not isinstance(function.get("arguments"), str)):
                        raise ValueError("MODEL_TOOL_PROTOCOL_ERROR")
                    identifiers.add(identifier)
                if not calls and not (content or "").strip(): raise ValueError("MODEL_TOOL_PROTOCOL_ERROR")
                return ModelTurn(message, data.get("usage") or {})
            finally:
                for task in (request, stopped):
                    if task and not task.done():
                        task.cancel()
                await asyncio.gather(*(t for t in (request, stopped) if t), return_exceptions=True)

    async def test_model(self, model: str) -> ProviderTestResult:
        capabilities = {"chat": "unknown"}
        try:
            basic = await self.complete([{"role": "user", "content": "Reply with OK."}], model, max_tokens=128)
            if not basic.message.get("content"):
                raise ValueError("基础聊天未返回文本")
            capabilities["chat"] = "verified"
            return ProviderTestResult(True, status="verified", capabilities=capabilities)
        except httpx.HTTPStatusError as error:
            status = error.response.status_code
            transient = status in {408, 429} or status >= 500
            if not transient:
                capabilities["chat"] = "failed"
            return ProviderTestResult(False, f"当前连接验证失败（HTTP {status}）",
                                      "incomplete" if transient else "failed", capabilities)
        except httpx.HTTPError:
            return ProviderTestResult(False, "连接超时或网络异常，请重试", "incomplete", capabilities)
        except (ValueError, KeyError, TypeError):
            capabilities["chat"] = "failed"
            return ProviderTestResult(False, "聊天连接验证未通过", "failed", capabilities)
