from __future__ import annotations

from collections.abc import AsyncGenerator
from dataclasses import dataclass
import asyncio
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ModelCandidate:
    name: str


@dataclass(frozen=True, slots=True)
class ProviderTestResult:
    ok: bool
    error: str | None = None


class ChatProvider(Protocol):
    async def list_models(self) -> list[ModelCandidate]: ...

    async def test_model(self, model: str) -> ProviderTestResult: ...

    def stream_chat(
        self, messages: list[dict], model: str, stop_event: asyncio.Event
    ) -> AsyncGenerator[str, None]: ...
