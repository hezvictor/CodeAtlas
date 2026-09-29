# 前端动效实施与验收

- 日期：2026-09-29；审计基线：b4db971。
- 用户批准后完成 001–005，未新增运行依赖、修改后端或提交部署。
- 原始问题证据保留在 AUDIT.md；各计划保留实施前代码片段。

## 实施结果

| 计划 | 文件 | 最终行为 |
| --- | --- | --- |
| 001 | frontend/src/app/problems/page.tsx、globals.css | 首次加载保留原提示；刷新保留已有卡片和分页，以固定 24px 状态栏提示正在显示上次结果。刷新期间禁用分页，页码来自已显示的 result.page。 |
| 002 | frontend/src/components/ChatRunProgress.tsx | 初次显示默认展开，用户控制后续展开选择；后台步骤完成和新增步骤均不覆盖选择。 |
| 003 | frontend/src/app/motion.css、globals.css | 抽屉入场 translateX，250ms；语言弹窗 scale(.97→1) 与 opacity，200ms。关闭保持即时。 |
| 004 | frontend/src/app/motion.css | global-notice 和 toast 首次入场 opacity，160ms；文本更新不重新入场。 |
| 005 | frontend/src/app/motion.css | 仅题库头部和抽屉动作区的启用按钮按压 scale(.97)，160ms；键盘 focus-visible 不缩放。 |

CSS 使用共享时长与缓动参数，动画只改变 transform/opacity。所有新增动效限定于 prefers-reduced-motion:no-preference；减少动态效果时保持即时显示。默认样式始终可见，不支持 @starting-style 的浏览器可直接显示最终状态。后端接口、取数、认证、SSE、模型调用、消息正文和高频菜单逻辑保持原实现。

## 自动化结果

在 frontend 目录运行：

```powershell
npm run typecheck
npm run lint
npm test
npm run build
```

全部退出码为 0；现有单元测试 34/34 通过。生产构建成功生成 11 个页面。构建仍报告原有 globals.css 中 start/end 对齐值的 Autoprefixer 兼容性提示；此次没有扩展范围修改这些样式。Windows 沙箱中的测试出现 spawn EPERM，构建曾长时间无输出；获准在沙箱外重跑后均通过。

浏览器回归使用项目真实 React 页面、原生 details、CSS transition 和 agent-browser 的隔离浏览器会话。在实现前，新增检查分别复现卡片消失、步骤完成自动收起和缺少入场动画；实现后完整回归 4/4 通过。

复现步骤（需要已安装的 agent-browser）：

```powershell
# 终端一，在 E:/agent/agentcode/frontend 启动
npm run dev -- --hostname 127.0.0.1 --port 3100

# 终端二，在 E:/agent/agentcode 执行
node scripts/check-frontend-motion.mjs
```

测试脚本为 scripts/check-frontend-motion.mjs、scripts/frontend-motion-fixture.js。它们不参与生产运行，不安装依赖；只允许连接 localhost/127.0.0.1，通过初始化脚本模拟外部 API 和 SSE，避免真实账号、模型调用或后端写入。

| 浏览器检查 | 结果 |
| --- | --- |
| 筛选和分页刷新期间保留 12 张卡片、禁用分页、保留旧页码、更新完成后显示新页码与预留状态高度 | 通过 |
| 步骤完成后保持展开；手动收起后新增步骤保持收起；空格键展开；后续完成仍保持选择 | 通过 |
| 抽屉真实生成一个 transform 过渡；弹窗生成 transform/opacity 过渡；时长均不超过 300ms；入场中可立即关闭 | 通过 |
| 全局通知保留 alert 语义，只有 opacity 过渡；同一节点更新文案不重播；立即关闭 | 通过 |
| 原生鼠标按压产生缩放且 offsetWidth 不变；键盘 focus-visible 的过渡时长为 0s | 通过 |
| 390×844 模拟视口、减少动态效果：抽屉零动画、立即可见、无横向页面溢出、可关闭 | 通过 |

## 截图与验证边界

截图目录：C:/Users/32157/.codex/visualizations/2026/09/29/01a0eac0-fa31-7731-b42b-e0045f37ad9f。

- [刷新列表截图](C:/Users/32157/.codex/visualizations/2026/09/29/01a0eac0-fa31-7731-b42b-e0045f37ad9f/problem-refresh.png)
- [已完成进度截图](C:/Users/32157/.codex/visualizations/2026/09/29/01a0eac0-fa31-7731-b42b-e0045f37ad9f/progress-completed.png)
- [题库抽屉截图](C:/Users/32157/.codex/visualizations/2026/09/29/01a0eac0-fa31-7731-b42b-e0045f37ad9f/problem-editor.png)
- [语言弹窗截图](C:/Users/32157/.codex/visualizations/2026/09/29/01a0eac0-fa31-7731-b42b-e0045f37ad9f/language-dialog.png)
- [移动视口减少动态效果截图](C:/Users/32157/.codex/visualizations/2026/09/29/01a0eac0-fa31-7731-b42b-e0045f37ad9f/mobile-editor-reduced-motion.png)

已人工查看抽屉、语言弹窗和移动视口截图，布局未出现裁切或横向溢出。自动化以 Chromium 和模拟视口为准；没有实机触屏、Safari/Firefox、旧浏览器或完整真实后端流程验收，没有测量帧率或 GPU 合成层。toast 共用通知样式，但浏览器回归直接触发的是 global-notice。各计划中的慢速录像、完整状态矩阵、设备手势和跨浏览器项目保留为人工检查项，不能把本记录解释为全部设备上的性能保证。
