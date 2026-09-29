from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ModelCandidate:
    name: str


@dataclass(frozen=True, slots=True)
class ProviderTestResult:
    ok: bool
    error: str | None = None
    status: str = "unverified"
    capabilities: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ModelTurn:
    message: dict
    usage: dict = field(default_factory=dict)

    @property
    def tool_calls(self) -> list[dict]:
        return self.message.get("tool_calls") or []


class ChatProvider(Protocol):
    async def list_models(self) -> list[ModelCandidate]: ...

    async def test_model(self, model: str) -> ProviderTestResult: ...

    async def complete(self, messages: list[dict], model: str, *, tools: list[dict] | None = None,
                       stop_event: asyncio.Event | None = None, max_tokens: int = 4096) -> ModelTurn: ...

    def stream_chat(
        self, messages: list[dict], model: str, stop_event: asyncio.Event
    ) -> AsyncGenerator[str, None]: ...
