# CodeAtlas 文档索引

- [实现说明：RAG、Agent、临时全文、生命周期与默认参数](agent-rag-architecture.md)
- [交互模块图](codeatlas-architecture.html)
- [API 契约](api-contract.md)
- [数据模型](data-model.md)
- [技术栈](technical-stack.md)
- [开发基线](development-baseline.md)
- [当前产品范围](product-requirements.md)
- [页面映射](frontend-screen-map.md)

`superpowers/` 保留长期资料、题库等历史设计与开发计划；其中部分路径指向已清理的旧脚本和验收材料，应作为历史记录阅读，当前流程以实现说明为准。历史 Alembic 文件保留完整升级路径。

`rag-evaluation/` 是离线契约与词面基线，不能替代当前运行机制及真实模型质量验收。旧浏览器结果、Docker 数据盘记录与前端动画实施计划已按清理选择移除；前端动画回归可在启动本地 3100 端口后，从项目根目录运行 `node scripts/check-frontend-motion.mjs`。
