import assert from "node:assert/strict";
import { test } from "node:test";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import DocumentPreview from "./DocumentPreview";

test("renders markdown documents as formatted content", () => {
  const html = renderToStaticMarkup(
    <DocumentPreview filename="notes.md" text={'## 平成骑士\n\n- 第一部\n- 第二部\n\n| 年份 | 作品 |\n| --- | --- |\n| 2000 | 空我 |'} />,
  );

  assert.match(html, /<h2>平成骑士<\/h2>/);
  assert.match(html, /<ul>\s*<li>第一部<\/li>\s*<li>第二部<\/li>\s*<\/ul>/);
  assert.match(html, /<table>/);
  assert.match(html, /<td>空我<\/td>/);
});

test("keeps non-markdown documents in a plain text preview", () => {
  const html = renderToStaticMarkup(<DocumentPreview filename="notes.txt" text={"line 1\nline 2"} />);

  assert.match(html, /<pre>line 1\nline 2<\/pre>/);
});

test("does not render raw HTML from markdown documents", () => {
  const html = renderToStaticMarkup(<DocumentPreview filename="notes.markdown" text={"<script>alert(1)<\/script>"} />);

  assert.doesNotMatch(html, /<script>/);
  assert.match(html, /&lt;script&gt;alert\(1\)&lt;\/script&gt;/);
});

test("renders source code files with a language toolbar and line numbers", () => {
  const html = renderToStaticMarkup(<DocumentPreview filename="segment-tree.cpp" text={'#include <bits/stdc++.h>\nint main() {\n  return 0;\n}'} />);

  assert.match(html, /<span class="document-code-language">C\+\+<\/span>/);
  assert.match(html, /class="document-code-line-number"[^>]*>1<\/span>/);
  assert.match(html, /class="document-code-line-number"[^>]*>4<\/span>/);
  assert.match(html, /复制代码/);
});

test("renders fenced markdown code as a code block", () => {
  const html = renderToStaticMarkup(<DocumentPreview filename="notes.md" text={'```python\nprint("hello")\n```'} />);

  assert.match(html, /<span class="document-code-language">Python<\/span>/);
  assert.match(html, /print/);
  assert.match(html, /hello/);
});
