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

模式当前只接受 `normal`。聊天内容去空白后长度为 1 到 20000；附件和题目字段只做协议保留，尚未处理。

SSE 当前事件为 `run.started`、`retrieval.completed`（固定 `count: 0`）、`run.first_token`、`message.delta`、`ping`、`run.interrupted`、`run.completed`、`run.failed`。尚未发送引用事件。消息支持 `completed`、`cancelled`、`failed` 状态；重新生成或编辑重试会删除目标消息及其后续消息后重新生成。

## 错误格式

```json
{"code":"VALIDATION_ERROR","message":"请求参数不合法","details":{}}
```

## 规划接口

知识库文件、文档和题库接口尚未注册。原规划路径见 [product-requirements.md](product-requirements.md) 和 [roadmap.md](roadmap.md)，上线前需以实际路由和 schema 重新确认。

所有资源必须由服务端根据 token 中的用户 ID 过滤。
