"use client";

import Link from "next/link";
import { ChangeEvent, useEffect, useMemo, useState } from "react";
import Navbar from "../../components/Navbar";
import { API, apiFetch, getToken } from "../../lib/auth";
import { reportError } from "../../lib/errors";

type Version = { id: string; original_filename: string; size_bytes: number; status: string };
type Document = { id: string; title: string; updated_at: string; latest_version: Version | null };
const statusText: Record<string, string> = { uploaded: "已上传", parsing: "解析中", chunking: "切块中", embedding: "向量化", indexed: "已索引", failed: "处理失败" };

export default function KnowledgePage() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [query, setQuery] = useState("");
  const [uploading, setUploading] = useState(false);
  const [token, setToken] = useState("");
  async function load() {
    const access = token || getToken();
    if (!access) return;
    const response = await apiFetch(`${API}/knowledge/documents`, { headers: { Authorization: `Bearer ${access}` } });
    setDocuments(await response.json());
  }
  useEffect(() => { const access = getToken(); setToken(access); if (access) load().catch((error) => reportError(error, "知识库加载失败")); }, []);
  useEffect(() => {
    if (!documents.some((item) => item.latest_version && !["indexed", "failed"].includes(item.latest_version.status))) return;
    const timer = window.setInterval(() => load().catch(() => undefined), 3000);
    return () => window.clearInterval(timer);
  }, [documents, token]);
  const visibleDocuments = useMemo(() => documents.filter((item) => `${item.title} ${item.latest_version?.original_filename || ""}`.toLowerCase().includes(query.toLowerCase())), [documents, query]);
  async function upload(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]; event.target.value = ""; if (!file) return;
    setUploading(true);
    try { const body = new FormData(); body.append("file", file); await apiFetch(`${API}/knowledge/documents`, { method: "POST", headers: { Authorization: `Bearer ${token}` }, body }); await load(); }
    catch (error) { reportError(error, "文件上传失败"); } finally { setUploading(false); }
  }
  if (!token) return <><Navbar /><main className="workspace"><h1 className="page-title">请先登录</h1><p className="sub">登录后才能管理私人知识库。</p></main></>;
  return <><Navbar /><main className="workspace knowledge-page"><div className="eyebrow">PRIVATE KNOWLEDGE / 03</div><div className="knowledge-hero"><div><h1 className="page-title">长期资料库</h1><p className="sub">上传模板、题解和复盘笔记。索引完成后，所有聊天会自动参考这些资料。</p></div><label className={`pill fill upload-cta ${uploading ? "disabled" : ""}`}><input type="file" accept=".md,.markdown,.pdf,.docx,.txt,.c,.cc,.cpp,.h,.hpp,.java,.py,.html,.htm" onChange={upload} disabled={uploading} />{uploading ? "处理中…" : "＋ 上传长期资料"}</label></div><section className="knowledge-list" style={{ marginTop: 38 }}><div className="knowledge-toolbar"><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="搜索文档、笔记或代码" /></div>{!visibleDocuments.length && <div className="panel empty-knowledge"><strong>{query ? "没有匹配文档" : "还没有长期资料"}</strong><p>{query ? "换个关键词试试。" : "上传后，索引完成的文件会自动参与所有会话。"}</p></div>}{visibleDocuments.map((document) => { const version = document.latest_version; const status = version?.status || "uploaded"; return <article className="document-row panel" key={document.id}><div className="document-glyph">{version?.original_filename.split(".").pop()?.toUpperCase() || "DOC"}</div><div className="document-main"><Link href={`/knowledge/${document.id}`}><strong>{document.title}</strong></Link><div className="muted">{version?.original_filename} · {version ? `${Math.ceil(version.size_bytes / 1024)} KB` : "等待上传"}</div></div><div className={`document-status status-${status}`}><i />{statusText[status] || status}</div><Link className="icon-button" href={`/knowledge/${document.id}`}>查看 →</Link>{status === "failed" && <button className="icon-button" onClick={() => apiFetch(`${API}/knowledge/documents/${document.id}/retry`, { method: "POST", headers: { Authorization: `Bearer ${token}` } }).then(load).catch((error) => reportError(error, "重试失败"))}>重试</button>}</article>; })}</section></main></>;
}
