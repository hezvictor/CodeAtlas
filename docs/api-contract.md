# CodeAtlas API 契约

API 前缀：`/api/v1`。除注册、登录、刷新和健康检查外，接口使用 Bearer access token。

## 已实现接口

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/auth/register` | 注册并返回 token 与用户 |
| POST | `/auth/login` | 登录并返回 token 与用户 |
| POST | `/auth/refresh` | 获取新 token |
| POST | `/auth/logout` | 撤销 refresh token |
| GET/PATCH | `/users/me` | 查询或修改用户资料 |
| PATCH | `/users/me/password` | 修改密码 |
| POST | `/users/me/avatar` | 上传头像 |
| GET/POST | `/conversations` | 查询或创建普通会话 |
| GET/PATCH/DELETE | `/conversations/{id}` | 查询、重命名或删除 |
| GET | `/conversations/{id}/messages` | 游标分页返回消息，支持 `limit` 和 `before` 参数 |
| POST | `/conversations/{id}/messages/stream` | SSE 流式聊天 |
| POST | `/conversations/{id}/run/stop` | 设置停止信号 |
| POST | `/conversations/{id}/run/resume` | 下一次请求复用已持久化消息 |
| GET/POST/PATCH/DELETE | `/knowledge/groups` | 私人知识库分组管理 |
| GET/POST | `/knowledge/documents` | 文档列表和 multipart 上传 |
| GET/DELETE | `/knowledge/documents/{id}` | 文档详情和软删除 |
| GET | `/knowledge/documents/{id}/status` | 查询处理状态 |
| POST | `/knowledge/documents/{id}/retry` | 重试失败处理 |
| POST | `/knowledge/documents/{id}/reindex` | 重新索引当前版本 |
| GET | `/knowledge/documents/{id}/preview` | 查看解析文本 |
| GET | `/knowledge/documents/{id}/download` | 获取短时效下载 URL |
| GET/POST/DELETE | `/conversations/{id}/attachments` | 管理会话文档附件 |
| GET | `/conversations/{id}/messages/{message_id}/citations` | 查询已验证引用 |

聊天模式支持 `normal`、`acm_analysis` 和 `acm_solution`。`acm_solution` 的 `solution_language` 支持 `cpp`、`java`、`python`。聊天内容去空白后长度为 1 到 20000。`knowledge_group_ids` 选择检索分组，`attachment_ids` 选择已挂载文档；`problem_id` 选择当前题库题目。重试内部使用 `reuse_last_user` 避免重复写入用户消息。

SSE 当前事件为 `run.started`、`retrieval.completed`、`retrieval.failed`、`run.first_token`、`message.delta`、`citations.validated`、`message.final`、`ping`、`run.interrupted`、`run.completed`、`run.failed`。知识库检索由请求中的 `knowledge_group_ids` 和 `attachment_ids` 控制；指定知识范围时检索失败会发送 `retrieval.failed` 并终止生成，未指定范围时会明确标记失败后继续普通聊天；引用只接受本次召回切片。消息支持 `completed`、`cancelled`、`failed` 状态；重新生成或编辑重试会删除目标消息及其后续消息后重新生成。

## 错误格式

```json
{"code":"VALIDATION_ERROR","message":"请求参数不合法","details":{}}
```

## 题库与首页接口

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/problems` | 按关键词、难度、标签分页查询当前用户自己的题目 |
| GET | `/problems/{id}` | 查询当前用户自己的题目详情 |
| POST | `/problems` | 创建当前用户题目 |
| PATCH | `/problems/{id}` | 修改当前用户题目 |
| DELETE | `/problems/{id}` | 删除当前用户题目 |
| GET | `/dashboard` | 查询首页真实会话统计和最近会话 |

系统题目是注册初始化模板，不直接出现在用户题库中。新账号注册事务会复制系统模板为 `source_type=default` 的用户题目；用户后续创建的题目使用 `source_type=user`。题目查询只返回当前用户自己的题目，创建、修改和删除也只能操作当前用户题目。ACM 分析模式必须提供 `problem_id`；ACM 解题模式必须同时提供 `problem_id` 和支持的编程语言。题目不存在或不属于当前用户时返回 404。

## 尚未实现接口

在线评测接口尚未注册。知识库接口已注册并以上表为准。

所有资源必须由服务端根据 token 中的用户 ID 过滤。
