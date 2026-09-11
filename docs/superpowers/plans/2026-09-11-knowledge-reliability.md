# Knowledge Reliability Improvements Implementation Plan

> **For agentic workers:** Execute this plan inline with a test-first cycle and review checkpoints.

**Goal:** Make private document delivery, indexing jobs, embedding configuration, and retrieval failures observable and safe under retries.

**Architecture:** Keep PostgreSQL as the source of truth. `DocumentJob` also acts as the durable outbox; Arq receives a stable job ID, while a periodic dispatcher retries jobs that were committed but not delivered. API S3 operations use the internal endpoint and presigning uses a browser-reachable endpoint.

**Tech Stack:** FastAPI, SQLAlchemy Async, Alembic, PostgreSQL/pgvector, Redis/Arq, MinIO/S3, pytest.

**Spec:** `docs/superpowers/specs/2026-09-11-private-knowledge-rag-design.md`

## Global Constraints

- One active (`queued` or `running`) document job is allowed per document version.
- Job delivery is at-least-once and task execution must be idempotent.
- Embedding dimensions must match configuration, provider output, and PostgreSQL.
- Retrieval failures are explicit; ordinary chat may continue only when no knowledge scope was requested.
- Existing user ownership filters and API compatibility remain intact.

### Task 1: S3 presign and job delivery contract

Modify `backend/app/storage/s3.py`, `backend/app/queue.py`, and the document routes. Add tests for browser-endpoint signing, stable Arq job IDs, and dispatch failure persistence.

### Task 2: Durable outbox and idempotent worker

Modify `backend/app/models.py`, `backend/app/tasks/document_tasks.py`, `backend/app/worker.py`, and add an Alembic migration. Add partial uniqueness, atomic job claiming, periodic dispatch, and duplicate-delivery tests.

### Task 3: Embedding and retrieval error contracts

Add startup dimension validation, explicit retrieval failure signaling, and tests for mismatch and scoped retrieval failure behavior.

### Task 4: Integration verification

Extend Compose configuration and tests for real PostgreSQL, Redis, and MinIO. Use a fake embedding/chat service for deterministic tests and cover cross-user access, download URLs, retries, and concurrent job delivery.
