import assert from "node:assert/strict";
import { test } from "node:test";
import { attachmentListRequest, attachRequest, detachRequest, indexedDocumentOptions, resolveAttachmentConversationId } from "./AttachmentPicker";

test("attachment request builders use the active conversation", () => {
  assert.match(attachmentListRequest("conversation-b").url, /conversation-b\/attachments$/);
  assert.match(attachRequest("conversation-b", "version-1").url, /conversation-b\/attachments\/version-1$/);
  assert.match(detachRequest("conversation-b", "attachment-1").url, /conversation-b\/attachments\/attachment-1$/);
});

test("uploading from a draft creates a conversation before binding the file", async () => {
  let created = 0;
  const conversationId = await resolveAttachmentConversationId("", async () => {
    created += 1;
    return "conversation-new";
  });

  assert.equal(conversationId, "conversation-new");
  assert.equal(created, 1);
});

test("only indexed long-term documents can be attached", () => {
  const documents = [
    { id: "a", title: "Ready", latest_version: { id: "v1", status: "indexed" } },
    { id: "b", title: "Pending", latest_version: { id: "v2", status: "embedding" } },
    { id: "c", title: "Empty", latest_version: null },
  ];
  assert.deepEqual(indexedDocumentOptions(documents).map(item => item.id), ["a"]);
});
