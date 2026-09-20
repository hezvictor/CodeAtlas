# Knowledge Scope and Session Files Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make long-term user documents automatically searchable while adding conversation-scoped uploads that can be managed and cited from the chat sidebar.

**Architecture:** Add an explicit document scope, retain attachments as the conversation boundary, and retrieve two source pools server-side on every chat request. Keep citations as durable snapshots so removing a file affects future retrieval without destroying history.

**Tech Stack:** FastAPI, SQLAlchemy/Alembic, PostgreSQL/pgvector, Arq/Redis, MinIO, Next.js/React/TypeScript, SSE.

**Spec:** `docs/superpowers/specs/2026-09-20-knowledge-scope-and-model-config-design.md`

## Global Constraints

- Long-term files are user-scoped; session files are conversation-scoped.
- Chat retrieval is automatic; no client knowledge-group or scope selector remains.
- Files that are not indexed are excluded from retrieval.
- Historical citations must survive document or attachment removal.
- Preserve existing parsers, SSE lifecycle, auth, ACM workflows, and vector dimension `1024`.

---

### Task 1: Add document scopes and durable citation metadata

**Files:**
- Modify: `backend/app/models.py`
- Modify: `backend/app/schemas.py`
- Create: `backend/migrations/versions/0010_document_scopes_and_citation_snapshots.py`
- Test: `backend/tests/test_knowledge_scope_migration.py`

**Interfaces:**
- `Document.scope: str` accepts `long_term` or `session`.
- Citation responses expose `source_scope`, filename, title, and locator without requiring an active group.

- [ ] **Step 1: Write failing model and migration tests** for scope backfill, nullable legacy group ownership, and citation snapshot fields.
- [ ] **Step 2: Run** `cd backend; pytest tests/test_knowledge_scope_migration.py -q` and verify the new fields are absent.
- [ ] **Step 3: Implement** model fields, migration backfill of existing documents to `long_term`, and snapshot columns needed after soft deletion.
- [ ] **Step 4: Run** the focused migration/model tests and the existing knowledge model tests.
- [ ] **Step 5: Commit** the schema change with `git add backend/app/models.py backend/app/schemas.py backend/migrations/versions/0010_document_scopes_and_citation_snapshots.py backend/tests/test_knowledge_scope_migration.py` and a focused commit message.

### Task 2: Make knowledge-page uploads long-term and remove group dependence

**Files:**
- Modify: `backend/app/routers/knowledge_documents.py`
- Modify: `backend/app/routers/knowledge_groups.py`
- Modify: `frontend/src/app/knowledge/page.tsx`
- Modify: `frontend/src/app/knowledge/[id]/page.tsx`
- Test: `backend/tests/test_knowledge_documents.py`
- Test: `frontend/src/app/knowledge/knowledge-page.test.tsx`

**Interfaces:**
- Long-term upload creates `Document(scope="long_term")` without a required group.
- Legacy group endpoints may remain compatibility-only but are not used by the UI.

- [ ] **Step 1: Add failing API tests** for upload without `group_id`, user isolation, and document listing without group selection.
- [ ] **Step 2: Run** the focused backend tests and confirm current validation still requires a group.
- [ ] **Step 3: Update** upload/list/detail/delete schemas and routes; preserve status, preview, retry, and reindex behavior.
- [ ] **Step 4: Update** knowledge UI to show a flat long-term file list and remove group creation/selection controls.
- [ ] **Step 5: Run** backend knowledge tests and the frontend page tests.
- [ ] **Step 6: Commit** the long-term document flow.

### Task 3: Add real conversation-scoped upload and deletion

**Files:**
- Modify: `backend/app/routers/attachments.py`
- Modify: `backend/app/tasks/document_tasks.py`
- Modify: `backend/app/schemas.py`
- Modify: `frontend/src/components/AttachmentPicker.tsx`
- Test: `backend/tests/test_conversation_attachments.py`
- Test: `frontend/src/components/AttachmentPicker.test.tsx`

**Interfaces:**
- `POST /conversations/{conversation_id}/attachments/upload` accepts multipart data and returns attachment metadata plus processing status.
- Attachment list returns filename, extension, scope, and processing status.
- Delete detaches the session file and soft-deletes future retrieval without deleting citation snapshots.

- [ ] **Step 1: Add failing upload/list/delete tests** including cross-user and cross-conversation rejection.
- [ ] **Step 2: Run** the focused tests and verify the upload route does not exist.
- [ ] **Step 3: Implement** session document creation, attachment creation, async indexing dispatch, status responses, and soft removal.
- [ ] **Step 4: Replace** the current picker behavior that only mounts existing knowledge documents with a file upload control plus active-file list.
- [ ] **Step 5: Run** attachment API and component tests.
- [ ] **Step 6: Commit** the session attachment flow.

### Task 4: Retrieve long-term and session pools automatically

**Files:**
- Modify: `backend/app/services/retrieval_service.py`
- Modify: `backend/app/schemas.py`
- Modify: `backend/app/routers/conversations.py`
- Modify: `backend/app/citations.py`
- Modify: `frontend/src/lib/chat-state.ts`
- Test: `backend/tests/test_retrieval_scope_v3.py`
- Test: `backend/tests/test_chat_rag.py`

**Interfaces:**
- `retrieve_chunks(session, user_id, conversation_id, query, ...)` automatically unions indexed long-term documents with indexed attachments for the conversation.
- `ChatRequest` no longer relies on client-supplied `knowledge_scope` or `knowledge_group_ids`.
- Retrieval events report source scope and pending/failed file counts.

- [ ] **Step 1: Add failing retrieval tests** for union scope, session tie priority, no cross-user access, pending files, and no embedding fallback.
- [ ] **Step 2: Run** the focused retrieval/chat tests and confirm the old opt-in behavior fails the new assertions.
- [ ] **Step 3: Implement** two-pool retrieval, source-aware merge, context budgeting, and automatic citation persistence.
- [ ] **Step 4: Preserve** graceful generation when no indexed sources or Embedding credentials are available, with an explicit warning event.
- [ ] **Step 5: Run** retrieval, citation, and conversation runtime tests.
- [ ] **Step 6: Commit** automatic retrieval scope.

### Task 5: Build the chat sidebar file and citation experience

**Files:**
- Modify: `frontend/src/app/chat/page.tsx`
- Modify: `frontend/src/components/CitationPanel.tsx`
- Modify: `frontend/src/components/AttachmentPicker.tsx`
- Modify: `frontend/src/app/globals.css`
- Test: `frontend/src/components/CitationPanel.test.tsx`
- Test: `frontend/src/components/AttachmentPicker.test.tsx`
- Test: `frontend/src/app/chat/chat-state.test.ts`

**Interfaces:**
- Sidebar section `session files` owns upload, status, and delete-confirmation UI.
- Sidebar section `answer citations` renders only validated citations and source type.

- [ ] **Step 1: Add failing component tests** for upload status, delete confirmation, source grouping, and PDF/code locators.
- [ ] **Step 2: Remove** the chat header knowledge selector and all client knowledge-scope state.
- [ ] **Step 3: Add** multipart upload progress, polling/reload status, delete confirmation, and source-type labels.
- [ ] **Step 4: Handle** `retrieval.failed`, pending-file warnings, and citation events without changing existing streaming behavior.
- [ ] **Step 5: Run** frontend tests and `npm run build`.
- [ ] **Step 6: Commit** the chat knowledge UX.

### Task 6: End-to-end validation and documentation

**Files:**
- Modify: `docs/api-contract.md`
- Modify: `docs/data-model.md`
- Modify: `docs/frontend-screen-map.md`
- Test: `backend/tests/test_retrieval_and_citations.py`
- Test: `test-artifacts/e2e_api_check.py`

- [ ] **Step 1: Add** an integration flow covering long-term upload, session upload, cited answer, session deletion, and historical citation rendering.
- [ ] **Step 2: Run** `cd backend; pytest -q` and fix regressions without changing unrelated behavior.
- [ ] **Step 3: Run** the frontend build and the browser/API smoke flow.
- [ ] **Step 4: Update** API, data-model, and screen-map documentation to remove user-facing group and scope controls.
- [ ] **Step 5: Commit** the completed knowledge-scope feature.
