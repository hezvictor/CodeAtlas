# CodeAtlas

面向 ACM/OI 学习者的个人题库与知识库 AI 助教。CodeAtlas 将题目管理、资料沉淀、智能对话、ACM 分析与可追溯引用整合到一个学习工作流中，帮助用户基于自己的题目和资料进行持续学习。

## 核心能力

- **个人题库与学习模式**：管理个人题目，并在普通问答、ACM 分析和指定语言解题模式之间切换。
- **长期知识库**：支持 Markdown、DOCX、TXT、源码和 HTML 等资料上传，经过异步解析、结构化分块、Embedding 与索引后用于检索。
- **可追溯的 RAG 对话**：执行用户隔离的混合检索，回答携带实际资料来源引用，方便回看依据。
- **会话临时资料**：临时上传内容仅用于当前会话，不进入长期知识库、不写入对象存储。
- **实时运行反馈**：通过 SSE 展示对话执行进度，支持停止、重连与有限恢复。
- **模型连接管理**：支持 OpenAI 兼容的聊天、Embedding 和可选 Reranker 服务，并可在页面中检测模型连接能力。

## 技术栈

| 模块 | 技术 |
| --- | --- |
| 前端 | Next.js 15、React 19、TypeScript、自定义 CSS |
| 后端 | Python 3.11+、FastAPI、Pydantic、SQLAlchemy Async |
| 数据库 | PostgreSQL 16、pgvector、Alembic |
| 异步任务 | Arq Worker、Redis |
| Agent 运行时 | LangGraph、PostgreSQL checkpoint（仅保存运行控制状态） |
| 检索与文件存储 | 混合检索、S3 兼容对象存储、MinIO |
| 部署 | Docker Engine、Docker Compose V2 |

## Docker 部署

以下步骤以 Ubuntu/Debian 等 Linux 服务器为例。项目使用 Docker Compose 一次启动前端、API、后台 Worker、PostgreSQL/pgvector、Redis、临时 Redis 和 MinIO。

### 1. 验证 Docker 环境

默认部署环境已经安装 Docker Engine 和 Docker Compose V2。开始部署前，使用以下命令确认 Docker 已安装并且当前用户可以运行容器：

```bash
docker -v
docker compose version
docker run --rm hello-world
```

如果 `docker run` 因权限不足失败，请先确保当前 Linux 用户具有 Docker 使用权限，然后重新登录服务器再继续部署。

### 2. 获取项目代码

```bash
git clone https://github.com/hezvictor/CodeAtlas.git
cd CodeAtlas
```

如果服务器已有项目目录，则进入该目录即可：

```bash
cd /path/to/CodeAtlas
```

### 3. 配置部署参数

项目默认允许直接启动，Compose 会为本地部署提供数据库、MinIO、JWT 和模型凭证加密密钥的默认值，因此首次部署可以不创建 `.env` 文件。

生产环境或已有数据的环境建议创建并修改 `.env`：

```bash
cp .env.example .env
sed -i "s/^JWT_SECRET_KEY=.*/JWT_SECRET_KEY=$(openssl rand -hex 32)/" .env
sed -i "s/^MODEL_CREDENTIAL_ENCRYPTION_KEY=.*/MODEL_CREDENTIAL_ENCRYPTION_KEY=$(openssl rand -hex 32)/" .env
```

请注意：

- 已有部署必须保留原来的 `JWT_SECRET_KEY` 和 `MODEL_CREDENTIAL_ENCRYPTION_KEY`，否则已有登录状态和已保存的模型凭证会失效。
- 生产环境应修改 `POSTGRES_PASSWORD`、`MINIO_ROOT_PASSWORD` 等默认凭证，并限制数据库、Redis 和 MinIO 管理端口的网络访问。
- 聊天模型连接和 Embedding 配置在 Web 应用的模型设置页面中完成，不需要把模型 API Key 写入 `.env`。
- 如果修改前端访问 API 的地址，请在 `.env` 中设置 `NEXT_PUBLIC_API_BASE_URL`，然后重新构建前端镜像。

### 4. 检查 Compose 配置并启动

启动前可先检查 Compose 配置是否有效：

```bash
docker compose config
```

构建并后台启动全部服务：

```bash
docker compose up -d --build
```

查看服务状态：

```bash
docker compose ps
```

后端容器启动时会自动执行数据库迁移；Worker 和前端会等待后端健康检查通过后再启动。首次构建需要下载基础镜像和项目依赖，请耐心等待。

### 5. 访问应用并配置模型

默认地址如下：

| 服务 | 地址 |
| --- | --- |
| Web 应用 | http://服务器IP:3000 |
| OpenAPI 文档 | http://服务器IP:8000/docs |
| MinIO 控制台 | http://服务器IP:9001 |

首次打开 Web 应用后：

1. 注册并登录账号。
2. 打开模型设置页面。
3. 添加并检测 OpenAI 兼容的聊天模型连接。
4. 配置并检测 Embedding 服务。
5. 返回聊天或知识库页面开始使用。

如果只在服务器本机访问，可将地址中的 `服务器IP` 替换为 `localhost`。如果从其他机器访问，请确保服务器防火墙和云安全组放行实际使用的端口。

## 日常运维

```bash
# 查看全部服务状态
docker compose ps

# 查看全部服务日志
docker compose logs -f

# 查看指定服务日志
docker compose logs -f backend
docker compose logs -f worker
docker compose logs -f frontend

# 更新代码并重新构建
git pull --ff-only
docker compose up -d --build

# 停止容器但保留数据卷
docker compose down

# 重启服务
docker compose restart
```

检查 API 是否就绪：

```bash
curl --fail http://localhost:8000/ready
```

不要对已有环境执行 `docker compose down -v`，该命令会删除 PostgreSQL、Redis 和 MinIO 数据卷。升级已有部署前请先备份数据，并确认密钥与 `.env` 配置保持不变。

## 目录结构

```text
.
├── backend/              # FastAPI API、Agent 运行时、数据库迁移和后台任务
├── frontend/             # Next.js Web 应用
├── infra/minio/          # MinIO 镜像构建配置
├── docker-compose.yml    # 完整 Docker Compose 部署编排
└── .env.example          # 环境变量示例
```

## 相关文档

- [技术栈与运行架构](docs/technical-stack.md)
- [Agent 与 RAG 实现说明](docs/agent-rag-architecture.md)
- [API 契约](docs/api-contract.md)
- [产品需求说明](docs/product-requirements.md)
