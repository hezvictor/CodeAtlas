# 001 — 保持题库刷新期间的列表稳定

- **Status**: 已实施，自动化浏览器验收通过；覆盖和人工检查边界见 [VALIDATION.md](VALIDATION.md)。
- **Commit**: b4db971
- **Severity**: MEDIUM
- **Category**: Purpose & frequency / 状态连续性
- **Estimated scope**: 2 个源文件，约 20–35 行修改
- **Dependency**: 无

## Problem

E:/agent/agentcode/frontend/src/app/problems/page.tsx:32 设置 loading=true；:65 用加载卡片替换列表；:67 和 :70 令列表及分页消失。每次输入筛选后经过 180ms 防抖都会触发这个分支。

当前代码（:65–67）：

~~~tsx
{!error && loading && <div className="panel problem-empty">正在加载题库…</div>}
{!error && !loading && result && !result.items.length && <div className="panel problem-empty"><strong>没有找到匹配题目</strong><p className="muted">换个关键词或创建一道新题目。</p></div>}
{!error && !loading && result && !!result.items.length && <>
~~~

内存渲染已确认同一 12 条结果在 loading=false/true/false 下为 12/0/12 张卡片。实际闪烁强度和滚动位置尚待浏览器验收。

## Target

首次加载且 result=null 时仍显示原加载卡片。已有 result 后，刷新期间保持原列表或原空结果、原分页，明确标记其为上次结果；响应到达后直接更新，没有淡入、stagger、位移或高度动画。

目标加载和结果条件：

~~~tsx
{!error && loading && !result && <div className="panel problem-empty">正在加载题库…</div>}
{!error && result && <div className="problem-refresh-status" role="status" aria-live="polite">{loading ? "正在更新题库，当前显示上次结果…" : ""}</div>}
{!error && result && !result.items.length && <div className="panel problem-empty"><strong>没有找到匹配题目</strong><p className="muted">换个关键词或创建一道新题目。</p></div>}
{!error && result && !!result.items.length && <>
~~~

分页保留原 onClick，上一页改为 disabled={loading || page <= 1}；下一页改为 disabled={loading || page * result.page_size >= result.total}；页码文案使用“第 {result.page} 页”，避免请求页码已经变化、旧结果却仍显示时错标页码。原列表内 ProblemCard 实际 ID 和链接不变。

在 E:/agent/agentcode/frontend/src/app/globals.css 末尾添加：

~~~css
.problem-refresh-status {
  min-height: 24px;
  line-height: 24px;
  margin: 0 0 8px;
  font-size: 12px;
  color: var(--muted);
}
~~~

这个容器在已有 result 且无 error 时始终存在，刷新结束只清空文本，不撤走其占位。动效目标值：无动画、无 transition、无额外延迟。24px 是状态栏布局高度，不是动画参数。

## Repo conventions to follow

- React 条件渲染沿用 problems/page.tsx:64–71 的写法。
- 样式复用 globals.css:4 的 --muted、--line 等现有参数。
- knowledge/page.tsx:23–25、32–35 在后台刷新时保留 documents 的模式可作参考。
- 不改变已有请求防抖，不新建取数状态库。

## Steps

1. 复核上述条件与 page.tsx:25–40 的 loadProblems 生命周期。
2. 在修改前以已加载 12 条结果＋网络 Slow 3G 重现：触发筛选，请求进行时原列表与分页消失。记录复现步骤作为回归基线。
3. 在 :65 的 loading 条件补上 !result。
4. 在加载卡片后插入固定占位的 problem-refresh-status。
5. 在空结果和非空结果分支仅去除 !loading；error 条件、内容和列表项键保持原样。
6. 调整两个分页 disabled 条件与页码文本，保留原点击处理。
7. 在 globals.css 末尾添加上述独立规则，不格式化现有压缩 CSS。
8. 执行机械与界面验收。

## Boundaries

只允许修改 problems/page.tsx、globals.css。不改 ProblemCard、过滤器、网络、token、删除/编辑逻辑、分页 API 或防抖。不处理请求竞态；如验收发现旧响应覆盖新结果，单独记录，不借此扩展动效计划。不移除错误状态或初次加载提示，不让旧结果冒充新筛选结果。不改现有结果条目的实际操作对象。

## Verification

在 E:/agent/agentcode/frontend 执行：

~~~powershell
npm run typecheck
npm run lint
npm test
npm run build
~~~

预期退出码均为 0。之后用既有登录账号、包含至少 12 道题的题库，在开发界面检查：

- 首次加载仍有占位；筛选、难度选择、分页和保存后刷新时旧卡片不被先清空。
- 在 Slow 3G 下能读到“当前显示上次结果”；刷新期间分页禁用，页码与实际展示的 result.page 一致。
- 检查结果→结果、结果→空结果、空结果→结果、失败四种路径；最终内容和错误提示正确。
- 屏幕录像逐帧检查：刷新进行中没有“12 行→1 个占位→12 行”的中间布局。响应后数量变化造成的真实布局调整可以保留。
- 动画面板 10% 下没有列表动画；键盘输入、按 Tab 和 Enter 即时可用。
- 模拟 prefers-reduced-motion=reduce：表现相同，状态提示仍可读。
- 本次修改不应增加网络请求，也不延迟用户操作来等待动画。

**Done when**：刷新期间已有结果稳定显示、状态可辨认、页码正确；已有回归通过，浏览器基线中的列表撤换不再出现。
