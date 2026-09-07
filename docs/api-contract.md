# CodeAtlas 初版 API 契约

API 前缀：`/api/v1`。所有需要登录的接口使用 Bearer access token。错误统一返回：

```json
{"code":"VALIDATION_ERROR","message":"请求参数不合法","details":{}}
```

## 1. 认证

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/auth/register` | 邮箱、密码、昵称注册 |
| POST | `/auth/login` | 返回 access token 和 refresh token |
| POST | `/auth/refresh` | 刷新 access token |
| POST | `/auth/logout` | 撤销 refresh token |
| GET | `/users/me` | 当前用户资料 |
| PATCH | `/users/me` | 修改昵称、头像 |
| PATCH | `/users/me/password` | 修改密码 |

## 2. 会话与消息

| 方法 | 路径 | 说明 |
|---|---|---|
| GET/POST | `/conversations` | 查询/创建会话 |
| GET/PATCH/DELETE | `/conversations/{id}` | 查询、重命名、删除 |
| GET | `/conversations/{id}/messages` | 分页查询消息 |
| POST | `/conversations/{id}/messages/stream` | SSE 流式发送消息 |
| POST | `/conversations/{id}/run/stop` | 停止当前运行 |
| POST | `/conversations/{id}/run/resume` | 从 checkpoint 恢复 |

发送消息请求至少包含：`content`、`mode`、`solution_language`（解题模式必填）、`attachment_ids`、`problem_id`。

SSE 事件：`run.started`、`retrieval.completed`、`message.delta`、`citation.created`、`run.interrupted`、`run.completed`、`run.failed`。

## 3. 知识库和文件

| 方法 | 路径 | 说明 |
|---|---|---|
| GET/POST | `/knowledge/groups` | 查询/创建分组 |
| GET | `/knowledge/documents` | 按分组、状态、关键字查询 |
| POST | `/knowledge/documents/upload` | 上传并创建处理任务 |
| GET | `/knowledge/documents/{id}` | 文档详情和处理状态 |
| POST | `/knowledge/documents/{id}/retry` | 重试处理 |
| POST | `/knowledge/documents/{id}/reindex` | 重新索引 |
| DELETE | `/knowledge/documents/{id}` | 删除文档及向量 |
| GET | `/knowledge/documents/{id}/preview` | 获取预览内容 |

## 4. 题库

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/problems` | 搜索、分页、难度和标签过滤 |
| GET | `/problems/{id}` | 题面与元数据 |
| GET | `/problems/mentions?q=` | `@` 选择器搜索 |

## 5. 权限原则

所有会话、附件、知识库、文档、分块和引用查询必须由服务端根据 token 的 `user_id` 做归属过滤，不能信任前端传入的用户 ID。
