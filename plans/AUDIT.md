# CodeAtlas 动画审计

> 本文记录 b4db971 基线的原始审计，不描述实施后的现状。用户随后批准全部五项计划，代码修改和浏览器验收见 [实施验收记录](VALIDATION.md)。

- 日期：2026-09-29；提交：b4db971。
- 来源：当前前端源代码、现有依赖、页面职责文档、两次只读内存渲染探针。
- 审计仅新增 plans/ 下文档；未修改源代码、安装依赖、运行构建、格式化或提交。
- 覆盖：frontend/src 全部动效关键词扫描，并重点追踪全部主要交互区域。源码文件共 60 个：5 个 CSS、21 个 TS、34 个 TSX（包含测试）。
- 限制：没有启动应用或登录浏览器，没有录像、设备手势或帧率测量。DOM 切换有代码和渲染证据；具体跳动幅度、浏览器滚动锚定以及是否肉眼可见闪烁需后续界面验收。

## 动效地图

Next.js 15、React 19，原生 CSS 与 React 状态渲染。package.json 没有 Motion、React Spring、GSAP 或其他独立动画依赖。

源码没有显式 animation、transition、@keyframes、WAAPI animate 调用、requestAnimationFrame 动画或 transform 动效，也没有动效参数或 prefers-reduced-motion 分支。静态 opacity、字体 text-transform、背景 backdrop-filter、模型列表的 overscroll-behavior 不属于动画问题。不能从“没有减少动态效果规则”推断现有显式动画违反可访问性要求。

样式入口为 frontend/src/app/globals.css:1–3。聊天另外导入 chat-overrides.css；知识库另外导入 knowledge-overrides.css。新动效应借用现有 :root 参数和 CSS 导入方式，不创建第二套设计系统。

原生动态表面：
- KnowledgeProgress.tsx:10：有确定值与不确定值的 progress。
- KnowledgeUpload.tsx:98：上传 progress。
- ProblemMentionPicker.tsx:13：候选项 scrollIntoView，未配置 smooth。
- ChatRunProgress.tsx:8 和 TemporaryFilePicker.tsx:32：原生 details 展开。
- React 条件渲染：抽屉、弹窗、菜单、通知、题库加载与空状态。

原生 progress 的实际动效由浏览器绘制，本次未测其减少动态效果表现；作为验证项，不宣称存在违规或自定义无限动画。

产品定位是私人题库与知识库学习工具，建议短促、克制的反馈。频率来自交互路径推断，没有用户遥测：
- 高频：输入、筛选、候选题目导航、消息复制、会话切换、状态更新。
- 偶发：菜单、题目编辑、语言选择、上传、错误与成功通知。
- 低频：账号资料修改、新建题目。

## 已核实的问题清单

按影响与修复成本排序。没有确认的 HIGH 动画问题。

| # | 严重度 | 类别 | 位置 | 问题及证据 | 修正方向 |
| --- | --- | --- | --- | --- | --- |
| F1 | MEDIUM | 目的与频率／状态连续性 | frontend/src/app/problems/page.tsx:32、65、67、70 | 每次刷新置 loading=true；列表、空结果和分页均受 !loading 控制。保留在 state 中的旧结果仍被整块移出 DOM。内存渲染确认 12 张卡片→0 张→12 张，分页同时消失。 | 首次加载保留占位；后续刷新保持旧结果可见，在固定高度状态栏说明刷新，分页显示 result.page 且刷新期间禁用。不用列表入场动画遮盖数据撤换。 |
| F2 | MEDIUM | 可中断性／状态连续性 | frontend/src/components/ChatRunProgress.tsx:6–8；frontend/src/lib/agent-events.ts:12–15 | open 与是否有 running/retrying 步骤绑定。最后一个活动步骤结束即关闭；后续活动步骤可能再次打开。SSR 确认 running=true、ok=false、retrying=true，步骤列表内容仍存在。 | 独立维护展开选择，组件首次显示默认展开，此后完成、重试和新增步骤不改变用户选择；手动与键盘展开仍即时。 |

F2 数据链：chat/page.tsx:126 更新 steps → reduceAgentEvent 生成 running/ok/retrying 状态 → ChatRunProgress 求 active → 原生 details 的 open 改变。资料要求“反馈可折叠”，没有发现必须“每个阶段完成自动收起”的设计约束。保留默认展开是本计划提出的交互选择，并非已有产品规范。

F1 数据链：筛选输入或翻页 → 180ms 防抖后 loadProblems → setLoading(true) → 列表条件为 false → 响应后 setResult 和 setLoading(false) → 列表重新创建。知识库现有刷新保留 documents，仅替换返回值，是可参考的稳定渲染模式。请求时序和竞态不在本次动效计划内。

## 可选动效增强

这三项是新增反馈，未计入现有动画缺陷。

| # | 优先级 | 位置 | 当前行为 | 提案 |
| --- | --- | --- | --- | --- |
| O1 | MEDIUM | ProblemEditor.tsx:47–49；LanguageDialog.tsx:5；globals.css:13、18 | 右侧编辑抽屉和居中语言弹窗直接出现，没有入场过程。 | 抽屉 translateX(100%)→0，250ms；弹窗 scale(.97)＋opacity 0→1，200ms。仅入场，关闭即时。 |
| O2 | LOW | GlobalErrorBoundary.tsx:4；profile/page.tsx:22；globals.css:4、6 | 通知直接挂载，内容替换直接更新。 | 初次挂载用 160ms opacity 入场；同一通知内容更新不重播；不延迟 alert/status、不添加自动关闭。 |
| O3 | LOW | problems/page.tsx:62；ProblemEditor.tsx:61；globals.css:4、13 | 新建题目、保存和取消按钮没有按下反馈。 | 只对这些低频按钮提供 scale(.97)、160ms 的按压反馈；禁用、键盘和减少动态效果下不缩放。 |

O1–O3 的优先级表示增强价值，不表示存在故障。所有动效只改变 transform 和 opacity；不增加全局 transition: all。旧浏览器不识别 @starting-style 时保留即时显示，具体兼容性留在实施验收。

## 八类审计结果

| 类别 | 结果 |
| --- | --- |
| 目的与频率 | F1 为重复刷新造成的撤换；高频输入、菜单、会话切换与候选导航应继续即时响应。 |
| 缓动与时长 | 没有现有自定义动画可判定缓动或时长错误；新提案给出具体时长与曲线。 |
| 空间关系与原点 | 没有现有 scale(0) 或错误动画原点；O1 居中弹窗从中心缩放，抽屉从自身右侧滑入。 |
| 可中断性 | F2 折叠状态被进度反复驱动；新入场采用 CSS transition，不用反复重启的关键帧。 |
| 性能 | 未发现显式布局动画、transition: all 或逐帧 JS 动画。没有帧率证据，不能称为性能故障。 |
| 可访问性 | 现有原生 progress 待浏览器检查；新增位移/缩放仅在 no-preference 下启用，保留现有即时反馈。 |
| 一致性与参数 | 当前没有动效参数，无重复缓动需要合并；若接受增强，建立少量 --motion-* 参数。 |
| 缺失反馈 | O1–O3；不推荐整页入场、打字机、候选列表 stagger 或逐步骤脉冲。 |

## 有意保留的行为

- docs/agent-rag-architecture.md:157 说明回答在校验后一次返回。不得为了动画改成逐字输出或提前展示内容。
- 候选题目滚动没有 smooth；高频键盘导航无需动画。
- 浏览器原生 select、confirm、prompt 不纳入自定义动效改造。
- 当前复制提示的 1200ms、候选检索的 120ms 和题库检索的 180ms 是反馈停留或请求防抖，不是动画时长。
- 静态 12px backdrop-filter 不构成“动画 blur 太大”。
- 不针对默认字体切换或 hover 字重提出动画修正：本次没有测量它们的布局影响。

## 只读验证记录

在现有 frontend/node_modules 下读取 TypeScript、React、react-dom/server，将当前 TSX 通过 transpileModule 在内存转换并用 vm 加载；没有生成文件。题库页面 React hooks 和子组件用无网络探针替代，以固定状态检查渲染分支。它验证 DOM 输出条件，不模拟浏览器交互。

| 探针 | 输入 | 输出 |
| --- | --- | --- |
| 题库 | result=12 个题目，loading=false | 12 张卡片；分页存在 |
| 题库 | 同一 result，loading=true | 0 张卡片；加载占位；分页不存在 |
| 题库 | 同一 result，loading=false | 12 张卡片；分页恢复 |
| 进度 | 单步骤 running | details open=true |
| 进度 | 同步骤 ok | details open=false，li 仍在输出中 |
| 进度 | 同步骤 retrying | details open=true |
| 进度 | 同步骤 no_hit / failed | details open=false |
| 进度 | steps=[] | 空输出 |

断言全部通过。没有运行 npm 测试、构建或浏览器性能检查；本次也未宣称修复已完成。具体实施、真机触摸和慢放验收见计划 001–005。

## 技术依据

新增 CSS 入场方案已核对 [MDN 的 @starting-style 文档](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/At-rules/%40starting-style)：该规则提供首次显示的过渡起点，独立规则放在最终样式之后。最终可见样式保留，因此旧浏览器可忽略起始规则并即时显示。实际目标浏览器仍须验收。

原生 disclosure 的展开与 toggle 语义参考 [MDN 的 details 文档](https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/details)。缓动曲线和时长预算来自本地 improve-animations/AUDIT.md；布局高度来自现有界面布局需要，不是动画预算。
