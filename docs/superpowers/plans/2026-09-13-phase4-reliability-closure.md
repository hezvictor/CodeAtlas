# Phase 4 Reliability Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the existing CodeAtlas Phase 4 workflow by fixing authentication revocation, private retrieval scope, conversation context isolation, attachments, document lifecycle, model-call reliability, deployment configuration, and verification without adding future features.

**Architecture:** Keep FastAPI, SQLAlchemy/Alembic, PostgreSQL/pgvector, Redis/Arq, MinIO, and Next.js. Add durable user authentication versions, conversation-scoped retrieval filters, idempotent storage cleanup metadata, bounded provider retries and budgets, and Redis-backed conversation run leases. Reuse the existing document and attachment APIs while adding only the missing version and UI operations.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy 2 async, Alembic, PostgreSQL/pgvector, Redis 7, Arq, MinIO/S3, httpx, PyJWT, Argon2, Next.js 15, React 19, TypeScript.

**Spec:** `docs/superpowers/specs/2026-09-13-phase4-reliability-closure-design.md`

## Global Constraints

- An empty knowledge-group selection and an empty attachment selection mean that retrieval is skipped completely.
- Retrieval must be limited to the authenticated user, and attachment retrieval must also be limited to the active conversation.
- Document deletion hides the document immediately and schedules object cleanup; cleanup failures are recorded and retried.
- Avatar replacement activates the new object before deleting the old object.
- Existing uncommitted Phase 4 work is preserved; unrelated refactors are excluded.
- `resume` continues to mean generating from persisted messages, not checkpoint restoration.
- Existing SSE event names and response contracts remain compatible unless a new field is additive.
- Online compilation, OJ evaluation, OCR, URL fetching, rerank, image understanding, table-specific parsing, and checkpoint persistence remain out of scope.

---

### Task 1: Add Durable Security and Storage State

**Files:**
- Modify: `backend/app/models.py`
- Create: `backend/migrations/versions/0008_phase4_reliability_closure.py`
- Test: `backend/tests/test_phase4_migration.py`

**Interfaces:**
- `User.auth_version: int` defaults to `1` for new rows.
- `DocumentVersion.storage_deleted_at: datetime | None`, `storage_delete_attempts: int`, and `storage_delete_error: str | None`.
- Migration revision `0008_phase4_reliability_closure` depends on `0007_problem_acm_workflow`.

- [ ] **Step 1: Write failing model and migration tests**

```python
def test_user_has_auth_version_default():
    from app.models import User
    user = User(email="a@example.com", password_hash="hash", nickname="A")
    assert user.auth_version == 1


def test_document_version_has_storage_cleanup_state():
    from app.models import DocumentVersion
    version = DocumentVersion(document_id=uuid.uuid4(), version_no=1, status="uploaded")
    assert version.storage_delete_attempts == 0
    assert version.storage_deleted_at is None


def test_migration_adds_phase4_columns():
    source = Path(__file__).parents[1].joinpath("migrations/versions/0008_phase4_reliability_closure.py").read_text()
    assert "auth_version" in source
    assert "storage_deleted_at" in source
    assert "storage_delete_attempts" in source
```

- [ ] **Step 2: Run the focused tests and verify they fail**

Run: `pytest backend/tests/test_phase4_migration.py -q`

Expected: FAIL because the model fields and migration do not exist.

- [ ] **Step 3: Add the SQLAlchemy fields and Alembic migration**

Set `User.auth_version` to a non-null integer with a server default of `1`. Add the three cleanup columns to `document_versions`, initialize existing rows to zero attempts, and remove the server defaults in the migration when the backfill is complete. Include a downgrade that drops only these new columns.

- [ ] **Step 4: Run the focused tests and verify they pass**

Run: `pytest backend/tests/test_phase4_migration.py -q`

Expected: PASS.

- [ ] **Step 5: Commit the isolated schema change**

```powershell
git add backend/app/models.py backend/migrations/versions/0008_phase4_reliability_closure.py backend/tests/test_phase4_migration.py
git commit -m "feat: add Phase 4 security and cleanup state"
```

### Task 2: Implement Immediate Access-Token Revocation

**Files:**
- Modify: `backend/app/auth.py`
- Modify: `backend/app/dependencies.py`
- Modify: `backend/app/routers/auth.py`
- Modify: `backend/app/routers/users.py`
- Modify: `backend/app/config.py`
- Test: `backend/tests/test_auth_security.py`

**Interfaces:**
- `create_access_token(user_id: UUID, auth_version: int) -> str` writes `sub`, `type="access"`, `auth_version`, `jti`, `iat`, and `exp`.
- `current_user_id(credentials, session) -> UUID` verifies the token and the current `User.auth_version`.
- `Settings.refresh_token_retention_days` controls cleanup retention and defaults to `refresh_token_expire_days`.

- [ ] **Step 1: Write failing token-version and logout tests**

```python
@pytest.mark.asyncio
async def test_old_access_token_is_rejected_after_auth_version_changes(monkeypatch):
    user = User(id=uuid.uuid4(), email="a@example.com", password_hash="hash", nickname="A", auth_version=1)
    token = create_access_token(user.id, user.auth_version)
    user.auth_version = 2
    session = FakeSession(user)
    with pytest.raises(HTTPException) as error:
        await current_user_id(credentials_for(token), session=session)
    assert error.value.status_code == 401


def test_access_token_contains_jti_and_auth_version():
    token = create_access_token(uuid.uuid4(), 3)
    claims = jwt.decode(token, get_settings().jwt_secret_key, algorithms=["HS256"])
    assert claims["auth_version"] == 3
    assert claims["jti"]
```

- [ ] **Step 2: Run the focused tests and verify they fail**

Run: `pytest backend/tests/test_auth_security.py -q`

Expected: FAIL because access-token claims and database version checks are absent.

- [ ] **Step 3: Implement version-aware token issuance and validation**

Pass `user.auth_version` from registration, login, and refresh into `token_response`. Make `current_user_id` depend on `get_session`, reject missing or mismatched versions, and preserve the existing generic 401 response. Use a UUID `jti` generated for every access token.

- [ ] **Step 4: Revoke versions and refresh records on logout/password change**

On a valid logout refresh token, revoke that token, increment `User.auth_version`, and revoke all active refresh tokens for the user in one transaction. On password change, increment the version and revoke all active refresh tokens. Add a bounded cleanup function that deletes refresh-token rows older than the configured retention period and call it from an existing worker cron hook.

- [ ] **Step 5: Run all authentication tests**

Run: `pytest backend/tests/test_auth_security.py backend/tests/test_users_api.py -q`

Expected: PASS, including refresh rotation and immediate invalidation after logout/password change.

- [ ] **Step 6: Commit the authentication change**

```powershell
git add backend/app/auth.py backend/app/dependencies.py backend/app/routers/auth.py backend/app/routers/users.py backend/app/config.py backend/tests/test_auth_security.py
git commit -m "feat: revoke access tokens on logout and password change"
```

### Task 3: Enforce Conversation-Scoped Retrieval

**Files:**
- Modify: `backend/app/services/retrieval_service.py`
- Modify: `backend/app/routers/conversations.py`
- Test: `backend/tests/test_retrieval_scope.py`
- Modify: `backend/tests/test_conversations_runtime.py`

**Interfaces:**
- `retrieve_chunks(session, user_id, conversation_id, query, group_ids=None, attachment_ids=None, limit=10, embedding_provider=None) -> list[RankedChunk]`.
- Empty `group_ids` and `attachment_ids` return `[]` before any SQL statement or provider call.

- [ ] **Step 1: Write failing scope tests**

```python
@pytest.mark.asyncio
async def test_empty_scope_skips_database_and_embedding():
    provider = ExplodingProvider()
    session = ExplodingSession()
    assert await retrieve_chunks(session, uuid.uuid4(), uuid.uuid4(), "query", embedding_provider=provider) == []


def test_attachment_query_contains_conversation_filter():
    statement = build_attachment_statement(uuid.uuid4(), uuid.uuid4(), [uuid.uuid4()])
    assert "conversation_id" in str(statement)
```

- [ ] **Step 2: Run the focused tests and verify they fail**

Run: `pytest backend/tests/test_retrieval_scope.py -q`

Expected: FAIL because the function has no conversation parameter and performs unrestricted retrieval.

- [ ] **Step 3: Add the early-return and ownership filters**

Normalize and deduplicate UUID lists. Return immediately when both lists are empty. Require `Document.user_id`, `deleted_at IS NULL`, and indexed versions. For attachments join `Attachment` and require matching `user_id` and `conversation_id`; keep the document ownership and indexed-status predicates.

- [ ] **Step 4: Pass the active conversation id from the chat route**

Call `retrieve_chunks(session, uid, cid, payload.content, payload.knowledge_group_ids, payload.attachment_ids)`. Preserve the existing `retrieval_requested` behavior so scoped retrieval failures terminate the run and emit `retrieval.failed`/`run.failed` without invoking the model.

- [ ] **Step 5: Run RAG and conversation tests**

Run: `pytest backend/tests/test_retrieval_scope.py backend/tests/test_retrieval_and_citations.py backend/tests/test_chat_rag.py backend/tests/test_conversations_runtime.py -q`

Expected: PASS, including no-scope skip, cross-conversation rejection, and scoped failure behavior.

- [ ] **Step 6: Commit the retrieval boundary**

```powershell
git add backend/app/services/retrieval_service.py backend/app/routers/conversations.py backend/tests/test_retrieval_scope.py backend/tests/test_conversations_runtime.py
git commit -m "fix: scope RAG retrieval to selected knowledge and conversation"
```

### Task 4: Add Versioned Document Upload and Cleanup Retry

**Files:**
- Modify: `backend/app/routers/knowledge_documents.py`
- Modify: `backend/app/tasks/document_tasks.py`
- Modify: `backend/app/queue.py`
- Modify: `backend/app/worker.py`
- Modify: `backend/app/storage/s3.py`
- Modify: `backend/app/schemas.py`
- Create: `backend/tests/test_document_lifecycle.py`

**Interfaces:**
- `POST /knowledge/documents/{document_id}/versions` creates the next immutable `DocumentVersion` for an existing document and queues indexing.
- `GET /knowledge/documents/{document_id}/versions` returns versions ordered by descending `version_no`.
- Worker function `cleanup_deleted_document_objects(_ctx=None) -> int` deletes objects for soft-deleted documents and returns the number successfully cleaned.
- `S3Storage.delete(key)` remains idempotent for missing objects.

- [ ] **Step 1: Write failing lifecycle tests**

```python
@pytest.mark.asyncio
async def test_reupload_existing_document_increments_version(monkeypatch):
    response = await upload_document_version(existing_document_id, upload, user_id, session)
    assert response.version_no == 2
    assert response.document_id == existing_document_id


@pytest.mark.asyncio
async def test_deleted_document_objects_are_retried(monkeypatch):
    deleted = await cleanup_deleted_document_objects(None)
    assert deleted == 1
    assert version.storage_deleted_at is not None
    assert version.storage_delete_attempts == 1
```

- [ ] **Step 2: Run focused tests and verify they fail**

Run: `pytest backend/tests/test_document_lifecycle.py -q`

Expected: FAIL because version upload, version listing, and cleanup worker are absent.

- [ ] **Step 3: Implement existing-document version endpoints**

Reuse `_validate_upload`, `object_key_for`, and the existing `DocumentJob` queue. Lock the document while calculating the next version, store the new object before committing the database transaction, set `current_version_id`, and return the new version. Reject uploads to deleted or foreign documents with 404.

- [ ] **Step 4: Implement cleanup metadata and idempotent worker cleanup**

On document deletion, keep the soft-delete update as the user-visible operation. Add a Worker cron function that selects versions of deleted documents whose cleanup timestamp is null, increments attempts, calls `S3Storage.delete`, records success or the truncated error, and applies bounded retry backoff through the existing task scheduler. Treat a missing-object client error as success.

- [ ] **Step 5: Add version schemas and status behavior**

Expose `storage_deleted_at` only where needed for operational status; keep user-facing document responses backward compatible. Ensure retry/reindex clears processing errors and never creates duplicate active jobs.

- [ ] **Step 6: Run document and worker tests**

Run: `pytest backend/tests/test_knowledge_documents.py backend/tests/test_document_jobs.py backend/tests/test_document_lifecycle.py backend/tests/test_s3_storage.py -q`

Expected: PASS, including version increments and cleanup retry behavior.

- [ ] **Step 7: Commit document lifecycle changes**

```powershell
git add backend/app/routers/knowledge_documents.py backend/app/tasks/document_tasks.py backend/app/queue.py backend/app/worker.py backend/app/storage/s3.py backend/app/schemas.py backend/tests/test_document_lifecycle.py
git commit -m "feat: complete document versions and object cleanup"
```

### Task 5: Harden Avatar Upload and Replacement

**Files:**
- Modify: `backend/app/routers/users.py`
- Modify: `backend/app/storage/s3.py`
- Modify: `backend/app/config.py`
- Test: `backend/tests/test_avatar_upload.py`

**Interfaces:**
- `upload_avatar` reads at most `avatar_max_size_bytes + 1` bytes and rejects larger payloads before storing them.
- Avatar URLs use the configured private/browser endpoint and do not install a bucket-wide public policy.

- [ ] **Step 1: Write failing avatar tests**

```python
def test_webp_requires_riff_and_webp_signature():
    with pytest.raises(HTTPException):
        validate_avatar_bytes("image/webp", b"RIFFxxxxNOPE")


def test_avatar_upload_does_not_make_bucket_public(monkeypatch):
    calls = record_s3_calls(monkeypatch)
    assert "put_bucket_policy" not in calls
```

- [ ] **Step 2: Run focused tests and verify they fail**

Run: `pytest backend/tests/test_avatar_upload.py -q`

Expected: FAIL because upload reads the complete body and installs a public policy.

- [ ] **Step 3: Implement bounded reads and strict signatures**

Read `max_avatar_size_bytes + 1`, validate exact JPEG, PNG, and WebP signatures (`RIFF` plus `WEBP` at bytes 8-12), and reject mismatched content types. Add a configurable avatar size and upload-rate limit hook without introducing a new external service.

- [ ] **Step 4: Replace and clean old avatar objects**

Persist the old object key in a private URL format or dedicated field, write the new object, update the user record, then delete the old object after commit. A failed old-object deletion is logged and recorded for the existing cleanup mechanism.

- [ ] **Step 5: Run users and storage tests**

Run: `pytest backend/tests/test_users_api.py backend/tests/test_avatar_upload.py backend/tests/test_s3_storage.py -q`

Expected: PASS.

- [ ] **Step 6: Commit the avatar hardening change**

```powershell
git add backend/app/routers/users.py backend/app/storage/s3.py backend/app/config.py backend/tests/test_avatar_upload.py
git commit -m "fix: harden avatar uploads and replacement cleanup"
```

### Task 6: Add Bounded Embedding Retries and Context Budgets

**Files:**
- Modify: `backend/app/providers/embedding.py`
- Modify: `backend/app/services/retrieval_service.py`
- Modify: `backend/app/routers/conversations.py`
- Modify: `backend/app/config.py`
- Create: `backend/app/services/context_budget.py`
- Test: `backend/tests/test_embedding_retries.py`
- Test: `backend/tests/test_context_budget.py`

**Interfaces:**
- `EmbeddingProvider.embed_documents(texts)` retries only transient 429/5xx/network/timeout failures up to `embedding_max_retries`.
- `trim_history(history, max_chars, max_messages) -> list[dict]` keeps the newest complete messages within budget.
- `trim_retrieved_chunks(chunks, max_chars, limit) -> list[RankedChunk]` removes duplicate adjacent content and respects the configured budget.

- [ ] **Step 1: Write failing retry and budget tests**

```python
@pytest.mark.asyncio
async def test_embedding_retries_429_then_succeeds(monkeypatch):
    client = FakeHttpClient([429, 200])
    monkeypatch.setattr(httpx, "AsyncClient", lambda **_: client)
    assert await EmbeddingProvider().embed_query("q") == [0.1, 0.2]
    assert client.calls == 2


def test_history_budget_keeps_newest_messages_without_partial_records():
    result = trim_history(history, max_chars=20, max_messages=3)
    assert len(result) <= 3
    assert sum(len(item["content"]) for item in result) <= 20
```

- [ ] **Step 2: Run focused tests and verify they fail**

Run: `pytest backend/tests/test_embedding_retries.py backend/tests/test_context_budget.py -q`

Expected: FAIL because Provider calls once and no shared budget helper exists.

- [ ] **Step 3: Implement transient classification and exponential backoff**

Use explicit connect/read timeout values. Retry 429, 5xx, `httpx.TimeoutException`, and transport errors with `base_delay * 2**attempt`, capped by `embedding_retry_max_delay_seconds`. Raise immediately for other 4xx responses. Log status, attempt, and elapsed milliseconds without logging request content or credentials.

- [ ] **Step 4: Apply deterministic history and RAG budgets**

Load only the newest messages that fit the configured history count/character budget. Apply the RAG budget after retrieval and before prompt construction, preserving ranking order and the current user prompt. Keep citation IDs for retained chunks only.

- [ ] **Step 5: Run chat and worker tests**

Run: `pytest backend/tests/test_embedding_retries.py backend/tests/test_context_budget.py backend/tests/test_chat_rag.py backend/tests/test_conversations_runtime.py backend/tests/test_worker.py -q`

Expected: PASS with bounded retries and stable prompt sizes.

- [ ] **Step 6: Commit model reliability changes**

```powershell
git add backend/app/providers/embedding.py backend/app/services/retrieval_service.py backend/app/routers/conversations.py backend/app/services/context_budget.py backend/app/config.py backend/tests/test_embedding_retries.py backend/tests/test_context_budget.py
git commit -m "feat: bound embedding retries and chat context budgets"
```

### Task 7: Replace Process-Local Run State with Redis Leases

**Files:**
- Create: `backend/app/services/run_state.py`
- Modify: `backend/app/routers/conversations.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/config.py`
- Test: `backend/tests/test_run_state.py`
- Modify: `backend/tests/test_conversations_runtime.py`

**Interfaces:**
- `RunState.acquire(conversation_id) -> RunLease` raises HTTP 409 when another live lease exists.
- `RunLease.stop_requested() -> bool` reads the distributed stop signal.
- `RunLease.release() -> None` releases only the owner lease and is idempotent.
- `RunState.request_stop(conversation_id) -> None` writes a short-lived stop key.

- [ ] **Step 1: Write failing Redis lease tests**

```python
@pytest.mark.asyncio
async def test_second_instance_cannot_acquire_same_conversation():
    redis = FakeRedis()
    first = RunState(redis)
    second = RunState(redis)
    lease = await first.acquire("conversation-1")
    with pytest.raises(HTTPException) as error:
        await second.acquire("conversation-1")
    assert error.value.status_code == 409
    await lease.release()
```

- [ ] **Step 2: Run focused tests and verify they fail**

Run: `pytest backend/tests/test_run_state.py -q`

Expected: FAIL because Redis run state does not exist.

- [ ] **Step 3: Implement owner-checked Redis lease and stop signal**

Use `redis.asyncio` with `SET NX EX` for acquisition. Store a random owner token, refresh the lease while generating, release with an owner-checking Lua script, and write a stop key with a bounded TTL. Keep an in-memory adapter only for unit tests.

- [ ] **Step 4: Integrate the lease into SSE generation**

Acquire before persisting the user message, use `lease.stop_requested()` alongside disconnect detection, replace `/run/stop` with `request_stop`, and release in the existing `finally` block. Preserve all current SSE event names and failed-message persistence.

- [ ] **Step 5: Add cleanup lifecycle wiring**

Close the Redis client in FastAPI lifespan and keep the existing stale-run cleanup only for test adapters. Do not add checkpoint persistence or change `/run/resume` semantics.

- [ ] **Step 6: Run runtime tests**

Run: `pytest backend/tests/test_run_state.py backend/tests/test_conversations_runtime.py -q`

Expected: PASS for same-instance and simulated multi-instance behavior.

- [ ] **Step 7: Commit the distributed run-state change**

```powershell
git add backend/app/services/run_state.py backend/app/routers/conversations.py backend/app/main.py backend/app/config.py backend/tests/test_run_state.py backend/tests/test_conversations_runtime.py
git commit -m "feat: coordinate conversation runs with Redis leases"
```

### Task 8: Isolate Frontend Conversation Context

**Files:**
- Modify: `frontend/src/app/chat/page.tsx`
- Create: `frontend/src/lib/chat-context.ts`
- Test: `frontend/src/lib/chat-context.test.ts`

**Interfaces:**
- `emptyConversationContext()` returns mode `normal`, null problem/language, empty citations, no attachments, and reset pagination.
- `restoreConversationContext(messages)` derives context only from the supplied conversation messages.

- [ ] **Step 1: Write failing pure-state tests**

```typescript
test("restoring a conversation never uses another conversation's problem", () => {
  const context = restoreConversationContext([{ problem_id: "b", mode: "acm_analysis", solution_language: null }]);
  expect(context.problemId).toBe("b");
  expect(context.mode).toBe("acm_analysis");
});

test("empty context clears ACM state", () => {
  expect(emptyConversationContext().mode).toBe("normal");
  expect(emptyConversationContext().problemId).toBeNull();
});
```

- [ ] **Step 2: Run focused frontend tests and verify they fail**

Run: `npm --prefix frontend exec tsx --test src/lib/chat-context.test.ts`

Expected: FAIL because the context helper does not exist.

- [ ] **Step 3: Implement conversation context helpers**

Create pure helpers for reset and restoration. Restoration must use the latest context-bearing message from the supplied list and must not consult global component state.

- [ ] **Step 4: Reset state on active conversation changes**

In `page.tsx`, clear problem, mode, language, citations, attachments, pagination cursor, and loading flags before loading a new conversation. Capture the requested conversation id in each async load and ignore responses for stale ids.

- [ ] **Step 5: Update send/retry paths**

Use only the active conversation's context when building `ChatRequest`. Include `attachment_ids`, preserve retry metadata, and prevent a stale request from updating the current message list.

- [ ] **Step 6: Run TypeScript checks and tests**

Run: `npm --prefix frontend run test:message` and `npm --prefix frontend exec tsc -- --noEmit`

Expected: PASS.

- [ ] **Step 7: Commit the frontend context isolation change**

```powershell
git add frontend/src/app/chat/page.tsx frontend/src/lib/chat-context.ts frontend/src/lib/chat-context.test.ts
git commit -m "fix: isolate chat context when switching conversations"
```

### Task 9: Complete Frontend Chat Attachments

**Files:**
- Modify: `frontend/src/app/chat/page.tsx`
- Create: `frontend/src/components/AttachmentPicker.tsx`
- Modify: `frontend/src/lib/auth.ts`
- Test: `frontend/src/components/AttachmentPicker.test.tsx`

**Interfaces:**
- `AttachmentPicker` accepts `conversationId`, `token`, `onChange`, and `disabled` props.
- It calls `GET /conversations/{id}/attachments`, `POST /conversations/{id}/attachments/{versionId}`, and `DELETE /conversations/{id}/attachments/{attachmentId}`.
- Chat requests include `attachment_ids` alongside the optional selected group id.
- Export pure request builders `attachmentListRequest`, `attachRequest`, and `detachRequest`; tests use the repository's existing dependency-free `node:test` runner rather than Vitest.
- Export pure request builders `attachmentListRequest`, `attachRequest`, and `detachRequest` so the repository's dependency-free `node:test` runner can verify conversation scoping without adding a test framework.

- [ ] **Step 1: Write failing picker contract tests**

```typescript
test("attachment request builders use the active conversation", () => {
  assert.match(attachmentListRequest("conversation-b").url, /conversation-b\\/attachments$/);
  assert.match(attachRequest("conversation-b", "version-1").url, /conversation-b\\/attachments\\/version-1$/);
  assert.match(detachRequest("conversation-b", "attachment-1").url, /conversation-b\\/attachments\\/attachment-1$/);
});
```

- [ ] **Step 2: Run the focused test and verify it fails**

Run: `npm --prefix frontend exec tsx --test src/components/AttachmentPicker.test.tsx`

Expected: FAIL because the component does not exist.

- [ ] **Step 3: Implement attachment listing, mounting, and detaching**

Render current attachments and an indexed-document selector. On attach/detach, refresh the active conversation list and expose the resulting IDs to the parent. Use `apiFetch` so expired access tokens refresh consistently.

- [ ] **Step 4: Wire the composer button and request body**

Replace the no-op attachment button with the picker. Clear attachments on conversation switch and include `attachment_ids` in `messages/stream`. Keep the selected knowledge group independent from attachments.

- [ ] **Step 5: Run frontend build and component tests**

Run: `npm --prefix frontend exec tsx --test src/components/AttachmentPicker.test.tsx` and `npm --prefix frontend run build`

Expected: PASS.

- [ ] **Step 6: Commit the chat attachment flow**

```powershell
git add frontend/src/app/chat/page.tsx frontend/src/components/AttachmentPicker.tsx frontend/src/components/AttachmentPicker.test.tsx frontend/src/lib/auth.ts
git commit -m "feat: attach and detach knowledge documents from chat"
```

### Task 10: Complete Knowledge Document UI and Version History

**Files:**
- Modify: `frontend/src/app/knowledge/page.tsx`
- Modify: `frontend/src/app/knowledge/[id]/page.tsx`
- Create: `frontend/src/components/DocumentActions.tsx`
- Test: `frontend/src/components/DocumentActions.test.tsx`

**Interfaces:**
- Detail page consumes `GET /knowledge/documents/{id}/versions` and renders descending versions.
- Actions call existing `download`, `retry`, `reindex`, and `DELETE` endpoints; re-upload calls the new version endpoint.
- A successful delete navigates back to `/knowledge` and removes the item from the list.
- Export pure action request builders; tests use the repository's existing dependency-free `node:test` runner rather than React Testing Library.

- [ ] **Step 1: Write failing action tests**

```typescript
test("failed document exposes retry and reindex actions", () => {
  render(<DocumentActions documentId="doc-1" status="failed" token="token" onChanged={vi.fn()} />);
  expect(screen.getByRole("button", { name: "重试" })).toBeTruthy();
  expect(screen.getByRole("button", { name: "重新索引" })).toBeTruthy();
});
```

- [ ] **Step 2: Run focused test and verify it fails**

Run: `npm --prefix frontend exec tsx --test src/components/DocumentActions.test.tsx`

Expected: FAIL because lifecycle controls do not exist.

- [ ] **Step 3: Implement document actions and version display**

Add loading/error states, disable duplicate submissions, refresh status after each action, and show all version numbers with the active version highlighted. Download must open the returned presigned URL without exposing storage credentials.

- [ ] **Step 4: Implement re-upload as a new version**

Use a file input on the detail page, submit to the version endpoint, then poll status until indexed or failed. Keep the document id stable and refresh the version list.

- [ ] **Step 5: Run frontend build and tests**

Run: `npm --prefix frontend exec tsx --test src/components/DocumentActions.test.tsx` and `npm --prefix frontend run build`

Expected: PASS.

- [ ] **Step 6: Commit the knowledge document lifecycle UI**

```powershell
git add frontend/src/app/knowledge/page.tsx frontend/src/app/knowledge/[id]/page.tsx frontend/src/components/DocumentActions.tsx frontend/src/components/DocumentActions.test.tsx
git commit -m "feat: complete knowledge document lifecycle controls"
```

### Task 11: Normalize Compose and Environment Configuration

**Files:**
- Modify: `docker-compose.yml`
- Modify: `frontend/Dockerfile`
- Modify: `frontend/next.config.ts`
- Modify: `.env.example`
- Modify: `backend/app/config.py`
- Test: `backend/tests/test_deployment_config.py`

**Interfaces:**
- Compose interpolates database, Redis, MinIO, JWT, model, upload, retry, budget, and frontend API variables from `.env`.
- Backend uses service DNS names for internal connections and `browser_s3_endpoint` only for browser URLs.
- Production settings reject default credentials and browser API URLs containing `localhost`.

- [ ] **Step 1: Write failing configuration tests**

```python
def test_production_rejects_localhost_browser_api_url():
    with pytest.raises(ValueError):
        Settings(app_env="production", jwt_secret_key="x" * 40, frontend_url="http://localhost:3000")


def test_compose_does_not_hardcode_service_credentials():
    compose = Path(__file__).parents[2].joinpath("docker-compose.yml").read_text()
    assert "POSTGRES_PASSWORD: codeatlas-dev-password" not in compose
    assert "MINIO_ROOT_PASSWORD: codeatlas-dev-password" not in compose
```

- [ ] **Step 2: Run focused tests and verify they fail**

Run: `pytest backend/tests/test_deployment_config.py -q`

Expected: FAIL because Compose and production validation still contain development assumptions.

- [ ] **Step 3: Parameterize Compose services**

Use required environment variables for production secrets, service-internal URLs for backend/worker, and separate browser endpoint variables. Pass `NEXT_PUBLIC_API_BASE_URL` as a frontend build argument or runtime configuration consumed by Next.js.

- [ ] **Step 4: Add production validation and document all variables**

Reject default JWT, database, and MinIO credentials in production. Add upload, retry, history, RAG budget, and avatar settings to `.env.example`; update README and technical-stack documentation with container versus browser addresses.

- [ ] **Step 5: Run configuration and build checks**

Run: `pytest backend/tests/test_deployment_config.py -q`, `docker compose config`, and `npm --prefix frontend run build`.

Expected: PASS with no hard-coded production credentials and no production `localhost` API default.

- [ ] **Step 6: Commit deployment configuration changes**

```powershell
git add docker-compose.yml frontend/Dockerfile frontend/next.config.ts .env.example backend/app/config.py backend/tests/test_deployment_config.py README.md docs/technical-stack.md
git commit -m "fix: normalize production deployment configuration"
```

### Task 12: Execute Integration, Browser, and Documentation Closure

**Files:**
- Create: `backend/tests/test_integration_phase4.py`
- Modify: `docs/api-contract.md`
- Modify: `docs/data-model.md`
- Modify: `docs/development-baseline.md`
- Modify: `docs/browser-test-plan.md`
- Modify: `docs/browser-test-results.md`
- Modify: `README.md`

**Interfaces:**
- Integration fixture starts PostgreSQL/pgvector, Redis, MinIO, backend, and Worker with production-style environment variables.
- Browser matrix covers login/logout, conversation switching, ACM problem selection, knowledge selection, attachment mount/detach, document lifecycle, and mobile layout.

- [ ] **Step 1: Write integration test scenarios**

```python
@pytest.mark.integration
async def test_private_attachment_cannot_cross_conversations(real_stack):
    # Create one user, two conversations, and one indexed document.
    # Mount the document only in conversation A.
    # Query conversation B and assert retrieval.completed count is zero.
    assert await real_stack.retrieval_count(conversation_b) == 0
```

- [ ] **Step 2: Run the existing backend suite before full-stack changes**

Run: `docker compose --profile test run --rm backend-test`

Expected: the baseline suite passes before integration additions; record the exact count.

- [ ] **Step 3: Run the full real-service integration matrix**

Run: `docker compose up --build -d`, `docker compose --profile test run --rm backend-test`, and the documented browser command against the running frontend. Verify health, readiness, migration head, Worker indexing, MinIO cleanup, Redis lease stop, and all Phase 4 UI flows.

- [ ] **Step 4: Update documentation from observed results**

Record only commands and results that actually ran. Update API contracts for version upload/listing, attachment IDs, token invalidation, and SSE behavior. Update data-model and baseline documents to revision `0008_phase4_reliability_closure`.

- [ ] **Step 5: Perform final regression and review**

Run: `pytest backend/tests -q`, `npm --prefix frontend run build`, `docker compose config`, and the browser matrix. Review `git diff --check`, confirm no future-scope feature was added, and verify all acceptance criteria in the design document have an evidence entry.

- [ ] **Step 6: Commit the verified closure**

```powershell
git add backend frontend docker-compose.yml .env.example README.md docs
git commit -m "feat: close Phase 4 reliability and workflow gaps"
```
