# CodeAtlas

CodeAtlas 是面向 ACM/OI 学习者的私人题库与知识库 AI 助教，仍在开发中。前端使用 Next.js 15、React 19 和 TypeScript；后端使用 FastAPI、PostgreSQL/pgvector、Redis/Arq 和 MinIO。当前代码包含账号、题库、会话聊天、模型连接配置、文档索引与 RAG 检索、ACM 分析和解题模式。

## 快速启动

1. 复制 `.env.example` 为 `.env`，设置随机的 `JWT_SECRET_KEY` 与 `MODEL_CREDENTIAL_ENCRYPTION_KEY`，并修改数据库和 MinIO 密码。不要提交 `.env`。
2. 启动 Docker Desktop，执行 `docker compose up --build`。后端容器启动时执行 Alembic 迁移。
3. 打开 `http://localhost:3000`；API 文档位于 `http://localhost:8000/docs`，MinIO 控制台位于 `http://localhost:9001`。可用 `FRONTEND_PORT` 修改前端宿主机端口，同时调整 `FRONTEND_URL`。

首次登录后在“模型配置”中添加并验证聊天模型，聊天才可生成回答。知识库检索需要已索引文档和可用的 Embedding 配置：可在项目环境中设置 `DASHSCOPE_API_KEY`、`EMBEDDING_MODEL`，或配置并验证用户自己的 Embedding 连接。Reranker 是可选项；未配置或失败时使用原有混合检索顺序。

## 当前功能与边界

- 会话支持重命名、置顶、多选、消息分页、编辑重试、重新生成、停止和同一后端进程内的流重连。`POST /run/resume` 仅表示下一次请求使用已保存的消息，不是断点续算。
- 聊天知识库范围只有 `none` 和 `all`。`none` 不检索；`all` 检索当前用户已索引的长期资料与本会话关联的资料。知识库分组用于管理文件，不作为聊天检索过滤条件。
- 支持 Markdown、DOCX、TXT、C/C++、Java、Python、HTML 文件的批量上传、异步索引、预览和下载。暂不接收新的 PDF；已有 PDF 索引仍可使用。
- 原文件保存确认后，解析、切块、向量化和索引提交在后台继续。页面展示实际阶段与文本块完成数，导航栏显示处理中、失败及尚未查看的完成任务。没有可用 Embedding 时保留原文件并显示等待配置。
- 同名冲突按用户和目标分组判断：相同内容可跳过，不同内容需选择新版本或独立文档。新版本成功后切换并清理旧内容；失败保留当前索引。删除会停止检索和任务，再清理 MinIO 原件、文本和向量，仅保留历史引用摘要。
- ACM 模式能结合用户题目生成分析或指定语言的解法。项目尚无编译执行、在线评测或 LangGraph checkpoint；独立的静态代码校验工具目前未接入聊天结果。
- RAG 评测资料是离线契约与词面基线，不代表真实检索或端到端回答质量。

## 本地验证

```powershell
cd backend
python -m pytest -q -p no:cacheprovider
ruff check app tests --no-cache

cd ../frontend
npm ci
npm test
npm run lint
npm run typecheck
npm run build
```

详细架构、接口和当前限制见 [开发基线](docs/development-baseline.md)、[技术栈](docs/technical-stack.md) 与 [API 契约](docs/api-contract.md)。`docs/superpowers/` 中的设计稿和计划是历史记录，不能替代当前代码和这些维护中的文档。

## 删除容器后重建环境

容器可重新创建；原资料能否保留取决于 `postgres_data`、`minio_data` 数据卷是否仍在。不要使用 `docker compose down -v`，该命令会删除数据卷。已有 `.env` 中的数据库密码、MinIO 密码和模型凭证加密密钥应保留。

MinIO 使用 [官方固定源码发布](https://github.com/minio/minio/releases/tag/RELEASE.2025-10-15T17-29-55Z) 构建，首次构建需要下载 Go 模块。其他基础镜像仍固定原来的 digest，改用官方仓库地址。

Windows 如遇本地测试缓存权限导致 Docker 无法读取构建目录，可运行：

```powershell
$env:DOCKER_BUILDKIT = '0'
.\scripts\rebuild-environment.ps1
```

脚本仅复制源码和构建配置到忽略提交的 `.build-context`，构建全部镜像并启动服务，不复制 `.env` 到镜像。平时启动已构建镜像使用 `docker compose up -d --no-build`；查看状态使用 `docker compose ps`。后端启动会自动迁移至 `0015_knowledge_lifecycle`。

本机 Docker 数据盘已迁至 `E:\DockerData\DockerDesktopWSL`，迁移前备份位于 `E:\DockerData\migration-backup-20260928`。详细结果见 [Docker 数据盘迁移检查记录](docs/docker-data-migration-2026-09-28.md)。

本次知识库开发与实际服务验收见 [知识库生命周期验收记录](docs/knowledge-ingestion-acceptance-2026-09-28.md)。
