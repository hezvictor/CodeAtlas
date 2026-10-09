import assert from "node:assert/strict";
import { test } from "node:test";
import React, { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import DocumentActions, { deleteRequest, downloadRequest, reindexRequest, retryRequest, uploadVersionRequest } from "./DocumentActions";

// tsx uses classic JSX for this standalone Node render; Next supplies its own runtime.
Object.assign(globalThis, { React });

test("unsupported document formats keep deletion available without processing actions", () => {
  for (const extension of [".pdf", ".exe"]) {
    for (const status of ["failed", "indexed"]) {
      const html = renderToStaticMarkup(createElement(DocumentActions, {
        documentId: "doc-1", status, extension, token: "test",
        supportedExtensions: [".md", ".txt"], onChanged: () => undefined,
      }));
      assert.match(html, /删除/);
      assert.doesNotMatch(html, /重试|重新索引/);
    }
  }
});

test("document action builders target the requested document", () => {
  assert.match(retryRequest("doc-1").url, /documents\/doc-1\/retry$/);
  assert.match(reindexRequest("doc-1").url, /documents\/doc-1\/reindex$/);
  assert.match(deleteRequest("doc-1").url, /documents\/doc-1$/);
});

test("document version builders target the requested document", () => {
  assert.match(uploadVersionRequest("doc-1").url, /knowledge\/documents\/doc-1\/versions$/);
  assert.match(downloadRequest("doc-1").url, /knowledge\/documents\/doc-1\/download$/);
});
