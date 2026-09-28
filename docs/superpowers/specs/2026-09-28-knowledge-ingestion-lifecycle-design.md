# Knowledge ingestion lifecycle

Date: 2026-09-28. Status: approved in conversation; execution authorized.

## Scope and user contract
Extend the existing FastAPI/PostgreSQL/pgvector/MinIO/Redis/Arq pipeline. Store uploaded originals independently from searchable indexes. A document becomes searchable only after a nonempty, complete index transaction commits. Uploading, server storage, processing, failure, waiting for configuration, and deletion are distinct states.

Batch upload chooses its destination group independently from browsing filters. Each file has independent transfer progress, errors, and retry. Only a successful server acknowledgement means MinIO storage and durable task creation have completed. Navigation aborts unfinished transfers; acknowledged uploads continue. The batch shows safe-to-leave only when every selected file is acknowledged or intentionally skipped. Failed transfers require reselection after navigation.

Same-name conflicts are scoped to user and group, including Ungrouped. The user explicitly chooses new version or independent document. Same name and hash defaults to skip with a link. Independent files receive a Shanghai-time timestamp in the displayed name, MinIO basename and download filename, preserving extensions. Existing names are unchanged. A collision within a minute receives a numeric suffix.

New versions and reindexing retain the previous index until activation. On successful replacement, obsolete original files, extracted text, chunks and vectors are cleaned asynchronously. Concise version records remain without download or restoration. Failed replacement leaves the previous version intact.

Delete immediately excludes the document and cancels processing. A deleting row remains until all originals, extracted text, chunks and vectors have been cleaned. Cleanup failure is visible and retried. Citation snapshots retain source title, filename, locator and quoted excerpt independently of chunk existence.

PDF is removed from every new document upload entry. Existing indexed PDFs stay usable; existing failed PDFs may be downloaded/deleted but not retried or reindexed. No OCR, multimodal parsing, pause/resume, cross-page unfinished transfer, or query-time ranking/generation redesign.

## Architecture and persistence
`documents.current_version_id` is the active version pointer. `document_versions.active_index_job_id` selects the active chunk generation. Each indexing job owns staging chunks through `document_chunks.index_job_id`; activation changes pointers under a document row lock in one transaction. Batch commits never expose staging chunks. Existing indexes are backfilled to the latest successfully indexed version; legacy chunks have a null generation.

Document jobs persist stage, completed/total chunks, attempts, retry timing, errors and completion acknowledgement. Queue delivery uses distinct dispatch IDs while the database job state and row lock ensure idempotency. Workers check deletion/cancellation under the document lock before every write and activation. Expired leases are recovered. Transient errors retry; permanent errors stop. Empty chunks and vector count/dimension mismatches fail.

Version cleanup uses durable pending/error/timestamp fields and existing storage retry counters. Cleanup and indexing acquire the same document lock. Deletion and superseded-content cleanup run frequently and idempotently. A failed MinIO deletion does not remove the cleanup obligation.

The API returns latest version, active version, newest operation, deletion status and task summaries. Global navigation polls one lightweight user-scoped summary. Completed jobs are acknowledged only after the knowledge page has observed them. Knowledge list/detail poll while work is active; global summary refreshes on route and focus changes.

## UI
Empty knowledge pages hide zero statistics. List supported types and size, without a special PDF warning. Preserve current visual language and group behavior. Rows distinguish current usable version from processing replacement, show stage and real embedding counts, and offer view/retry/delete. Details show active preview/download, latest task timeline, upload version, reindex and concise history. A shared Navbar displays processing, failed and unseen-completed badges consistently across pages.

## Verification
Use test-first regressions for provider batching/errors, job delivery, zero-text handling, failure preserving active chunks, activation and cleanup, deletion during embedding, citation retention, group conflicts/duplicate hashes, PDF policy, batch transfer states and global summaries. Exercise real PostgreSQL/pgvector and MinIO with disposable fixtures; run frontend tests, lint, typecheck and build. Keep query-time changes limited to active-version/generation filtering and citation snapshot fallback.
