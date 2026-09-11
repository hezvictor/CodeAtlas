# 私人知识库与 RAG 设计说明

**日期：** 2026-09-11  
**状态：** 待用户评审  
**适用阶段：** CodeAtlas Phase 3

## 1. 目标与范围

在现有账号、会话和普通聊天基础上，实现单用户私人知识库与 RAG 基础能力。第一期支持 Markdown、PDF、DOCX、TXT、C/C++、Java、Python 和 HTML 文件上传；不支持网页 URL 抓取。第一期使用 Arq + Redis 作为异步队列，不强制引入 LangGraph；不引入 rerank，使用 PostgreSQL 全文检索与 pgvector 混合召回。

用户可以创建知识库分组、上传文件、查看处理状态、预览内容、删除或重新索引文件。聊天请求可选择知识库分组和当前会话附件，回答必须引用本次检索得到的切片，后端验证引用后才将其作为可信来源展示。

## 2. 已确认的技术决策

- 队列：Arq，复用现有 Redis。
- 对象存储：MinIO，知识库 Bucket 私有；不复用头像 Bucket 的公开读策略。
- 数据库：PostgreSQL 16 + pgvector。
- Embedding：DashScope OpenAI 兼容 Embeddings API。
- Embedding 模型：部署配置指定的 `EMBEDDING_MODEL`，默认建议 `text-embedding-v3`。
- 向量维度：配置固定为 `EMBEDDING_DIMENSIONS=1024`（已按当前 DashScope `text-embedding-v3` 部署实测确认）；API 返回维度不匹配时任务失败。
- 检索：全文检索 + cosine 向量检索 + RRF 合并；第一期不使用 rerank。
- 文档版本：逻辑文档与不可变版本分离，重新上传创建新版本。
- URL：不实现网页 URL 上传或抓取。
- LangGraph：不是 Phase 3 的强制依赖，后续 ACM 工作流可单独引入。

## 3. 系统架构

```text
Next.js
  -> FastAPI /api/v1
       -> Auth / Knowledge / Document / Retrieval / Chat Services
       -> PostgreSQL + pgvector
       -> MinIO (private bucket)
       -> Redis -> Arq Worker
                             -> parse -> chunk -> embed -> index
```

业务路由只负责认证、参数校验和响应；对象存储、解析、切块、Embedding、检索和引用校验分别封装为独立服务，便于单元测试和替换实现。

## 4. 数据模型

### 4.1 `knowledge_groups`

- `id UUID` 主键
- `user_id UUID` 外键 `users.id`，级联删除
- `name VARCHAR(100)`，同一用户唯一
- `description TEXT` 可空
- `created_at`, `updated_at`

### 4.2 `documents`

- `id UUID` 主键
- `user_id UUID` 外键
- `group_id UUID` 外键 `knowledge_groups.id`
- `title VARCHAR(200)`
- `current_version_id UUID` 可空
- `deleted_at TIMESTAMPTZ` 可空
- `created_at`, `updated_at`

### 4.3 `document_versions`

- `id UUID` 主键
- `document_id UUID` 外键
- `version_no INTEGER`
- `original_filename VARCHAR(255)`
- `mime_type VARCHAR(120)`
- `extension VARCHAR(20)`
- `size_bytes BIGINT`
- `sha256 CHAR(64)`
- `object_key TEXT`
- `status VARCHAR(20)`：`uploaded`、`parsing`、`chunking`、`embedding`、`indexed`、`failed`
- `error_code VARCHAR(80)`、`error_message TEXT`
- `extracted_text TEXT`，用于预览和定位
- `created_at`, `indexed_at`

对 `(document_id, version_no)` 建立唯一约束；对 `(document_id, sha256)` 建立去重辅助索引。

### 4.4 `document_chunks`

- `id UUID` 主键
- `document_version_id UUID` 外键
- `ordinal INTEGER`
- `content TEXT`
- `content_hash CHAR(64)`
- `token_count INTEGER`
- `page_start`, `page_end INTEGER` 可空
- `line_start`, `line_end INTEGER` 可空
- `section_path TEXT` 可空
- `char_start`, `char_end INTEGER` 可空
- `locator JSONB`
- `embedding vector(1024)`
- `search_vector TSVECTOR`

对 `(document_version_id, ordinal)` 建立唯一约束；`search_vector` 使用 GIN；`embedding` 使用 cosine HNSW 索引。

### 4.5 `attachments`

- `id UUID` 主键
- `user_id UUID` 外键
- `conversation_id UUID` 外键
- `document_version_id UUID` 外键
- `created_at`

附件只建立会话与文档版本的关联，不复制文件内容。

### 4.6 `citations`

- `id UUID` 主键
- `message_id UUID` 外键
- `chunk_id UUID` 外键
- `quote TEXT`
- `score FLOAT`
- `rank INTEGER`
- `locator JSONB`
- `is_valid BOOLEAN`
- `validation_error VARCHAR(120)` 可空
- `created_at`

对 `(message_id, chunk_id)` 建立唯一约束。

### 4.7 `document_jobs`

- `id UUID` 主键
- `document_version_id UUID` 外键
- `stage VARCHAR(20)`
- `status VARCHAR(20)`
- `attempts INTEGER`
- `available_at TIMESTAMPTZ`
- `locked_at TIMESTAMPTZ`、`locked_by VARCHAR(100)`
- `error_message TEXT`
- `created_at`, `finished_at`

## 5. 数据库迁移

新增 Alembic revision，按以下顺序执行：

1. `CREATE EXTENSION IF NOT EXISTS vector`。
2. 创建知识库、版本、切片、附件、引用和任务表。
3. 创建外键、唯一约束和用户范围索引。
4. 创建全文 GIN 索引和 pgvector HNSW 索引。

不得修改已有账号、会话和消息字段的语义。迁移必须支持全新数据库和已有数据库升级。

## 6. 文件与对象存储流程

知识库对象路径：

```text
users/{user_id}/groups/{group_id}/documents/{document_id}/versions/{version_no}/{random_id}-{safe_filename}
```

上传时校验扩展名、声明 MIME、文件头和最大大小；原始文件写入私有 `codeatlas-documents` Bucket。数据库只保存对象 Key，不保存 MinIO 凭证。

下载使用短时效预签名 URL，生成 URL 前必须验证文档属于当前用户。预览优先返回解析后的文本和定位信息。删除采用软删除加异步对象清理；历史版本默认保留，避免已保存引用立即失效。

## 7. 异步处理

API 创建版本后投递一个幂等任务。Arq Worker 依次执行：

1. 读取 MinIO 原始对象并进入 `parsing`。
2. 解析正文和定位元数据并进入 `chunking`。
3. 删除该版本旧切片，写入新切片并进入 `embedding`。
4. 批量调用 Embedding，写入向量和全文索引，进入 `indexed`。

失败任务保存内部错误码和用户可读错误，按指数退避重试；超过最大尝试次数进入 `failed`。重复任务通过版本 ID、切片顺序和内容哈希保证幂等。

## 8. 解析和切块

- Markdown/TXT：按标题、段落和语义边界切分，保留标题路径和字符偏移。
- PDF：按页提取，保留页码。
- DOCX：按标题和段落提取。
- C/C++、Java、Python：按类、函数和代码块切分，保留起止行号。
- HTML：移除脚本、样式和导航噪声，保留正文、标题和段落；只处理上传文件。

普通文本目标为 500–800 token、重叠 50–100 token；代码优先按语法结构切分，过大时按代码块拆分。单文件大小、解析超时和总文本长度均由配置限制。

## 9. Embedding 与检索

封装：

```text
embed_documents(texts: list[str]) -> list[list[float]]
embed_query(text: str) -> list[float]
```

对 429、5xx、超时进行指数退避；校验响应数量和 1024 维度。检索先按 `user_id`、分组、会话附件和 `indexed` 状态过滤，再执行全文和向量召回。

初始参数：向量候选 20、关键词候选 20、合并后保留 8–12 个切片；使用 RRF 合并，去除同一文档的重复相邻切片，并限制总上下文长度。

## 10. 引用校验和聊天集成

模型上下文要求使用 `[cite:chunk_uuid]` 标记。后端只接受本次检索候选中的切片 ID，并再次验证用户、文档版本和定位信息。

SSE 事件扩展为：

```text
run.started
retrieval.completed
message.delta
citations.validated
message.final
run.completed / run.interrupted / run.failed
```

`message.final` 返回去除无效引用后的最终文本，前端用它替换流式临时内容。检索不足时明确返回“知识库未找到足够依据”，不伪造来源。

## 11. API

```text
GET/POST/PATCH/DELETE /knowledge/groups
GET/POST              /knowledge/documents
GET/DELETE            /knowledge/documents/{id}
GET                   /knowledge/documents/{id}/status
POST                  /knowledge/documents/{id}/retry
POST                  /knowledge/documents/{id}/reindex
GET                   /knowledge/documents/{id}/preview
GET                   /knowledge/documents/{id}/download
POST/DELETE           /conversations/{id}/attachments
GET                   /conversations/{id}/messages/{message_id}/citations
```

聊天请求增加 `knowledge_group_ids`；已有 `attachment_ids` 改为实际校验和检索范围输入。所有资源查询都必须附带当前用户条件。

## 12. 前端

`/knowledge` 提供分组、搜索、筛选、上传弹窗、文档列表、处理状态、重试、重新索引和删除。

`/knowledge/[id]` 提供元数据、版本、预览、页码/章节/代码行定位。

聊天页增加分组选择、会话附件管理和引用侧栏；桌面端显示右侧栏，移动端使用抽屉。继续复用现有 `apiFetch`、错误通知、导航和 CSS 变量。

## 13. 安全与可观测性

- 所有表和向量检索按用户隔离。
- Bucket 私有，使用短时效预签名 URL。
- 限制扩展名、MIME、文件头、大小和解析时间。
- HTML 解析时去除脚本；文档内容视为不可信数据。
- 日志不记录密钥、密码、refresh token 或完整敏感原文。
- 记录请求 ID、文档任务阶段、解析耗时、Embedding 耗时、检索耗时、命中数、重试数和引用校验失败数。

## 14. 测试与验收

必须覆盖：

- 分组和文档 CRUD。
- 跨用户访问拒绝。
- 文件类型、大小和文件头校验。
- HTML、PDF、DOCX 和代码解析。
- 切块边界、重叠和定位。
- Embedding Mock、维度错误、超时和重试。
- Worker 幂等和失败恢复。
- 全文、向量和混合检索。
- 引用合法性和最终文本净化。
- SSE 事件顺序。
- 前端上传、状态刷新、预览、引用跳转和移动端布局。
- Docker Compose 全链路启动及现有 Phase 1/2 回归测试。

完成标准是：用户可以上传支持格式的文件，看到异步处理状态，处理完成后在聊天中获得只引用本人资料的回答，并能从引用跳转到文档定位；已有登录、普通聊天和消息操作保持兼容。
