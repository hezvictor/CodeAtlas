# CodeAtlas 初版数据模型

数据库：PostgreSQL 16 + pgvector。ID 使用 UUID，时间统一存储 UTC。

## 1. 业务表

| 表 | 关键字段 |
|---|---|
| users | id, email unique, password_hash, nickname, avatar_url, created_at |
| refresh_tokens | id, user_id, token_hash, expires_at, revoked_at |
| conversations | id, user_id, title, mode, created_at, updated_at |
| messages | id, conversation_id, role, content, status, model, token_usage, created_at |
| attachments | id, conversation_id, user_id, object_key, filename, mime_type, size |
| knowledge_groups | id, user_id, name, description |
| documents | id, user_id, group_id, title, source_type, version, status, error_message |
| document_chunks | id, document_id, content, metadata jsonb, embedding vector |
| citations | id, message_id, chunk_id, rank, score |
| problems | id, user_id, title, slug, statement, input_spec, output_spec, constraints, tags jsonb |

## 2. 约束与索引

- `users.email` 唯一且统一小写。
- 所有用户资源带 `user_id`，删除用户时级联删除其资源。
- `messages(conversation_id, created_at)` 查询索引。
- `documents(user_id, group_id, status)` 过滤索引。
- `document_chunks` 使用 pgvector HNSW 或 IVFFlat 索引；embedding 维度由实际百炼模型确定。
- 引用保存检索时的 score 和 rank，便于调试回答质量。

## 3. 文档元数据

`document_chunks.metadata` 至少包含：`page`、`section`、`line_start`、`line_end`、`language`、`source_filename`。缺失字段使用 null，不伪造定位信息。

## 4. LangGraph 状态

图状态使用 thread ID 关联 `conversation_id`，由 PostgreSQL checkpointer 管理。业务表保存最终消息和运行状态，checkpointer 保存可恢复的中间状态，二者不互相替代。
