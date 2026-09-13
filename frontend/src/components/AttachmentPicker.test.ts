import assert from "node:assert/strict";
import { test } from "node:test";
import { attachmentListRequest, attachRequest, detachRequest } from "./AttachmentPicker";

test("attachment request builders use the active conversation", () => {
  assert.match(attachmentListRequest("conversation-b").url, /conversation-b\/attachments$/);
  assert.match(attachRequest("conversation-b", "version-1").url, /conversation-b\/attachments\/version-1$/);
  assert.match(detachRequest("conversation-b", "attachment-1").url, /conversation-b\/attachments\/attachment-1$/);
});
