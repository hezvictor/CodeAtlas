# CodeAtlas 浏览器与集成验证结果

执行日期：2026-09-11
测试工具：agent-browser 与 Docker Compose
前端：http://localhost:3000
后端：http://localhost:8000

## 环境结果

- Docker Compose 已启动前端、后端、Worker、PostgreSQL、Redis 和 MinIO。
- Alembic current 为 0005_embedding_dimensions (head)。
- /health、/ready、/knowledge 均返回 200。
- 前端 Next.js 生产构建通过。
- backend-test 测试套件 27 passed。

## Phase 3 结果

| 用例 | 结果 | 实际结果 |
|---|---|---|
| 分组管理 | 通过 | 创建、列表和用户隔离接口可用 |
| HTML 上传 | 通过 | 扩展名、文件头和大小校验生效 |
| 文档处理 | 通过 | Worker 执行解析、切块、Embedding、索引状态流转 |
| HTML 清理 | 通过 | BeautifulSoup 移除 script/style/nav/footer |
| 文档预览 | 通过 | indexed 文档返回解析文本和定位信息 |
| 私有下载 | 通过 | 返回 5 分钟预签名 URL，资源按用户隔离 |
| 混合检索 | 通过 | PostgreSQL 全文 + pgvector，RRF 合并 |
| 引用校验 | 通过 | 仅持久化本次召回切片的有效引用 |
| 聊天分组选择 | 通过 | knowledge_group_ids 已写入 SSE 请求 |
| 重试一致性 | 通过 | reuse_last_user 避免重试重复创建用户消息 |

## 未覆盖或限制

- 尚未用浏览器完成真实 DashScope Embedding 的跨账号完整 RAG 对话回归；后端解析、检索、引用和 Worker 测试已覆盖。
- 尚未完成移动端视口截图矩阵和 stop/resume 独立浏览器流程。
- 当前不支持网页 URL、OCR、rerank、题库、ACM 工作流和 LangGraph checkpoint。
