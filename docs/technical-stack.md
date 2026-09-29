# CodeAtlas 技术栈与运行架构

更新：2026-09-29。

| 层次 | 实现 |
|---|---|
| Web | Next.js 15、React 19、TypeScript、自定义 CSS |
| API | Python 3.11+、FastAPI、Pydantic、SQLAlchemy Async |
| 数据库 | PostgreSQL 16 / pgvector、Alembic |
| 后台任务 | 独立 Arq Worker、队列 Redis，任务载荷仅 ID |
| Agent | LangGraph 1.2.12 单图；checkpoint-postgres 3.1.2，只存控制状态 |
| 私有临时上下文 | 独立非持久 Redis，启动校验关闭 AOF/RDB |
| 长期原件 | S3 兼容存储，Compose 使用 MinIO |
| 模型 | OpenAI 兼容原生工具协议；用户/项目 Embedding；可选 Reranker |
| 环境 | Docker Compose；Windows 原生专用 API/Worker 入口 |

API 管理鉴权、模型能力、会话互斥与运行准入；数据库保存 queued 记录作为可靠投递来源。Worker 获取租约并准备历史、题面、临时全文与固定长期检索，再执行 model → tools → model。模型对话存在非持久共享缓存，检查点和队列不会保存正文。SSE 实时推送安全执行状态，最终正文校验后一次返回。

长期上传使用独立任务和 staging generation，原子切换完整索引。在线检索同时提供普通服务与两个只读工具；授权过滤在服务层执行，工具参数不允许指定用户。

配置与版本见 `.env.example`、`backend/pyproject.toml` 和 lock 文件。模型凭证加密密钥必须长期保留，轮换需要独立迁移。向量维度与数据库列必须一致。

Windows 原生启动：`uv run python -m app.api_runner` / `uv run python -m app.worker_runner`。启动不自动执行数据库迁移。没有 MCP、多 Agent、代码执行或联网工具。

详细模块图、时序、恢复及部署前置条件见 [实现说明](agent-rag-architecture.md)。
