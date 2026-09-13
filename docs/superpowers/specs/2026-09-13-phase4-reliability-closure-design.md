# Phase 4 Reliability Closure Design

## Goal

Close the existing CodeAtlas Phase 4 workflow by making authentication revocation, private knowledge retrieval, conversation context, attachments, document lifecycle, model calls, deployment configuration, and verification consistent and production-safe. Future capabilities such as online compilation, OJ evaluation, OCR, URL fetching, rerank, and checkpoint recovery remain out of scope.

## Scope and Constraints

- An empty knowledge-group selection and an empty attachment selection mean that retrieval is skipped completely.
- Retrieval must be limited to the authenticated user, and attachment retrieval must also be limited to the active conversation.
- Document deletion hides the document immediately and schedules object cleanup; cleanup failures are recorded and retried.
- Avatar replacement activates the new object before deleting the old object.
- Existing uncommitted Phase 4 work is preserved; unrelated refactors are excluded.
- `resume` continues to mean generating from persisted messages, not checkpoint restoration.
- Existing SSE event names and response contracts remain compatible unless a new field is additive.

## Design

### Authentication

Add a durable `auth_version` integer to `users`. Access tokens contain the user id, token type, issued-at time, expiry, a token id, and the current authentication version. `current_user_id` verifies the signature, token type, UUID, and version against the current user record. Logout revokes the presented refresh token and increments the user version. Password changes revoke all active refresh tokens and increment the version. Refresh token hashes remain the only persisted token material. A scheduled cleanup removes expired or revoked refresh-token records according to the configured retention period.

### Retrieval and attachment isolation

`retrieve_chunks` receives `conversation_id` in addition to user, query, group ids, and attachment ids. It returns an empty list without invoking the embedding provider when both scopes are empty. Group filters require the current user and non-deleted, indexed documents. Attachment filters require the current user, the active conversation, a non-deleted document, and an indexed version. Duplicate identifiers are normalized before querying. The chat route reports retrieval status through the existing SSE events and never falls back to unrestricted retrieval after a scoped retrieval failure.

### Conversation context

The chat page treats problem, mode, solution language, citations, pagination state, and attachments as conversation-scoped state. Switching or creating a conversation clears that state before loading the new conversation. Only messages from the active conversation may restore problem context. Async loads carry the conversation id they started for and cannot overwrite state after the user switches conversations.

### Attachments and documents

The chat page uses the existing attachment endpoints to list, attach, and detach indexed document versions. Uploading from chat reuses the knowledge-document upload flow and attaches the resulting indexed version. The knowledge detail page exposes preview, download, delete, retry, reindex, re-upload as a new version, and version history. A new version preserves the document id and increments `version_no`; the existing create-document endpoint continues to create a new document.

### Object cleanup

Document versions gain idempotent storage-cleanup metadata: deletion timestamp, attempt count, and last error. A worker/cron task scans versions belonging to soft-deleted documents, deletes their MinIO objects through `S3Storage.delete`, treats missing objects as success, and applies bounded retry backoff. The database remains the source of business visibility. Avatar uploads are stream-limited, signature-validated for JPEG/PNG/WebP, and use private or short-lived access URLs. Replacing an avatar deletes the previous object after the new record is committed.

### Embedding and context budgets

Embedding requests use explicit connect/read timeouts and bounded exponential backoff for 429, 5xx, timeout, and transient network failures. Other 4xx responses fail immediately. Retry count and timing are logged, and Worker retries are kept bounded so Provider and Worker retries cannot multiply without limit. Chat history and retrieved chunks are trimmed against configured character/token budgets, with deterministic ordering and adjacent-chunk deduplication while retaining the current prompt.

### Distributed run state

Conversation generation uses a Redis lease keyed by conversation id, with an owner token and expiry. Stop requests write a short-lived stop signal that any backend instance can observe. Lease release is owner-checked and idempotent. This removes the current multi-worker dependence on process-local `asyncio` state without introducing LangGraph or checkpoint persistence.

### Deployment configuration

Compose injects PostgreSQL, Redis, MinIO, JWT, model, upload, retry, and frontend API settings from environment variables. Container-internal service URLs are separate from browser-reachable URLs. Production rejects development credentials and a browser API URL containing `localhost`. MinIO management ports are optional for production. `.env.example`, Dockerfiles, README, and baseline records describe the same variables and defaults.

## Error handling

- Authentication failures return the existing 401 contract and do not reveal whether a token was revoked or expired.
- Cross-user and cross-conversation resources return 404, matching existing ownership semantics.
- Scoped retrieval failures emit `retrieval.failed` and terminate the run without calling the chat model.
- Object-storage cleanup is asynchronous and observable through stored attempt/error fields.
- Provider failures emit the existing `run.failed` event and persist a failed assistant message with timing metrics.
- All retries have finite limits and leave a durable failure state when exhausted.

## Verification

Backend tests cover token-version invalidation, refresh rotation, empty-scope retrieval skipping, cross-user and cross-conversation attachment isolation, document versions, storage cleanup retry, avatar validation, embedding retry classification, context budgets, and Redis run leases. Integration tests exercise real PostgreSQL, MinIO, Redis, and the document Worker. Frontend checks cover conversation switching, problem restoration, ACM language selection, attachment attach/detach, document lifecycle actions, and desktop/mobile builds. Compose health checks and production-style environment validation are part of acceptance.

## Acceptance criteria

1. A normal chat request with no knowledge-group or attachment scope performs no document query and no embedding call.
2. An attachment from another conversation cannot affect retrieval, even for the same user.
3. Logout and password change immediately invalidate previously issued access tokens.
4. Switching conversations cannot reuse a previous conversation's problem, mode, language, citations, or attachments.
5. Documents support upload, indexing, preview, download, retry, reindex, version history, re-upload, delete, and object cleanup with retry.
6. Chat attachments can be listed, mounted, detached, and sent through the existing SSE workflow.
7. Embedding and chat failures are bounded, observable, and persisted consistently.
8. Compose configuration works without hard-coded credentials or browser-localhost assumptions in production.
9. Backend tests, frontend production build, service health checks, and the documented integration/browser matrix pass.

