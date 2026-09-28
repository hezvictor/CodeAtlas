import assert from "node:assert/strict";
import test from "node:test";
import { documentProgress, canLeaveBatch } from "./knowledge";
import type { KnowledgeDocument } from "./knowledge";

const doc = { id: "doc", latest_version: { status: "embedding" }, operation: { status: "running", stage: "embedding", completed_chunks: 10, total_chunks: 20 } } as KnowledgeDocument;
test("embedding progress never promises completion before index commit", () => {
  assert.equal(documentProgress(doc).label, "向量化 10 / 20");
  assert.ok((documentProgress(doc).percent || 0) < 100);
  assert.equal(documentProgress({ ...doc, operation: { ...doc.operation!, completed_chunks: 20 } }).percent, 95);
  assert.equal(documentProgress({ ...doc, active_version: { status: "indexed" }, operation: { ...doc.operation!, status: "completed" } } as KnowledgeDocument).percent, 100);
});
test("safe navigation requires each file stored or intentionally skipped", () => {
  assert.equal(canLeaveBatch(["stored", "skipped"]), true);
  assert.equal(canLeaveBatch(["stored", "uploading"]), false);
  assert.equal(canLeaveBatch(["stored", "failed"]), false);
});
test("replacement failure keeps old availability explicit", () => {
  const failed = documentProgress({ ...doc, active_version: { status: "indexed" }, operation: { ...doc.operation!, status: "failed", error_message: "参数错误" } } as KnowledgeDocument);
  assert.match(failed.detail, /当前版本仍可检索/);
});
test("legacy completed job cannot label an inactive failed index as searchable", () => {
  const legacy = { ...doc, active_version: null, latest_version: { status: "failed", error_message: "原索引未完整生成" }, operation: { ...doc.operation!, status: "completed" } } as KnowledgeDocument;
  const progress = documentProgress(legacy);
  assert.equal(progress.label, "处理失败");
  assert.match(progress.detail, /原索引未完整生成/);
  assert.notEqual(progress.percent, 100);
});
