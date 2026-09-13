import assert from "node:assert/strict";
import { test } from "node:test";
import { emptyConversationContext, restoreConversationContext } from "./chat-context";

test("restoring a conversation uses only its latest context-bearing message", () => {
  const context = restoreConversationContext([
    { problem_id: "a", mode: "acm_analysis", solution_language: null },
    { problem_id: "b", mode: "acm_solution", solution_language: "cpp" },
  ]);
  assert.equal(context.problemId, "b");
  assert.equal(context.mode, "acm_solution");
  assert.equal(context.solutionLanguage, "cpp");
});

test("empty context clears ACM state", () => {
  const context = emptyConversationContext();
  assert.equal(context.mode, "normal");
  assert.equal(context.problemId, null);
  assert.equal(context.solutionLanguage, null);
});
