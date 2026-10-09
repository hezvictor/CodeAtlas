# CodeAtlas API 契约

更新：2026-09-29。前缀 `/api/v1`，资源查询按当前用户过滤。精确 schema 以 FastAPI `/docs` 为准。

账号、用户资料、首页、私人题库、模型连接、会话管理、知识库分组与长期文档接口继续保留。

首页 `GET /dashboard` 的 `today_conversation_count` 按北京时间（UTC+08:00）当天 00:00 至次日 00:00 的 `conversations.created_at` 统计；只包含当前用户。最近会话仍按更新时间排序。

## 聊天、运行与临时全文

- `POST /conversations/{id}/messages/stream`：请求 `content`、`mode`、`chat_model_id`、可选 `problem_id`、`solution_language`、重试 `reuse_last_user`。普通/ACM 共用运行；可粘贴题面，解题必须指定 cpp/java/python。旧范围与资料关联字段不接受，额外字段返回422。
- `GET /conversations/{id}/messages?limit=30&before=<消息位置>`：按消息持久顺序分页 `{items,has_more,next_before}`；每条消息包含整数 `position`，`next_before` 是同一序列的整数游标。
- `POST /conversations/{id}/messages/{message_id}/retry`：准备编辑重试或重新生成历史，再调用消息流；活跃运行409，临时内容持久化限制在修改前检查。
- `GET /conversations/{id}/runs/active`：共享数据库中的活跃运行快照或 null。
- `GET /conversations/{id}/runs/{run_id}/stream`：订阅原运行，先快照再安全过程事件，跨实例工作。
- `POST /conversations/{id}/run/stop`：持久取消状态并取消模型请求；不保存半成品。
- `POST /conversations/{id}/run/resume`：仅 waiting_context 可用，先补传文件，再恢复同一 run ID，保留预算并重建依赖推理。
- `GET /conversations/{id}/messages/{message_id}/citations`：本次实际证据支持的引用及必要历史来源。
- `GET /conversations/{id}/temporary-files`：当前会话非持久缓存的公开临时元数据，不返回全文。
- `POST /conversations/{id}/temporary-files`：raw body，`X-File-Name=encodeURIComponent(filename)`；内存解析后只进独立非持久缓存，201表示全文就绪；无文档/版本/索引记录。
- `DELETE /conversations/{id}/temporary-files/{file_id}`：清除缓存；运行中禁止修改，waiting_context允许补传/移除。

旧聊天资料关联接口已移除，不提供兼容。临时文件格式不含 PDF/OCR；DOCX 无法解读的嵌入对象、公式和图片明确拒绝。

## 实时事件

`run.snapshot`、`run.started`、`retrieval.started/completed`、`model.started/retrying/completed`、`tool.started/retrying/completed`、`citations.validated`、`message.final`、`run.waiting/completed/interrupted/failed`。事件包含安全标题、状态、条数、步骤标识与单调序号；不含原始参数、工具正文或隐藏思维链。

初次检索状态为 no_hit/ok/failed。最终正文先缓冲校验再返回，不推送未校验 token。事件最多128条/24小时；最终消息和状态可从数据库恢复。断线不重新发送问题；重连订阅同一运行并按序号去重。等待补传及终态结束当前订阅。

HTTP 错误使用现有 `{code,message,details}`；SSE失败需从流事件处理，HTTP可能已200。已知容量不足、输出隐私限制与预算超限都有明确安全错误码；容量未知时由模型服务商判断超限。

## 模型配置

模型测试发送一次普通聊天请求，成功时记录 `capabilities.chat=verified`。聊天连接验证成功即可设默认或进入 available 列表；不检测工具调用或结果回传。连接凭证变化清除验证；检测期间修改连接不能提交旧结果。新检测模型走普通聊天；旧模型保留已验证工具能力时可继续补查。

`PATCH /model-connections/{connection_id}/models/{model_id}` 仍兼容修改可选的 `context_window_tokens`；模型配置界面无需填写，测试也不推断容量。已有可信容量可用于提前判断临时文件超限；容量未知时允许发送，超限由服务商返回。网络或限流失败记为 incomplete，失败不自动切换模型。

## 文档生命周期（2026-09-28）

- `GET /knowledge/documents/policy` 返回服务端支持的扩展名、单文件大小和格式说明，所有上传入口使用同一策略。项目不提供 PDF 解析；不支持格式的既有原文件仍可下载或删除，不能重试或重新索引。
- `POST /knowledge/documents/preflight` 接收 `{filename, sha256, group_id}`，返回当前用户目标分组内的冲突文档与 `same_content`。未分组使用 `group_id=null`。
- `POST /knowledge/documents` 使用 multipart：`file`、可选 `group_id`、`title`、`upload_token`（UUID）、`conflict_action`（`new_version` / `independent`）、`target_document_id`。服务器在锁内再次校验冲突；不同内容且没有明确选择返回 409。相同内容默认返回已有文档。独立文档追加北京时间时间戳并保持扩展名，页面、对象 key 末段、下载名称一致。
- 202 表示原文件已保存到 MinIO 且后台任务已持久化；不能解释为已经可检索。相同 `upload_token` 重试不会重复创建版本。
- 文档响应包含 `latest_version`（最新提交）、`active_version`（当前可检索）、`operation`（最新任务与阶段、尝试次数、完成块数/总块数、下次重试时间、错误）、`cleanup_status`、`cleanup_error` 和 `deleted_at`。
- 后台阶段：`queued` → `parsing` → `chunking` → `embedding` → `committing` → `indexed`。无可用配置进入 `waiting_embedding`；配置验证成功后自动重新排队。429、超时、5xx 在有限次数内自动重试；400 等永久错误停止，手动重试复用已保存原文件。
- `GET /knowledge/documents/summary` 返回 `ready`、`processing`、`waiting`、`failed`、`completed` 与 `completed_job_ids`。`POST /knowledge/documents/acknowledge` 接收 `{job_ids}`，只标记当前用户已完成任务。客户端只提交实际观察到的任务 ID，避免误消除随后完成的标记。
- 新版本与重新索引使用独立 staging generation，完整非空索引才原子切换。预览/下载优先当前有效版本；历史版本仅保留简要记录，不提供下载或恢复。
- `DELETE /knowledge/documents/{id}` 返回 204 后立即停止参与检索并取消文档处理。列表保留删除中/清理失败记录，后台清理完成才隐藏；清理失败自动重试。删除和版本替换清理原文件、提取文本及向量/全文索引，历史引用以快照保留并返回 `source_deleted`。
