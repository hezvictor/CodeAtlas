# CodeAtlas 技术栈与运行架构

更新：2026-09-23。以下以当前代码为准。

| 层次 | 当前实现 | 位置 |
|---|---|---|
| Web | Next.js 15、React 19、TypeScript、自定义 CSS | `frontend/src/app/`、`frontend/src/components/` |
| API | Python 3.11+、FastAPI、Pydantic、SQLAlchemy Async | `backend/app/main.py`、`backend/app/routers/` |
| 持久化 | PostgreSQL 16 + pgvector、Alembic | `backend/app/models.py`、`backend/migrations/` |
| 后台任务 | Redis + Arq | `backend/app/worker.py`、`backend/app/tasks/` |
| 文件 | S3 兼容存储；Compose 开发环境使用 MinIO | `backend/app/storage/` |
| 模型 | 用户配置的 OpenAI 兼容聊天连接；项目或用户配置的 Embedding；可选 Reranker | `backend/app/providers/`、`backend/app/routers/model_connections.py` |
| 部署 | Docker Compose | `docker-compose.yml` |

## 请求与数据流

浏览器经 Bearer token 调用 FastAPI。聊天请求先校验用户、题目和模型；`knowledge_scope=all` 时执行用户隔离的检索，然后持久化用户消息与助手占位消息，启动后端持有的生成任务，以 SSE 推送状态、增量、最终内容和引用。Redis 租约用于跨进程互斥与停止信号；运行记录和 SSE 订阅仍位于任务所属进程内。结果会写入 PostgreSQL，断线后可从消息接口读取。

上传文档写入 MinIO 并创建文档任务；Arq Worker 完成解析、切块、Embedding 和索引。检索结合全文与向量召回，并可选重排。文档分组是管理字段，不参与聊天检索过滤。会话关联的文件与用户长期资料均受用户 ID 限制。

## 凭证与配置

`.env.example` 给出配置项。`JWT_SECRET_KEY` 用于签发 JWT，`MODEL_CREDENTIAL_ENCRYPTION_KEY` 用于加密用户模型密钥；两者必须在生产环境设置为长期保存的随机密钥。聊天模型可在“模型配置”页面添加和验证。项目默认 Embedding 使用 `DASHSCOPE_API_KEY`、`DASHSCOPE_BASE_URL`、`EMBEDDING_MODEL`；用户配置并验证 Embedding 后可覆盖项目默认值。`EMBEDDING_DIMENSIONS` 必须与数据库向量列一致，启动时会检查。

当前没有 LangGraph、PostgreSQL checkpoint、在线编译评测或模型 token 用量统计。`resume` 使用持久化消息发起下一次请求，不能继续已经结束或因后端重启中断的模型流。更多实际接口与限制见 [API 契约](api-contract.md) 和 [开发基线](development-baseline.md)。
