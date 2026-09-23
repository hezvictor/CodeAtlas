# RAG 评测集

`hzvictory-template-v1.md` 是当前代码模板知识库的第一版内部评测集，共 20 条用例。

后端契约测试会解析这份 Markdown，检查用例编号、聊天模式、知识库范围和关键约束是否完整：

```powershell
cd backend
pytest -q tests/test_rag_evaluation_contract.py

# 运行真实源文档上的离线词法基线
python -m scripts.evaluate_rag --top-k 5
```

这份评测集先验证检索契约和 grounding 行为，不要求源文档中的代码可以直接编译。图片内容暂时不进入索引，因此涉及图片独有信息的回答必须明确说明资料不足。

质量验收重点：

- `all` 用例在前五个结果中命中至少一个期望章节。
- 标记 `must_retrieve_together` 的用例同时召回解释和代码，或通过父级上下文覆盖两者。
- `none` 不产生检索调用和引用。
- 无命中时不生成虚构模板或引用。
- `acm_analysis` 不输出可直接提交的完整程序，`acm_solution` 才允许完整代码。
- 未索引文件不进入检索结果，并暴露 pending 状态。
