# CodeAtlas

CodeAtlas 是面向 ACM/OI 学习者的私人知识库 AI 助教。当前已完成 Phase 1 账号与页面骨架，以及 Phase 2 会话与普通聊天基础链路。

## Docker 启动

要求：Docker Desktop 已启动。

```powershell
docker compose up --build
```

访问：

- 前端：http://localhost:3000
- 后端文档：http://localhost:8000/docs
- MinIO：http://localhost:9001

首次启动会自动执行 Alembic 数据库迁移。停止服务使用 `docker compose down`；数据保存在 Docker volumes 中。

## 配置

复制 `.env.example` 为 `.env`。普通聊天需要配置：

```env
DASHSCOPE_API_KEY=your-key
CHAT_MODEL=your-model
```

未配置模型时，会话和消息接口仍可用，但发送聊天请求会返回 `run.failed` 事件并说明缺少配置。

## 当前 API

API 前缀为 `/api/v1`。认证接口位于 `/auth`，会话接口位于 `/conversations`，聊天使用 `POST /conversations/{id}/messages/stream` 返回 SSE 事件。所有会话和消息接口要求 Bearer access token，并按当前用户隔离数据。

## 开发阶段

- Phase 1：账号、JWT、页面骨架，已完成
- Phase 2：会话 CRUD、消息持久化、普通模式 SSE、停止和恢复，开发中
- Phase 3：私人知识库 RAG
- Phase 4：ACM 分析与解题工作流
