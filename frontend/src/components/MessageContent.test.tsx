import assert from "node:assert/strict";
import { test } from "node:test";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import MessageContent from "./MessageContent";

test("renders assistant markdown with headings, lists, and fenced code", () => {
  const html = renderToStaticMarkup(
    <MessageContent
      content={'## 算法\n\n1. 读取输入\n2. 输出结果\n\n```cpp\nint main() { return 0; }\n```'}
    />,
  );

  assert.match(html, /<h2>算法<\/h2>/);
  assert.match(html, /<ol>\s*<li>读取输入<\/li>\s*<li>输出结果<\/li>\s*<\/ol>/);
  assert.match(html, /<pre><code class="language-cpp">/);
  assert.match(html, /复制代码/);
  assert.doesNotMatch(html, /node="\[object Object\]"/);
});

test("does not execute raw HTML in an assistant response", () => {
  const html = renderToStaticMarkup(<MessageContent content={"<script>alert('xss')</script>"} />);

  assert.doesNotMatch(html, /<script>/);
  assert.match(html, /&lt;script&gt;/);
});
