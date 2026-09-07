# CodeAtlas Phase 1 基线

版本：1.0 · 日期：2026-09-07 · 状态：开发中

## 当前范围

- 顶部导航与 Next.js 路由骨架：`/`、`/chat`、`/problems`、`/knowledge`、`/auth/login`、`/auth/register`。
- 用户注册、登录、刷新、登出和当前用户查询。
- PostgreSQL `users`、`refresh_tokens` 表及 Alembic 初始迁移。
- Argon2 密码哈希、JWT access token、哈希存储的 refresh token。
- 前端登录态展示、用户菜单入口和未登录时的登录/注册入口。

## 后续阶段

会话 CRUD、聊天 SSE、知识库上传、RAG、题库和 ACM 工作流留待后续 Phase。

## 运行

复制 `.env.example` 为 `.env`，启动依赖后分别运行后端和前端。迁移命令：`cd backend; alembic upgrade head`。
