# Knowledge Ingestion Lifecycle Implementation Plan

> **For agentic workers:** Implement this plan task-by-task in the current session with test-first checkpoints. The user has already authorized inline execution.

**Goal:** Reliable, observable document ingestion, replacement and deletion with batch upload and consistent global status.

**Architecture:** Extend existing Arq jobs with durable progress and generation-owned staging chunks. Atomically activate completed indexes and asynchronously purge obsolete content. Keep source objects in MinIO, vectors in PostgreSQL/pgvector, and progress in PostgreSQL.

**Tech Stack:** FastAPI, SQLAlchemy, PostgreSQL/pgvector, MinIO, Redis/Arq, Next.js/React/TypeScript.

**Spec:** `docs/superpowers/specs/2026-09-28-knowledge-ingestion-lifecycle-design.md`

## Global constraints
- No query-time ranking, prompting or model configuration redesign.
- No new PDF uploads, PDF retries/reindexing, OCR, pause/resume or cross-page unfinished transfers.
- MinIO acknowledgement and database commit precede safe-to-leave; ready follows a complete nonempty index commit.
- Keep the active version on failed replacement; clean all obsolete content after successful activation.
- User/group isolation, historical citation snapshots and unified supported-type policy are mandatory.

## Task 1: Provider and policy regressions
Files: `backend/tests/test_embedding_retries.py`, `backend/tests/test_knowledge_documents.py`, `backend/app/providers/embedding.py`, `backend/app/config.py`.
- [x] Add failing tests that feed 23 texts to text-embedding-v3 with configured batch 16 and assert successful ordered 10/10/3 requests; reject new PDF; classify 400 permanent and 429 transient.
- [x] Run `backend/.venv/Scripts/python.exe -m pytest tests/test_embedding_retries.py tests/test_knowledge_documents.py -q` from backend and observe expected failures.
- [x] Cap v3/v4 batch inputs at 10; normalize safe error code/message/retryability; remove PDF from upload policy.
- [x] Rerun the focused tests.

## Task 2: Durable schema and generation contract
Files: `backend/app/models.py`, `backend/app/schemas.py`, `backend/migrations/versions/0015_knowledge_lifecycle.py`, `backend/tests/test_knowledge_lifecycle.py`.
- [x] Test generation-aware chunk identity, job progress/acknowledgement and snapshot-compatible citation deletion.
- [x] Add active index job, chunk generation, document filename/cleanup, version cleanup/upload token and job progress fields.
- [x] Backfill current pointers to latest indexed versions and citation metadata before relaxing citation chunk foreign keys.
- [x] Return `active_version`, `operation`, `cleanup_status`; keep `latest_version` compatibility.
- [x] Validate migration on disposable PostgreSQL and verify existing records remain readable.

## Task 3: Reliable staging pipeline and cleanup
Files: `backend/app/tasks/document_tasks.py`, `backend/app/services/document_lifecycle.py`, `backend/app/queue.py`, `backend/app/worker.py`, `backend/app/citations.py`, `backend/app/services/retrieval_service.py`.
- [x] Write failing integration tests for 0 chunks, 400, transient failure, staging preserving old vectors, atomic activation, delete during embedding, superseded cleanup and citation retention.
- [x] Create chunks per job, commit batch vectors/progress, lock/check cancellation before writes, and atomically activate only complete generations.
- [x] Persist permanent failure or scheduled retry and recover expired jobs; dispatch with fresh delivery IDs so retained Arq results cannot suppress retry.
- [x] Cleanup old generations and superseded/deleted version objects/text/chunks under document locks; retain source snapshots.
- [x] Restrict retrieval to the active version/generation, without changing ranking.
- [x] Run lifecycle, queue, embedding and citation tests.

## Task 4: Upload/conflict/status APIs
Files: `backend/app/routers/knowledge_documents.py`, `backend/app/routers/model_connections.py`, `backend/app/storage/s3.py`.
- [x] Test group-scoped preflight, same-hash skip, explicit conflict decision, timestamp naming, upload idempotency, active preview/download, PDF rejection and summary acknowledgement.
- [x] Add preflight, summary and acknowledgement endpoints; validate conflicts again at upload under scoped locks.
- [x] Store originals and durable jobs before response; support independent/new-version actions and keep active pointer unchanged until indexing.
- [x] Trigger full cleanup on delete; requeue waiting configuration after verification; select active versions for download and attachment options.
- [x] Set UTF-8 download disposition and preserve readable MinIO basenames.
- [x] Run focused API/storage tests.

## Task 5: Batch upload and truthful UI
Files: `frontend/src/lib/knowledge.ts`, `frontend/src/components/KnowledgeUpload.tsx`, `frontend/src/components/KnowledgeProgress.tsx`, knowledge list/detail pages, `DocumentActions.tsx`, `AttachmentPicker.tsx`, knowledge CSS.
- [x] Test status text/readiness, duplicate choice, transfer acknowledgement and safe-to-leave behavior with hand-derived fixtures.
- [x] Use per-file XHR byte progress, UUID upload tokens and group preflight; distinguish transmission from server storage acknowledgement.
- [x] Abort unfinished requests on navigation/unmount and warn before leave; retain acknowledged work on server.
- [x] Render list/detail active/latest versions, counts, retry errors, deleting/cleanup failures, concise history and supported policy.
- [x] Run `npm test`, `npm run lint`, `npm run typecheck`.

## Task 6: Global summary and end-to-end acceptance
Files: shared `Navbar.tsx`, knowledge summary hook, API/docs/tests.
- [x] Test summary counts and acknowledgement race: completion after a page snapshot must stay unseen.
- [x] Add consistent Navbar badges with focus/route refresh and no zero badges; acknowledge only observed completed job IDs.
- [x] Exercise batch stored/failed files, navigation, waiting configuration, 11+ chunks, version failure/success, reindex, deletion and historical citations against local services.
- [x] Run backend suite/ruff, frontend suite/lint/typecheck/build and migrate local services after backing up the database.
- [x] Update README and API/development baseline; inspect diff and report verified results and any remaining limitations.

## Completion record
Completed 2026-09-28: backend 149 passing tests with PostgreSQL integration; frontend 37 passing tests. Real MinIO/DashScope and browser acceptance: docs/knowledge-ingestion-acceptance-2026-09-28.md.
