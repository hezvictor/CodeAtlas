# CodeAtlas RAG Evaluation Set: hzvictory Template v1

Source document: `docs/hzvictory模板-最终版.md`

Source size at creation: 3,355 lines / approximately 68 KB / 50+ fenced C/C++ blocks.

This is a retrieval-and-grounding evaluation draft. Expected sources use source
headings and line numbers so that the cases remain stable when chunk IDs change.

## Evaluation semantics

- `all` means the source document is eligible for retrieval.
- `none` means no source should be retrieved or cited.
- `expected_sources` are acceptable evidence regions, not necessarily one exact chunk.
- `must_retrieve_together` marks cases where explanation and code should be expanded as one parent context.
- `style_sources` are style-only references and must not be treated as algorithm evidence.
- A valid answer must not claim that this document contains information that is only present in an image.

## Cases

### R01: Binary-search template direction

- mode: `normal`
- query: `二分答案求最小的最大值和求最大的最小值分别应该怎么写？mid 为什么一个不加 1，一个要加 1？`
- expected_sources:
  - `2.1.2 二分答案模板` (approximately lines 226-264)
  - `2.1.6 二分总结` (approximately lines 403-445)
- must_retrieve_together: true
- must_include: `l = r`, `l + r >> 1`, `l + r + 1 >> 1`, the two update patterns
- citation_required: true

### R02: Binary-search usage conditions

- mode: `acm_analysis`
- query: `什么时候适合使用二分答案？如何判断答案区间具有单调性？`
- expected_sources:
  - `2.1.3 二分答案使用说明` (approximately lines 266-300)
- must_include: answer interval, feasibility check, monotonicity, examples of monotonic conditions
- forbidden: complete submit-ready program
- citation_required: true

### R03: lower_bound and upper_bound distinction

- mode: `normal`
- query: `lower_bound 和 upper_bound 分别返回什么？返回值是下标、数值还是地址？`
- expected_sources:
  - `2.1.5 二分查找函数` (approximately lines 342-442)
- must_include: first greater-than, first greater-than-or-equal, iterator/address, subtracting the begin pointer for an index
- citation_required: true

### R04: DSU path compression

- mode: `normal`
- query: `给出这份模板里的并查集路径压缩写法，并说明 find 和合并操作的作用。`
- expected_sources:
  - `2.3.1 并查集代码（路径压缩）` (approximately lines 452-474)
  - `并查集总结` and code summary (approximately lines 518-580)
- must_retrieve_together: true
- must_include: initialization, find, representative/root, path compression, merge/connectivity
- citation_required: true

### R05: Weighted DSU versus path compression

- mode: `acm_analysis`
- query: `带权并查集和普通路径压缩并查集有什么区别？rank 数组解决了什么问题？`
- expected_sources:
  - `带权并查集` (approximately lines 475-517)
  - `并查集总结` (approximately lines 518-580)
- must_include: rank/height, choosing the parent, extra space, representative
- forbidden: complete submit-ready program
- citation_required: true

### R06: Fenwick tree operations

- mode: `normal`
- query: `这份模板里的树状数组如何实现单点增加和前缀和查询？lowbit 在哪里起作用？`
- expected_sources:
  - `2.3.2 树状数组` (approximately lines 583-682)
  - `update 函数` and `getprefix 函数`
- must_retrieve_together: true
- must_include: `x & -x`, `i += lowbit(i)`, `i -= lowbit(i)`, O(log n)
- citation_required: true

### R07: Fenwick tree versus prefix sums

- mode: `acm_analysis`
- query: `什么时候用前缀和，什么时候用树状数组？请比较初始化、修改和区间查询复杂度。`
- expected_sources:
  - `区分与前缀和的区别和联系` (approximately lines 604-625)
- must_include: static versus dynamic arrays, O(1) query for prefix sums, O(log n) update/query for Fenwick tree
- forbidden: complete submit-ready program
- citation_required: true

### R08: Minimum spanning tree template retrieval

- mode: `normal`
- query: `最小生成树模板在哪里？给我 Kruskal 的 C++ 代码，并说明它依赖什么数据结构。`
- expected_sources:
  - `最小生成树` (approximately lines 1179-1277)
  - `2.4.3 生成树 / Kruskal 模板` (approximately lines 1845-2033)
  - `2.3.1 并查集总结` (approximately lines 518-580)
- must_retrieve_together: true
- must_include: Kruskal, edge sorting, DSU/find, union of components
- style_sources:
  - `Kruskal 模板` (approximately lines 1979-2033)
- citation_required: true

### R09: Minimum spanning tree strategy comparison

- mode: `acm_analysis`
- query: `Prim 和 Kruskal 都能求最小生成树时，应该如何选择？请只讲思路、复杂度和适用场景。`
- expected_sources:
  - `2.4.3 生成树 / Prim 模板` (approximately lines 1845-1978)
  - `2.4.3 生成树 / Kruskal 模板` (approximately lines 1979-2033)
- must_retrieve_together: true
- must_include: Prim growth from a vertex, Kruskal sorted edges plus DSU, relevant complexity discussion if present
- forbidden: complete code block
- citation_required: true

### R10: Dijkstra constraints and implementation

- mode: `normal`
- query: `模板中的堆优化 Dijkstra 使用什么优先队列技巧？它适用于什么边权条件？`
- expected_sources:
  - `最短路` (approximately lines 1067-1178)
  - `2.4.2 最短路 / Dijkstra 模板` (approximately lines 1590-1650)
- must_retrieve_together: true
- must_include: priority queue, negative-distance trick for max heap, relaxation, non-negative edge-weight caveat
- citation_required: true

### R11: LCA method selection

- mode: `acm_analysis`
- query: `这份资料提供了哪些 LCA 方法？倍增、Tarjan 和树链剖分分别适合什么场景？`
- expected_sources:
  - `2.4.4 最近公共祖先(LCA)` (approximately lines 2034-2247)
  - `lca 树链` (approximately lines 1348-1405)
- must_retrieve_together: true
- must_include: at least two of binary lifting, offline Tarjan, heavy-light decomposition, and their query/processing characteristics
- forbidden: complete submit-ready program
- citation_required: true

### R12: Longest common subsequence and tree DP

- mode: `normal`
- query: `动态规划部分有哪些模板？最长公共子序列和树形 DP 分别位于哪里？`
- expected_sources:
  - `2.5 动态规划类` (approximately lines 2682-2808)
- must_retrieve_together: true
- must_include: both LCS and tree DP sections, not only one of them
- citation_required: true

### R13: String algorithm lookup

- mode: `normal`
- query: `字符串部分有哪些内容？请列出哈希、字典树、KMP 和 manacher 对应的章节。`
- expected_sources:
  - `2.6 字符串类` (approximately lines 2811-3089)
- must_include: all four topics
- citation_required: true

### R14: Code-style reference for ACM solution

- mode: `acm_solution`
- solution_language: `cpp`
- query: `请用 C++ 解决一个无向带权图最小生成树问题，代码风格参考知识库中的模板。`
- expected_sources:
  - algorithm evidence: `Kruskal 模板` (approximately lines 1979-2033)
  - style evidence: `图论类` and nearby C++ templates (approximately lines 1065-2033)
- style_sources:
  - `#include <bits/stdc++.h>`, `using namespace std`, fast I/O, short competitive-programming naming style
- must_include: explanation, correctness idea, complexity, complete C++ code, citations to algorithm evidence
- style_rule: style references may influence formatting and naming, but must not be copied as an unrelated algorithm
- citation_required: true

### R15: ACM analysis without a problem-bank item

- mode: `acm_analysis`
- problem_id: none
- query: `有 n 个点和 m 条带权边，要求求最小生成树。请根据我的文字描述分析应该使用什么算法。`
- expected_sources:
  - `最小生成树` and `Prim/Kruskal` sections (approximately lines 1179-1277 and 1845-2033)
- must_include: recognize the user-described problem, compare candidate algorithms, complexity, boundary conditions
- forbidden: complete submit-ready code
- citation_required: true

### R16: Multi-turn rewrite preservation

- mode: `normal`
- turn_1: `我最近在复习 Kruskal 和并查集。`
- turn_2: `那它的时间复杂度和代码模板呢？`
- expected_sources:
  - `Kruskal 模板` (approximately lines 1979-2033)
  - `并查集总结` (approximately lines 518-580)
- must_retrieve_together: true
- must_include: preserve `Kruskal` and `并查集` from history while retrieving the current evidence
- citation_required: true

### R17: Long-document section targeting

- mode: `normal`
- query: `在这份长模板中，Johnson 全源最短路和 Floyd 分别在哪一节？不要返回二分或最小生成树内容。`
- expected_sources:
  - `2.4.2 最短路 / FLoyd 模板` (approximately lines 1725-1736)
  - `2.4.2 最短路 / Johnson 全源最短路模板` (approximately lines 1737-1844)
- must_not_retrieve_as_primary: binary search, MST, unrelated string sections
- citation_required: true

### R18: No-hit behavior

- mode: `normal`
- query: `这份模板中有没有 Dinic 最大流和费用流？`
- expected_sources: none
- expected_behavior: state that no supporting section was found; do not invent a template or citation
- citation_required: false

### R19: Retrieval failure

- mode: `normal`
- query: `请解释 Kruskal。`
- fixture: retrieval provider unavailable
- expected_sources: none
- expected_behavior: expose retrieval failure, continue using remaining inputs, and do not invent a citation
- citation_required: false

### R20: Pending-index behavior

- mode: `normal`
- query: `请给出 Kruskal 模板。`
- fixture: source document exists but is not indexed yet
- expected_behavior: continue the chat without using this source; expose a pending-index status; the next request after indexing may retrieve it
- citation_required: false

## Initial quality gates

- Exact and semantic retrieval cases should return at least one expected source in top-5.
- Cases marked `must_retrieve_together` should return both explanatory and code evidence, or a parent context containing both.
- R18 must not hallucinate a citation.
- R19 must expose the failed initial retrieval and continue without a fabricated source.
- R14 must produce complete C++ only in `acm_solution`; R02, R05, R07, R09, R11 and R15 must not produce a complete submit-ready program.
- R16 must preserve code terms during query rewriting.
- R20 must exclude non-indexed documents from retrieval.

## Known source limitations

- Several sections rely on local image paths; text-only ingestion cannot evaluate the image content.
- Some code blocks are incomplete or illustrative, so this set evaluates retrieval and grounding, not compilation correctness of the source document.
- The source contains multiple variants of the same algorithm; evaluation should accept the relevant section family and inspect citation scope rather than require one exact code block.
