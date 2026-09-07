# CodeAtlas 开发文档

这些文档与 `页面原型/index.html` 共同构成初版开发基线。原型用于确认页面结构和交互位置，文档用于确认业务边界、接口和数据约束。

## 阅读顺序

1. [development-baseline.md](development-baseline.md)：初版范围、开发顺序和完成定义。
2. [product-requirements.md](product-requirements.md)：完整产品功能需求和非功能要求。
3. [frontend-screen-map.md](frontend-screen-map.md)：页面路由、布局和交互状态。
4. [technical-stack.md](technical-stack.md)：技术选型、系统架构和 RAG/LangGraph 流程。
5. [api-contract.md](api-contract.md)：前后端接口和 SSE 事件。
6. [data-model.md](data-model.md)：数据库表、索引和权限约束。
7. [roadmap.md](roadmap.md)：阶段计划和后续决策。

## 基线约定

- 产品名：CodeAtlas。
- 页面方向：A / 对话优先。
- 当前模型服务：阿里云百炼；密钥只通过环境变量提供。
- 当前知识库：单用户私人知识库。
- 当前部署目标：个人或小规模服务器，Docker Compose。
- `页面原型` 是 throwaway prototype，接通后端时应按文档重写为生产组件，不直接复制原型代码。

## 变更规则

需求、接口或数据模型发生变化时，先更新对应文档，再修改代码。每次较大的变更更新版本号和日期，并在 `roadmap.md` 的决策记录中留下原因。
