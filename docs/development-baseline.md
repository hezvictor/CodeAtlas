# CodeAtlas 当前开发基线

版本：0.3 · 日期：2026-09-11 · 状态：Phase 3 基础能力已完成，持续验证中

## 阶段状态

- Phase 1（账号与基础页面）：已完成。
- Phase 2（普通会话与聊天）：已完成普通模式、SSE、持久化、停止/失败处理、重试和历史分页；未实现 ACM 工作流和 LangGraph checkpoint 恢复。
- Phase 3（私人知识库与 RAG）：基础闭环已完成，包括分组、文件上传、MinIO、Arq Worker、解析、切块、1024 维 Embedding、pgvector/全文混合检索、引用校验、预览、下载和前端知识库页面。
- Phase 4（题库与 ACM 工作流）：尚未开始。

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
- 当前只提供普通聊天模式；resume 是复用持久化消息，不是 checkpoint 恢复。
- 题库、@ 题目选择、ACM 分析/解题模式、语言选择和在线评测尚未实现。
- 前端暂未提供文档版本历史和独立引用跳转视图；已提供文本预览。

## 运行与验证

复制 .env.example 为 .env，配置 JWT_SECRET_KEY；真实回答和索引需要 DASHSCOPE_API_KEY、CHAT_MODEL、EMBEDDING_MODEL。

```powershell
docker compose up --build
docker compose --profile test run --rm backend-test
```

当前验证：后端 Docker 测试 27 passed；前端生产构建通过；Compose 中 PostgreSQL/Redis/MinIO/Backend/Worker/Frontend 均可启动；/health、/ready 和 /knowledge 返回 200；数据库 revision 为 0005_embedding_dimensions。

默认地址：前端 http://localhost:3000，后端 http://localhost:8000，MinIO 控制台 http://localhost:9001。
