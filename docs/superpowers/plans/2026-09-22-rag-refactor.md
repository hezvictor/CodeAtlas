# RAG Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve CodeAtlas retrieval quality and make per-conversation knowledge/mode behavior match the confirmed product contract.

**Architecture:** Keep FastAPI, PostgreSQL/pgvector, MinIO, Redis/Arq, and the existing SSE run registry. Add explicit retrieval stages for batched embedding, structure-aware chunks, hybrid retrieval, optional reranking, context expansion, and citation validation. Keep LangChain/LangGraph out of the core runtime.

**Tech Stack:** Python/FastAPI, SQLAlchemy/Alembic, PostgreSQL full-text search + pgvector, DashScope-compatible Embeddings, Next.js/React, pytest, Vitest.

**Spec:** `.grill/rag-refactor-design.md` and `docs/rag-evaluation/hzvictory-template-v1.md`.

## Global Constraints

- Chat knowledge scope is only `none` or `all`.
- `all` searches the user's long-term documents plus current conversation attachments.
- `none` performs no knowledge retrieval.
- Groups remain in management/storage but never enter chat protocol or retrieval filters.
- New conversations default to `none`; reopening restores the conversation snapshot.
- Streaming locks mode and knowledge scope for the current message; changes affect the next message.
- `normal` needs no problem or language; `acm_analysis` needs neither and emits no complete code; `acm_solution` requires language but not a problem-bank item.
- Indexing occurs on upload/reindex, never once per chat message.
- Retrieval failure under `all` fails the run; successful no-hit retrieval may continue with an explicit no-source state.
- Images are ignored by text ingestion; OCR and multimodal parsing are out of scope.

### Task 1: Chat Contract and Persistence

**Files:**
- Modify: `backend/app/schemas.py`, `backend/app/models.py`, `backend/app/routers/conversations.py`
- Create: `backend/migrations/versions/0012_rag_chat_state.py`
- Test: `backend/tests/test_retrieval_scope_v2.py`, `backend/tests/test_acm_workflow.py`, `backend/tests/test_conversations_runtime.py`

- [ ] Add failing tests for `none`/`all`, new-conversation default `none`, message snapshots, and optional ACM problem.
- [ ] Remove `groups` from chat request and retrieval invocation while retaining group database/API management.
- [ ] Add conversation knowledge scope and message knowledge scope columns with migration defaults.
- [ ] Persist the actual mode/scope/problem/language snapshot for every user and assistant message.
- [ ] Make `acm_analysis` accept `problem_id=None`; keep language validation only for `acm_solution`.
- [ ] Run focused backend tests and then the conversation test module.

### Task 2: Embedding Batching

**Files:**
- Modify: `backend/app/providers/embedding.py`, `backend/app/tasks/document_tasks.py`, `backend/app/config.py`
- Test: `backend/tests/test_embedding_retries.py`, `backend/tests/test_storage_embedding.py`, `backend/tests/test_document_jobs.py`

- [ ] Add a failing test proving a document list is split into bounded batches and preserves order.
- [ ] Add batch-size and per-input limits to settings.
- [ ] Implement shared batching for project and user providers with retry/error metadata per batch.
- [ ] Ensure one oversized chunk is rejected clearly instead of sending an invalid request.
- [ ] Run embedding and document-job tests.

### Task 3: Structure-Aware Parsing and Chunking

**Files:**
- Modify: `backend/app/parsers/text.py`, `backend/app/parsers/dispatcher.py`, `backend/app/chunking.py`
- Create: `backend/app/parsers/markdown.py` if the existing text parser cannot preserve headings/fenced blocks
- Test: `backend/tests/test_parsers_and_chunking.py`

- [ ] Add failing cases for Markdown heading paths, complete fenced code blocks, and parent/child metadata.
- [ ] Parse Markdown sections without OCR or image content.
- [ ] Keep code blocks intact when within limits; split oversized blocks only at safe line boundaries.
- [ ] Add stable parent identifiers and source locators while preserving existing chunk compatibility.
- [ ] Run parser/chunker tests and the document ingestion tests.

### Task 4: Retrieval Pipeline

**Files:**
- Modify: `backend/app/retrieval.py`, `backend/app/services/retrieval_service.py`, `backend/app/chat_rag.py`
- Create: `backend/app/services/query_rewrite.py`, `backend/app/services/reranker.py`, `backend/app/services/context_assembly.py`
- Test: `backend/tests/test_retrieval_scope.py`, `backend/tests/test_retrieval_and_citations.py`, new focused retrieval tests

- [ ] Add failing tests for zero retrieval on `none`, all long-term documents plus attachments on `all`, and exclusion of pending versions.
- [ ] Remove group parameters and filters from the runtime retrieval path.
- [ ] Preserve original and rewritten queries, merge both candidate sets, then apply RRF.
- [ ] Add optional reranking with project default/user override and RRF fallback.
- [ ] Expand selected child chunks to parent/neighbor context within the context budget.
- [ ] Keep session attachment provenance and citation locators intact.
- [ ] Run focused retrieval tests and the complete backend suite.

### Task 5: Streaming and Citation Semantics

**Files:**
- Modify: `backend/app/routers/conversations.py`, `backend/app/citations.py`, `backend/app/services/context_budget.py`
- Test: `backend/tests/test_chat_rag.py`, `backend/tests/test_conversations_runtime.py`, `backend/tests/test_retrieval_and_citations.py`

- [ ] Add failing tests for retrieval failure termination, successful no-hit generation, and no-source citation state.
- [ ] Snapshot knowledge scope and mode before starting the run.
- [ ] Emit retrieval status events without exposing internal error details.
- [ ] Keep citation validation and right-panel payloads tied to the assistant message snapshot.
- [ ] Preserve retry behavior and avoid re-indexing during message sends.
- [ ] Run all backend tests.

### Task 6: Frontend Chat Controls

**Files:**
- Modify: `frontend/src/app/chat/page.tsx`, `frontend/src/components/ModeSelector.tsx`, `frontend/src/lib/chat-state.ts`, `frontend/src/lib/chat-context.ts`
- Create: `frontend/src/components/KnowledgeScopeSelector.tsx` if the control is not reusable inline
- Test: `frontend/src/app/chat/chat-state.test.ts`, `frontend/src/lib/chat-context.test.ts`, new component tests

- [ ] Add failing tests for new draft default `none`, conversation restoration, and `none`/`all` payloads without groups.
- [ ] Add a visible knowledge scope control with `none` and `all` only.
- [ ] Lock mode and knowledge scope while a run is active.
- [ ] Remove the ACM analysis requirement for selecting a problem; keep language dialog for solutions.
- [ ] Render non-model-visible transition separators for mode and knowledge changes.
- [ ] Keep citations in the right panel and show retrieval/no-hit/pending states.
- [ ] Run frontend unit tests and a production build.

### Task 7: Model Configuration

**Files:**
- Modify: `backend/app/models.py`, `backend/app/schemas.py`, `backend/app/routers/model_connections.py`, `frontend/src/app/settings/models/page.tsx`
- Create: `backend/migrations/versions/0013_reranker_config.py`, `backend/app/providers/reranker.py`
- Test: `backend/tests/test_model_config_models.py`, new reranker API/provider tests, frontend model-page tests

- [ ] Add failing tests for project defaults, optional user overrides, and fallback behavior.
- [ ] Add encrypted reranker configuration using the existing credential pattern.
- [ ] Keep Embedding changes marked as requiring reindex; make reranker changes query-time only.
- [ ] Update settings UI with effective configuration and validation status.
- [ ] Run backend model/config tests and frontend build.

### Task 8: Evaluation and Documentation

**Files:**
- Modify: `docs/rag-evaluation/hzvictory-template-v1.md`, `docs/development-baseline.md`, `.grill/rag-refactor-design.md`
- Create: `backend/tests/test_rag_evaluation_contract.py`, `docs/rag-evaluation/README.md`

- [ ] Add executable contract checks for the 20 existing cases.
- [ ] Verify top-5 expected-source recall, no-hit behavior, no-retrieval behavior, ACM output restrictions, and multi-turn term preservation.
- [ ] Document configuration, indexing lifecycle, reranker fallback, and known image limitations.
- [ ] Run backend tests, frontend tests, build, and the evaluation contract.
