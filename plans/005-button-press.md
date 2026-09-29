# 005 — 添加低频按钮按压反馈

- **Status**: 已实施，自动化浏览器验收通过；覆盖和人工检查边界见 [VALIDATION.md](VALIDATION.md)。
- **Commit**: b4db971
- **Severity**: LOW
- **Category**: Missed opportunities / Physicality / Purpose & frequency
- **Estimated scope**: 1 个已建 CSS 文件，约 20 行新增
- **Dependency**: 003 的 motion.css、导入及共享参数；无需接受其弹层动效

## Problem

E:/agent/agentcode/frontend/src/app/problems/page.tsx:62 的新建按钮和 E:/agent/agentcode/frontend/src/components/ProblemEditor.tsx:61 的取消/保存按钮无 :active 按压反馈。既有 globals.css:4、13 设置按钮外观，但没有 transform 过渡。

当前抽屉操作区：

~~~tsx
<div className="drawer-actions"><button className="pill" type="button" onClick={onClose}>取消</button><button className="pill fill" type="submit" disabled={saving}>{saving ? "保存中…" : "保存题目"}</button></div>
~~~

这是低频反馈增强，不是按钮功能故障。候选导航、复制、发送、会话切换不包含在本计划中。

## Target

仅以下两个范围的原生 button：
- .problem-hero-actions > button.pill
- .drawer-actions > button.pill

指针按下时 scale(0.97)，松开回到 1；transform 过渡 160ms，cubic-bezier(0.23, 1, 0.32, 1)。禁用按钮不缩放；键盘 focus-visible 下不缩放、不等待动画；减少动态效果下完全保持现有行为。没有 hover 位移，因此触屏不会触发粘滞的 hover 动画。

motion.css 参数必须包含：

~~~css
--motion-ease-out: cubic-bezier(0.23, 1, 0.32, 1);
--motion-duration-press: 160ms;
~~~

在 E:/agent/agentcode/frontend/src/app/motion.css 末尾添加：

~~~css
@media (prefers-reduced-motion: no-preference) {
  .problem-hero-actions > button.pill,
  .drawer-actions > button.pill {
    transform: scale(1);
    transition: transform var(--motion-duration-press) var(--motion-ease-out);
  }

  .problem-hero-actions > button.pill:enabled:active:not(:focus-visible),
  .drawer-actions > button.pill:enabled:active:not(:focus-visible) {
    transform: scale(0.97);
  }

  .problem-hero-actions > button.pill:focus-visible,
  .drawer-actions > button.pill:focus-visible {
    transform: scale(1);
    transition: none;
  }
}
~~~

点击处理不等待视觉过渡；取消按钮可在指针释放后立即关闭抽屉。

## Repo conventions to follow

沿用现有 .pill 类；通过明确的父级范围约束，不为所有 button/.pill 设动画。003 已建 motion.css 与参数。本计划不改 JSX，也不添加手势监听。

## Steps

1. 若 motion.css 不存在，先完成 003 的基础步骤：参数和 CSS import；不必执行弹层动效。
2. 核对新建按钮与抽屉操作区选择器，确认没有误包含链接、分页、发送、菜单等按钮。
3. 在 motion.css 追加 Target 样式；不追加其他 hover、颜色或布局动画。
4. 检查鼠标、触屏、键盘、禁用和减少动态效果路径；保留实际提交即时性。

## Boundaries

执行基础依赖后只允许修改 motion.css。不改组件、表单、保存、关闭、指针事件或键盘事件。不给所有 .pill 添加规则；不处理业务等待；不为长按添加逻辑。禁止缩小点击布局尺寸或改变 border/width/padding，transform 只改变绘制。

## Verification

在 E:/agent/agentcode/frontend 执行 npm run typecheck、npm run lint、npm test、npm run build，全部退出码应为 0。

界面验收：
- 鼠标按住“新建题目”、抽屉“取消”或“保存”时有轻微缩放；松开即恢复，点击处理不等待 160ms。
- 保存等待期间按钮 disabled，无按压缩放。
- 快速反复按下、松开，在 Animations 面板 10% 下观察 transition 从当前状态反向，无关键帧重播、尺寸布局跳动或卡在 .97。
- Tab 聚焦后用 Enter/Space 操作，焦点环保留、无缩放。
- 真实触屏上按下和释放，无粘滞 hover；浏览器若为触屏保留 focus-visible，允许即时无缩放，功能完整。
- prefers-reduced-motion=reduce 下不缩放；反馈文案和禁用状态正常。
- 复制、发送、会话切换、候选题目导航、分页等高频按钮不出现新动画。

**Done when**：反馈仅覆盖明确的低频按钮，状态可中断，键盘/触屏/减少动态效果正常，不影响任何业务提交。
