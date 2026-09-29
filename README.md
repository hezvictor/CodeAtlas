# CodeAtlas

CodeAtlas 是面向 ACM/OI 学习者的私人题库与知识库 AI 助教。账号、题库、普通聊天、ACM 分析/解题、长期资料管理与来源引用共用统一学习流程。

## 当前实现

- 长期资料在知识库页面上传：MinIO 原件 → 后台解析、结构分块、Embedding → PostgreSQL/pgvector 与全文索引；完整提交后才切换可检索版本。
- 每次聊天固定执行一次用户隔离的长期混合检索；LangGraph 单 Agent 可以按需通过两个只读工具补查。不存在手动知识库开关或聊天长期资料关联入口。
- 临时文件解析全文直接进入当前会话上下文，只放在独立非持久 Redis；不创建知识库文档、版本、索引，不写 MinIO。容量不足明确拒绝。
- 模型配置实际验证普通聊天、原生工具调用、工具结果回传；三项通过才能进入聊天模型列表。上下文容量需按服务商规格填写。
- SSE 实时显示可折叠执行状态，答案通过引用与临时内容校验后返回；不展示模型隐藏思维链。
- 后台运行状态及预算由 PostgreSQL 管理；停止、重连和有限恢复跨 API/Worker 实例工作。私有模型输入和工具结果不进入持久检查点。

流程、默认参数、失败恢复及数据期限见 [实现说明](docs/agent-rag-architecture.md) 和 [交互架构图](docs/codeatlas-architecture.html)。接口见 [API 契约](docs/api-contract.md)。

## 运行准备

复制 `.env.example` 为 `.env`，填写数据库、MinIO、JWT 与模型凭证加密密钥；保留既有环境的密钥与数据卷。新增 `EPHEMERAL_REDIS_URL` 必须指向独立 Redis 服务器，关闭 AOF/RDB。Compose 已给出该服务。

Docker 后端启动时会先执行 `alembic upgrade head`，成功后再启动 API；Worker 和前端等待后端健康后启动。更新已有环境前请备份数据库，然后执行：

```powershell
docker compose up --build
```

迁移 `0016_agent_runtime` 保留旧资料与关联历史，不将其自动转换为新临时文件。已有模型须重新完成能力检测。Windows/Linux 原生运行时仍须先手动执行 `alembic upgrade head`。

前端默认 `http://localhost:3000`；API 文档 `http://localhost:8000/docs`。Windows 原生 API 使用 `uv run python -m app.api_runner`，Worker 使用 `uv run python -m app.worker_runner`；Linux/Docker 使用 Uvicorn 与 Arq。

## 本地验证

```powershell
cd backend
uv run python -m pytest -q -p no:cacheprovider
uv run ruff check app tests --no-cache

cd ../frontend
npm test
npm run lint
npm run typecheck
npm run build
```

真实 PostgreSQL/Redis 的隔离测试方式见 [验收记录](docs/agent-rag-acceptance.md)。支持 Markdown、DOCX、TXT、源码和 HTML；本次不新增 PDF/OCR、代码执行、联网搜索、MCP 或多 Agent。测试响应验证调用协议与恢复机制，真实模型的教学质量仍需要单独评测。

不要使用 `docker compose down -v` 清理现有环境，该操作会删除数据卷。既有 Docker 数据盘迁移及长期资料验收记录仍保留供查阅。
