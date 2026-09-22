"use client";

import { useState } from "react";
import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";
import hljs from "highlight.js/lib/common";

type Props = { filename: string; text: string };

export function isMarkdownFilename(filename: string) {
  const normalized = filename.trim().toLowerCase();
  return normalized.endsWith(".md") || normalized.endsWith(".markdown");
}

const codeLanguages: Record<string, string> = {
  ".c": "C",
  ".cc": "C++",
  ".cpp": "C++",
  ".h": "C/C++",
  ".hpp": "C++",
  ".java": "Java",
  ".py": "Python",
};

function filenameExtension(filename: string) {
  const normalized = filename.trim().toLowerCase();
  const index = normalized.lastIndexOf(".");
  return index >= 0 ? normalized.slice(index) : "";
}

function highlightLanguage(language: string) {
  const normalized = language.toLowerCase();
  if (["c++", "cpp", "cc", "hpp"].includes(normalized)) return "cpp";
  if (normalized === "c") return "c";
  if (normalized === "java") return "java";
  if (["python", "py"].includes(normalized)) return "python";
  return "plaintext";
}

export function codeLanguageForFilename(filename: string) {
  return codeLanguages[filenameExtension(filename)] || "Code";
}

export function isCodeFilename(filename: string) {
  return Boolean(codeLanguages[filenameExtension(filename)]);
}

function CodeBlock({ language, code }: { language: string; code: string }) {
  const [copied, setCopied] = useState(false);
  const lines = code.replace(/\n$/, "").split("\n");

  async function copyCode() {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1200);
    } catch {
      setCopied(false);
    }
  }

  return <div className="document-code-block">
    <div className="document-code-toolbar"><span className="document-code-language">{language}</span><button type="button" onClick={copyCode}>{copied ? "已复制" : "复制代码"}</button></div>
    <pre><code>{lines.map((line, index) => <span className="document-code-line" key={`${index}-${line}`}><span className="document-code-line-number" aria-hidden="true">{index + 1}</span><span className="document-code-line-text" dangerouslySetInnerHTML={{ __html: hljs.highlight(line || " ", { language: highlightLanguage(language), ignoreIllegals: true }).value }} /></span>)}</code></pre>
  </div>;
}

const markdownComponents: Components = {
  pre: ({ children }) => <>{children}</>,
  code: ({ children, className, node: _node }) => {
    const language = className?.match(/language-([\w+#-]+)/)?.[1];
    if (!language && !className) return <code className="document-inline-code">{children}</code>;
    return <CodeBlock language={language || "Code"} code={String(children).replace(/\n$/, "")} />;
  },
  table: ({ children }) => <div className="document-markdown-table"><table>{children}</table></div>,
  a: ({ children, href }) => <a href={href} target="_blank" rel="noreferrer">{children}</a>,
};

export default function DocumentPreview({ filename, text }: Props) {
  if (isCodeFilename(filename)) {
    return <CodeBlock language={codeLanguageForFilename(filename)} code={text || "文档尚未完成解析，稍后刷新。"} />;
  }

  if (!isMarkdownFilename(filename)) {
    return <pre className="document-plain-preview">{text || "文档尚未完成解析，稍后刷新。"}</pre>;
  }

  return <div className="document-markdown-preview"><ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>{text || "文档尚未完成解析，稍后刷新。"}</ReactMarkdown></div>;
}
