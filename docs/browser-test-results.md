# CodeAtlas 浏览器测试结果

执行日期：2026-09-07
测试工具：agent-browser
前端：`http://localhost:3000`
后端：`http://localhost:8000`

## 环境结果

- Docker Compose 已成功启动前端、后端、PostgreSQL、Redis 和 MinIO。
- 后端健康检查：`GET /health` 返回 `200`。
- 前端生产镜像构建通过。
- Docker 构建过程中发现并修复 `backend/pyproject.toml`、`backend/alembic.ini` 的 BOM 兼容问题。

## 用例结果

| 用例 | 结果 | 实际结果 |
|---|---|---|
| 首页加载 | 通过 | 页面和固定导航正常 |
| 登录页加载 | 通过 | 表单控件正常 |
| 注册成功 | 通过 | 新账号创建成功并跳转 `/chat` |
| 重复邮箱注册 | 通过 | 全局提示 `Email already registered` |
| 错误密码登录 | 通过 | 全局提示 `Invalid email or password`，留在登录页 |
| 正确账号登录 | 通过 | 成功跳转 `/chat`，并拉取会话列表 |
| 新建会话 | 通过 | 左侧出现“新对话”，输入框启用 |
| 发送消息 | 通过 | 用户消息立即显示，SSE 请求完成 |
| 模型未配置 | 通过 | 助手消息显示 `CHAT_MODEL and DASHSCOPE_API_KEY are required`，没有白屏 |
| 首条消息自动命名 | 通过 | 会话名自动变为消息摘要 `binary search` |
| 双击重命名 | 通过 | 可编辑并按 Enter 保存为 `renamed session` |
| 消息复制 | 通过 | 按钮状态变为 `已复制` |
| 模式菜单 | 通过 | 普通模式可用，ACM 两项显示 Phase 4 占位 |
| 右侧回答依据 | 通过 | Phase 3 未实现说明正常显示 |
| 题库占位页 | 通过 | Phase 4 占位内容正常 |
| 知识库占位页 | 通过 | Phase 3 占位内容正常 |
| 聊天未登录保护 | 通过 | 未登录时显示“请先登录” |
| 后端健康检查 | 通过 | `/health` 返回 `200` |

## 追加验证\n\n- `.env` 中的模型配置已传入后端容器，容器内检查为 `model-configured`。\n- 真实请求通过 SSE 完成，助手消息已渲染：`Binary search is an efficient algorithm...`。\n- 后端 `/health` 和 Docker 服务均保持正常。\n\n## 未覆盖

- 真实 DashScope 模型流式回答：通过。补充映射 Compose 环境变量后，浏览器收到完整英文回答并显示在助手消息中。此前发现并修复了上游 `choices: []` 事件导致的 `list index out of range`。
- 停止生成和恢复：当前浏览器流程未触发独立 stop/resume 操作。
- 移动端视口截图：本轮重点覆盖了完整业务链路，尚未做视口矩阵截图。

测试方案：`docs/browser-test-plan.md`
测试截图：`test-artifacts/login-page.png`