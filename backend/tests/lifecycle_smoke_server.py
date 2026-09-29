"""Disposable browser harness: actual API/PG/Redis, simulated external providers.

Refuses any database except codeatlas_agent_test. Never imported by production.
Run with the same environment as test_agent_integration: uv run python -m tests.lifecycle_smoke_server
"""
import asyncio
import json
import sys
from contextlib import asynccontextmanager
from uuid import uuid4

import uvicorn

from app.auth import hash_password
from app.config import get_settings
from app.db import session_factory
from app.main import app
from app.models import ChatModel, Document, DocumentChunk, DocumentVersion, ModelConnection, User
from app.providers.chat import ModelTurn
from app.providers.openai_compatible import OpenAICompatibleChatProvider
from app.security.provider_credentials import encrypt_secret


class SmokeChatProvider(OpenAICompatibleChatProvider):
    async def complete(self, messages, model, **kwargs):
        await asyncio.sleep(1)
        tools = kwargs.get("tools") or []
        if model == "plain-only" or not tools and messages[-1]["role"] != "tool":
            return ModelTurn({"role": "assistant", "content": "OK"})
        if tools and tools[0]["function"]["name"] == "lookup_test_value":
            name, arguments = "lookup_test_value", '{"key":"probe"}'
        elif tools and not any(m["role"] == "tool" for m in messages):
            name, arguments = "search_knowledge", '{"query":"Graph shortest path"}'
        elif messages[-1]["role"] == "tool":
            result = json.loads(messages[-1]["content"])
            if "value" in result:
                return ModelTurn({"role": "assistant", "content": result["value"]})
            evidence = result.get("evidence") or []
            citation = " [cite:" + evidence[0]["id"] + "]" if evidence else ""
            return ModelTurn({"role": "assistant", "content": "最短路分析：非负权图可使用 Dijkstra。先维护当前最短距离，再逐步松弛相邻边。请先检查权值条件。" + citation})
        else:
            return ModelTurn({"role": "assistant", "content": "请根据权值条件选择最短路算法。"})
        return ModelTurn({"role": "assistant", "content": None, "tool_calls": [
            {"id": "smoke-" + str(uuid4()), "type": "function", "function": {"name": name, "arguments": arguments}}]})


class SmokeEmbedding:
    async def embed_query(self, query): return [0.1] * 1024


original_lifespan = app.router.lifespan_context


@asynccontextmanager
async def lifespan(application):
    if not get_settings().database_url.endswith("/codeatlas_agent_test"):
        raise RuntimeError("Smoke harness refuses non-disposable database")
    import app.chat_runtime.service as service
    import app.routers.model_connections as connections
    service.OpenAICompatibleChatProvider = connections.OpenAICompatibleChatProvider = SmokeChatProvider
    service.UserEmbeddingProvider = lambda *_: SmokeEmbedding()
    tasks = set()
    async def enqueue(resources, run_id):
        task = asyncio.create_task(service.process_chat_run({"chat_runtime": resources}, str(run_id)))
        tasks.add(task)
        task.add_done_callback(tasks.discard)
    service.enqueue = enqueue
    original_search = service.retrieve_for_run
    async def delayed_search(*args, **kwargs):
        await asyncio.sleep(2)
        return await original_search(*args, **kwargs)
    service.retrieve_for_run = delayed_search
    async with original_lifespan(application):
        async with session_factory() as session:
            user = User(id=uuid4(), email="agent-smoke@example.com", password_hash=hash_password("SmokeTest123!"), nickname="测试学习者")
            session.add(user); await session.flush()
            encrypted = encrypt_secret("fake-only")
            connection = ModelConnection(id=uuid4(), user_id=user.id, name="隔离测试连接", base_url="https://test.invalid/v1",
                api_key_ciphertext=encrypted.ciphertext, api_key_nonce=encrypted.nonce, status="active")
            session.add(connection); await session.flush()
            session.add_all([ChatModel(connection_id=connection.id, name=name, source="manual", status="unverified",
                                      capabilities={}, context_window_tokens=256000) for name in ("native-tools", "plain-only")])
            document = Document(id=uuid4(), user_id=user.id, scope="long_term", title="Graph shortest path", filename="graph.txt")
            session.add(document); await session.flush()
            version = DocumentVersion(id=uuid4(), document_id=document.id, version_no=1, original_filename="graph.txt",
                extension=".txt", sha256="0"*64, object_key="smoke-only", status="indexed")
            session.add(version); await session.flush(); document.current_version_id = version.id
            session.add(DocumentChunk(document_version_id=version.id, ordinal=0,
                content="Graph shortest path: Dijkstra requires nonnegative weights. Relax adjacent edges using current distances.",
                content_hash="0"*64, embedding=[0.1]*1024, locator={"section_path": "Shortest paths"}))
            await session.commit()
        try: yield
        finally:
            for task in tasks: task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)


app.router.lifespan_context = lifespan


if __name__ == "__main__":
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=18001))
    with asyncio.Runner(loop_factory=asyncio.SelectorEventLoop if sys.platform == "win32" else asyncio.new_event_loop) as runner:
        runner.run(server.serve())
