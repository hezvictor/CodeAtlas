import assert from "node:assert/strict";
import { test } from "node:test";
import { emptyConversationContext, restoreConversationContext } from "./chat-context";

test("restoring a conversation uses only its latest context-bearing message", () => {
  const context = restoreConversationContext([
    { problem_id: "a", mode: "acm_analysis", knowledge_scope: "all", solution_language: null },
    { problem_id: null, mode: "normal", knowledge_scope: "none", solution_language: null },
  ]);
  assert.equal(context.problemId, "a");
  assert.equal(context.mode, "normal");
  assert.equal(context.knowledgeScope, "none");
  assert.equal(context.solutionLanguage, null);
});

test("empty context clears ACM state", () => {
  const context = emptyConversationContext();
  assert.equal(context.mode, "normal");
  assert.equal(context.knowledgeScope, "none");
  assert.equal(context.problemId, null);
  assert.equal(context.solutionLanguage, null);
});
