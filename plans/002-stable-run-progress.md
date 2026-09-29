# 002 — 保留执行进度的展开选择

- **Status**: 已实施，自动化浏览器验收通过；覆盖和人工检查边界见 [VALIDATION.md](VALIDATION.md)。
- **Commit**: b4db971
- **Severity**: MEDIUM
- **Category**: Interruptibility / 状态连续性
- **Estimated scope**: 1 个源文件，约 10–20 行修改
- **Dependency**: 无

## Problem

E:/agent/agentcode/frontend/src/components/ChatRunProgress.tsx:6–8：

~~~tsx
if (!steps.length) return null;
const active = [...steps].reverse().find(step => step.state === "running" || step.state === "retrying");
~~~

同一 return 中的当前属性为：

~~~tsx
open={Boolean(active)}
~~~

步骤完成就自动折叠；下一活动阶段又自动展开。调用位置为 chat/page.tsx:357，steps 更新来自 :126。agent-events.ts:12–15 将状态转成 running/retrying/ok 等值。内存渲染已验证 open=true→false→true。现有文档要求可折叠，没有规定自动逐阶段收起。

## Target

组件初次显示默认展开。只让用户手动选择改变展开状态，进度完成、重试、失败和新增步骤均保持当前选择。恢复同一已挂载组件也保持选择；新组件挂载时重新默认展开。无需持久化到 localStorage。

只修改 ChatRunProgress.tsx：在文件顶部明确添加 "use client";，在 import type 前引入：

~~~tsx
import { useState } from "react";
~~~

在组件函数第一行、任何提前 return 之前添加：

~~~tsx
const [expanded, setExpanded] = useState(true);
~~~

将 details 起始标签的 open 属性替换并增加 onToggle：

~~~tsx
<details
  className="agent-progress"
  open={expanded}
  onToggle={event => setExpanded(event.currentTarget.open)}
>
~~~

保留现有 active 计算、summary 的 aria-live="polite"、所有状态标签及 ol/li 内容。初次显示只有已完成步骤也默认展开；这是一项明确的交互改变。用户可以立即收起。

动效目标值：不添加 animation、transition、height/max-height 动画或延迟，原生 summary 的键盘交互保持即时。

## Repo conventions to follow

- TemporaryFilePicker.tsx:32 已使用原生 details；保留原生 summary 语义。
- 当前样式在 E:/agent/agentcode/frontend/src/app/chat-overrides.css:4，不需修改。
- 只新增局部 useState，不修改 steps 的数据格式和 reducer，不新增动画库。

## Steps

1. 在现有界面发送一条问题，观察相邻步骤完成与开始时的折叠变化，或使用测试环境的合法 SSE 事件回放复现。
2. 按 Target 引入 useState；hook 必须位于 !steps.length 提前 return 之前，保持调用顺序固定。
3. 保留 active 仅用于标题，不再用它驱动 details.open。
4. 添加 onToggle 同步原生展开选择，保留全部原有输出。
5. 用相同步骤更新序列验证展开状态不再由后台事件改写。
6. 执行机械和界面验收。

## Boundaries

只允许修改 ChatRunProgress.tsx。不修改 chat/page.tsx、agent-events.ts、SSE、模型执行、内容校验、标题文案或后台步骤。不为折叠加入高度动画，不为了减少跳动隐藏执行反馈，也不改变“最终正文校验后一次返回”的约束。不修复其他消息滚动问题。

## Verification

在 E:/agent/agentcode/frontend 执行：

~~~powershell
npm run typecheck
npm run lint
npm test
npm run build
~~~

全部退出码应为 0。现有 SSR 测试不验证原生 toggle 事件，因此浏览器验收必做：

- steps=[] 仍无面板；首个步骤到来时默认展开。
- 展开状态经历 running→ok→下一 running→retrying→failed，不自动收起或弹开；标题和状态及时更新。
- 手动收起后重复这些更新，保持收起；手动展开后保持展开。
- summary 用 Tab 聚焦，再用 Enter/Space 切换，行为即时且可重复。
- 检查新消息组件首次挂载与恢复同一组件的区别，不要求选择跨页面刷新持久化。
- 慢放录屏逐帧检查：没有活动步骤结束导致的 ol 突然隐藏；新增步骤和新正文的真实内容增量仍正常出现。
- 动画面板 10% 下不出现折叠动画；prefers-reduced-motion=reduce 下行为相同。

**Done when**：后台状态不再改写展开选择，用户可立即控制 disclosure，反馈数据与现有回归保持正确。
