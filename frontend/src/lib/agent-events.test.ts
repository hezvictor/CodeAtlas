import assert from "node:assert/strict";
import test from "node:test";
import { reduceAgentEvent, capabilityLabel, modelIsChatReady } from "./agent-events";

test("tool events update the same step, reject stale replay and exclude raw payloads", () => {
  let steps = reduceAgentEvent([], "tool.started", { step_id: "one", tool: "search_knowledge", sequence: 1 });
  assert.equal(steps[0].state, "running");
  steps = reduceAgentEvent(steps, "tool.completed", { step_id: "one", status: "no_hit", sequence: 2, count: 0, reasoning: "SECRET", arguments: "RAW" });
  steps = reduceAgentEvent(steps, "tool.started", { step_id: "one", sequence: 1 });
  assert.equal(steps.length, 1);
  assert.equal(steps[0].state, "no_hit");
  assert.doesNotMatch(JSON.stringify(steps), /SECRET|RAW/);
});

test("verified chat connection is ready without tool capability", () => {
  assert.equal(modelIsChatReady({ status: "verified", capabilities: { chat: "verified" } }), true);
  assert.equal(modelIsChatReady({ status: "verified", capabilities: {} }), false);
  assert.equal(capabilityLabel({ status: "incomplete" }), "检测未完成，请重试");
  assert.equal(capabilityLabel({ status: "verified", capabilities: { chat: "verified" } }), "连接成功");
});
