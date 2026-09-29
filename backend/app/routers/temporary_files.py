import asyncio
from pathlib import PurePosixPath
from urllib.parse import unquote
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select

from ..chat_runtime.infrastructure import resources
from ..chat_runtime.service import active_run
from ..config import get_settings
from ..db import get_session
from ..dependencies import current_user_id
from ..models import Conversation
from ..temporary.parsing import parse_temporary
from .conversations import conversation

router = APIRouter(prefix="/conversations/{cid}/temporary-files", tags=["temporary-files"])


async def allow_changes(session, cid, uid):
    await session.execute(select(Conversation.id).where(Conversation.id == cid, Conversation.user_id == uid).with_for_update())
    run = await active_run(session, cid, uid)
    if run and run.status != "waiting_context":
        raise HTTPException(409, "请先停止当前运行，再修改临时文件")


@router.get("")
async def list_files(cid: UUID, request: Request, uid=Depends(current_user_id), session=Depends(get_session)):
    await conversation(cid, uid, session)
    store = resources(request).temporary
    return [store.public(file) for file in await store.files(uid, cid)]


@router.post("", status_code=201)
async def upload_file(cid: UUID, request: Request, uid=Depends(current_user_id), session=Depends(get_session)):
    await conversation(cid, uid, session)
    await allow_changes(session, cid, uid)
    # Raw body avoids multipart UploadFile spooling onto disk. Filename stays out of URLs/logs.
    filename = unquote(request.headers.get("X-File-Name", ""))
    if not filename or len(filename) > 255 or PurePosixPath(filename.replace("\\", "/")).name != filename:
        raise HTTPException(422, "文件名不合法")
    maximum = get_settings().max_upload_size_bytes
    data = bytearray()
    async for part in request.stream():
        if len(data) + len(part) > maximum: raise HTTPException(413, "临时文件超过上传容量")
        data.extend(part)
    try:
        text = await asyncio.to_thread(parse_temporary, filename, bytes(data))
        return await resources(request).temporary.add(uid, cid, filename, text, PurePosixPath(filename).suffix.lower())
    except ValueError as error:
        messages = {
            "TEMPORARY_UNSUPPORTED_EMBEDDED_CONTENT": "DOCX 包含无法完整提取的图片、公式或嵌入对象，请提供纯文本版本",
            "TEMPORARY_UNSUPPORTED_FORMAT": "此临时文件格式暂不支持，请使用页面允许的文本或 DOCX 格式",
            "TEMPORARY_REQUIRES_UTF8": "文本文件必须使用 UTF-8 编码，请转换后重新上传",
            "TEMPORARY_EMPTY_DOCUMENT": "文件没有可提取正文，请检查内容",
        }
        raise HTTPException(422, {"code": str(error), "message": messages.get(str(error), "临时文件解析或缓存失败，请检查格式与容量")}) from None
    except Exception:
        raise HTTPException(422, "临时文件解析失败") from None


@router.delete("/{file_id}", status_code=204)
async def detach_file(cid: UUID, file_id: UUID, request: Request, uid=Depends(current_user_id), session=Depends(get_session)):
    await conversation(cid, uid, session)
    await allow_changes(session, cid, uid)
    await resources(request).temporary.remove(uid, cid, str(file_id))
