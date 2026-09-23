# CodeAtlas API 契约

更新：2026-09-23。API 前缀为 `/api/v1`。除注册、登录、刷新外，业务接口使用 Bearer access token；资源查询按当前用户过滤。精确请求体、响应字段和状态码以运行中的 FastAPI `/docs` 为准。

| 资源 | 已实现操作 |
|---|---|
| `/auth` | 注册、登录、刷新、登出 |
| `/users/me` | 查询/更新资料、修改密码、上传头像 |
| `/dashboard` | 首页会话统计 |
| `/problems` | 用户题目分页列表、创建、详情、更新、删除 |
| `/model-connections` | 连接增删改查、模型发现/新增/验证/设默认、可用模型列表、Embedding 与 Reranker 配置/验证 |
| `/conversations` | 列表、创建、详情、重命名/置顶、删除、批量置顶/取消置顶/删除 |
| `/knowledge/groups` | 分组列表、创建、更新、删除 |
| `/knowledge/documents` | 上传策略、列表/上传、详情、版本列表/上传、状态、预览、下载、软删除、重试、重建索引 |

## 聊天与附件

- `GET /conversations/{id}/messages?limit=30&before=<ISO 日期>` 返回 `{items, has_more, next_before}`；`limit` 限制在 1–100。
- `POST /conversations/{id}/messages/stream` 返回 SSE。请求包含 `content`、`mode`、`chat_model_id`、`knowledge_scope`、`problem_id`、`solution_language`、`attachment_ids`，重试可使用 `reuse_last_user=true`。`knowledge_scope` 仅允许 `none` 或 `all`。ACM 分析要求题目；ACM 解题还要求 `cpp`、`java` 或 `python` 语言。
- `POST /conversations/{id}/messages/{message_id}/retry` 可编辑用户消息并删除之后的历史，或删除最新一条助手消息供重新生成；运行中返回 409。该接口仅准备历史，随后仍需调用消息流接口发起生成。
- `GET /conversations/{id}/runs/active` 查询当前进程持有的运行快照；`GET /conversations/{id}/runs/{run_id}/stream` 订阅该运行；`POST /conversations/{id}/run/stop` 请求停止；`POST /conversations/{id}/run/resume` 返回可发送后续请求的状态，不恢复原流。
- `GET /conversations/{id}/messages/{message_id}/citations` 返回已验证引用及文档元数据。
- `GET /conversations/{id}/attachments` 列出关联；`POST /conversations/{id}/attachments/upload` 上传会话临时文件；`POST /conversations/{id}/attachments/{document_version_id}` 关联已索引文档版本；`DELETE /conversations/{id}/attachments/{attachment_id}` 移除关联。

SSE 主要事件为 `run.snapshot`、`run.started`、`retrieval.completed`（状态为 `not_requested`、`no_hit`、`ok` 或 `failed`）、`run.first_token`、`message.delta`、`citations.validated`、`message.final` 和 `run.completed` / `run.interrupted` / `run.failed`。已完成运行的重连先给完整快照，再重放非增量事件，不重放 token 增量。事件记录只保存在持有该运行的后端进程内，且会过期清理。

普通 HTTP 错误使用 `{code, message, details}`，请求校验失败返回 422。`run.failed` 是 SSE 事件，HTTP 可能已经返回 200；前端需同时处理传输错误和流内失败。

当前没有在线评测、编译执行或 checkpoint 恢复接口。
