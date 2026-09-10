# CodeAtlas 当前开发基线

版本：0.2 · 日期：2026-09-09 · 状态：开发中

## 当前已实现

- Next.js 页面与公共导航：`/`、`/chat`、`/problems`、`/knowledge`、`/auth/login`、`/auth/register`、`/profile`。
- FastAPI 服务，API 前缀为 `/api/v1`，并提供 `/health`、`/api/v1/health`、`/ready`。
- 邮箱注册、登录、刷新 token、登出、当前用户查询、资料更新、密码修改和头像上传接口。
- Argon2 密码哈希、JWT access token、哈希存储的 refresh token。
- 会话创建、列表、详情、重命名、删除和消息列表。
- 普通模式聊天：调用百炼 OpenAI 兼容接口，以 SSE 增量返回回答并持久化消息。
- 运行互斥、停止信号、断开连接检测、过期运行清理，以及 `run/stop` 和 `run/resume` 接口。
- 前端登录态、聊天会话列表、首条消息自动命名、重命名、消息复制和全局错误提示。
- 聊天前端支持停止生成、历史消息分页加载、重新生成、编辑重试、失败/中断状态提示，以及模型耗时和首 token 时延展示。
- PostgreSQL + Alembic 迁移；Docker Compose 包含 PostgreSQL/pgvector、Redis、MinIO，但 Redis/MinIO 尚未接入业务流程。

## 当前未实现

- 题库和知识库页面仍为占位页。
- 文件上传、文档解析、切块、Embedding、pgvector 检索和引用展示。
- LangGraph、PostgreSQL checkpointer、真正的 checkpoint 恢复。
- ACM 分析/解题模式、语言选择和 `@` 题目引用。

## 本地运行

复制 `.env.example` 为 `.env`，至少配置 `JWT_SECRET_KEY`；需要真实模型回答时再配置 `DASHSCOPE_API_KEY` 和 `CHAT_MODEL`。

```powershell
docker compose up --build
docker compose --profile test run --rm backend-test
```

默认地址为前端 `http://localhost:3000`、后端 `http://localhost:8000`。不使用 Compose 时，后端先执行 `alembic upgrade head`，前端在 `frontend` 目录执行 `npm run dev`。

提交前请启用仓库钩子：`git config core.hooksPath .githooks`。钩子会拒绝暂存文件中的非法 UTF-8 和乱码字符，并要求含非 ASCII 字符的源码与文档以 UTF-8 BOM 保存。

## 后续阶段

Phase 3 接入私人知识库和 RAG；Phase 4 接入题库与 ACM 工作流。具体范围见 [roadmap.md](roadmap.md)。
