# 既有认证与长期存储实施记录

仅保留与当前重构共享的账号认证、头像及长期资料管理内容，记录并非本次执行指令。当前聊天、工具与临时全文流程见 [实现说明](../../agent-rag-architecture.md)。

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
