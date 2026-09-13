# 题库与 ACM 工作流设计

**日期**：2026-09-11  
**状态**：已确认，进入实施  
**范围**：题库、题目关联、三种聊天模式、ACM 语言选择、基础代码验证和首页真实数据

## 目标

在现有 CodeAtlas FastAPI 编排、普通聊天 SSE、私人知识库 RAG 和用户隔离基础上，增加系统题库与 ACM 学习工作流。用户可以搜索题目、查看详情、在聊天中通过 `@` 选择题目，并使用普通、ACM 分析或 ACM 解题模式。

## 明确不做

- 本阶段不引入 LangGraph。
- 本阶段不引入 PostgreSQL checkpoint。
- 不实现 OCR、题目链接抓取、网页搜索、在线编译、OJ 提交、正式评测、知识图谱和多人共享。
- 基础代码验证只能说明静态检查结果，不能声称代码通过在线评测。

## 技术决策

### 编排方式

继续使用 `backend/app/routers/conversations.py` 当前的 FastAPI + SSE 编排方式。题目上下文和知识库检索在生成前解析，模型输出继续通过 `message.delta` 流式发送，消息状态继续使用现有 `completed`、`cancelled`、`failed`。

LangGraph 和 checkpoint 作为未来扩展边界保留，不新增图状态、thread 状态或 checkpoint 表。

### 题目模型

新增 `problems` 表。系统内置题目使用 `owner_user_id = NULL` 和 `source_type = system`；未来私人题目可使用用户 ID，但本阶段不开放用户题目 CRUD。

字段包括：题目 ID、所有者、来源类型、唯一标识、标题、难度、标签、题面、输入描述、输出描述、样例、约束、支持语言、全文检索字段和时间字段。

题目查询只返回系统题目或当前用户拥有的私人题目。题目详情和聊天关联都必须再次执行相同权限检查。

### 消息上下文

在 `messages` 增加 nullable `problem_id`、`mode` 和 `solution_language`。这样模式切换只影响下一次请求，历史消息仍能还原其实际题目和模式。

现有知识库 `citations` 结构保持不变。题目通过消息关联展示为题库来源，知识库引用继续关联 `DocumentChunk`，避免改变已有引用数据契约。

### 聊天模式

有效模式为：

- `normal`：普通问答，可选题目和知识库。
- `acm_analysis`：需要题目，不需要语言；输出题意、约束、算法和复杂度，不输出完整代码。
- `acm_solution`：需要题目和 `cpp`、`java`、`python` 之一；输出解释、复杂度、竞赛代码和基础验证结果。

服务端是最终校验方。前端语言弹窗只负责改善体验，不能替代 API 校验。

### 上下文和 RAG

题面直接作为题目上下文。选定的知识库分组或附件继续走现有混合检索。ACM 检索查询由题目标题、标签、题面摘要和用户问题组合而成。

用户文档继续按不可信资料处理，不能把文档中的指令提升为系统指令。知识库检索失败遵循现有语义：指定知识范围时失败终止；没有指定知识范围时可继续，但必须明确没有知识库依据。

### 输出保护

ACM 分析提示词禁止完整代码；服务端对 fenced code block 和明显完整程序进行基础清理，防止模型偶尔违反模式。ACM 解题模式允许完整代码，但必须声明基础验证范围，不能宣称在线评测通过。

## API

新增：

- `GET /api/v1/problems?query=&difficulty=&tag=&page=&page_size=`：分页搜索。
- `GET /api/v1/problems/{id}`：返回题目详情。
- `GET /api/v1/dashboard`：返回当前用户首页所需的今日会话数、最近会话和最新会话。

扩展 `ChatRequest`：

- `mode: normal | acm_analysis | acm_solution`
- `solution_language: cpp | java | python | null`
- `problem_id: UUID | null`

扩展消息响应和 SSE 元数据：模式、语言和题目 ID 都可被前端还原。

## SSE

保留现有事件，并增加 `context.resolved`：

- `run.started`：会话 ID、模式、题目 ID和语言。
- `context.resolved`：题目摘要和知识库检索范围。
- `retrieval.completed` / `retrieval.failed`：沿用现有语义。
- `run.first_token`、`message.delta`、`citations.validated`、`message.final`、`run.completed`、`run.interrupted`、`run.failed`：保持兼容，`message.final` 增加消息上下文元数据。

## 前端流程

- `/problems`：搜索、难度筛选、标签筛选、分页和题目摘要列表。
- `/problems/:id`：完整题面、样例、约束、支持语言，以及进入分析/解题的入口。
- `/chat`：模式菜单、语言选择、`@` 题目候选下拉、已选题目状态、题目来源和知识库引用。
- `/`：登录后读取 dashboard API；没有数据时显示真实空状态，不伪造统计。

题库详情入口通过 query 参数跳转聊天，例如 `/chat?problem_id=<id>&mode=acm_analysis`。发送前前端可以保留题目选择，但服务端仍重新加载题目。

## 错误和安全

- 题目不存在或不属于当前用户时返回 404。
- ACM 分析缺少题目、ACM 解题缺少题目或语言时返回 422/400，并使用项目统一错误格式。
- 不改变现有 Bearer token、用户隔离、知识库权限和普通聊天失败/停止/重试行为。
- 题目种子迁移必须幂等，不覆盖用户数据。
- 日志不记录模型密钥、完整私人文档或不必要的题面内容。

## 验收

- 新账号能看到系统内置题目并通过关键词、难度和标签筛选。
- 题目详情可从题库进入聊天。
- 聊天输入 `@` 能选择题目并发送 `problem_id`。
- 普通模式行为不回归。
- ACM 分析模式缺少题目时拒绝请求，成功回答不含完整代码块。
- ACM 解题模式缺少语言时拒绝请求，选择三种语言之一后生成对应代码。
- 停止、失败、重试、刷新历史后题目和模式元数据一致。
- 首页使用真实数据并覆盖无会话空状态。
- 后端测试、前端构建、Docker Compose 和浏览器主流程通过。
