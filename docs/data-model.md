# CodeAtlas 数据模型

更新：2026-09-29。精确字段、索引和外键以 `backend/app/models.py` 与 Alembic 为准。ID 使用 UUID，时间使用 UTC。

| 数据 | 持久位置与用途 |
|---|---|
| users / refresh_tokens | 账号、资料、令牌与默认模型 |
| problems | 用户拥有的题面；注册时复制默认题目；删除题目不会删除历史消息 |
| conversations / messages | 会话、模式、合规用户输入、通过校验的最终回答；停止不保存未校验半成品 |
| model_connections / chat_models | 加密凭证、模型名、聊天连接检测结果与兼容保留的可选上下文容量 |
| embedding_configs / reranker_configs | 用户检索模型配置 |
| knowledge_groups / documents / document_versions | 长期资料组织、版本、有效索引 generation、处理与删除状态 |
| document_chunks | 长期正文分块、位置、pgvector 向量、全文检索字段 |
| document_jobs | 长期后台任务、阶段、进度、有限重试、租约与错误 |
| citations | 已验证长期引用的必要快照 |
| chat_runs | 后台聊天状态、消息/模型关联、归属租约、预算计数、累计活跃时间、事件序号及安全错误码 |
| checkpoints 等 LangGraph 表 | 仅控制标记与计数；不包含模型输入、工具参数或结果 |
| legacy_chat_associations | 迁移保留的旧关联归档；没有活动 ORM 或业务接口 |

聊天请求与模型不接受旧知识库范围或关联字段。同一会话只有一个 queued/running/waiting_context 运行，数据库部分唯一索引与归属条件负责并发控制。

临时文件全文、文件名和文件 ID 只放独立非持久 Redis；不进入上述长期文档表、消息元数据、队列或检查点。消息最终答案允许受限摘录与学习结论，保存前执行全文、元数据和引用比例检查。

旧会话文档与索引保留但不参与新检索；`documents.scope` 仅用于区分有效长期资料与历史归档，不能重新作为聊天选择开关。历史迁移保留升级路径；用户原件和历史资料不自动清理。

数据期限、删除流程与失败恢复见 [实现说明](agent-rag-architecture.md)。
