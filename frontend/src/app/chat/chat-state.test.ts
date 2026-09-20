import assert from "node:assert/strict";
import { test } from "node:test";
import {
  buildKnowledgePayload,
  createDraftConversation,
  deriveConversationTitle,
  sortMessages,
  sortConversations,
} from "../../lib/chat-state";

test("new conversation starts as a local draft without an id", () => {
  const draft = createDraftConversation();
  assert.equal(draft.id, null);
  assert.equal(draft.title, "新对话");
});

test("first question derives a bounded conversation title", () => {
  assert.equal(deriveConversationTitle("  Explain Dijkstra's algorithm in detail  "), "Explain Dijkstra's algor…");
});

test("knowledge scope payload distinguishes none, all and selected groups", () => {
  assert.deepEqual(buildKnowledgePayload("none", ""), { knowledge_scope: "none", knowledge_group_ids: [] });
  assert.deepEqual(buildKnowledgePayload("all", ""), { knowledge_scope: "all", knowledge_group_ids: [] });
  assert.deepEqual(buildKnowledgePayload("groups", "g-1"), { knowledge_scope: "groups", knowledge_group_ids: ["g-1"] });
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
