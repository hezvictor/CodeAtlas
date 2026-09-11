# Private Knowledge RAG Implementation Plan

> **For agentic workers:** Implement this plan task-by-task with a test-first cycle and review checkpoints.

**Goal:** Deliver a private, user-isolated knowledge base with MinIO uploads, asynchronous parsing/indexing, pgvector hybrid retrieval, citation validation, preview, and frontend management.

**Architecture:** FastAPI routes delegate to storage, document, retrieval, and citation services. Arq workers consume Redis jobs and run parse → chunk → embed → index for immutable document versions. PostgreSQL stores metadata, full-text vectors, pgvector embeddings, and validated citations; MinIO stores private originals.

**Tech Stack:** FastAPI, SQLAlchemy Async, Alembic, PostgreSQL 16 + pgvector, Redis, Arq, MinIO/S3, DashScope Embeddings, Next.js, React, TypeScript.

**Spec:** `docs/superpowers/specs/2026-09-11-private-knowledge-rag-design.md`

## Global Constraints

- Phase 3 accepts uploaded Markdown, PDF, DOCX, TXT, C/C++, Java, Python, and HTML files; no URL ingestion.
- Arq is the queue; LangGraph and rerank are not required.
- Knowledge objects remain private and every query is filtered by the authenticated user ID.
- Embedding vectors are fixed at 1024 dimensions and must match `EMBEDDING_DIMENSIONS`.
- Existing authentication, conversation, message, and SSE behavior remains compatible.

---

### Task 1: Configuration, dependencies, and service interfaces

**Files:**
- Modify: `backend/app/config.py`, `backend/pyproject.toml`, `.env.example`
- Create: `backend/app/storage/s3.py`, `backend/app/providers/embedding.py`, `backend/app/queue.py`
- Test: `backend/tests/test_knowledge_config.py`

Define upload limits, supported extensions, queue retry settings, embedding model/dimensions, and typed storage/embedding interfaces. Add Arq, pgvector, pypdf, python-docx, and beautifulsoup4 dependencies. Tests must verify settings parsing and vector-dimension validation.

### Task 2: Database models and migration

**Files:**
- Modify: `backend/app/models.py`
- Create: `backend/migrations/versions/0004_knowledge_rag.py`
- Test: `backend/tests/test_knowledge_models.py`

Add knowledge groups, documents, immutable document versions, chunks, attachments, citations, and document jobs. Enable `vector`, create ownership indexes, GIN full-text index, and cosine HNSW index. Verify upgrade SQL and foreign-key behavior without changing existing tables.

### Task 3: Knowledge-group API

**Files:**
- Create: `backend/app/routers/knowledge_groups.py`, `backend/app/services/knowledge_groups.py`
- Modify: `backend/app/schemas.py`, `backend/app/main.py`
- Test: `backend/tests/test_knowledge_groups_api.py`

Implement authenticated CRUD with per-user uniqueness and cross-user denial. Return consistent error envelopes and pagination-ready list responses.

### Task 4: Private MinIO document upload and lifecycle API

**Files:**
- Create: `backend/app/routers/knowledge_documents.py`, `backend/app/services/documents.py`
- Modify: `backend/app/storage/s3.py`, `backend/app/schemas.py`, `backend/app/main.py`
- Test: `backend/tests/test_document_upload_api.py`, `backend/tests/test_s3_storage.py`

Validate extension, MIME, file signature, and size; write a random object key under the user/group/document/version prefix; create a version in `uploaded`; enqueue processing; implement status, retry, reindex, preview, download, and soft-delete endpoints. Use private Bucket and short-lived presigned URLs.

### Task 5: Arq worker and idempotent job state

**Files:**
- Create: `backend/app/worker.py`, `backend/app/tasks/document_tasks.py`, `backend/app/services/job_state.py`
- Modify: `docker-compose.yml`, `backend/Dockerfile`
- Test: `backend/tests/test_document_jobs.py`

Add a Worker service that updates stage/status, applies exponential retry, expires stale locks, and prevents duplicate chunks for the same version. Keep API and Worker image dependencies identical.

### Task 6: Safe document parsers and chunking

**Files:**
- Create: `backend/app/parsers/base.py`, `text.py`, `pdf.py`, `docx.py`, `code.py`, `html.py`, `backend/app/chunking.py`
- Modify: `backend/app/tasks/document_tasks.py`
- Test: `backend/tests/parsers/`, `backend/tests/test_chunking.py`

Parse only uploaded files. Remove scripts/styles from HTML, preserve PDF pages, DOCX headings, and source line ranges. Chunk prose by headings/paragraphs with configured overlap and code by class/function/block while retaining locator metadata.

### Task 7: Embedding and index writing

**Files:**
- Modify: `backend/app/providers/embedding.py`, `backend/app/tasks/document_tasks.py`
- Create: `backend/app/services/indexing.py`
- Test: `backend/tests/test_embedding_provider.py`, `backend/tests/test_indexing.py`

Batch DashScope embedding calls, retry transient failures, validate result count/dimensions, and write vectors plus `tsvector`. Make reindexing idempotent and mark the version `indexed` only after all chunks succeed.

### Task 8: Hybrid retrieval

**Files:**
- Create: `backend/app/retrieval.py`, `backend/app/services/retrieval_service.py`
- Test: `backend/tests/test_retrieval.py`, `backend/tests/test_retrieval_postgres.py`

Filter by user, selected groups, session attachments, and indexed versions. Combine keyword and cosine candidates with RRF, deduplicate adjacent chunks, enforce top-k and context limits, and return stable chunk IDs plus locator data.

### Task 9: Citation validation and preview

**Files:**
- Create: `backend/app/citations.py`, `backend/app/services/preview.py`
- Modify: `backend/app/schemas.py`, `backend/app/routers/knowledge_documents.py`
- Test: `backend/tests/test_citations.py`, `backend/tests/test_document_preview.py`

Validate `[cite:chunk_uuid]` markers against the current retrieval set and ownership chain, persist valid citations, remove invalid markers, and expose preview text with page/section/line anchors.

### Task 10: Chat RAG and SSE integration

**Files:**
- Create: `backend/app/services/chat_rag.py`
- Modify: `backend/app/routers/conversations.py`, `backend/app/schemas.py`
- Test: `backend/tests/test_chat_rag.py`, `backend/tests/test_conversations_runtime.py`

Accept `knowledge_group_ids` and existing `attachment_ids`, retrieve context before generation, emit retrieval and validated-citation events, emit sanitized `message.final`, and preserve ordinary-chat stop/failure/retry behavior.

### Task 11: Knowledge-base frontend

**Files:**
- Modify: `frontend/src/app/knowledge/page.tsx`, `frontend/src/app/globals.css`
- Create: `frontend/src/app/knowledge/[id]/page.tsx`, `frontend/src/components/KnowledgeGroupList.tsx`, `DocumentList.tsx`, `UploadDocumentDialog.tsx`, `DocumentPreview.tsx`
- Test: browser flows in `docs/browser-test-plan.md`

Replace the placeholder with group management, upload progress, status polling, search/filter, retry/reindex/delete, document details, and responsive preview while reusing existing auth/error utilities.

### Task 12: Chat citations, integration tests, and deployment verification

**Files:**
- Modify: `frontend/src/app/chat/page.tsx`, `frontend/src/app/globals.css`, `docs/api-contract.md`, `docs/data-model.md`, `docs/technical-stack.md`, `docs/roadmap.md`
- Create: `frontend/src/components/CitationPanel.tsx`
- Test: backend regression suite, browser E2E, Docker Compose smoke test

Render citations and jump-to-preview behavior, document final SSE handling, run cross-user and failure-retry tests, start PostgreSQL/Redis/MinIO/Worker/frontend together, and document backup/restore verification.
