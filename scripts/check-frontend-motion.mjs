// Usage: start frontend on 127.0.0.1:3100, then node scripts/check-frontend-motion.mjs.
// Requires the existing agent-browser CLI; no real backend credentials or writes.
import assert from "node:assert/strict";
import { execFileSync, spawn } from "node:child_process";
import { dirname, resolve, join } from "node:path";
import { fileURLToPath } from "node:url";
import { test } from "node:test";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const base = process.env.MOTION_TEST_URL || "http://127.0.0.1:3100";
assert.ok(["127.0.0.1", "localhost"].includes(new URL(base).hostname), "Fixture must only run against a local frontend");
const session = "codeatlas-motion-regression";
let binary = process.env.AGENT_BROWSER_BIN || "agent-browser";
if (process.platform === "win32" && !process.env.AGENT_BROWSER_BIN) {
  const shim = execFileSync("where.exe", ["agent-browser.cmd"], { encoding: "utf8" }).trim().split(/\r?\n/)[0];
  binary = join(dirname(shim), "node_modules", "agent-browser", "bin", "agent-browser-win32-x64.exe");
}
function browser(...args) {
  let output;
  try {
    output = execFileSync(binary, ["--session", session, "--json", ...args], { encoding: "utf8", timeout: 45000 });
  } catch (error) {
    throw new Error(error.stdout?.toString().trim() || error.stderr?.toString().trim() || error.message, { cause: error });
  }
  const result = JSON.parse(output);
  assert.notEqual(result.success, false, result.error || output);
  return result.data;
}
function evaluate(source) { return browser("eval", "-b", Buffer.from(source).toString("base64")).result; }
function wait(condition) {
  try { browser("wait", "--fn", condition); }
  catch (error) {
    console.error("Browser state:", evaluate(`({
      url: location.pathname,
      requests: window.__motionFixture?.requests.slice(-10),
      hold: window.__motionFixture?.holdProblems,
      pagination: document.querySelector('.problem-pagination')?.textContent,
      buttons: [...document.querySelectorAll('.problem-pagination button')].map(button => ({text: button.textContent, disabled: button.disabled})),
      cards: document.querySelectorAll('.problem-card').length
    })`));
    throw error;
  }
}
function open(path) { browser("open", base + path); }
function capture(name) {
  if (process.env.MOTION_ARTIFACT_DIR) browser("screenshot", join(process.env.MOTION_ARTIFACT_DIR, name + ".png"));
}
// On Windows the first daemon can inherit stdout. Wait for the CLI process,
// rather than its inherited pipe, so a successful launch cannot time out.
await new Promise((resolveLaunch, reject) => {
  const child = spawn(binary, ["--session", session, "--json", "open", "--init-script", join(root, "scripts/frontend-motion-fixture.js"), base],
    { stdio: ["ignore", "pipe", "pipe"] });
  let output = "";
  let errors = "";
  child.stdout.on("data", chunk => { output += chunk; });
  child.stderr.on("data", chunk => { errors += chunk; });
  const timer = setTimeout(() => { child.kill(); reject(new Error("Browser launch timed out")); }, 45000);
  child.on("error", error => { clearTimeout(timer); reject(error); });
  child.on("exit", code => {
    clearTimeout(timer);
    child.stdout.destroy();
    child.stderr.destroy();
    try {
      assert.equal(code, 0, errors);
      const result = JSON.parse(output);
      assert.notEqual(result.success, false, result.error);
      resolveLaunch();
    } catch (error) { reject(error); }
  });
});
process.on("exit", () => {
  try { browser("close"); } catch { /* Preserve the actual test outcome. */ }
});

test("refresh keeps existing problems and the displayed page until the response arrives", () => {
  open("/problems");
  wait("document.querySelectorAll('.problem-card').length === 12");
  evaluate("window.__motionFixture.holdProblems = true");
  browser("fill", ".problem-filters input:first-child", "新的筛选");
  wait("window.__motionFixture.pendingProblems !== null");
  const loading = evaluate(`({ cards: document.querySelectorAll('.problem-card').length,
    pagination: !!document.querySelector('.problem-pagination'),
    buttonsDisabled: [...document.querySelectorAll('.problem-pagination button')].every(button => button.disabled),
    status: document.querySelector('.problem-refresh-status')?.textContent })`);
  assert.equal(loading.cards, 12, "Refreshing must not clear the already loaded cards");
  assert.equal(loading.pagination, true);
  assert.equal(loading.buttonsDisabled, true);
  assert.match(loading.status, /上次结果/);
  capture("problem-refresh");
  evaluate("window.__motionFixture.pendingProblems()");
  wait("document.querySelector('.problem-pagination button:last-child')?.disabled === false");
  evaluate("window.__motionFixture.holdProblems = true");
  browser("scrollintoview", ".problem-pagination button:last-child");
  browser("click", ".problem-pagination button:last-child");
  wait("window.__motionFixture.pendingProblems !== null");
  assert.match(evaluate("document.querySelector('.problem-pagination').textContent"), /第 1 页/);
  evaluate("window.__motionFixture.pendingProblems()");
  wait("document.querySelector('.problem-pagination').textContent.includes('第 2 页')");
  const settledHeight = evaluate("document.querySelector('.problem-refresh-status').getBoundingClientRect().height");
  assert.ok(settledHeight >= 24, "Refresh status keeps its reserved space after completion");
});

test("progress completion and later steps preserve the user's disclosure choice", () => {
  open("/chat");
  wait("document.querySelector('.conversation-row .side-item') !== null");
  browser("click", ".conversation-row .side-item");
  wait("document.querySelector('.mode-select select').value === 'motion-model'");
  browser("fill", ".composer textarea", "测试执行反馈");
  browser("click", ".composer-foot .send");
  wait("document.querySelector('.agent-progress')?.open === true");
  evaluate("window.__motionFixture.emit('retrieval.completed', {step_id:'retrieval-1', sequence:2, status:'ok'})");
  wait("document.querySelector('.agent-progress summary').textContent.includes('处理步骤')");
  assert.equal(evaluate("document.querySelector('.agent-progress').open"), true, "Completing a step must not collapse its results");
  browser("click", ".agent-progress summary");
  wait("document.querySelector('.agent-progress').open === false");
  evaluate("window.__motionFixture.emit('tool.started', {step_id:'tool-1', tool:'search_knowledge', sequence:3})");
  wait("document.querySelector('.agent-progress summary').textContent.includes('补充检索')");
  assert.equal(evaluate("document.querySelector('.agent-progress').open"), false, "New steps must preserve manual collapse");
  browser("focus", ".agent-progress summary");
  browser("press", "Space");
  wait("document.querySelector('.agent-progress').open === true");
  evaluate("window.__motionFixture.emit('tool.completed', {step_id:'tool-1', sequence:4, status:'ok'})");
  wait("document.querySelector('.agent-progress summary').textContent.includes('处理步骤')");
  assert.equal(evaluate("document.querySelector('.agent-progress').open"), true);
  capture("progress-completed");
  evaluate("window.__motionFixture.emit('run.completed', {sequence:5}); window.__motionFixture.finish()");
});

test("overlays and notices enter with short composited transitions and close immediately", () => {
  browser("set", "media", "light");
  open("/problems");
  wait("document.querySelectorAll('.problem-card').length === 12");
  const drawer = evaluate(`(async () => {
    document.querySelector('.problem-hero-actions button').click();
    await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
    const panel = document.querySelector('.problem-editor');
    const animations = panel.getAnimations();
    animations.forEach(animation => animation.pause());
    return {count: animations.length, timing: animations.map(animation => animation.effect.getTiming().duration),
      properties: animations.map(animation => animation.transitionProperty), width: panel.getBoundingClientRect().width};
  })()`);
  assert.equal(drawer.count, 1, "The drawer must actually animate on insertion");
  assert.ok(drawer.timing.every(duration => duration > 0 && duration <= 300));
  assert.deepEqual(drawer.properties, ["transform"]);
  evaluate("document.querySelector('.problem-editor').getAnimations().forEach(animation => animation.finish())");
  capture("problem-editor");
  browser("click", ".problem-editor .dialog-close");
  assert.equal(evaluate("document.querySelector('.problem-editor') === null"), true);
  const notice = evaluate(`(async () => {
    window.dispatchEvent(new CustomEvent('codeatlas:error', {detail:{message:'测试提示'}}));
    await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
    const node = document.querySelector('.global-notice');
    const animations = node.getAnimations(); animations.forEach(animation => animation.pause());
    return {count: animations.length, role: node.getAttribute('role'), properties: animations.map(animation => animation.transitionProperty)};
  })()`);
  assert.equal(notice.count, 1);
  assert.equal(notice.role, "alert");
  assert.deepEqual(notice.properties, ["opacity"]);
  evaluate("document.querySelector('.global-notice').getAnimations().forEach(animation => animation.finish())");
  const replay = evaluate(`(async () => {
    const node = document.querySelector('.global-notice');
    window.dispatchEvent(new CustomEvent('codeatlas:error', {detail:{message:'更新后的测试提示'}}));
    await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
    return {sameNode: node === document.querySelector('.global-notice'), animations: node.getAnimations().length};
  })()`);
  assert.equal(replay.sameNode, true);
  assert.equal(replay.animations, 0, "Updating an existing notice must not replay its entry");
  browser("click", ".global-notice button");
  assert.equal(evaluate("document.querySelector('.global-notice') === null"), true);
  browser("scrollintoview", ".problem-hero-actions button");
  const button = evaluate(`(() => {
    const node = document.querySelector('.problem-hero-actions button');
    const box = node.getBoundingClientRect();
    return {x: box.x + box.width / 2, y: box.y + box.height / 2, width: node.offsetWidth};
  })()`);
  browser("mouse", "move", String(Math.round(button.x)), String(Math.round(button.y)));
  browser("mouse", "down", "left");
  wait("new DOMMatrix(getComputedStyle(document.querySelector('.problem-hero-actions button')).transform).a < 0.99");
  const pressed = evaluate(`(() => {
    const node = document.querySelector('.problem-hero-actions button');
    return {scale: new DOMMatrix(getComputedStyle(node).transform).a, width: node.offsetWidth};
  })()`);
  assert.ok(pressed.scale >= 0.95 && pressed.scale < 0.99);
  assert.equal(pressed.width, button.width, "Press feedback must not change layout width");
  browser("mouse", "up", "left");
  wait("document.querySelector('.problem-editor') !== null");
  evaluate("document.querySelector('.problem-editor .dialog-close').click()");
  browser("focus", ".problem-hero-actions button");
  browser("press", "Tab");
  browser("press", "Shift+Tab");
  const focused = evaluate(`(() => {
    const node = document.querySelector('.problem-hero-actions button');
    return {keyboard: node.matches(':focus-visible'), transition: getComputedStyle(node).transitionDuration};
  })()`);
  assert.equal(focused.keyboard, true);
  assert.equal(focused.transition, "0s", "Keyboard focus must not acquire press motion");
  open("/chat");
  wait("document.querySelector('.chat-head .mode') !== null");
  browser("click", ".chat-head .mode");
  const dialog = evaluate(`(async () => {
    document.querySelector('.mode-menu button:last-child').click();
    await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
    const node = document.querySelector('.language-dialog');
    const animations = node.getAnimations(); animations.forEach(animation => animation.pause());
    return { count: animations.length, properties: animations.map(animation => animation.transitionProperty).sort(),
      durations: animations.map(animation => animation.effect.getTiming().duration) };
  })()`);
  assert.equal(dialog.count, 2);
  assert.deepEqual(dialog.properties, ["opacity", "transform"]);
  assert.ok(dialog.durations.every(duration => duration > 0 && duration <= 300));
  evaluate("document.querySelector('.language-dialog').getAnimations().forEach(animation => animation.finish())");
  capture("language-dialog");
  browser("click", ".language-dialog .dialog-close");
  assert.equal(evaluate("document.querySelector('.language-dialog') === null"), true);
});

test("reduced motion shows overlays instantly and mobile layouts do not overflow", () => {
  browser("set", "media", "light", "reduced-motion");
  browser("set", "viewport", "390", "844");
  open("/problems");
  wait("document.querySelectorAll('.problem-card').length === 12");
  browser("click", ".problem-hero-actions button");
  const result = evaluate(`({ animations: document.querySelector('.problem-editor').getAnimations().length,
    visible: getComputedStyle(document.querySelector('.problem-editor')).opacity,
    overflow: document.documentElement.scrollWidth > innerWidth })`);
  assert.equal(result.animations, 0);
  assert.equal(result.visible, "1");
  assert.equal(result.overflow, false);
  capture("mobile-editor-reduced-motion");
  browser("click", ".problem-editor .dialog-close");
  assert.equal(evaluate("document.querySelector('.problem-editor') === null"), true);
  browser("set", "viewport", "1280", "900");
  browser("set", "media", "light");
});
