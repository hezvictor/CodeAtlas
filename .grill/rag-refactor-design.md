# Grill: RAG refactor and chat context design
Date: 2026-09-22

## Intent
重构现有 RAG 流程，提升代码知识库和 Markdown 技术总结的索引稳定性、召回相关性、长文本上下文质量和引用可靠性。聊天界面需要支持普通聊天、ACM 分析、ACM 解题三种模式，并允许每条消息选择是否使用知识库；引用文档继续在右侧展示。

## Constraints
- 聊天知识库范围只保留 `none` 和 `all`。
- `none` 表示本条消息不检索知识库。
- `all` 表示检索所有当前用户的长期知识库文档，并包含当前会话附件。
- 知识库分组字段和分组管理界面保留，但不再参与聊天请求或 RAG 过滤。
- 新建会话默认使用 `none`。
- 会话需要保存最近使用的知识库状态；重新打开会话时恢复该状态。
- 流式生成期间锁定模式和知识库开关，切换只作用于下一条消息。
- 文档上传或重新索引时才执行解析、切块和 Embedding；每次发送消息只执行检索，不重复索引。
- 语料以代码为主，包含 Markdown 技术总结、复杂度分析、模板代码块，规模可能持续增长并出现长文本。
- ACM 分析不强制选择题库题目，可以直接使用用户文本描述；分析模式不输出可直接提交的完整代码。
- ACM 解题必须选择编程语言，但题库题目可选，也可以使用用户文本描述。
- ACM 解题在启用知识库时需要参考对应语言的个人代码风格。
- 模式切换和知识库切换应显示非模型可见的聊天状态分隔提示。

## Key decisions
- Decision: 保留 FastAPI、Arq/Redis、MinIO、PostgreSQL/pgvector。Reason: 现有基础设施已经覆盖异步索引、对象存储、全文检索和向量检索，迁移数据库的收益不足。Alternative considered: 直接迁移到独立向量数据库，暂不采用。
- Decision: 暂不引入 LangGraph。Reason: 当前目标是固定的检索流水线，不是复杂 Agent 状态机。Alternative considered: 用 LangGraph 重写聊天运行时，暂不采用。
- Decision: LangChain 只作为可选适配层，不接管权限、会话、检索 SQL 和引用持久化。Reason: 保持现有边界清晰并降低迁移成本。
- Decision: 采用显式 RAG 阶段：结构化解析、父子 chunk、批量 Embedding、全文与向量混合召回、rerank、上下文扩展、生成、引用校验和评测。
- Decision: Markdown 标题、解释、复杂度和完整代码块优先作为父 chunk；子 chunk 用于精确召回，父 chunk 用于上下文扩展。
- Decision: 借鉴 Quivr 的 query rewrite/retrieve/rerank/generate、PaperQA 的证据相关性阈值、RAGFlow/WeKnora 的结构化解析和父子 chunk、Langchain-Chatchat/FastGPT 的 BM25+向量+rerank、PageIndex 的长文档层级索引、Ragas/Promptfoo 的质量评测。
- Decision: ACM 模式按消息独立快照处理。`normal` 不要求题目和语言；`acm_analysis` 题目可选且只给思路；`acm_solution` 语言必选且题目可选。
- Decision: 会话保存下一次打开时的默认模式、知识库状态和 ACM 上下文；消息保存本次实际使用的 mode、knowledge scope、problem、language 和引用。
- Decision: 状态提示通过前端根据相邻消息快照差异渲染，不作为模型消息发送；可显示“已切换到 ACM 分析模式”“本条消息将使用知识库”等分隔条。
- Decision: ACM 解题的代码风格参考单独作为 style context，与题目证据分开召回和展示；默认按语言维护个人风格画像，冲突风格后续再支持覆盖。
- Decision: 长文本 Embedding 错误优先通过分批请求、单块长度/token 限制、失败批次重试和错误响应记录解决；当前 400 很可能来自一次请求发送过多 chunks 或输入过长。
- Decision: 查询采用双路策略：保留原始查询，同时基于历史生成改写查询；两路候选合并后再 rerank。Reason: 支持多轮省略表达，又保护代码标识符和模板名称。
- Decision: 为每个用户增加独立的可选 reranker 配置；配置后对混合召回候选精排，未配置时直接使用 RRF 结果。Reason: 提升相关性，同时兼容当前 Embedding 配置和多种 reranker 服务。
- Decision: Embedding 和 reranker 都采用“项目级默认配置 + 用户级可选覆盖”；Embedding 配置变化提示需要重新索引，reranker 配置变化立即影响查询但不触发重索引；相关模型设置页面同步更新。Reason: 普通用户开箱即用，高级用户可覆盖，且区分索引期和查询期依赖。
- Decision: `all` 下检索服务失败时终止本次生成并返回明确的可重试错误；检索成功但没有命中时允许生成，并明确标记没有找到相关资料。Reason: 不把基础设施失败伪装成无命中，也不在用户要求知识库时静默退化为无依据回答。
- Decision: 文件尚未完成索引时允许继续聊天，但 pending/failed 文件不参与 `all` 检索；前端显示处理状态，索引完成后下一条消息自动生效。Reason: 上传和索引异步解耦，避免阻塞聊天。
- Decision: 本轮不扩展会话压缩或持久化摘要系统，保留现有普通历史裁剪，优先完成 RAG 索引、召回、重排、上下文和引用重构。Reason: 控制范围，先解决知识库质量问题。
- Decision: 使用 `docs/hzvictory模板-最终版.md` 建立第一版内部 RAG 评测集，先以标题和行号作为黄金来源标识，覆盖代码模板、解释与代码联合召回、多轮改写、长文、ACM 模式、代码风格和无命中。Reason: 当前项目代码/文档不代表实际 ACM 语料，真实模板文档更适合验证目标效果。
- Decision: 第一阶段不把文档图片 OCR 或多模态解析纳入索引；保留原 Markdown 和图片引用，图片中独有的信息不进入当前评测集。Reason: 当前目标先验证文本/代码 RAG 主链路，避免把 OCR 误识别混入基线；后续可单独增加 OCR 评测集。

## Surfaced assumptions
- 当前 `Conversation.mode` 和 `Message.mode` 可作为模式状态基础，但需要新增持久化的知识库范围字段；消息需要记录范围以便历史显示。
- 当前引用右侧展示链路可以继续使用，但需要区分“未检索”“检索无命中”和“存在有效引用”。
- 当前 PostgreSQL 全文检索和 pgvector 的用户隔离逻辑可以继续复用。
- 题库题目只是 ACM 上下文的增强来源，不应限制用户使用自然语言描述题目。
- 代码知识库可能包含多种风格，因此风格参考必须受语言和相关性约束，不能无条件复制检索到的代码。

## Open questions
- 是否允许同一会话在 ACM 模式之间切换时记住上一次选择的题目和语言；推荐记住，缺失时再要求选择。
- 是否需要为不同编程语言建立可编辑的个人代码风格画像，以及用户如何覆盖自动推断风格。
- 长期知识库规模、文件数量、单文件最大大小和可接受的索引延迟尚未确定。
- 是否需要在知识库检索失败时终止本次回答，还是继续普通回答并显示失败状态。
- 需要建立哪些真实问题集来衡量代码模板召回、长文上下文、引用准确性和 ACM 输出质量。
- 是否在后续独立阶段加入 token-aware 历史裁剪和持久化会话摘要。

## Out of scope
- 本阶段不立即修改代码。
- 本阶段不直接复制或整体迁移 Dify、RAGFlow、LangChain-Chatchat 等项目。
- 本阶段不把知识库分组删除；只移除其在聊天检索协议中的作用。
- 本阶段不默认引入知识图谱、多模态 RAG 或 PageIndex 全量替换现有索引。
