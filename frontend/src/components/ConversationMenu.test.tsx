import assert from "node:assert/strict";
import { test } from "node:test";
import { conversationMenuActions } from "./ConversationMenu";

test("conversation menu exposes management actions and never exposes sharing", () => {
  const text = JSON.stringify(conversationMenuActions(false));
  assert.match(text, /重命名/);
  assert.match(text, /置顶/);
  assert.match(text, /多选/);
  assert.match(text, /删除/);
  assert.doesNotMatch(text, /分享/);
});
