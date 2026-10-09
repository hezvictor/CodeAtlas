"""Message order contracts against the disposable PostgreSQL test schema."""
import asyncio
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app.models import Conversation, Message, User
from app.routers.conversations import messages, retry_message
from app.schemas import RetryRequest


async def conversation_with_pair(factory):
    async with factory() as session:
        user = User(email="message-order@test.invalid", password_hash="test", nickname="test")
        session.add(user)
        await session.flush()
        conversation = Conversation(user_id=user.id, title="order")
        session.add(conversation)
        await session.flush()
        question = Message(conversation_id=conversation.id, role="user", content="old question")
        answer = Message(conversation_id=conversation.id, role="assistant", content="old answer")
        session.add_all([question, answer])
        await session.commit()
        assert question.created_at == answer.created_at
        return user.id, conversation.id, question.id, answer.id


@pytest.mark.asyncio
async def test_retry_latest_assistant_finds_user_with_same_timestamp(db):
    factory, _, _ = db
    uid, cid, _, answer_id = await conversation_with_pair(factory)
    async with factory() as session:
        result = await retry_message(cid, answer_id, RetryRequest(), None, uid=uid, session=session)
        assert result["content"] == "old question"
        assert await session.get(Message, answer_id) is None


@pytest.mark.asyncio
async def test_edit_retry_removes_same_timestamp_answer(db):
    factory, _, _ = db
    uid, cid, question_id, answer_id = await conversation_with_pair(factory)

    class Temporary:
        async def files(self, *_):
            return []

    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(runtime=SimpleNamespace(temporary=Temporary()))))
    async with factory() as session:
        await retry_message(cid, question_id, RetryRequest(content="new question"), request, uid=uid, session=session)
        assert await session.get(Message, answer_id) is None
        assert (await session.get(Message, question_id)).content == "new question"


@pytest.mark.asyncio
async def test_message_pagination_does_not_skip_same_timestamp_pair(db):
    factory, _, _ = db
    uid, cid, question_id, answer_id = await conversation_with_pair(factory)
    async with factory() as session:
        first = await messages(cid, limit=1, before=None, uid=uid, session=session)
        second = await messages(cid, limit=1, before=first.next_before, uid=uid, session=session)
        assert {first.items[0].id, second.items[0].id} == {question_id, answer_id}
        assert second.has_more is False


@pytest.mark.asyncio
async def test_retry_waits_for_admission_lock_before_active_run_check(db, monkeypatch):
    from fastapi import HTTPException

    from app.routers import conversations as routes

    factory, _, _ = db
    uid, cid, _, answer_id = await conversation_with_pair(factory)
    admitted = False

    async def active_after_lock(*_args):
        return object() if admitted else None

    monkeypatch.setattr(routes, "active_run", active_after_lock)
    async with factory() as admission:
        await admission.execute(select(Conversation.id).where(Conversation.id == cid).with_for_update())

        async def attempt_retry():
            async with factory() as retry_session:
                await retry_message(cid, answer_id, RetryRequest(), None, uid=uid, session=retry_session)

        task = asyncio.create_task(attempt_retry())
        await asyncio.sleep(0.1)
        assert not task.done()
        admitted = True
        await admission.commit()
        with pytest.raises(HTTPException) as error:
            await task
        assert error.value.status_code == 409
    async with factory() as session:
        assert await session.get(Message, answer_id) is not None
