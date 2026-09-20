# User Model Configuration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let each user configure multiple secure OpenAI-compatible chat connections, validate models, choose them in chat, and separately configure the fixed DashScope embedding credential.

**Architecture:** Move chat HTTP calls behind a provider interface. Store encrypted per-user credentials and verified model records server-side. The chat page receives only verified model IDs; the backend resolves credentials and provider details.

**Tech Stack:** FastAPI, SQLAlchemy/Alembic, Pydantic, httpx, PostgreSQL, Next.js/React/TypeScript, SSE, `cryptography`.

**Spec:** `docs/superpowers/specs/2026-09-20-knowledge-scope-and-model-config-design.md`

## Global Constraints

- Chat models are text-only and streaming in the first version.
- No system default chat model; no verified model means sending is disabled.
- `/models` discovery is optional; manual model entry is always available.
- Only server-side tested models appear in chat.
- Embedding uses a fixed DashScope model and vector dimension `1024`; only the user's DashScope key is configurable.
- API keys are encrypted at rest and never returned to the browser or logs.
- Provider URLs must be reachable by the backend and pass SSRF validation.
- Preserve existing auth, ACM workflows, SSE run lifecycle, and message history.

---

### Task 1: Add encrypted credential and provider URL primitives

**Files:**
- Modify: `backend/pyproject.toml`
- Modify: `backend/app/config.py`
- Create: `backend/app/security/provider_credentials.py`
- Create: `backend/app/providers/url_validation.py`
- Test: `backend/tests/test_provider_security.py`

**Interfaces:**
- `encrypt_secret(value: str) -> EncryptedSecret`
- `decrypt_secret(ciphertext: str, nonce: str) -> str`
- `validate_provider_base_url(value: str) -> str`

- [ ] **Step 1: Add failing tests** for encryption round-trip, wrong-key failure, masked output, HTTPS/local-dev URL rules, and private-network rejection.
- [ ] **Step 2: Run** `cd backend; pytest tests/test_provider_security.py -q` and verify the primitives are missing.
- [ ] **Step 3: Add** the cryptography dependency, master-key setting, authenticated encryption, URL normalization, and SSRF checks.
- [ ] **Step 4: Run** the focused security tests and lint the new modules.
- [ ] **Step 5: Commit** the credential and URL security layer.

### Task 2: Add model connection, verified model, embedding config, and selection fields

**Files:**
- Modify: `backend/app/models.py`
- Modify: `backend/app/schemas.py`
- Create: `backend/migrations/versions/0011_user_model_configuration.py`
- Test: `backend/tests/test_model_config_migration.py`
- Test: `backend/tests/test_model_config_models.py`

**Interfaces:**
- `ModelConnection` owns an encrypted API key and normalized base URL.
- `ChatModel` owns a model name, source (`discovered` or `manual`), verification status, and last test result.
- `EmbeddingConfig` is one-to-one with a user and stores encrypted DashScope credentials.
- Conversations and messages retain selected model IDs plus model-name snapshots.

- [ ] **Step 1: Add failing model and migration tests** for user isolation, uniqueness, status transitions, nullable history references, and encrypted fields.
- [ ] **Step 2: Run** the focused tests and verify the new schema is absent.
- [ ] **Step 3: Implement** SQLAlchemy models, migration tables/indexes, conversation selection, and message snapshots.
- [ ] **Step 4: Run** model tests plus existing conversation/auth tests.
- [ ] **Step 5: Commit** the model-configuration schema.

### Task 3: Extract chat and embedding providers

**Files:**
- Create: `backend/app/providers/chat.py`
- Create: `backend/app/providers/openai_compatible.py`
- Modify: `backend/app/providers/embedding.py`
- Modify: `backend/app/tasks/document_tasks.py`
- Test: `backend/tests/test_chat_provider.py`
- Test: `backend/tests/test_embedding_user_config.py`

**Interfaces:**
- `ChatProvider.stream_chat(messages, model, stop_event) -> AsyncGenerator[str, None]`
- `ChatProvider.list_models() -> list[ModelCandidate]`
- `ChatProvider.test_model(model) -> ProviderTestResult`
- `EmbeddingProvider.for_user(user_id)` resolves the fixed DashScope model and encrypted user key.

- [ ] **Step 1: Add failing provider tests** for streaming SSE normalization, non-JSON/error responses, model discovery, minimal test requests, and user-specific embedding credentials.
- [ ] **Step 2: Run** the focused provider tests and confirm the current inline implementation cannot satisfy the interface.
- [ ] **Step 3: Implement** the adapter, retry/timeout behavior, response normalization, and fixed embedding credential lookup.
- [ ] **Step 4: Refactor** `backend/app/routers/conversations.py` to call the provider interface while preserving stop and reconnect behavior.
- [ ] **Step 5: Run** provider and conversation runtime tests.
- [ ] **Step 6: Commit** the provider abstraction.

### Task 4: Implement model and embedding configuration APIs

**Files:**
- Create: `backend/app/routers/model_connections.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/schemas.py`
- Test: `backend/tests/test_model_connections_api.py`
- Test: `backend/tests/test_embedding_config_api.py`

**Interfaces:**
- `GET/POST/PATCH/DELETE /model-connections`
- `POST /model-connections/{id}/discover-models`
- `POST /model-connections/{id}/models`
- `POST /model-connections/{id}/models/{model_id}/test`
- `PATCH /model-connections/{id}/models/{model_id}/default`
- `GET /chat-models`
- `GET/PATCH /embedding-config`, `POST /embedding-config/test`

- [ ] **Step 1: Add failing API tests** for CRUD isolation, masked secrets, discovery failure/manual fallback, verification gating, default selection, key rotation invalidation, and embedding configuration.
- [ ] **Step 2: Run** the focused API tests and verify routes are absent.
- [ ] **Step 3: Implement** authenticated routes, encrypted persistence, discovery, manual insertion, test transitions, and safe response schemas.
- [ ] **Step 4: Ensure** deletion/credential changes invalidate future use without destroying message snapshots.
- [ ] **Step 5: Run** API tests and security regression tests.
- [ ] **Step 6: Commit** model configuration APIs.

### Task 5: Integrate verified model selection into chat

**Files:**
- Modify: `backend/app/schemas.py`
- Modify: `backend/app/routers/conversations.py`
- Modify: `frontend/src/app/chat/page.tsx`
- Modify: `frontend/src/lib/chat-state.ts`
- Test: `backend/tests/test_conversation_models.py`
- Test: `frontend/src/app/chat/model-selector.test.tsx`

**Interfaces:**
- `ChatRequest.chat_model_id: UUID` is resolved and authorized server-side.
- `GET /chat-models` returns grouped verified models without secrets.
- Conversation creation uses the user's default model; an existing conversation can override it.

- [ ] **Step 1: Add failing tests** for no-model disabled send, default assignment, per-conversation override, invalidated-model rejection, and message model snapshots.
- [ ] **Step 2: Run** the focused tests and verify current chat still uses environment-level configuration.
- [ ] **Step 3: Implement** model resolution and persistence without changing ACM mode or SSE event semantics.
- [ ] **Step 4: Add** a grouped model selector to the chat header and remove any direct credential/config controls from chat.
- [ ] **Step 5: Implement** unavailable-model and no-verified-model states.
- [ ] **Step 6: Run** backend conversation tests, frontend selector tests, and the frontend build.
- [ ] **Step 7: Commit** chat model selection.

### Task 6: Build the model configuration page

**Files:**
- Create: `frontend/src/app/settings/models/page.tsx`
- Create: `frontend/src/components/ModelConnectionCard.tsx`
- Create: `frontend/src/components/ModelTestStatus.tsx`
- Modify: `frontend/src/components/Navbar.tsx`
- Modify: `frontend/src/app/globals.css`
- Test: `frontend/src/app/settings/models/model-config-page.test.tsx`

- [ ] **Step 1: Add failing UI tests** for connection creation, masked key editing, discovery fallback, manual model entry, test status, default selection, deletion confirmation, and Embedding configuration.
- [ ] **Step 2: Implement** the page using the existing auth/API helpers and stable loading/error states.
- [ ] **Step 3: Add** navigation from the profile menu without adding configuration controls to chat.
- [ ] **Step 4: Run** frontend tests and `npm run build`.
- [ ] **Step 5: Commit** the model configuration UI.

### Task 7: Complete integration, migration, and documentation verification

**Files:**
- Modify: `docs/api-contract.md`
- Modify: `docs/data-model.md`
- Modify: `docs/technical-stack.md`
- Test: `backend/tests/test_provider_model_e2e.py`
- Test: `test-artifacts/e2e_api_check.py`

- [ ] **Step 1: Add** an integration flow that creates a connection, discovers/manual-adds a model, tests it, configures Embedding, sends a streaming chat, switches the conversation model, and verifies message snapshots.
- [ ] **Step 2: Run** `cd backend; pytest -q` and the frontend test/build commands.
- [ ] **Step 3: Run** the browser/API smoke flow against the configured local services.
- [ ] **Step 4: Update** API, data-model, and technical-stack documentation to remove environment-only chat assumptions and document credential handling.
- [ ] **Step 5: Perform** a final search for plaintext key logging, client-supplied provider URLs in chat, and stale group/scope controls.
- [ ] **Step 6: Commit** the completed model configuration feature.
