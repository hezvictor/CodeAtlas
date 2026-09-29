import json
import time
from uuid import uuid4

from redis.exceptions import WatchError


class TemporaryContextStore:
    def __init__(self, redis, *, clock=time.time, idle_seconds=86400, max_seconds=259200,
                 max_bytes=50 * 1024 * 1024):
        self.redis = redis
        self.clock = clock
        self.idle_seconds = idle_seconds
        self.max_seconds = max_seconds
        self.max_bytes = max_bytes

    @staticmethod
    def key(user_id, conversation_id):
        return f"codeatlas:ephemeral:context:{user_id}:{conversation_id}"

    async def _change(self, user_id, conversation_id, change):
        key = self.key(user_id, conversation_id)
        for _ in range(8):
            async with self.redis.pipeline(transaction=True) as pipe:
                try:
                    await pipe.watch(key)
                    raw = await pipe.get(key)
                    now = self.clock()
                    files = [f for f in json.loads(raw or "[]")
                             if now < f["created_at"] + self.max_seconds
                             and now < f["last_used"] + self.idle_seconds]
                    files, result = change(files, now)
                    data = json.dumps(files, ensure_ascii=False)
                    if len(data.encode()) > self.max_bytes or len(files) > 20:
                        raise ValueError("TEMPORARY_CACHE_CAPACITY_EXCEEDED")
                    pipe.multi()
                    if files:
                        deadline = max(min(f["created_at"] + self.max_seconds,
                                           f["last_used"] + self.idle_seconds) for f in files)
                        pipe.set(key, data, ex=max(1, int(deadline - now)))
                    else:
                        pipe.delete(key)
                    await pipe.execute()
                    return result
                except WatchError:
                    continue
        raise ValueError("TEMPORARY_CONTEXT_BUSY")

    async def add(self, user_id, conversation_id, filename, text, extension):
        def change(files, now):
            item = {"id": str(uuid4()), "filename": filename, "text": text,
                    "extension": extension, "created_at": now, "last_used": now}
            return files + [item], self.public(item)
        return await self._change(user_id, conversation_id, change)

    async def files(self, user_id, conversation_id):
        def change(files, now):
            for item in files:
                item["last_used"] = now
            return files, files
        return await self._change(user_id, conversation_id, change)

    async def remove(self, user_id, conversation_id, file_id):
        return await self._change(user_id, conversation_id,
                                  lambda files, now: ([f for f in files if f["id"] != file_id], None))

    async def clear(self, user_id, conversation_id):
        await self.redis.delete(self.key(user_id, conversation_id))

    @staticmethod
    def public(item):
        return {"id": item["id"], "original_filename": item["filename"],
                "extension": item["extension"], "status": "ready", "characters": len(item["text"])}
