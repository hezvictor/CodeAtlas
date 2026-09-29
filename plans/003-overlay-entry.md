# 003 — 添加抽屉和语言弹窗入场反馈

- **Status**: 已实施，自动化浏览器验收通过；覆盖和人工检查边界见 [VALIDATION.md](VALIDATION.md)。
- **Commit**: b4db971
- **Severity**: MEDIUM（增强优先级，不是已确认故障）
- **Category**: Missed opportunities / Physicality & origin / Cohesion
- **Estimated scope**: 修改 1 个入口文件、新增 1 个 CSS 文件，约 55 行
- **Dependency**: 无；为 004、005 提供样式入口与参数

## Problem

E:/agent/agentcode/frontend/src/components/ProblemEditor.tsx:47–49 的现有节点：

~~~tsx
<div className="drawer-backdrop" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
  <aside className="problem-editor" aria-label={isEditing ? "编辑题目" : "新建题目"}>
~~~

E:/agent/agentcode/frontend/src/components/LanguageDialog.tsx:5 使用 dialog-backdrop 与 language-dialog。题库列表 :73、详情页 :37、聊天页 :365 都条件挂载这些组件。现有 globals.css:13、18 仅设置固定布局，没有入场动画。本计划提供空间反馈；静态审计未证明现有即时出现是故障。

## Target

保留所有条件挂载和关闭逻辑，只添加 CSS 入场过渡：
- 右侧抽屉：translateX(100%)→translateX(0)，250ms，cubic-bezier(0.32, 0.72, 0, 1)。
- 居中弹窗：scale(0.97)→scale(1)、opacity 0→1，200ms，cubic-bezier(0.23, 1, 0.32, 1)，原点为 center。
- 背景遮罩即时出现；关闭即时卸载，不实现退场、不保留不可见节点。
- 默认最终状态可见；仅 prefers-reduced-motion:no-preference 启用移动和缩放。
- 不支持 @starting-style 的浏览器保持即时可见；不得把基准状态设为隐藏后等待 JS。

首次样式过渡与规则顺序已按 [MDN 的 @starting-style 文档](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/At-rules/%40starting-style) 核对；规则置于最终样式之后。计划明确采用渐进增强，目标浏览器兼容性仍须实际验收。

创建 E:/agent/agentcode/frontend/src/app/motion.css，完整内容：

~~~css
:root {
  --motion-ease-out: cubic-bezier(0.23, 1, 0.32, 1);
  --motion-ease-drawer: cubic-bezier(0.32, 0.72, 0, 1);
  --motion-duration-dialog: 200ms;
  --motion-duration-drawer: 250ms;
  --motion-duration-notice: 160ms;
  --motion-duration-press: 160ms;
}

@media (prefers-reduced-motion: no-preference) {
  .problem-editor {
    transform: translateX(0);
    transition: transform var(--motion-duration-drawer) var(--motion-ease-drawer);
  }

  .language-dialog {
    transform-origin: center;
    transform: scale(1);
    opacity: 1;
    transition:
      transform var(--motion-duration-dialog) var(--motion-ease-out),
      opacity var(--motion-duration-dialog) var(--motion-ease-out);
  }

  @starting-style {
    .problem-editor {
      transform: translateX(100%);
    }

    .language-dialog {
      transform: scale(0.97);
      opacity: 0;
    }
  }
}
~~~

在 globals.css:3 现有导入后、首个 :root 规则前添加：

~~~css
@import "./motion.css";
~~~

如果仅执行本计划的基础部分以支持 004 或 005，只创建 :root 参数与导入，暂不添加上述弹层媒体查询。

## Repo conventions to follow

现有 globals.css:2–3 分别导入 message-content.css、model-settings.css；新 motion.css 用相同方式导入。globals.css:4 已有 :root，新的 --motion-* 作为补充，不改颜色、字体、间距参数。布局仍由既有 globals.css、chat-overrides.css、knowledge-overrides.css 管理。

## Steps

1. 复核两个组件 className 与父页面挂载条件，记录现有关闭操作的即时性。
2. 新建 motion.css，精确使用 Target 中的参数与样式。
3. 在现有 CSS import 区插入导入，不把 @import 放到样式规则之后。
4. 不修改组件 JSX，不添加 hook、关键帧、setTimeout 或新依赖。
5. 检查默认状态始终可见，并在减少动态效果下确认媒体查询完全不启用这些 transform/opacity 规则。
6. 执行机械检查、三个入口与移动端界面验收。

## Boundaries

只允许 globals.css 和新 motion.css。不改 ProblemEditor、LanguageDialog、题库/聊天页面、焦点策略、提交处理或父组件卸载方式。禁止 scale(0)、整页动画、列表 stagger、transition: all、动画 width/height/top/left、永久 will-change。关闭不等待动画。若后续明确需要退场，另写包含生命周期、焦点与中断处理的独立计划。

## Verification

在 E:/agent/agentcode/frontend 执行：

~~~powershell
npm run typecheck
npm run lint
npm test
npm run build
~~~

全部退出码为 0。用现有开发入口运行界面，并检查：

- 题库新建、题库详情编辑、聊天切换 ACM 解题打开语言弹窗三条路径。
- 正常速度下按钮响应立即开始，抽屉在 250ms 内到位，弹窗在 200ms 内到位，过程中可操作。
- DevTools Animations 面板设 10%：抽屉从自身宽度 100% 的右侧进入；弹窗从 .97 居中缩放，不从触发按钮或页面角落缩放。
- 入场中立即点击关闭，节点即时移除；再打开从新挂载状态进入，不残留遮罩或不可点击层。
- 在 DevTools Rendering 模拟 reduced motion：即时显示、不平移缩放，内容和现有交互完整。
- 在 390px 宽度及真实触屏设备上检查抽屉无横向页面滚动、按钮无遮挡、关闭无粘滞。
- 确认目标浏览器确实支持并执行 @starting-style；不支持时应即时显示。如要求这些浏览器也有入场动效，报告兼容性需求，不能擅自新增 JS 回退。
- Performance 记录中不得增加每帧布局计算；本次不能据静态代码宣称稳定帧率。

**Done when**：指定入口正常过渡、关闭即时、减少动态效果与兼容回退正常；机械检查通过且慢放/触屏验收记录完整。
