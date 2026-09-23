"use client";

import Link from "next/link";
import "./knowledge-overrides.css";
import { ChangeEvent, FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import Navbar from "../../components/Navbar";
import { API, getToken } from "../../lib/auth";
import { apiFetch, reportError } from "../../lib/errors";

type Version = { id: string; original_filename: string; size_bytes: number; status: string };
type Document = { id: string; group_id: string | null; title: string; updated_at: string; latest_version: Version | null };
type Group = { id: string; name: string; description: string | null };
const statusText: Record<string, string> = { uploaded: "已上传", parsing: "解析中", chunking: "切块中", embedding: "向量化", indexed: "已索引", failed: "处理失败" };

export default function KnowledgePage() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [groups, setGroups] = useState<Group[]>([]);
  const [selectedGroupId, setSelectedGroupId] = useState("");
  const [newGroupName, setNewGroupName] = useState("");
  const [query, setQuery] = useState("");
  const [uploading, setUploading] = useState(false);
  const [token, setToken] = useState("");
  const load = useCallback(async () => {
    const access = getToken();
    if (!access) return;
    const headers = { Authorization: `Bearer ${access}` };
    const [documentsResponse, groupsResponse] = await Promise.all([apiFetch(`${API}/knowledge/documents`, { headers }), apiFetch(`${API}/knowledge/groups`, { headers })]);
    setDocuments(await documentsResponse.json());
    setGroups(await groupsResponse.json());
  }, []);
  useEffect(() => { const access = getToken(); setToken(access); if (access) load().catch((error) => reportError(error, "知识库加载失败")); }, [load]);
  useEffect(() => {
    if (!documents.some((item) => item.latest_version && !["indexed", "failed"].includes(item.latest_version.status))) return;
    const timer = window.setInterval(() => load().catch(() => undefined), 3000);
    return () => window.clearInterval(timer);
  }, [documents, load]);
  const visibleDocuments = useMemo(() => documents.filter((item) => {
    const inGroup = !selectedGroupId || (selectedGroupId === "ungrouped" ? !item.group_id : item.group_id === selectedGroupId);
    return inGroup && `${item.title} ${item.latest_version?.original_filename || ""}`.toLowerCase().includes(query.toLowerCase());
  }), [documents, query, selectedGroupId]);
  async function upload(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]; event.target.value = ""; if (!file) return;
    setUploading(true);
    try { const body = new FormData(); body.append("file", file); if (selectedGroupId && selectedGroupId !== "ungrouped") body.append("group_id", selectedGroupId); await apiFetch(`${API}/knowledge/documents`, { method: "POST", headers: { Authorization: `Bearer ${token}` }, body }); await load(); }
    catch (error) { reportError(error, "文件上传失败"); } finally { setUploading(false); }
  }
  async function createGroup(event: FormEvent) {
    event.preventDefault(); const name = newGroupName.trim(); if (!name) return;
    try { const response = await apiFetch(`${API}/knowledge/groups`, { method: "POST", headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" }, body: JSON.stringify({ name }) }); const group = await response.json() as Group; setNewGroupName(""); setSelectedGroupId(group.id); await load(); }
    catch (error) { reportError(error, "创建分组失败"); }
  }
  async function renameGroup(group: Group) {
    const name = window.prompt("新的分组名称", group.name)?.trim(); if (!name || name === group.name) return;
    try { await apiFetch(`${API}/knowledge/groups/${group.id}`, { method: "PATCH", headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" }, body: JSON.stringify({ name, description: group.description }) }); await load(); }
    catch (error) { reportError(error, "重命名分组失败"); }
  }
  async function deleteGroup(group: Group) {
    if (!window.confirm(`删除分组“${group.name}”？分组内文档将变为未分组。`)) return;
    try { await apiFetch(`${API}/knowledge/groups/${group.id}`, { method: "DELETE", headers: { Authorization: `Bearer ${token}` } }); setSelectedGroupId(""); await load(); }
    catch (error) { reportError(error, "删除分组失败"); }
  }
  if (!token) return <><Navbar /><main className="workspace"><h1 className="page-title">请先登录</h1><p className="sub">登录后才能管理私人知识库。</p></main></>;
  const selectedGroup = groups.find(group => group.id === selectedGroupId);
  return <><Navbar /><main className="workspace knowledge-page">
    <div className="eyebrow">PRIVATE KNOWLEDGE / 03</div>
    <div className="knowledge-hero"><div><h1 className="page-title">长期资料库</h1><p className="sub">上传模板、题解和复盘笔记。索引完成后，可在聊天中开启“使用知识库”进行检索。</p></div><label className={`pill fill upload-cta ${uploading ? "disabled" : ""}`}><input type="file" accept=".md,.markdown,.pdf,.docx,.txt,.c,.cc,.cpp,.h,.hpp,.java,.py,.html,.htm" onChange={upload} disabled={uploading} />{uploading ? "处理中…" : "＋ 上传长期资料"}</label></div>
    <section className="knowledge-groups panel" aria-label="知识库分组"><div className="knowledge-group-header"><strong>资料分组</strong><form onSubmit={createGroup}><input aria-label="新分组名称" placeholder="新分组名称" value={newGroupName} maxLength={100} onChange={event => setNewGroupName(event.target.value)} /><button className="icon-button" disabled={!newGroupName.trim()}>＋ 创建</button></form></div><div className="knowledge-group-list"><button className={selectedGroupId === "" ? "selected" : ""} onClick={() => setSelectedGroupId("")}>全部资料</button><button className={selectedGroupId === "ungrouped" ? "selected" : ""} onClick={() => setSelectedGroupId("ungrouped")}>未分组</button>{groups.map(group => <button key={group.id} className={selectedGroupId === group.id ? "selected" : ""} onClick={() => setSelectedGroupId(group.id)}>{group.name}</button>)}</div>{selectedGroup && <div className="knowledge-group-actions"><span>上传文件时将归入“{selectedGroup.name}”</span><button className="icon-button" onClick={() => renameGroup(selectedGroup)}>重命名</button><button className="icon-button" onClick={() => deleteGroup(selectedGroup)}>删除分组</button></div>}</section>
    <section className="knowledge-list" style={{ marginTop: 28 }}><div className="knowledge-toolbar"><input value={query} onChange={event => setQuery(event.target.value)} placeholder="搜索文档、笔记或代码" /></div>{!visibleDocuments.length && <div className="panel empty-knowledge"><strong>{query ? "没有匹配文档" : "还没有长期资料"}</strong><p>{query ? "换个关键词试试。" : "上传后，索引完成的文件可参与开启知识库的会话。"}</p></div>}{visibleDocuments.map(document => { const version = document.latest_version; const status = version?.status || "uploaded"; return <article className="document-row panel" key={document.id}><div className="document-glyph">{version?.original_filename.split(".").pop()?.toUpperCase() || "DOC"}</div><div className="document-main"><Link href={`/knowledge/${document.id}`}><strong>{document.title}</strong></Link><div className="muted">{groups.find(group => group.id === document.group_id)?.name || "未分组"} · {version?.original_filename} · {version ? `${Math.ceil(version.size_bytes / 1024)} KB` : "等待上传"}</div></div><div className={`document-status status-${status}`}><i />{statusText[status] || status}</div><Link className="icon-button" href={`/knowledge/${document.id}`}>查看 →</Link>{status === "failed" && <button className="icon-button" onClick={() => apiFetch(`${API}/knowledge/documents/${document.id}/retry`, { method: "POST", headers: { Authorization: `Bearer ${token}` } }).then(load).catch(error => reportError(error, "重试失败"))}>重试</button>}</article>; })}</section>
  </main></>;
}
