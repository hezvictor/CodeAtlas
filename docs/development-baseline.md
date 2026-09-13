# CodeAtlas 当前开发基线

版本：0.4 · 日期：2026-09-13 · 状态：Phase 4 题库与 ACM 工作流已完成

## 阶段状态

- Phase 1（账号与基础页面）：已完成。
- Phase 2（普通会话与聊天）：已完成普通模式、SSE、持久化、停止/失败处理、重试和历史分页。
- Phase 3（私人知识库与 RAG）：基础闭环已完成，包括分组、文件上传、MinIO、Arq Worker、解析、切块、1024 维 Embedding、pgvector/全文混合检索、引用校验、预览、下载和前端知识库页面。
- Phase 4（题库与 ACM 工作流）：已完成题库列表/详情、系统题目种子、`@` 题目关联、ACM 分析/解题模式和 C++/Java/Python 语言选择；不引入 LangGraph 和 PostgreSQL checkpoint。

## Phase 3 已实现

- 支持 Markdown、PDF、DOCX、TXT、C/C++、Java、Python 和 HTML 文件上传；不支持网页 URL 上传或抓取。
- 私人分组和文档 CRUD；所有资源按当前用户隔离。
- MinIO 私有 Bucket 保存原始文件，下载使用 5 分钟预签名 URL。
- 文档版本不可变；状态为 uploaded、parsing、chunking、embedding、indexed、failed。
- Arq + Redis 异步执行解析、切块和向量化，失败支持 API 重试/重新索引。
- PostgreSQL pgvector 1024 维向量、全文 tsvector、RRF 混合召回。
- 引用标记校验、引用持久化、SSE retrieval.completed/citations.validated/message.final。
- /knowledge 分组管理、上传、搜索、状态和文档预览；聊天页可选择知识库分组并将 knowledge_group_ids 传入 RAG。

## 尚未实现或限制

- 不支持网页 URL 抓取、OCR、表格专用解析、图片理解和 rerank。
- `resume` 仍是复用持久化消息，不是 checkpoint 恢复。
- 在线评测、编译执行和提交结果不在本阶段范围内；解题模式只做服务端基础静态代码检查。
- 前端暂未提供文档版本历史和独立引用跳转视图；已提供文本预览。

## 运行与验证

复制 .env.example 为 .env，配置 JWT_SECRET_KEY；真实回答和索引需要 DASHSCOPE_API_KEY、CHAT_MODEL、EMBEDDING_MODEL。

```powershell
docker compose up --build
docker compose --profile test run --rm backend-test
```

当前验证记录为后端 Docker 测试 54 passed、前端 Docker 生产构建通过、前后端健康检查通过；本机 `next build` 因环境进程卡顿未完成。当前迁移文件链已到 `0007_problem_acm_workflow`。

默认地址：前端 http://localhost:3000，后端 http://localhost:8000，MinIO 控制台 http://localhost:9001。
