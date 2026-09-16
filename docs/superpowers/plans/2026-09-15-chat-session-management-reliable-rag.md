# 聊天会话管理与可靠知识库回答实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现临时新会话、DeepSeek 风格会话管理、与页面解耦的后台生成、三种知识库范围、持久化回答依据和上传错误提示。

**Architecture:** 前端以草稿状态表示未发送的新会话；首问后调用会话创建接口。后端把用户消息和生成中的助手占位消息先持久化，再通过进程内后台任务运行模型，SSE 仅作为可重连的实时订阅。PostgreSQL 保存会话置顶状态、生成结果和检索切片 ID，知识库检索继续使用用户隔离的全文+向量混合召回。

**Tech Stack:** FastAPI、SQLAlchemy Async、Alembic、PostgreSQL/pgvector、Redis、Next.js、React、TypeScript、SSE。

**Spec:** `docs/superpowers/specs/2026-09-14-chat-session-management-reliable-rag-design.md`

## Global Constraints

- 分享功能永久不实现，不出现在 UI、API 或数据模型中。
- 生成任务只需在后端进程持续运行期间可恢复，不要求后端重启续生成。
- 所有会话、消息、知识库和来源查询必须按当前用户隔离。
- 默认知识库范围为 `none`；支持 `none`、`all`、`groups`。
- 兼容现有认证、普通聊天、ACM 模式、附件和 SSE 调用方式。
- 新增行为必须先写失败测试并确认失败，再写生产代码。

---

### Task 1: 会话数据模型、迁移与 API

**Files:**
- Modify: `backend/app/models.py`
- Modify: `backend/app/schemas.py`
- Modify: `backend/app/routers/conversations.py`
- Create: `backend/migrations/versions/0009_chat_session_management.py`
- Test: `backend/tests/test_conversation_management.py`

**Interfaces:**
- `Conversation.pinned: bool`
- `Message.retrieved_chunk_ids: list[str]`
- `ConversationUpdate(title?: str, pinned?: bool)`
- `BulkConversationRequest(conversation_ids, action)`
- `POST /conversations/bulk`

- [ ] 写测试：置顶排序、PATCH 只更新传入字段、批量 pin/unpin/delete 只影响当前用户、跨用户 ID 无副作用。
- [ ] 运行 `pytest backend/tests/test_conversation_management.py -v`，确认因字段和接口不存在而失败。
- [ ] 添加模型字段、Schema 和迁移，列表按 `pinned DESC, updated_at DESC` 排序。
- [ ] 实现批量接口和兼容的部分 ID 处理。
- [ ] 运行新增测试及现有会话测试，确认通过。

### Task 2: 后台生成运行时与可重连 SSE

**Files:**
- Modify: `backend/app/routers/conversations.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_conversations_runtime.py`

**Interfaces:**
- `RunRegistry.start(conversation_id, runner) -> run_id`
- `GET /conversations/{id}/runs/active`
- `GET /conversations/{id}/runs/{run_id}/stream`
- `run.snapshot` SSE 事件

- [ ] 先写断开 SSE 后任务仍完成、活动运行快照、重连先快照后增量、显式 stop 才取消的测试。
- [ ] 运行测试确认当前生成器会在断开时结束或没有新接口而失败。
- [ ] 将模型调用移入 `asyncio.create_task`，任务开始前保存用户消息和 `generating` 助手消息。
- [ ] 维护每会话单运行锁、停止事件、当前答案、有界订阅队列和终态。
- [ ] SSE 初始订阅只负责转发事件；断开仅移除订阅者。
- [ ] 任务完成/失败/取消时更新助手消息、指标、检索切片 ID、引用并释放运行锁。
- [ ] 对数据库中遗留但进程内不存在的 `generating` 消息按重启中断处理。
- [ ] 运行完整后端回归测试。

### Task 3: 临时新会话前端状态

**Files:**
- Modify: `frontend/src/app/chat/page.tsx`
- Modify: `frontend/src/lib/chat-context.ts`
- Modify: `frontend/src/app/globals.css`
- Test: `frontend/src/app/chat/chat-state.test.ts`（必要时抽取纯函数）

- [ ] 写测试：点击新建不调用 API；首条发送先创建会话；空草稿离开不出现在列表。
- [ ] 运行前端测试确认失败。
- [ ] 用 `draftConversation` 替代立即 POST 创建；发送首问时生成标题并创建真实会话。
- [ ] 将运行状态按会话 ID保存，切换会话时仅取消订阅。
- [ ] 进入会话时加载消息、活动运行快照并订阅重连流。
- [ ] 页面刷新、重新打开和重新登录后恢复消息及生成状态。
- [ ] 运行 TypeScript 检查和前端测试。

### Task 4: 三个点菜单、置顶和多选 UI

**Files:**
- Modify: `frontend/src/app/chat/page.tsx`
- Modify: `frontend/src/app/globals.css`
- Create: `frontend/src/components/ConversationMenu.tsx`
- Create: `frontend/src/components/ConversationBulkBar.tsx`
- Test: `frontend/src/components/ConversationMenu.test.tsx`

- [ ] 写测试：菜单包含重命名/置顶/多选/删除且不包含分享；多选批量操作调用正确 action。
- [ ] 运行测试确认失败。
- [ ] 移除双击编辑，添加右侧三个点按钮并阻止冒泡切换会话。
- [ ] 实现重命名输入、置顶/取消置顶、单独删除和删除后的会话切换。
- [ ] 实现复选框、多选计数、底部批量置顶和批量删除栏。
- [ ] 添加置顶图标、菜单定位、键盘/点击外关闭和移动端样式。
- [ ] 运行前端测试和构建。

### Task 5: 知识库范围和检索修复

**Files:**
- Modify: `backend/app/schemas.py`
- Modify: `backend/app/services/retrieval_service.py`
- Modify: `backend/app/routers/conversations.py`
- Test: `backend/tests/test_retrieval_scope.py`

- [ ] 写测试覆盖 `none`、`all`、`groups`、附件并集、空 groups 参数和用户隔离。
- [ ] 运行测试确认 `knowledge_scope` 和 all 范围尚不存在。
- [ ] 增加 `knowledge_scope` 字段及兼容旧客户端的推导规则。
- [ ] 让 `all` 不添加 group 过滤但保留 user/deleted/indexed 过滤。
- [ ] 让 `none` 无附件时跳过检索；有附件时只检索附件。
- [ ] 在上下文中保留文档来源标识并强化引用提示。
- [ ] 运行 RAG、检索和会话回归测试。

### Task 6: 来源元数据和回答依据接口

**Files:**
- Modify: `backend/app/citations.py`
- Modify: `backend/app/models.py`
- Modify: `backend/app/routers/conversations.py`
- Modify: `backend/app/schemas.py`
- Test: `backend/tests/test_citation_sources.py`

- [ ] 写测试：来源接口返回文档标题、文件名、分组、定位和显式引用标记；跨用户不可读。
- [ ] 运行测试确认接口不存在。
- [ ] 持久化检索切片 ID到助手消息，并扩展 citations 查询关联 Document/KnowledgeGroup。
- [ ] 新增 `GET /conversations/{id}/messages/{message_id}/sources`。
- [ ] 保持现有 citations 接口兼容并补充元数据。
- [ ] 运行引用、RAG 和权限测试。

### Task 7: 聊天前端知识库选择、流恢复和回答依据

**Files:**
- Modify: `frontend/src/app/chat/page.tsx`
- Modify: `frontend/src/app/globals.css`
- Create: `frontend/src/components/CitationPanel.tsx`
- Test: `frontend/src/components/CitationPanel.test.tsx`

- [ ] 写测试：默认 none、all 和指定分组 payload 正确；切换会话后重新加载来源。
- [ ] 运行测试确认当前只有单分组选择且来源只在内存中。
- [ ] 将选择器改为“不使用知识库/使用所有知识库/选择知识库分组”。
- [ ] 发送时传递 `knowledge_scope`，切换会话和新草稿重置为 none。
- [ ] 订阅快照和增量，显示已有内容并继续追加；终态用数据库最终消息覆盖。
- [ ] 用 CitationPanel 显示文档、文件、分组、定位、片段和“显式引用/检索参考”状态。
- [ ] 运行前端测试、类型检查和构建。

### Task 8: 知识库上传策略和错误反馈

**Files:**
- Modify: `backend/app/routers/knowledge_documents.py`
- Modify: `backend/app/schemas.py`
- Modify: `frontend/src/app/knowledge/page.tsx`
- Modify: `frontend/src/app/globals.css`
- Test: `backend/tests/test_knowledge_upload_policy.py`

- [ ] 写测试：policy 接口、错误码映射、扩展名/大小/MIME/文件头错误均有稳定消息。
- [ ] 运行测试确认 policy 接口和错误码不存在或不完整。
- [ ] 新增 `GET /knowledge/documents/policy`，返回实际允许扩展名、格式说明和最大字节数。
- [ ] 将 `_validate_upload` 异常映射为稳定错误码和中文消息。
- [ ] 前端加载 policy，文件选择时先校验扩展名和大小，并显示支持格式说明。
- [ ] 失败文档显示 `error_message`，保留重试入口。
- [ ] 运行知识库、文档任务和前端构建回归。

### Task 9: 文档、端到端验收与清理

**Files:**
- Modify: `docs/api-contract.md`
- Modify: `docs/data-model.md`
- Modify: `docs/roadmap.md`
- Test: `backend/tests/` 全量、前端测试和浏览器流程

- [ ] 运行后端全量测试并修复回归。
- [ ] 运行前端类型检查、测试和 `npm run build`。
- [ ] 用浏览器验证草稿、首问入库、菜单、多选、后台生成恢复、三种知识库范围、来源面板和上传提示。
- [ ] 更新 API、数据模型和路线图文档，记录分享功能永久不实现及后端重启边界。
- [ ] 检查迁移可升级/回滚，确认无临时调试代码和未处理错误。
