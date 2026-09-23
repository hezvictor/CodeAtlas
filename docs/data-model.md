# CodeAtlas 数据模型

更新：2026-09-23。当前数据库为 PostgreSQL + pgvector，ID 使用 UUID，时间字段使用 UTC。以下是概要，精确字段和约束以 `backend/app/models.py` 及 Alembic 迁移为准。

## 已实现表

| 表 | 关键字段 | 用途 |
|---|---|---|
| `users` | `id`, `email`, `password_hash`, `nickname`, `avatar_url` | 用户资料 |
| `refresh_tokens` | `id`, `user_id`, `token_hash`, `expires_at`, `revoked_at` | refresh token |
| `conversations` | `id`, `user_id`, `title`, `mode`, `created_at`, `updated_at` | 会话 |
| `messages` | `id`, `conversation_id`, `role`, `content`, `status`, `model`, `duration_ms`, `first_token_latency_ms` | 消息与模型耗时 |
| `problems` | `owner_user_id`, `source_type`, `slug`, `statement` | 用户题目与注册模板 |
| `model_connections`, `chat_models` | `user_id`, 加密模型凭证、验证状态 | 用户聊天模型配置 |
| `embedding_configs`, `reranker_configs` | `user_id`, 加密凭证、验证状态 | 用户检索模型配置 |

助手被停止时已生成内容会以 `cancelled` 状态保存。本项目记录模型耗时和首 token 延迟，不记录模型 token 用量统计。

## 约束

- 邮箱唯一，应用层按小写处理。
- 会话和消息查询强制带当前用户条件。
- 会话按更新时间倒序，消息按创建时间正序。
- 会话的 `mode` 字段保留兼容性；实际模式记录在每条消息上，支持 `normal`、`acm_analysis` 和 `acm_solution`。

## 已实现知识库模型

`knowledge_groups`、`documents`、`document_versions`、`document_chunks`、`attachments`、`citations` 和 `document_jobs` 已通过 `0004_knowledge_rag` 迁移创建。`0006_job_reliability` 为 `document_jobs` 增加投递尝试和错误记录，并限制同一版本只能有一个 `queued`/`running` 任务。`0010_knowledge_scope_and_model_config` 允许文档无分组；`0014_group_delete_set_null` 把删分组时的文档外键行为改为 `SET NULL`，保留文档。`document_chunks.embedding` 的 pgvector 维度必须与 `EMBEDDING_DIMENSIONS` 一致，应用启动时会校验；`search_vector` 使用 PostgreSQL 全文索引。文档版本状态为 `uploaded`、`parsing`、`chunking`、`embedding`、`indexed` 或 `failed`。

## 题目模型

`problems` 已通过 Phase 4 迁移加入。系统题目使用空 `owner_user_id` 作为注册模板；注册时复制为当前用户拥有的 `source_type=default` 题目，用户新建题目使用 `source_type=user`。题目 ID 使用 UUID，用户只能管理自己的题目。`messages.problem_id` 使用 `ON DELETE SET NULL`，删除题目不会破坏历史消息。

本阶段不引入 LangGraph checkpoints；checkpoint 属于后续单独阶段。
