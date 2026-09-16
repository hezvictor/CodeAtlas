import assert from "node:assert/strict";
import { test } from "node:test";
import { citationViewModel } from "./CitationPanel";

test("citation panel renders document metadata and explicit citation state", () => {
  const text = JSON.stringify(citationViewModel({ chunk_id: "c1", quote: "private text", score: 0.9, locator: { page: 3 }, document_title: "算法模板", file_name: "algo.md", group_name: "我的文档", explicitly_cited: true }));
  assert.match(text, /算法模板/);
  assert.match(text, /algo.md/);
  assert.match(text, /我的文档/);
  assert.match(text, /已引用/);
});
