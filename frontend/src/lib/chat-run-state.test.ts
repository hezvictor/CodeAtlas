import assert from "node:assert/strict";
import { test } from "node:test";
import { emptyRunView, reduceRunFrame, RunStreamGate, updateAssistantMessage } from "./chat-run-state";

test("snapshot restores a durable final answer and ignores replayed terminal events", () => {
  const snapshot = reduceRunFrame(emptyRunView(), "run.snapshot", {
    run_id: "run-1", message_id: "answer-1", sequence: 9,
    status: "completed", content: "已校验的答案",
  });
  assert.equal(snapshot.answer, "已校验的答案");
  assert.equal(snapshot.status, "completed");
  assert.equal(snapshot.messageId, "answer-1");
  assert.deepEqual(reduceRunFrame(snapshot, "run.waiting", { sequence: 8, code: "TEMPORARY_CONTEXT_LOST" }), snapshot);
});

test("progress events update steps without showing model output before message.final", () => {
  let state = reduceRunFrame(emptyRunView(), "run.snapshot", {
    run_id: "run-1", message_id: "answer-1", sequence: 1, status: "queued", content: "",
  });
  state = reduceRunFrame(state, "model.started", { step_id: "model-1", sequence: 2 });
  state = reduceRunFrame(state, "model.completed", { step_id: "model-1", status: "ok", sequence: 3 });
  assert.equal(state.answer, "");
  assert.equal(state.steps[0].state, "ok");
  state = reduceRunFrame(state, "message.final", { message_id: "answer-1", content: "最终答案", sequence: 4 });
  assert.equal(state.answer, "最终答案");
});

test("waiting and resumed snapshots replace the old error without accepting stale events", () => {
  let state = reduceRunFrame(emptyRunView(), "run.waiting", {
    run_id: "run-1", sequence: 5, code: "TEMPORARY_CONTEXT_LOST",
  });
  assert.equal(state.status, "waiting_context");
  assert.match(state.answer, /重新上传/);
  state = reduceRunFrame(emptyRunView(), "run.snapshot", {
    run_id: "run-1", message_id: "answer-1", status: "queued", sequence: 6, content: "",
  });
  assert.equal(state.answer, "");
  assert.equal(reduceRunFrame(state, "run.waiting", { sequence: 5, code: "TEMPORARY_CONTEXT_LOST" }).status, "queued");
});

test("retrieval and citation events keep evidence separate from the answer", () => {
  let state = reduceRunFrame(emptyRunView(), "retrieval.completed", { step_id: "initial-retrieval", status: "no_hit", sequence: 1 });
  state = reduceRunFrame(state, "citations.validated", { items: [{ chunk_id: "chunk-1", quote: "证据", score: 1 }], sequence: 2 });
  assert.equal(state.retrievalStatus, "no_hit");
  assert.equal(state.citations[0].chunk_id, "chunk-1");
  assert.equal(state.answer, "");
});

test("an optimistic user message is never overwritten by an assistant run frame", () => {
  const view = { ...emptyRunView(), answer: "最终答案", status: "completed" };
  const messages = [
    { role: "user" as const, content: "我的问题" },
    { role: "assistant" as const, content: "", status: "generating" },
  ];
  assert.deepEqual(updateAssistantMessage(messages, view), [
    messages[0], { role: "assistant", content: "最终答案", status: "completed" },
  ]);
});

test("a resumed stream rejects frames from the previous reader without affecting another conversation", () => {
  const gate = new RunStreamGate();
  const old = gate.begin("conversation-1");
  const other = gate.begin("conversation-2");
  gate.invalidate("conversation-1");
  const resumed = gate.begin("conversation-1");
  assert.equal(gate.isCurrent("conversation-1", old), false);
  assert.equal(gate.isCurrent("conversation-1", resumed), true);
  assert.equal(gate.isCurrent("conversation-2", other), true);
});
