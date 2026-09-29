from __future__ import annotations

import asyncio
import json
import secrets
from collections.abc import AsyncGenerator

import httpx

from .chat import ModelCandidate, ModelTurn, ProviderTestResult


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

    async def complete(self, messages: list[dict], model: str, *, tools: list[dict] | None = None,
                       stop_event: asyncio.Event | None = None, max_tokens: int = 4096) -> ModelTurn:
        body = {"model": model, "messages": messages, "stream": False, "max_tokens": max_tokens}
        if tools:
            body["tools"] = tools
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            request = asyncio.create_task(client.post(f"{self.base_url}/chat/completions", headers=self.headers, json=body))
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
        capabilities = dict.fromkeys(("chat", "tool_calling", "tool_result"), "unknown")
        stage = "chat"
        try:
            basic = await self.complete([{"role": "user", "content": "Reply with OK."}], model, max_tokens=128)
            if not basic.message.get("content"):
                raise ValueError("基础聊天未返回文本")
            capabilities[stage] = "verified"
            stage = "tool_calling"
            schema = {"type": "function", "function": {
                "name": "lookup_test_value", "description": "Look up the unknown value for a test key.",
                "parameters": {"type": "object", "properties": {"key": {"type": "string", "enum": ["probe"]}},
                               "required": ["key"], "additionalProperties": False},
            }}
            messages = [{"role": "user", "content": "Use lookup_test_value with key probe to retrieve its unknown value. Do not guess it."}]
            turn = await self.complete(messages, model, tools=[schema], max_tokens=256)
            if len(turn.tool_calls) != 1:
                raise ValueError("未返回一个有效的原生工具调用")
            call = turn.tool_calls[0]
            function = call.get("function") or {}
            if (not call.get("id") or call.get("type") != "function"
                    or function.get("name") != "lookup_test_value"
                    or json.loads(function.get("arguments", "")) != {"key": "probe"}):
                raise ValueError("工具名称、参数或调用 ID 验证未通过")
            capabilities[stage] = "verified"
            stage = "tool_result"
            value = secrets.token_hex(12)
            messages.extend([turn.message, {"role": "tool", "tool_call_id": call["id"],
                                            "content": json.dumps({"value": value})}])
            final = await self.complete(messages, model, max_tokens=256)
            if final.tool_calls or value not in str(final.message.get("content") or ""):
                raise ValueError("工具结果回传验证未通过")
            capabilities[stage] = "verified"
            return ProviderTestResult(True, status="verified", capabilities=capabilities)
        except httpx.HTTPStatusError as error:
            status = error.response.status_code
            try:
                detail = error.response.json().get("error") or {}
            except ValueError:
                detail = {}
            unsupported = (status in {400, 422} and stage == "tool_calling"
                           and detail.get("code") in {"unsupported_parameter", "unsupported_feature"}
                           and detail.get("param") in {"tools", "tool_choice"})
            if unsupported:
                capabilities[stage] = "unsupported"
            return ProviderTestResult(False, f"当前连接验证失败（HTTP {status}）",
                                      "unsupported" if unsupported else "incomplete", capabilities)
        except httpx.HTTPError:
            return ProviderTestResult(False, "连接超时或网络异常，请重试", "incomplete", capabilities)
        except (ValueError, KeyError, TypeError):
            capabilities[stage] = "failed"
            return ProviderTestResult(False, f"{stage} 能力验证未通过", "failed", capabilities)

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
