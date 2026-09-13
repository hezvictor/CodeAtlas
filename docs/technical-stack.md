# ACM 私人知识库 AI 助教平台：技术栈与架构

**版本**：0.3（技术基线）  
**日期**：2026-09-11  
**状态**：以当前代码为准

## 1. 推荐技术栈

| 层次 | 选择 | 说明 |
|---|---|---|
| 前端 | Next.js、React、TypeScript、自定义 CSS | 当前实现；尚未使用 Tailwind CSS 或 shadcn/ui |
| 后端 | Python、FastAPI、Pydantic | API、鉴权、上传和流式接口 |
| Agent | FastAPI 服务编排 | 当前不强制引入 LangGraph；未来可选接入 |
| 数据库 | PostgreSQL + pgvector | 业务数据、消息、文档元数据和向量检索 |
| 检查点 | 未启用 | resume 当前复用持久化消息，不是 checkpoint 恢复；后续阶段再评估 PostgreSQL checkpoint |
| 异步任务 | Redis + Arq | 文档解析、切块和 Embedding Worker |
| 文件存储 | S3 兼容存储；开发环境 MinIO | 保存原始文档和版本文件 |
| 模型 | 阿里云百炼 OpenAI 兼容接口 | 当前聊天模型和 embedding 模型 |
| 鉴权 | JWT Access Token + Refresh Token、Argon2 | 邮箱密码登录和会话续期 |
| 部署 | Docker Compose、Nginx/Caddy | 适合个人或小规模服务器部署 |

## 2. 百炼配置约定

配置使用以下环境变量，示例文件只放占位符：

```env
DASHSCOPE_API_KEY=sk-your-key
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
CHAT_MODEL=<configured-chat-model>
EMBEDDING_MODEL=<configured-embedding-model>
EMBEDDING_DIMENSIONS=1024
```

实际模型名称由部署配置决定。应用层封装 `ChatModelProvider` 和 `EmbeddingProvider`，避免未来切换 DeepSeek 或其他 OpenAI 兼容服务时修改业务逻辑。

## 3. 逻辑架构

```text
浏览器
  -> Next.js 前端
  -> FastAPI API / SSE
       -> Auth Service
       -> Chat Service
       -> Chat Router -> Retriever -> 百炼 OpenAI 兼容接口
       -> PostgreSQL 会话、消息、文档、向量与引用
       -> Redis/Arq Worker -> MinIO 原始文件
```

## 4. RAG 流程（已实现）

1. 上传文件并创建文档记录，状态为 `uploaded`。
2. 异步解析文本和结构信息，保留页码、章节、代码行号等定位元数据。
3. 按文档类型切分：普通文本按语义段落，代码按类/函数/代码块并保留语言信息。
4. 调用百炼 embedding 模型写入 pgvector。
5. 用户提问时按用户 ID、知识库分组、会话文件和可选题目过滤召回。
6. 进行关键词 + 向量混合检索，拼接有限上下文并要求模型输出引用标识。
7. 后端校验引用标识，SSE 返回回答增量、状态事件和引用信息。

## 5. 可选的未来 LangGraph 工作流

普通问答建议节点：`load_context -> retrieve -> compose_prompt -> generate -> validate_citations -> persist`。

ACM 模式建议节点：`classify_mode -> extract_problem -> retrieve_problem_context -> analyze -> language_gate -> generate_solution -> validate -> persist`。

暂停/恢复策略：

- MVP 实现 `stop`：取消当前生成任务，持久化已生成内容和图状态。
- 使用 thread ID 绑定会话，使用 PostgreSQL checkpointer 保存 checkpoint。
- 恢复时从最近 checkpoint 继续；若第三方模型调用已结束，则从最后一个可恢复节点重新执行。
- LangGraph `interrupt` 用于等待用户选择编程语言、确认是否进入解题模式等人工决策。
- 真正的 token 级暂停取决于模型 SDK 的取消能力，不承诺任意时刻无损暂停。

## 6. 数据模型说明

- `users`：用户、密码摘要、资料信息。
- `conversations`：会话标题、模式、用户归属、时间戳。
- `messages`：角色、内容、生成状态、模型、耗时。
- `attachments`：会话附件、文件存储地址、解析状态。
- `knowledge_groups`：私人知识库分组。
- `documents`：文档、版本、来源类型和处理状态。
- `document_chunks`：文本块、页码/章节/代码位置、embedding 向量。
- `citations`：消息与文档块之间的引用关系。
- `langgraph_checkpoints`：由官方 PostgreSQL checkpointer 管理。

所有查询必须带 `user_id` 或等价权限条件；向量召回也必须先执行用户范围过滤。

## 7. API 约定

- `POST /auth/register`、`POST /auth/login`、`POST /auth/refresh`、`POST /auth/logout`
- `GET/POST/PATCH/DELETE /conversations`
- `GET/POST /conversations/{id}/messages`：SSE 返回流式事件
- `POST /conversations/{id}/stop`、`POST /conversations/{id}/resume`
- `GET/POST/PATCH/DELETE /knowledge/documents`
- `GET /problems`：题库列表和 `@` 选择器题目搜索
- `GET /problems/{id}`：题目详情
- `GET /dashboard`：首页真实会话数据

知识库实际路径和 SSE 事件以 [api-contract.md](api-contract.md) 为准；题库路径仍为规划。

## 8. 安全与运维

- `.env`、密钥和上传文件目录加入忽略规则；日志禁止打印 API Key。
- 文件上传采用白名单扩展名与 MIME 校验，限制大小和解压路径，避免路径穿越。
- 文档内容视为不可信数据，RAG 提示词明确区分“资料内容”和“系统指令”。
- 记录模型请求耗时、首 token 延迟、检索命中率和失败原因；不记录模型 token 用量统计。
- PostgreSQL、Redis、MinIO 定期备份；MVP 至少提供手工备份与恢复说明。
- 先使用 Docker Compose，服务边界稳定后再考虑拆分部署。
