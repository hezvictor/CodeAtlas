# CodeAtlas 数据模型

当前数据库为 PostgreSQL，ID 使用 UUID，时间字段使用 UTC。实际迁移目前只创建账号、refresh token、会话和消息相关表。

## 已实现表

| 表 | 关键字段 | 用途 |
|---|---|---|
| `users` | `id`, `email`, `password_hash`, `nickname`, `avatar_url` | 用户资料 |
| `refresh_tokens` | `id`, `user_id`, `token_hash`, `expires_at`, `revoked_at` | refresh token |
| `conversations` | `id`, `user_id`, `title`, `mode`, `created_at`, `updated_at` | 会话 |
| `messages` | `id`, `conversation_id`, `role`, `content`, `status`, `model`, `duration_ms`, `first_token_latency_ms` | 消息与模型耗时 |

助手被停止时已生成内容会以 `cancelled` 状态保存。模型耗时字段将在普通聊天完善阶段补充；本项目不记录模型 token 用量统计。引用字段在知识库接入时再确定。

## 约束

- 邮箱唯一，应用层按小写处理。
- 会话和消息查询强制带当前用户条件。
- 会话按更新时间倒序，消息按创建时间正序。
- 模式仅支持 `normal`。

## 规划模型

尚未建立迁移或 ORM 实体：`attachments`、`knowledge_groups`、`documents`、`document_chunks`、`citations`、`problems`、LangGraph checkpoints。接入知识库时再确定 embedding 维度、向量索引、版本和级联规则。
