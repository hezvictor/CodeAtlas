# 004 — 添加通知入场反馈

- **Status**: 已实施，自动化浏览器验收通过；覆盖和人工检查边界见 [VALIDATION.md](VALIDATION.md)。
- **Commit**: b4db971
- **Severity**: LOW
- **Category**: Missed opportunities / Interruptibility / Accessibility
- **Estimated scope**: 1 个已建 CSS 文件，约 15 行新增
- **Dependency**: 003 的 motion.css、导入及共享参数；无需接受 003 的弹层动效

## Problem

E:/agent/agentcode/frontend/src/components/GlobalErrorBoundary.tsx:4 在 notice 为空时 return null，否则挂载 global-notice，并保留 role="alert"。E:/agent/agentcode/frontend/src/app/profile/page.tsx:22 条件挂载 toast success/error，语义分别为 status/alert。globals.css:4、6 的通知样式没有过渡。

当前全局通知的节点片段：

~~~tsx
<div className="global-notice" role="alert"><strong>操作未完成</strong><span>{notice.message}</span><button aria-label="关闭提示" onClick={()=>setNotice(null)}>×</button></div>
~~~

现有即时显示没有被判为故障；本计划仅补充首次挂载反馈。

## Target

只让首次挂载的通知 opacity 0→1，160ms，cubic-bezier(0.23, 1, 0.32, 1)。不位移、不缩放、不加退出生命周期、不改 alert/status 内容时序。原 DOM 上更新通知内容不重复入场。

E:/agent/agentcode/frontend/src/app/motion.css 的共享参数必须包含：

~~~css
--motion-ease-out: cubic-bezier(0.23, 1, 0.32, 1);
--motion-duration-notice: 160ms;
~~~

在该文件末尾添加：

~~~css
@media (prefers-reduced-motion: no-preference) {
  .global-notice,
  .toast {
    opacity: 1;
    transition: opacity var(--motion-duration-notice) var(--motion-ease-out);
  }

  @starting-style {
    .global-notice,
    .toast {
      opacity: 0;
    }
  }
}
~~~

减少动态效果下保留当前即时反馈；不支持 @starting-style 时也即时可见。默认状态不得隐藏。

首次显示的过渡语义参考 [MDN 的 @starting-style 文档](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/At-rules/%40starting-style)。它不会因同一可见节点的文字更新而重新采用起始状态；验收时须确认节点未重挂载。

## Repo conventions to follow

沿用 globals.css:2–3 的 CSS 导入模式和现有 .global-notice/.toast 选择器。003 已建 motion.css；不得复制第二套参数或覆盖通知的定位、颜色、z-index 和布局。

## Steps

1. 若没有 motion.css，先执行 003 的基础步骤：创建其 :root 参数并在 globals.css import 区导入；不必添加弹层样式。
2. 复核两个通知节点的 className 与语义，按 Target 追加 CSS。
3. 保留原通知更新与关闭方式，不添加 key 来强制重挂载，不添加自动关闭计时器。
4. 完成正常、快速关闭和减少动态效果验收。

## Boundaries

执行基础依赖后只允许修改 motion.css。不改 GlobalErrorBoundary.tsx、profile/page.tsx、errors.ts、提示文案、错误处理或表单请求。不合并不同通知组件，不处理现有通知重叠问题，不把通知重构成 toast 服务。不为错误信息增加等待时间。

## Verification

在 E:/agent/agentcode/frontend 执行 npm run typecheck、npm run lint、npm test、npm run build，全部退出码应为 0。

界面验收：
- 用开发环境既有可控失败路径触发全局错误；在测试账号中修改资料触发成功提示。不在正式账号上为验收改密码。
- 首次挂载 160ms 淡入；内容在 DOM 中立即存在，role 与 aria-label 保留。
- 通知显示期间让同一节点更新消息，用慢放确认不会再次从 opacity 0 开始；不添加 key。
- 淡入期间立即关闭全局通知，应即时移除；连续触发新通知不能留下不可见节点。
- Animations 面板设 10%：仅 opacity 变化，没有位置和尺寸动画。
- reduced motion 下完全即时可见；不支持 @starting-style 的浏览器也是即时可见。
- 检查触屏关闭按钮与键盘可用性。

**Done when**：挂载淡入、内容更新不重播、关闭即时、语义与减少动态效果表现正确。
