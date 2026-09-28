# Grill: Knowledge ingestion lifecycle
Date: 2026-09-23

## Intent
Make long-term document ingestion truthful and observable from file transfer through parsing, chunking, embedding, index activation, version replacement, and deletion. Users should be able to leave the knowledge page after source files reach MinIO, then return to see durable progress and results.

## Constraints
- Do not change how questions retrieve or use knowledge in this design cycle.
- Do not implement business code until the user reviews the design.
- A browser navigation before every selected file finishes transfer interrupts only transfers that have not reached MinIO. Saved files continue in the background.
- New PDF uploads, PDF versions, PDF retries, and PDF reindexing are disabled until future OCR and multimodal work. Existing PDFs remain: indexed ones stay usable; failed ones may be downloaded or deleted.
- No separate pause or cancel control. Delete stops processing and starts cleanup.

## Key decisions
- Decision: Treat MinIO storage and searchable indexing as distinct milestones, with clear status text. Reason: `uploaded` currently appears even when embedding fails. Alternative considered: one generic uploaded state.
- Decision: Show exact transfer progress, stage labels during parsing, and completed/total chunk counts during embedding. Show 100% only after index commit. Reason: parsing has no reliable denominator. Alternative considered: one continuous estimated percentage.
- Decision: Persist processing status on the server and show processing, failed, and unseen completed counts in the global knowledge navigation item. Reason: users may leave the knowledge page after transfer and return later. Alternative considered: page-only status.
- Decision: Classify transient failures for automatic retry with timing; stop on permanent request errors with a readable reason and manual retry. Keep the source file for retry. Reason: repeated retries of a 400 cannot repair invalid input. Alternative considered: retry every failure.
- Decision: Keep the previous indexed version active while a new version processes. Switch only after the new index is complete. On success, remove the previous source file, extracted text, chunks, and vectors; retain only a concise, non-downloadable version record. On failure, keep the old version usable. Reason: preserve availability without accumulating obsolete content. Alternative considered: immediate switch or retaining historical source files.
- Decision: Deletion immediately excludes the document from retrieval, stops processing, then asynchronously removes source files, extracted text, chunks, and vectors. Retain minimal historical citation snapshots. Keep a visible deleting row until cleanup completes; show and retry cleanup failures. Reason: users need accurate deletion semantics and progress. Alternative considered: soft delete only.
- Decision: Allow multiple files per selection with independent progress and failures. A failed transfer can be retried while the local file remains selected; after navigation it must be selected again. Reason: independent tasks and a truthful safe-to-leave signal. Alternative considered: single-file upload.
- Decision: Choose the upload destination group explicitly, independent of the knowledge list filter. When a concrete group is open, default to it; from All, default to Ungrouped. Same-name conflicts are checked within the destination group. Reason: the list filter should not silently set the upload destination. Alternative considered: globally unique names or implicit destination.
- Decision: For a same-name conflict, explicitly choose new version or independent document. The new-version option warns that the old source is irrecoverably deleted after successful replacement. Independent documents get a timestamp in the displayed filename, MinIO filename, and download filename; existing names stay unchanged. Reason: avoid accidental overwrite and make duplicates recognizable. Alternative considered: automatic overwrite.
- Decision: For an identical name and identical content in the same group, default to skip duplicate storage and embedding while linking to the existing document; allow explicit independent creation. Reason: avoid accidental repeated work. Alternative considered: always reindex.
- Decision: Permit raw uploads without a verified embedding configuration, but show `saved, awaiting embedding configuration, not searchable` and start processing automatically after verification. Reason: users need not re-upload but must not mistake storage for readiness. Alternative considered: reject upload.
- Decision: Files with no effective indexable chunks cannot be marked searchable. Reason: an empty successful task would mislead users. Alternative considered: mark zero-chunk jobs indexed.

## Surfaced assumptions
- The project uses PostgreSQL with pgvector for vectors, MinIO for source objects, and Redis/Arq for background document jobs.
- The current document delete soft-deletes the document and later deletes MinIO objects, but does not remove stored chunks or vectors.
- The current default embedding request batch is 16 texts, while Alibaba Cloud documents at most 10 texts per request for `text-embedding-v3`; the precise 400 response body was not recorded.
- Group membership is an organization field in the current application; groups do not alter the current chat retrieval scope.

## Open questions
- The final architecture and screen-by-screen behavior remain subject to user review.
- The exact provider-side cause of every observed HTTP 400 requires the response body; batch size is a strong code-and-documentation-based candidate.

## Out of scope
- OCR and multimodal PDF ingestion.
- Redesigning the question-time retrieval and answer flow.
- Background persistence of browser-to-MinIO transfer across page navigation.
- Pause, resume, or cancel-but-keep-file actions.
