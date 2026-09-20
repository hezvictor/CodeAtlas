# Knowledge Scope and User Model Configuration Design

**Date:** 2026-09-20  
**Status:** Approved in conversation, pending written review  
**Scope:** CodeAtlas knowledge retrieval, chat attachments, and user-configured chat providers

## 1. Goals

CodeAtlas will treat user documents as either long-term personal knowledge or conversation-scoped temporary files. Every chat request will automatically search both the user's indexed long-term documents and the current conversation's indexed temporary attachments. The chat page will show manageable temporary files separately from sources actually cited by the current answer.

CodeAtlas will also support multiple user-owned OpenAI-compatible chat connections. A connection contains a base URL and an encrypted API key. Models can be discovered from `/models` or added manually, but only models that pass a server-side test request are available in chat. Chat configuration is isolated from the fixed DashScope embedding configuration.

## 2. Product Rules

### 2.1 Knowledge and files

- Long-term files are uploaded from the knowledge page and are searchable in every conversation owned by the user.
- Temporary files are uploaded from a conversation, are automatically attached to that conversation, and remain active until the user removes them.
- The chat header has no knowledge toggle and no knowledge-group selector.
- Retrieval is automatic. The effective scope is the union of all indexed long-term files and indexed attachments for the current conversation.
- Temporary files are favored when relevance is tied, but both source types are subject to the same context budget.
- The right sidebar has two independent sections: `session files` and `answer citations`.
- The first section lists all temporary files available to the conversation, including processing and failure states, with upload and delete controls.
- The second section lists only validated citations from the current assistant message, with source type and PDF page, section, or code-line locator.
- Removing a temporary attachment prevents future retrieval but does not erase historical citation evidence.
- If no embedding key exists, normal chat remains usable without RAG and must state that the answer did not use knowledge-base material.

### 2.2 Chat models

- There is no system default chat model. A user must configure and validate one before sending chat messages.
- Users may save multiple connections. Each connection has a display name, backend-reachable base URL, and encrypted API key.
- `/models` discovery is optional. Discovery failure does not prevent manually entering a model name.
- A discovered or manually entered model starts as unverified. A server-side minimal streaming chat request must succeed before it is selectable.
- The model configuration page owns connection creation, editing, deletion, discovery, manual model entry, testing, and default selection.
- The chat page only selects from verified models and never receives or edits credentials.
- A global personal default is used for new conversations. A conversation may override it; the override persists for later messages in that conversation.
- Deleting a connection or changing its credentials invalidates its models. Existing message history retains model snapshots; future sends using an unavailable model require explicit reselection.
- The first version supports text messages and streaming only. It does not promise multimodal input, tools, audio, video, or provider-specific parameters.

### 2.3 Embeddings

- Embedding configuration is separate from chat connections.
- The user supplies a DashScope API key in the configuration page.
- The embedding model name and vector dimension remain fixed by the application configuration (`vector(1024)`). Users cannot select arbitrary embedding models in this version.
- Changing a chat connection never changes document embeddings.
- Without a valid embedding key, uploads may be stored but remain waiting for indexing; they must not be presented as usable RAG sources.

## 3. Architecture

### 3.1 Provider boundary

Business code depends on provider interfaces rather than HTTP details:

```text
ChatProvider
  stream_chat(messages, model, stop_event) -> async text deltas
  list_models() -> normalized model candidates
  test_model(model) -> validation result

EmbeddingProvider
  embed_documents(texts) -> vectors
  embed_query(text) -> vector
```

The chat implementation uses an OpenAI-compatible adapter. The embedding implementation remains a fixed DashScope adapter and loads the authenticated user's embedding configuration when indexing or retrieving.

### 3.2 Retrieval flow

```text
chat request
  -> resolve verified chat model
  -> load indexed long-term chunks for the user
  -> load indexed chunks from current conversation attachments
  -> keyword + vector retrieval per pool
  -> merge with source-aware tie breaking and context budget
  -> generate with the selected ChatProvider
  -> validate citations against retrieved chunks
  -> persist message model snapshot and citations
```

No client-supplied base URL, API key, group ID, or arbitrary model name is trusted by the chat endpoint. The client supplies a verified chat-model identifier and the server resolves all provider credentials and scope filters.

### 3.3 Credential security

API keys are encrypted at rest with an application master key held outside the database. The backend decrypts them only for outbound provider requests. API responses, browser storage, logs, traces, and SSE events never contain plaintext keys. User-supplied provider URLs are normalized and checked for an allowed scheme and SSRF targets before discovery, testing, or generation.

## 4. Data Model Changes

- `documents.scope`: `long_term` or `session`; existing grouped documents are backfilled to `long_term`.
- `documents.group_id`: no longer required for new uploads; legacy group data is not exposed in the product UI.
- `attachments`: remains the conversation-to-document-version association for temporary files.
- `citations`: stores enough document metadata and source scope to render historical citations after a document is soft-deleted.
- `model_connections`: user, name, normalized base URL, encrypted key material, status, and timestamps.
- `chat_models`: connection, model name, discovery source, verification status, last test result, and timestamps.
- `users` or a one-to-one `embedding_configs` table: encrypted DashScope embedding key, fixed model metadata, status, and timestamps.
- `conversations.selected_chat_model_id`: nullable conversation override.
- `messages`: provider/connection/model identifiers and model-name snapshot; existing `model` remains compatible where practical.

Connection/model deletion uses soft invalidation or nullable references so historical messages remain readable. Temporary document removal detaches the conversation and soft-deletes future retrieval while preserving citation snapshots.

## 5. API Surface

### Model configuration

- `GET/POST/PATCH/DELETE /model-connections`
- `POST /model-connections/{id}/discover-models`
- `POST /model-connections/{id}/models`
- `POST /model-connections/{id}/models/{model_id}/test`
- `PATCH /model-connections/{id}/models/{model_id}/default`
- `GET /chat-models` returns only verified models safe for chat selection.
- `GET/PATCH /embedding-config` and `POST /embedding-config/test` manage the separate DashScope key.

### Knowledge and chat

- Long-term document upload no longer requires a group.
- `POST /conversations/{id}/attachments/upload` creates and attaches a session-scoped document.
- Existing attachment list/delete operations remain conversation-scoped and gain filename/status metadata.
- `ChatRequest` accepts `chat_model_id`; knowledge-group and client-controlled retrieval-scope fields are removed or ignored after migration.

## 6. Error and State Rules

- No verified chat model: chat history is readable, but sending is disabled with a configuration link.
- No embedding configuration: normal generation continues with a visible no-RAG warning; indexing waits.
- `/models` unavailable: show a recoverable discovery error and keep manual entry available.
- Model test failure: preserve the model as unverified with a safe, classified error message.
- Provider failure during chat: persist the failure without exposing credentials; do not silently switch models.
- File processing states remain visible. Processing or failed files are excluded from retrieval until indexed.
- Citation validation only accepts chunks retrieved for that request.

## 7. Verification

Backend tests cover migrations, encrypted-secret handling, URL/SSRF validation, user isolation, provider normalization, discovery fallback, model testing, default and conversation model selection, embedding configuration, long-term/session retrieval scope, temporary upload/delete, citation retention, and graceful no-RAG behavior.

Frontend tests cover masked credential forms, connection/model status transitions, manual model entry, grouped verified-model selection, disabled chat states, temporary upload progress, delete confirmation, sidebar source separation, and citation metadata.

Integration and browser tests cover a full flow: configure and test a chat model, configure Embedding, upload a long-term file, upload a session file, ask a question, verify citations, remove the session file, and verify that future retrieval excludes it while the historical citation remains visible.

## 8. Out of Scope

Provider-specific adapters beyond the OpenAI-compatible text protocol, multimodal messages, tools/function calling, arbitrary embedding-model selection, shared/public knowledge bases, and unrelated ACM or authentication redesign are not part of this work.
