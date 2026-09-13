import assert from "node:assert/strict";
import { test } from "node:test";
import { deleteRequest, downloadRequest, reindexRequest, retryRequest, uploadVersionRequest } from "./DocumentActions";

test("document action builders target the requested document", () => {
  assert.match(retryRequest("doc-1").url, /documents\/doc-1\/retry$/);
  assert.match(reindexRequest("doc-1").url, /documents\/doc-1\/reindex$/);
  assert.match(deleteRequest("doc-1").url, /documents\/doc-1$/);
});

test("document version builders target the requested document", () => {
  assert.match(uploadVersionRequest("doc-1").url, /knowledge\/documents\/doc-1\/versions$/);
  assert.match(downloadRequest("doc-1").url, /knowledge\/documents\/doc-1\/download$/);
});
