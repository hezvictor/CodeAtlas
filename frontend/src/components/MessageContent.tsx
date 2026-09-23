"use client";

import React, { useState, type HTMLAttributes } from "react";
import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";

function CodeBlock({ className, children, node: _node, ...props }: HTMLAttributes<HTMLElement> & { node?: unknown }) {
  void _node;
  const [copied, setCopied] = useState(false);
  const language = className?.match(/language-([\w+#-]+)/)?.[1] || "text";
  const code = String(children).replace(/\n$/, "");
  const isBlock = Boolean(className);

  if (!isBlock) return <code className="message-inline-code" {...props}>{children}</code>;

  async function copyCode() {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1200);
    } catch {
      setCopied(false);
    }
  }

  return <div className="message-code-block">
    <div className="message-code-toolbar"><span>{language}</span><button type="button" onClick={copyCode}>{copied ? "已复制" : "复制代码"}</button></div>
    <pre><code className={className} {...props}>{children}</code></pre>
  </div>;
}

const components: Components = {
  pre: ({ children }) => <>{children}</>,
  code: CodeBlock,
  a: ({ children, href }) => <a href={href} target="_blank" rel="noreferrer">{children}</a>,
  table: ({ children }) => <div className="message-table-wrap"><table>{children}</table></div>,
};

export default function MessageContent({ content }: { content: string }) {
  return <div className="message-markdown"><ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>{content}</ReactMarkdown></div>;
}
