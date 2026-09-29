"""Run only against infra/compose.agent-test.yml, never an existing user database."""
import asyncio
import json
import os
import sys
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import get_settings
from app.db import get_session, session_factory
from app.models import (
    ChatModel,
    ChatRun,
    Citation,
    Conversation,
    Document,
    DocumentChunk,
    DocumentVersion,
    Message,
    ModelConnection,
    User,
)
from app.providers.chat import ModelTurn
from app.schemas import ChatRequest


@pytest.fixture(scope="module")
def event_loop_policy():
    if sys.platform == "win32": return asyncio.WindowsSelectorEventLoopPolicy()
    return asyncio.DefaultEventLoopPolicy()


@pytest.fixture
async def runtime(monkeypatch):
    if os.getenv("RUN_AGENT_INTEGRATION") != "1": pytest.skip("requires disposable agent test services")
    if not get_settings().database_url.endswith("/codeatlas_agent_test"):
        pytest.fail("Refusing integration writes outside codeatlas_agent_test")
    import app.chat_runtime.service as service
    from app.chat_runtime.infrastructure import RuntimeResources
    from app.dependencies import current_user_id
    from app.main import app
    from app.security.provider_credentials import encrypt_secret
    engine = create_async_engine(get_settings().database_url, poolclass=NullPool)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(service, "session_factory", factory)
    monkeypatch.setattr(sys.modules[__name__], "session_factory", factory)
    resources = await RuntimeResources().open()
    app.state.runtime = resources
    users, conversations, models = [], [], []
    async with session_factory() as session:
        for _ in range(2):
            user = User(id=uuid4(), email=f"{uuid4()}@test.invalid", password_hash="test", nickname="test")
            session.add(user)
            await session.flush()
            key = encrypt_secret("fake-only")
            connection = ModelConnection(id=uuid4(), user_id=user.id, name="test", base_url="http://invalid.test/v1",
                         api_key_ciphertext=key.ciphertext, api_key_nonce=key.nonce, status="active")
            session.add(connection)
            await session.flush()
            model = ChatModel(id=uuid4(), connection_id=connection.id, name="fake", status="verified", capabilities={
                    "chat": "verified", "tool_calling": "verified", "tool_result": "verified"}, context_window_tokens=256000)
            conversation = Conversation(id=uuid4(), user_id=user.id, title="test", selected_chat_model_id=model.id)
            session.add_all([model, conversation])
            users.append(user.id); conversations.append(conversation.id); models.append(model.id)
        await session.commit()
    async def no_enqueue(*args): pass
    monkeypatch.setattr(service, "enqueue", no_enqueue)
    app.dependency_overrides[current_user_id] = lambda: users[0]
    async def api_session():
        async with session_factory() as session: yield session
    app.dependency_overrides[get_session] = api_session
    fixture = SimpleNamespace(resources=resources, users=users, conversations=conversations, models=models,
                              service=service, app=app)
    try: yield fixture
    finally:
        app.dependency_overrides.clear()
        async with session_factory() as session:
            runs = (await session.scalars(select(ChatRun.id).where(ChatRun.user_id.in_(users)))).all()
            for run_id in runs:
                await resources.checkpointer.adelete_thread(str(run_id))
                await resources.cache.clear(run_id)
            for uid, cid in zip(users, conversations, strict=True): await resources.temporary.clear(uid, cid)
            await session.execute(delete(User).where(User.id.in_(users)))
            await session.commit()
        await resources.close()
        await engine.dispose()


async def new_run(fixture, *, content="Explain shortest paths", mode="normal"):
    async with session_factory() as session:
        return await fixture.service.start_run(fixture.resources, session, fixture.conversations[0], fixture.users[0],
                   ChatRequest(content=content, chat_model_id=fixture.models[0], mode=mode))


async def execute(fixture, run):
    await fixture.service.process_chat_run({"chat_runtime": fixture.resources}, str(run.id))
    async with session_factory() as session:
        saved = await session.get(ChatRun, run.id)
        message = await session.get(Message, saved.message_id)
        return saved, message


@pytest.mark.asyncio
async def test_real_checkpoint_tool_loop_user_isolation_and_citation(runtime, monkeypatch):
    f = runtime
    chunks = []
    async with session_factory() as session:
        for uid, scope, content in [(f.users[0], "long_term", "Graph shortest path own evidence"),
                                     (f.users[1], "long_term", "OTHER_USER_SECRET"),
                                     (f.users[0], "session", "LEGACY_SESSION_SECRET")]:
            doc = Document(id=uuid4(), user_id=uid, scope=scope, title="Graph", filename="graph.txt")
            session.add(doc); await session.flush()
            version = DocumentVersion(id=uuid4(), document_id=doc.id, version_no=1, original_filename="graph.txt",
                      extension=".txt", sha256="0"*64, object_key="test-only", status="indexed")
            session.add(version); await session.flush(); doc.current_version_id = version.id
            chunk = DocumentChunk(id=uuid4(), document_version_id=version.id, ordinal=0, content=content,
                    content_hash="0"*64, embedding=[0.01]*1024, locator={"section_path": "Graph"})
            session.add(chunk); chunks.append(chunk.id)
        await session.commit()
    class Embedding:
        async def embed_query(self, query): return [0.01]*1024
    monkeypatch.setattr(f.service, "UserEmbeddingProvider", lambda *_: Embedding())
    inputs = []
    class Provider:
        def __init__(self, *_): pass
        async def complete(self, messages, model, **kwargs):
            inputs.append(json.dumps(messages))
            if not any(m["role"] == "tool" for m in messages):
                return ModelTurn({"role": "assistant", "content": None, "tool_calls": [{"id": "call1", "type": "function",
                    "function": {"name": "search_knowledge", "arguments": '{"query":"Graph"}'}}]}, {})
            return ModelTurn({"role": "assistant", "content": f"Use the graph algorithm [cite:{chunks[0]}]"}, {})
    monkeypatch.setattr(f.service, "OpenAICompatibleChatProvider", Provider)
    run = await new_run(f)
    saved, message = await execute(f, run)
    assert saved.status == "completed", saved.error_code
    assert saved.model_calls == 2 and saved.tool_calls == 1
    assert "OTHER_USER_SECRET" not in "".join(inputs) and "LEGACY_SESSION_SECRET" not in "".join(inputs)
    async with session_factory() as session:
        assert await session.scalar(select(func.count()).select_from(Citation).where(Citation.message_id == message.id)) == 1
        assert "messages" not in json.dumps((await f.resources.checkpointer.aget_tuple({"configurable": {"thread_id": str(run.id)}})).checkpoint)
    events = await f.resources.cache.events(run.id, 0)
    assert any(e["name"] == "tool.started" for e in events)
    assert not any("arguments" in e["data"] for e in events)


@pytest.mark.asyncio
async def test_temporary_upload_never_enters_document_pipeline_and_is_owned(runtime):
    f = runtime
    async with session_factory() as session:
        count = await session.scalar(select(func.count()).select_from(Document).where(Document.user_id == f.users[0]))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=f.app), base_url="http://test") as client:
        response = await client.post(f"/api/v1/conversations/{f.conversations[0]}/temporary-files", content=b"FULL TEXT\n    indentation", headers={"X-File-Name": "private.txt"})
        assert response.status_code == 201, response.text
        assert "text" not in response.json()
        forbidden = await client.get(f"/api/v1/conversations/{f.conversations[1]}/temporary-files")
        assert forbidden.status_code == 404
        assert (await client.get(f"/api/v1/conversations/{f.conversations[0]}/attachments")).status_code == 404
    async with session_factory() as session:
        assert await session.scalar(select(func.count()).select_from(Document).where(Document.user_id == f.users[0])) == count
    assert (await f.resources.temporary.files(f.users[0], f.conversations[0]))[0]["text"].endswith("    indentation")


@pytest.mark.asyncio
async def test_temporary_output_is_blocked_before_message_or_checkpoint_persistence(runtime, monkeypatch):
    f = runtime
    private = "TOP_PRIVATE_CONTENT"*100
    await f.resources.temporary.add(f.users[0], f.conversations[0], "private.txt", private, ".txt")
    class Provider:
        def __init__(self, *_): pass
        async def complete(self, messages, model, **kwargs): return ModelTurn({"role": "assistant", "content": private}, {})
    monkeypatch.setattr(f.service, "OpenAICompatibleChatProvider", Provider)
    run = await new_run(f)
    saved, message = await execute(f, run)
    assert saved.status == "failed" and saved.error_code == "TEMPORARY_CONTENT_PERSISTENCE"
    assert message.content == ""
    checkpoint = await f.resources.checkpointer.aget_tuple({"configurable": {"thread_id": str(run.id)}})
    assert private not in repr(checkpoint)


@pytest.mark.asyncio
async def test_cache_loss_waits_and_reupload_resumes_same_run_with_budget(runtime, monkeypatch):
    f = runtime
    await f.resources.temporary.add(f.users[0], f.conversations[0], "private.txt", "private source "*100, ".txt")
    run = await new_run(f)
    await f.resources.temporary.clear(f.users[0], f.conversations[0])
    saved, _ = await execute(f, run)
    assert saved.status == "waiting_context"
    await f.resources.temporary.add(f.users[0], f.conversations[0], "new.txt", "new source "*100, ".txt")
    class Provider:
        def __init__(self, *_): pass
        async def complete(self, messages, model, **kwargs): return ModelTurn({"role": "assistant", "content": "Learning conclusion."}, {})
    monkeypatch.setattr(f.service, "OpenAICompatibleChatProvider", Provider)
    async with session_factory() as session:
        result = await f.service.resume_run(f.resources, session, f.conversations[0], f.users[0])
    assert result["run_id"] == str(run.id)
    saved, message = await execute(f, run)
    assert saved.status == "completed" and message.content == "Learning conclusion."


@pytest.mark.asyncio
async def test_stop_is_durable_and_cancels_request_without_saving_partial_text(runtime, monkeypatch):
    f = runtime
    started = asyncio.Event()
    class Provider:
        def __init__(self, *_): pass
        async def complete(self, messages, model, *, stop_event, **kwargs):
            started.set(); await stop_event.wait(); raise asyncio.CancelledError
    monkeypatch.setattr(f.service, "OpenAICompatibleChatProvider", Provider)
    run = await new_run(f)
    task = asyncio.create_task(execute(f, run))
    await asyncio.wait_for(started.wait(), 10)
    async with session_factory() as session:
        await f.service.stop_run(f.resources, session, f.conversations[0], f.users[0])
    saved, message = await asyncio.wait_for(task, 5)
    assert saved.status == "cancelled" and message.content == ""


@pytest.mark.asyncio
async def test_failed_initial_retrieval_continues_with_visible_warning(runtime, monkeypatch):
    f = runtime
    async def fail(*args, **kwargs): raise ConnectionError("do not log raw context")
    monkeypatch.setattr(f.service, "retrieve_chunks", fail)
    class Provider:
        def __init__(self, *_): pass
        async def complete(self, messages, model, **kwargs):
            assert "检索失败" in messages[0]["content"]
            return ModelTurn({"role": "assistant", "content": "知识库暂不可用，以下基于题意分析。"}, {})
    monkeypatch.setattr(f.service, "OpenAICompatibleChatProvider", Provider)
    run = await new_run(f)
    saved, _ = await execute(f, run)
    assert saved.status == "completed"
    assert any(e["name"] == "retrieval.completed" and e["data"]["status"] == "failed" for e in await f.resources.cache.events(run.id, 0))


@pytest.mark.asyncio
async def test_edit_retry_cannot_persist_temporary_full_text(runtime):
    f = runtime
    private = "PRIVATE_INPUT_CONTENT" * 100
    await f.resources.temporary.add(f.users[0], f.conversations[0], "private.txt", private, ".txt")
    async with session_factory() as session:
        message = Message(id=uuid4(), conversation_id=f.conversations[0], role="user", content="original question", status="completed")
        session.add(message); await session.commit()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=f.app), base_url="http://test") as client:
        response = await client.post(f"/api/v1/conversations/{f.conversations[0]}/messages/{message.id}/retry", json={"content": private})
        assert response.status_code == 409
    async with session_factory() as session:
        assert (await session.get(Message, message.id)).content == "original question"


@pytest.mark.asyncio
async def test_worker_shutdown_restores_checkpoint_with_spent_budgets(runtime, monkeypatch):
    f = runtime
    started = asyncio.Event()
    original = f.service.retrieve_for_run
    calls = 0
    async def blocked(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1: return await original(*args, **kwargs)
        started.set()
        await asyncio.Event().wait()
    monkeypatch.setattr(f.service, "retrieve_for_run", blocked)
    class Provider:
        def __init__(self, *_): pass
        async def complete(self, messages, model, **kwargs):
            if not any(m["role"] == "tool" for m in messages):
                return ModelTurn({"role": "assistant", "content": None, "tool_calls": [{"id": "recover", "type": "function",
                    "function": {"name": "search_knowledge", "arguments": '{"query":"Graph"}'}}]})
            return ModelTurn({"role": "assistant", "content": "Recovered learning answer"})
    monkeypatch.setattr(f.service, "OpenAICompatibleChatProvider", Provider)
    run = await new_run(f)
    task = asyncio.create_task(execute(f, run))
    await asyncio.wait_for(started.wait(), 10)
    task.cancel()
    with pytest.raises(asyncio.CancelledError): await task
    async with session_factory() as session:
        saved = await session.get(ChatRun, run.id)
        assert saved.model_calls == 1 and saved.tool_calls == 1
        saved.locked_at = datetime.now(UTC) - timedelta(seconds=30)
        await session.commit()
    monkeypatch.setattr(f.service, "retrieve_for_run", original)
    await f.service.dispatch_chat_runs({"chat_runtime": f.resources})
    saved, message = await execute(f, run)
    assert saved.status == "completed", saved.error_code
    assert saved.model_calls == 2 and saved.tool_calls == 2 and saved.tool_rounds == 2
    assert message.content == "Recovered learning answer"


@pytest.mark.asyncio
async def test_deleted_run_orphan_control_checkpoint_is_cleaned(runtime):
    from app.agent.graph import build_graph
    f = runtime
    run = await new_run(f)
    config = {"configurable": {"thread_id": str(run.id)}}
    async with session_factory() as session:
        await session.execute(delete(ChatRun).where(ChatRun.id == run.id))
        await session.commit()
    # Simulate an old graph writing its final control checkpoint after conversation deletion.
    await build_graph(f.resources.checkpointer).aupdate_state(config, {"done": True}, as_node="model")
    assert await f.resources.checkpointer.aget_tuple(config) is not None
    await f.service.cleanup_chat_runs({"chat_runtime": f.resources})
    assert await f.resources.checkpointer.aget_tuple(config) is None


@pytest.mark.asyncio
async def test_temporary_changes_serialize_with_chat_admission(runtime):
    f = runtime
    async with session_factory() as locked:
        await locked.execute(select(Conversation.id).where(Conversation.id == f.conversations[0]).with_for_update())
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=f.app), base_url="http://test") as client:
            task = asyncio.create_task(client.post(f"/api/v1/conversations/{f.conversations[0]}/temporary-files",
                content=b"temporary text", headers={"X-File-Name": "race.txt"}))
            try:
                with pytest.raises(TimeoutError): await asyncio.wait_for(asyncio.shield(task), 0.5)
            finally:
                await locked.rollback()
                response = await asyncio.wait_for(task, 5)
    assert response.status_code == 201
