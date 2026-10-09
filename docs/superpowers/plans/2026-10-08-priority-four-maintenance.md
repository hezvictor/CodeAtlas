# CodeAtlas 四项维护改进 Implementation Plan

> **For agentic workers:** 依照下列复选步骤逐项执行并在每项完成后复核。若使用子代理，须由用户明确授权；也可在当前任务中顺序执行。

**Goal:** 修正部署说明和首页日期口径，收口未接入的旧接口，并降低聊天页状态逻辑的维护成本。

**Architecture:** 保留 FastAPI、Arq Worker、PostgreSQL、Redis 与现有 Next.js 页面之间的接口。文档问题只改文档；统计问题在 API 层修正时间窗口；闲置接口先收口；聊天页在不改 SSE 协议的条件下把运行状态与流读取从页面抽出。

**Tech Stack:** Python 3.11+、FastAPI、SQLAlchemy Async、pytest；Next.js 15、React 19、TypeScript、tsx/node:test。

**Spec:** `docs/superpowers/specs/2026-10-08-priority-four-maintenance-design.md`

## Global Constraints

- 当前仓库有大量未提交改动；执行时先查看 `git status --short`，只修改各任务列出的文件，不覆盖用户现有改动。
- 每个任务独立验收后再进行下一项。建议顺序为原问题 1 → 2 → 4 → 3。
- 不修改 API 字段、数据库表结构、聊天模式、最终答案校验和持久化策略。
- 不启用真实 token 流、代码执行、编译或在线评测；不运行真实数据迁移或部署。

---

## Task 1：统一迁移启动说明（原问题 1）

**Files:**
- Modify: `docs/agent-rag-architecture.md:209`
- Review: `README.md:18-26`、`backend/Dockerfile:12`、`backend/tests/test_docker_startup.py`

**Interface:** 无运行时代码或 API 变化。交付物是与当前 Docker 启动命令一致的部署说明。

- [ ] **Step 1：复核事实。** 检查 Dockerfile 的 `CMD`、README 的启动段落和现有启动测试，确认“迁移成功才启动 API”。命令：`rg -n 'alembic upgrade head|自动迁移|不自动迁移' README.md docs/agent-rag-architecture.md backend/Dockerfile`。
- [ ] **Step 2：修改实现说明。** 将错误句子改成以下明确口径，并保留检查点表不由运行时自动创建的说明：

  ```text
  LangGraph 运行时不会自行创建检查点表，检查点 schema 由 Alembic 迁移管理。Docker/Compose 后端容器启动时先执行 alembic upgrade head；迁移失败则 API 不启动。已有数据升级前先备份。Windows/Linux 原生启动不会自动迁移，须先手动执行 alembic upgrade head。
  ```

- [ ] **Step 3：静态验收。** 再次搜索当前文档，确认没有互相矛盾的自动迁移表述；对照 `backend/tests/test_docker_startup.py` 的现有断言。文档变更无需新增镜像启动测试，也不运行迁移。
- [ ] **Step 4：审查改动。** `git diff -- docs/agent-rag-architecture.md` 应仅包含迁移说明；阶段完成后再进入 Task 2。

## Task 2：按北京时间统计“今日会话”（原问题 2）

**Files:**
- Modify: `backend/app/routers/dashboard.py:1-43`
- Modify: `backend/tests/test_dashboard.py`
- Modify: `docs/api-contract.md` 的首页说明（增加日期口径）

**Interface:** `GET /api/v1/dashboard` 响应形状不变，`today_conversation_count` 表示北京时间当天新建的会话数。

- [ ] **Step 1：先写边界测试。** 为 `dashboard.py` 中拟新增的纯函数 `beijing_day_utc_bounds(now_utc: datetime) -> tuple[datetime, datetime]` 添加用例：`2026-10-07T15:59:59Z` 对应 UTC 区间 `[2026-10-06T16:00Z, 2026-10-07T16:00Z)`；`2026-10-07T16:00:00Z` 对应 `[2026-10-07T16:00Z, 2026-10-08T16:00Z)`。再加入下界包含、上界排除的路由查询测试，确认只统计当前用户，最近会话仍按 `updated_at` 排序。测试使用固定时间输入，不依赖机器本地时区。
- [ ] **Step 2：确认新测试先失败。** 在 `backend` 执行 `uv run python -m pytest tests/test_dashboard.py -q -p no:cacheprovider`；预期失败原因仅为新口径尚未实现。
- [ ] **Step 3：最小实现。** 使用标准库 `timezone(timedelta(hours=8))`，避免 Windows 原生运行额外依赖时区数据库。核心计算：

  ```python
  local = now_utc.astimezone(timezone(timedelta(hours=8)))
  start_local = local.replace(hour=0, minute=0, second=0, microsecond=0)
  start_utc = start_local.astimezone(UTC)
  end_utc = (start_local + timedelta(days=1)).astimezone(UTC)
  ```

  在现有 `Conversation.created_at >= day_start` 查询中加入 `< end_utc`，并传入 `start_utc`。不改 `recent_conversations` 和 `latest_conversation` 查询。
- [ ] **Step 4：验证与文档。** 重跑 `test_dashboard.py`，再执行 `uv run ruff check app/routers/dashboard.py tests/test_dashboard.py --no-cache`；在 `docs/api-contract.md` 注明北京时间半开区间和按 `created_at` 统计。
- [ ] **Step 5：审查。** 确认 API JSON 字段和前端首页均无需改动；检查 `git diff` 后再进入 Task 3。

## Task 3：清理未接入主流程的能力（原问题 4）

**Files:**
- Delete: `backend/app/code_validation.py`、`backend/tests/test_code_validation.py`
- Modify: `backend/app/providers/chat.py:1-43`、`backend/app/providers/openai_compatible.py:105-155`
- Modify: `backend/tests/test_chat_provider.py`，删除只验证 `stream_chat()` 的用例，保留 `complete()`、工具协议、模型测试相关用例
- Modify: `frontend/src/app/chat/page.tsx:120`、`frontend/src/lib/sse.test.ts`
- Review: `docs/api-contract.md`、`docs/agent-rag-architecture.md`；历史 `docs/superpowers/` 不回写

**Interface:** 运行时仍通过 `complete()` 获取整轮模型输出，通过 `message.final` 发送已校验正文。`SseDecoder` 保持通用，不限定事件名。

- [ ] **Step 1：确认调用边界。** 执行 `rg -n 'validate_solution_code|extract_solution_code|stream_chat|message\.delta' backend/app frontend/src backend/tests docs/api-contract.md`。除定义、孤立测试和聊天页旧分支外，如发现新增生产调用，停止删除并重新评审本任务。
- [ ] **Step 2：补齐当前协议测试。** 在现有聊天运行测试中验证最终正文只由 `message.final` 或终态快照交付，运行过程事件不包含未校验正文；将 `frontend/src/lib/sse.test.ts` 的中文分片样例改成 `message.final`，继续验证 UTF-8 分片和 CRLF。
- [ ] **Step 3：运行相关测试基线。** 在 `backend` 运行 `uv run python -m pytest tests/test_agent_contract.py tests/test_chat_provider.py -q -p no:cacheprovider`；在 `frontend` 运行 `npm test`。新增协议断言应基于当前实现通过。
- [ ] **Step 4：删除孤立代码。** 删除静态验证模块和专属测试；从 `ChatProvider` Protocol 及 `OpenAICompatibleChatProvider` 移除 `stream_chat()`；删除其专属测试与闲置 `AsyncGenerator` 导入；从聊天页移除 `message.delta` 处理分支及 `StreamPayload.delta` 字段。保留 `SseDecoder`、`message.final` 和所有进度事件。
- [ ] **Step 5：验证与审查。** 执行 `uv run python -m pytest tests/test_agent_contract.py tests/test_chat_provider.py tests/test_acm_workflow.py -q -p no:cacheprovider`、`uv run ruff check app tests --no-cache`、`npm test`、`npm run typecheck`。再次 `rg` 确认生产代码不再引用删除的接口；历史设计文档只作为历史记录。完成后再进入 Task 4。

## Task 4：拆分聊天页运行状态（原问题 3）

**Files:**
- Create: `frontend/src/lib/chat-run-state.ts`、`frontend/src/lib/chat-run-state.test.ts`
- Create: `frontend/src/hooks/useChatRun.ts`
- Modify: `frontend/src/app/chat/page.tsx:37-160,188-305`
- Review: `frontend/src/lib/agent-events.ts`、`frontend/src/lib/sse.ts`、`frontend/src/lib/chat-state.ts`

**Interfaces:**
- `chat-run-state.ts` 输出运行视图状态及 `reduceRunFrame(state, event, data)`；仅做纯状态转换，不执行网络请求。
- `useChatRun.ts` 管理 reader、运行 ID、按会话的状态、订阅和重连；通过明确回调把最终消息、检索状态与引用交给页面。现有会话 CRUD、消息分页与布局仍由页面负责。

- [ ] **Step 1：写纯状态测试。** 覆盖 `run.snapshot`、`run.started`、`retrieval.completed`、`model/tool` 进度、`message.final`、`run.waiting/completed/failed/interrupted`；测试旧序号事件不能覆盖新快照，终态快照可恢复最终正文，处理过程不得累加正文增量。保持 `reduceAgentEvent()` 现有去重语义。
- [ ] **Step 2：确认测试先失败。** 在 `frontend` 运行 `npm test`；预期仅新文件缺少实现。
- [ ] **Step 3：实现纯 reducer。** 将 `page.tsx` 中 `consumeReader` 的事件判定移到 `reduceRunFrame`，状态至少包含 `runId`、`status`、`answer`、`messageId`、`snapshotSequence`、`steps`、`retrievalStatus` 和 `citations`。返回新状态及必要的外部动作标记，不在 reducer 中调用 React setter 或 `fetch`。
- [ ] **Step 4：抽取订阅 hook。** 将 reader 生命周期、`consumeStream`、`reconnect`、`stop`、`resume` 收进 `useChatRun`；入口接收 `conversationId` 和鉴权请求函数，出口提供当前运行状态及这些动作。通过 `conversationId` 与 `runId` 检查阻止旧 reader 的事件写回新会话；切换会话时取消旧 reader。hook 不保存另一份消息历史。
- [ ] **Step 5：页面接线。** 页面用 hook 的状态渲染 `ChatRunProgress`、等待补传、断线提示、停止/恢复按钮；保留原有 `run()` 请求载荷、消息分页、题目与模型选择。发送失败时恢复输入文本的行为不变。
- [ ] **Step 6：验证交互。** 执行 `npm test`、`npm run lint`、`npm run typecheck`、`npm run build`。人工按以下顺序检查：新会话发送 → 切换会话 → 断线重连 → 停止 → 临时上下文丢失后补传恢复 → 重试历史消息 → 引用展示。确认没有重复请求，且正文只在最终事件出现。
- [ ] **Step 7：审查差异。** 对照重构前后 API URL、请求体、SSE 事件表、用户可见文案和状态转移；无意外行为变更后再视为完成。

## 总体验收

- [ ] 四个任务分别经过代码审查；执行记录包含各自的测试命令和结果。
- [ ] 检查 `git status --short`，确保未覆盖本计划建立前的用户改动。
- [ ] 若某阶段发现与设计假设不符，先修订该阶段计划再改代码；不自动扩大为真实流式输出或在线评测。

## 执行记录（2026-10-08）

- Task 1：已核对 Docker 启动命令并修正文档中的迁移说明；未执行真实迁移。
- Task 2：已按北京时间半开区间实现今日会话统计；固定时间边界与查询条件测试通过。
- Task 3：已移除生产流程未调用的静态代码验证模块、服务商 token 流接口和前端 `message.delta` 分支；现有 `message.final` 及进度 SSE 保留。
- Task 4：已抽出运行状态 reducer 与订阅 hook，并覆盖旧 reader 事件、恢复运行、最终答案及乐观消息更新的单元测试。
- 验证：后端 `pytest` 152 passed、38 skipped；改动文件 Ruff 通过；前端 43 tests passed，lint、typecheck、build 通过；`git diff --check` 通过。全仓 Ruff 仍有本次未修改文件中的既有错误。
- 待人工验证：当前 `docker compose ps` 没有运行中的服务，尚未在真实登录及模型连接下执行聊天交互清单。
