# CodeAtlas 开发路线

## 已完成：账号与基础页面

已实现导航、注册/登录/刷新/登出、JWT + Argon2、用户资料接口、账号迁移和前端登录态。

## 已完成：普通会话与聊天

已实现会话 CRUD、消息持久化、百炼兼容接口、SSE 增量回答、首条消息自动命名、运行互斥和停止信号；前端已补齐停止按钮、断线/失败状态展示、消息游标分页、重新生成与编辑重试，以及模型耗时和首 token 时延记录。

当前只支持普通模式；`resume` 不是 LangGraph checkpoint 恢复。重新生成或编辑重试时，从目标消息开始截断后续消息，再基于截断后的历史重新生成。

## 已完成：私人知识库与 RAG 基础闭环

已实现分组、文件上传、MinIO、Arq 异步解析、切块、Embedding、pgvector/全文混合检索、引用校验和文档预览。当前支持 Markdown、PDF、DOCX、TXT、C/C++、Java、Python 和 HTML 文件上传，不支持网页 URL 抓取。Embedding 使用部署中 `text-embedding-v3` 的 1024 维向量。

## 已完成：题库与 ACM 工作流

已实现题目搜索/详情、系统题目种子、`@` 题目选择、ACM 分析模式、语言选择和解题模式。当前由 FastAPI 服务编排，不引入 LangGraph 和 PostgreSQL checkpoint；LangGraph/checkpoint 作为未来单独阶段。

## 长期计划

公开知识库与协作权限、OCR、训练计划、错题整理、知识图谱、在线 OJ、编译评测、比赛系统、讨论区、排行榜、其他模型和本地模型部署。
