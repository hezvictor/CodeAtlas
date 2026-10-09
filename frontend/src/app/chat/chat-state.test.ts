import assert from "node:assert/strict";
import { test } from "node:test";
import {
  ChatSubmitGate,
  ConversationSelection,
  createDraftConversation,
  deriveConversationTitle,
  mergeMessagePage,
  parseChatLaunch,
  sortMessages,
  sortConversations,
} from "../../lib/chat-state";

test("failed first conversation creation restores the draft and allows retry", async () => {
  const gate = new ChatSubmitGate();
  let draft = "original question";
  let sends = 0;
  const callbacks = {
    onStart: () => { draft = ""; },
    onCreateFailure: (text: string) => { draft ||= text; },
  };
  await gate.submit("original question", async () => { throw new Error("offline"); }, async () => { sends++; }, callbacks);
  assert.equal(draft, "original question");
  assert.equal(sends, 0);
  await gate.submit("original question", async () => ({ id: "new" }), async () => { sends++; }, callbacks);
  assert.equal(sends, 1);
});

test("a pending first send admits only one conversation creation", async () => {
  const gate = new ChatSubmitGate();
  let release!: (value: { id: string }) => void;
  let creations = 0;
  const create = () => { creations++; return new Promise<{ id: string }>(resolve => { release = resolve; }); };
  const sent: string[] = [];
  const callbacks = { onStart: () => undefined, onCreateFailure: () => undefined };
  const first = gate.submit("question", create, async conversation => { sent.push(conversation.id); }, callbacks);
  await gate.submit("question", create, async conversation => { sent.push(conversation.id); }, callbacks);
  assert.equal(creations, 1);
  release({ id: "once" });
  await first;
  assert.deepEqual(sent, ["once"]);
});

test("a newly created conversation skips its initial history reload but reloads when revisited", () => {
  const selection = new ConversationSelection();
  selection.created("new");
  assert.equal(selection.currentId, "new");
  assert.equal(selection.select("new"), false);
  assert.equal(selection.select("old"), true);
  assert.equal(selection.select("old"), false);
  assert.equal(selection.select("new"), true);
});

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
  assert.deepEqual(parseChatLaunch("?problem_id=abc&mode=acm_solution"), { conversationId: null, problemId: "abc", mode: "acm_solution" });
  assert.deepEqual(parseChatLaunch("?problem_id=abc&mode=invalid"), { conversationId: null, problemId: "abc", mode: "normal" });
  assert.deepEqual(parseChatLaunch("?mode=acm_analysis"), { conversationId: null, problemId: null, mode: "normal" });
});

test("continue conversation link identifies the saved conversation", () => {
  assert.deepEqual(parseChatLaunch("?conversation_id=saved-123"), {
    conversationId: "saved-123", problemId: null, mode: "normal",
  });
  assert.deepEqual(parseChatLaunch("?conversation_id=saved-123&problem_id=other&mode=acm_solution"), {
    conversationId: "saved-123", problemId: null, mode: "normal",
  });
});

test("first question derives a bounded conversation title", () => {
  assert.equal(deriveConversationTitle("  Explain Dijkstra's algorithm in detail  "), "Explain Dijkstra's algor…");
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

test("message positions preserve server order across timestamp ties and page merges", () => {
  const sameTime = "2026-09-30T00:00:00Z";
  const older = [{ id: "first-user", role: "user" as const, position: 10, created_at: sameTime },
                 { id: "first-answer", role: "assistant" as const, position: 11, created_at: sameTime }];
  const current = [{ id: "second-user", role: "user" as const, position: 12, created_at: sameTime },
                   { id: "second-answer", role: "assistant" as const, position: 13, created_at: sameTime }];
  assert.deepEqual(mergeMessagePage(current, older).map(item => item.id),
                   ["first-user", "first-answer", "second-user", "second-answer"]);
});
