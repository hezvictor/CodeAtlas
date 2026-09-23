import assert from "node:assert/strict";
import { test } from "node:test";
import {
  buildKnowledgePayload,
  createDraftConversation,
  deriveConversationTitle,
  mergeMessagePage,
  parseChatLaunch,
  sortMessages,
  sortConversations,
} from "../../lib/chat-state";

test("new conversation starts as a local draft without an id", () => {
  const draft = createDraftConversation();
  assert.equal(draft.id, null);
  assert.equal(draft.title, "新对话");
});

test("older message pages merge without duplicating messages already loaded", () => {
  const older = [{ id: "1", role: "user" as const, created_at: "2026-01-01T00:00:00Z" }, { id: "2", role: "assistant" as const, created_at: "2026-01-01T00:00:01Z" }];
  const current = [{ id: "2", role: "assistant" as const, created_at: "2026-01-01T00:00:01Z" }, { id: "3", role: "user" as const, created_at: "2026-01-01T00:00:02Z" }];
  assert.deepEqual(mergeMessagePage(current, older).map(item => item.id), ["1", "2", "3"]);
});

test("problem detail links open the requested ACM mode safely", () => {
  assert.deepEqual(parseChatLaunch("?problem_id=abc&mode=acm_solution"), { problemId: "abc", mode: "acm_solution" });
  assert.deepEqual(parseChatLaunch("?problem_id=abc&mode=invalid"), { problemId: "abc", mode: "normal" });
  assert.deepEqual(parseChatLaunch("?mode=acm_analysis"), { problemId: null, mode: "normal" });
});

test("first question derives a bounded conversation title", () => {
  assert.equal(deriveConversationTitle("  Explain Dijkstra's algorithm in detail  "), "Explain Dijkstra's algor…");
});

test("knowledge scope payload supports only none and all", () => {
  assert.deepEqual(buildKnowledgePayload("none"), { knowledge_scope: "none" });
  assert.deepEqual(buildKnowledgePayload("all"), { knowledge_scope: "all" });
});

test("pinned conversations sort before recent conversations", () => {
  const sorted = sortConversations([
    { id: "old", title: "old", updated_at: "2024-01-03", pinned: false },
    { id: "pinned", title: "pinned", updated_at: "2024-01-01", pinned: true },
    { id: "new", title: "new", updated_at: "2024-01-04", pinned: false },
  ]);
  assert.deepEqual(sorted.map((item) => item.id), ["pinned", "new", "old"]);
});


test("messages sort chronologically and put the user first on timestamp ties", () => {
  const sorted = sortMessages([
    { id: "assistant", role: "assistant", content: "answer", created_at: "2024-01-01T00:00:00.000Z" },
    { id: "user", role: "user", content: "question", created_at: "2024-01-01T00:00:00.000Z" },
    { id: "older", role: "user", content: "older", created_at: "2023-12-31T23:59:59.000Z" },
  ]);

  assert.deepEqual(sorted.map((item) => item.id), ["older", "user", "assistant"]);
});
