# CodeAtlas

> 面向 ACM/OI 学习者的私人题库与知识库 AI 助教。

CodeAtlas 将账号体系、个人题库、普通聊天、ACM 分析/解题、长期资料管理与来源引用整合为统一的学习工作流。用户可以沉淀题目与学习资料，在对话中获得结合个人知识库的回答，并查看回答所依据的资料来源。

## 核心能力

- **个人题库与学习模式**：管理个人题目，在普通问答、ACM 分析和指定语言的 ACM 解题模式之间切换。
- **长期知识库**：支持 Markdown、DOCX、TXT、源码和 HTML；文件经异步解析、结构化分块、Embedding 和全文索引后，以原子方式切换为可检索版本。
- **可追溯的 RAG 回答**：每次聊天执行用户隔离的混合检索，最终答案携带真实来源引用。
- **会话临时资料**：临时文件全文仅写入独立的非持久 Redis，只用于当前会话，不建立长期索引或写入对象存储。
- **可靠运行反馈**：SSE 实时推送执行状态；停止、重连与有限恢复由 PostgreSQL 协调，且不持久化私有模型输入和工具结果。
- **模型配置**：支持 OpenAI 兼容的聊天、Embedding 与可选 Reranker 服务；模型连接通过实际聊天请求检测。

## 技术栈

| 模块 | 技术 |
| --- | --- |
| 前端 | Next.js 15、React 19、TypeScript、自定义 CSS |
| 后端 | Python 3.11+、FastAPI、Pydantic、SQLAlchemy Async |
| 数据与迁移 | PostgreSQL 16、pgvector、Alembic |
| 异步任务 | Arq Worker、Redis |
| Agent 运行时 | LangGraph、PostgreSQL checkpoint（仅控制状态） |
| 检索与存储 | 混合检索、S3 兼容对象存储、MinIO |
| 部署 | Docker Compose |

## Docker Compose 部署

### 前置条件

- Docker Engine 24+，并已安装 Docker Compose V2。
- 可访问 OpenAI 兼容的聊天与 Embedding 模型服务。示例默认使用阿里云百炼兼容接口，也可换为其他兼容服务。
- `3000`、`8000`、`9000` 与 `9001` 端口可用；如有冲突，请在 `.env` 中修改对应端口。

### 1. 无需配置环境变量

模型凭证不再通过环境变量下发，而是在页面上配置。Compose 已为数据库、MinIO、端口、JWT 与凭证加密密钥提供本地可用的默认值，因此**不需要先创建 `.env`**。

`DASHSCOPE_API_KEY`、`CHAT_MODEL`、`EMBEDDING_MODEL` 都不需要手动填写：聊天模型只使用模型配置页中添加并检测通过的连接；Embedding 使用页面上保存的百炼 Key。

### 2. 启动服务

```powershell
docker compose up -d --build
docker compose ps
```

Compose 会启动前端、FastAPI API、Arq Worker、PostgreSQL/pgvector、持久 Redis、临时 Redis 与 MinIO。后端启动时自动执行 `alembic upgrade head`，Worker 和前端会等待后端健康检查通过。

| 服务 | 地址 |
| --- | --- |
| Web 应用 | http://localhost:3000 |
| OpenAPI 文档 | http://localhost:8000/docs |
| MinIO 控制台 | http://localhost:9001 |

### 3. 日常运维

```powershell
# 查看全部服务或指定服务的日志
docker compose logs -f
docker compose logs -f backend
docker compose logs -f worker

# 更新代码后重建服务
git pull --ff-only
docker compose up -d --build

# 停止容器并保留数据卷
docker compose down
```

不要执行 `docker compose down -v`，该命令会删除 PostgreSQL、Redis 和 MinIO 数据卷。更新已有环境前，请备份数据卷，并保留原 `JWT_SECRET_KEY` 与 `MODEL_CREDENTIAL_ENCRYPTION_KEY`；否则已有登录状态或已保存的模型凭证将无法正常使用。

## 当前实现

- 长期资料在知识库页面上传：MinIO 原件 → 后台解析、结构分块、Embedding → PostgreSQL/pgvector 与全文索引；完整提交后才切换可检索版本。
- 每次聊天固定执行一次用户隔离的长期混合检索；已验证工具能力的旧模型可以按需通过两个只读工具补查。不存在手动知识库开关或聊天长期资料关联入口。
- 临时文件解析全文直接进入当前会话上下文，只放在独立非持久 Redis；不创建知识库文档、版本、索引，不写 MinIO。已知容量不足时提前拒绝，容量未知时由服务商判断。
- 模型配置发送一次普通聊天请求检测连接；通过后即可进入聊天模型列表，无需填写上下文容量。仅旧模型已验证的工具能力可用于补查。
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

PostgreSQL/Redis 集成测试使用 `infra/compose.agent-test.yml` 的独立测试环境。支持 Markdown、DOCX、TXT、源码和 HTML；项目不提供 PDF 解析，解析器及相关依赖已移除。不支持 OCR、代码执行、联网搜索、MCP 或多 Agent。测试响应验证调用协议与恢复机制，真实模型的教学质量仍需要单独评测。

不要使用 `docker compose down -v` 清理现有环境，该操作会删除数据卷。历史设计与开发计划保留在 docs/superpowers/；其中路径和测试结果描述的是当时版本，不能直接当作当前执行步骤。
