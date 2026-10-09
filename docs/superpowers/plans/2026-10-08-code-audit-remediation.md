# Code Audit Remediation Implementation Plan

> **For agentic workers:** Implement the tasks one at a time. Each task has its own acceptance check; review the diff before moving to the next task.

**Goal:** 修复已确认的前后端行为问题，保留临时资料隐私规则，并恢复后端静态检查。

**Architecture:** 个人中心统一使用会检查 HTTP 状态的请求入口；聊天页在创建会话期间保护输入和防重复提交；Reranker 的可选密钥在前后端形成一致契约。临时内容校验先建立语义与性能基线，再替换高耗时匹配路径；标题校验放在 API schema 层。

**Tech Stack:** Next.js 15、React 19、TypeScript、FastAPI、Pydantic、Pytest、Ruff。

**Spec:** `docs/superpowers/specs/2026-10-08-code-audit-remediation-design.md`

## Global Constraints

- 保留 Embedding 失败时现有检索行为。
- 临时资料的 500 字符、单文件累计 10%、连续 8 字符片段门槛不得降低。
- 不引入数据库迁移、生产依赖或外部服务。
- 不覆盖工作区其他未提交改动；仅检查和暂存本任务涉及的文件。

---

## Task 1：个人中心正确处理失败响应与改密后的会话

**Files:** 修改 `frontend/src/app/profile/page.tsx`；按需要在 `frontend/src/lib/` 增加可测试的请求函数及对应测试。

**接口约定:** `lib/auth.ts` 的 `apiFetch` 负责刷新 401 令牌，但允许调用方读取其他失败响应；`lib/errors.ts` 的 `apiFetch` 会在任何非 2xx 响应时抛错。个人中心操作应使用后者。后端 `PATCH /users/me/password` 成功返回 204，同时使全部旧令牌失效。

- [ ] 用错误旧密码提交改密请求，先记录当前页面会错误提示成功的复现结果；资料邮箱冲突的 409 也应记录，确认用户状态不会被错误 JSON 覆盖。
- [ ] 为请求处理增加回归验证：400/409 不触发成功提示或 `setUser`，204 才进入改密成功分支；头像上传 400/413 同样不触发成功提示。
- [ ] 将个人中心三个写操作改用会检查 `response.ok` 的请求入口。改密成功后调用 `clearSession()` 并跳转登录页；登录页应明确显示“密码已修改，请重新登录”。
- [ ] 运行前端测试、Lint、类型检查，并人工核对错误旧密码、邮箱冲突、有效改密三个流程。

## Task 2：首次创建聊天会话失败时保留输入

**Files:** 修改 `frontend/src/app/chat/page.tsx`；如将提交流程抽成纯函数，测试放在 `frontend/src/lib/`。

**接口约定:** `ensureConversation(text)` 在 API 失败时抛错；`run(conversation, text)` 现有失败处理负责已创建会话后的发送失败。

- [ ] 复现：新建草稿中输入文本，令 `POST /conversations` 返回 500；当前输入框会清空且无法自动恢复。
- [ ] 给创建会话阶段增加独立的失败断言，并验证快速双击发送只创建一个会话。
- [ ] 保留“提交时清空输入”的交互，但把 `ensureConversation(text)` 纳入 `try/catch`；创建失败时仅在输入框仍为空时恢复原文，显示错误，并在 `finally` 释放提交锁。已创建会话后的错误仍由 `run` 处理，避免重复恢复或重复提示。
- [ ] 验证正常首次发送、创建失败后重试、创建请求期间重复点击，以及已有会话发送。

## Task 3：统一 Reranker 的可选密钥契约

**Files:** 修改 `backend/app/schemas.py`、`backend/app/routers/model_connections.py`、`frontend/src/app/settings/models/page.tsx`；增加后端配置接口测试。

**接口约定:** 已有配置的 PATCH 请求可省略 `api_key` 并保留原加密密钥；新建配置缺少密钥返回 422；显式提供非空密钥才替换旧密钥。

- [ ] 写失败测试：已有配置仅修改 `base_url` 或 `model_name` 应保留密钥；新建配置缺少或传空密钥应拒绝。
- [ ] 将 `RerankerConfigUpdate.api_key` 改为可省略但非空的字段；路由在新建时要求提供，在编辑时仅当提供新值才重新加密。保持现有“编辑后待验证”的状态规则。
- [ ] 前端只在用户输入了新 Key 时提交 `api_key`；保存成功文案改为“已保存，请测试连接后启用”，并使现有配置的 Key 输入提示与行为一致。
- [ ] 验证首次配置、只改地址、只改模型、换 Key、空 Key 拒绝、测试成功后检索才使用用户 Reranker；运行相关后端测试和前端检查。

## Task 4：拒绝去空白后为空的会话标题

**Files:** 修改 `backend/app/schemas.py`；测试放在 `backend/tests/test_conversation_management.py`。

- [ ] 写失败测试：`ConversationCreate(title="   ")` 和 `ConversationUpdate(title="   ")` 都应校验失败；`"  题解  "` 应保存为 `"题解"`。
- [ ] 在两个 schema 中统一执行去首尾空白与非空校验；保留现有长度上限。创建接口不再依赖路由里的 `strip()` 修正无效标题。
- [ ] 运行会话管理测试，并验证前端正常派生的标题仍可创建。

## Task 5：优化临时原文引用校验的高耗时路径

**Files:** 修改 `backend/app/temporary/privacy.py` 及直接调用它的 `backend/app/chat_runtime/service.py`（仅当异步边界确实需要调整）；增加 `backend/tests/test_temporary_context.py` 中的语义测试和独立性能基准。

**已知复现:** 当前 `SequenceMatcher(..., autojunk=False)` 对 10 万重复字符来源与约 1000 字符回答耗时约 10.4 秒；实际入口位于 `start_run` 和 `finish_run` 的同步校验中。配置允许单文件提取文本达 200 万字符。

- [ ] 固定现有语义测试：完整原文、文件名/ID、8 字符以下片段、单次 500 字符、跨消息单文件累计 10%、多个文件分别计数。加入重复文本样本，并记录当前耗时，不以脆弱的绝对秒数作为普通单测断言。
- [ ] 在隔离的 API 请求中复现同一输入，记录请求延迟及事件循环调度延迟；如果请求路径没有出现可观测阻塞，停止算法改动并记录直接函数基准与实际路径的差异。
- [ ] 若请求路径确认阻塞，选定有明确时间和内存上界的匹配实现，再对样本语料比较新旧判定；所有判定差异均需查明，不能直接放宽原文拦截。
- [ ] 对调用点验证 API 事件循环不会被长时间同步计算占用；若计算仍需较长时间，放入受控工作线程并设置并发上限。不得仅开启 `autojunk=True` 或超时后直接放行。
- [ ] 在独立性能基准中重复 10 万字符/1000 字符样本，并覆盖接近配置上限的样本；记录新旧耗时和峰值内存，再运行临时文件及聊天运行测试。

## Task 6：恢复后端 Ruff 检查

**Files:** `backend/app/models.py`、`backend/app/providers/reranker.py`、`backend/app/routers/conversations.py`、`backend/tests/test_agent_integration.py`、`backend/tests/test_knowledge_lifecycle.py`、`backend/tests/test_message_order.py`。

- [ ] 运行 `uv run ruff check app tests --no-cache` 并保存当前 11 条结果。
- [ ] 修正导入顺序和真正未使用的导入。`test_message_order.py` 中的 `db` 来自另一测试模块并承担 Pytest fixture 注册作用，不直接删除；改为不会与测试参数重名的导入方式，并确认测试仍能解析 fixture。
- [ ] Ruff 零错误后运行涉及的 Pytest 文件；没有独立测试数据库时明确标记集成用例跳过，不把跳过视作通过。

## Task 7：总体验收与交付

- [ ] 运行 README 列出的 `pytest -q -p no:cacheprovider`、`ruff check app tests --no-cache`、`npm test`、`npm run lint`、`npm run typecheck`。
- [ ] 在项目专用 `infra/compose.agent-test.yml` 测试环境运行数据库和 Redis 集成用例，核对跳过数量；不得对开发或生产数据执行破坏性测试。
- [ ] 对照本计划六项行为契约逐项检查，确认 Embedding 失败策略及临时资料隐私门槛保持原样。只审阅和暂存本计划对应代码与测试；在交付说明中列出测试结果和仍未覆盖的环境风险。

## 执行记录（2026-10-09）

- 个人中心：统一使用会检查 HTTP 状态的请求封装；失败响应不更新用户状态或显示成功；改密成功清除本地令牌并跳转重新登录。
- 首次建会话：创建失败恢复输入，提交锁阻止重复创建；前端回归测试覆盖失败重试和快速重复提交。
- Reranker：编辑时可省略 Key 并保留原密钥；新建和空白 Key 被拒绝；更换 Key 会使配置进入待验证状态；页面明确提示测试成功后才参与检索。
- 会话标题：创建和更新统一 trim 并拒绝空白标题。
- 临时资料：保留完整原文、元数据、500 字符、单文件 10%、8 字符片段规则；异步校验受并发槽位和超时保护，超时拒绝；线性公共片段预筛降低重复文本路径耗时。基准：100k/1k 连续引用约 0.0047s、峰值 0.02MiB；2m/1k 无关回答约 0.0251s、峰值低于 0.01MiB。
- Ruff：补充共享 `tests/conftest.py` 注册 `db` fixture，修正导入后 `ruff check app tests --no-cache` 通过。
- 验证：后端 `160 passed, 38 skipped`；计划相关后端测试 `20 passed, 4 skipped`；前端 `51 passed`；`npm run lint`、`npm run typecheck`、`npm run build`、`git diff --check` 通过。跳过项需要 `infra/compose.agent-test.yml` 专用集成环境，未对开发或生产数据执行测试。
