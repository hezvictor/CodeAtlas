# RAG 离线评测材料

`hzvictory-template-v1.md` 包含20条内部用例，后端测试检查用例编号、学习模式和关键约束。该材料是离线契约与词面基线，不能代表实际在线检索、Agent 决策或教学答案质量。

```powershell
cd backend
uv run python -m pytest tests/test_rag_evaluation_contract.py -q -p no:cacheprovider
uv run python -m scripts.evaluate_rag --top-k 5
```

质量检查包括期望章节召回、解释与代码联合证据、无命中/检索失败不伪造引用、分析模式不输出完整提交程序、有效版本过滤以及资料中图片信息缺失时明确说明。

当前运行固定首次长期检索并允许有限工具补查；临时全文不进入该评测集的索引流水线。
