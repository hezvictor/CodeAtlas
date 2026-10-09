"use client";

import Link from "next/link";
import "./knowledge-overrides.css";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import Navbar from "../../components/Navbar";
import KnowledgeUpload from "../../components/KnowledgeUpload";
import KnowledgeProgress from "../../components/KnowledgeProgress";
import DocumentActions from "../../components/DocumentActions";
import { API, getToken } from "../../lib/auth";
import { apiFetch, reportError } from "../../lib/errors";
import { acknowledgeVisible, documentProcessing, Group, KnowledgeDocument, UploadPolicy } from "../../lib/knowledge";

export default function KnowledgePage() {
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([]);
  const [groups, setGroups] = useState<Group[]>([]);
  const [policy, setPolicy] = useState<UploadPolicy | null>(null);
  const [selectedGroupId, setSelectedGroupId] = useState("");
  const [newGroupName, setNewGroupName] = useState("");
  const [query, setQuery] = useState("");
  const [token, setToken] = useState("");
  const load = useCallback(async () => {
    const access = getToken(); if (!access) return;
    const response = await apiFetch(`${API}/knowledge/documents`, { headers: { Authorization: `Bearer ${access}` } });
    setDocuments(await response.json());
  }, []);
  useEffect(() => {
    const access = getToken(); setToken(access); if (!access) return;
    const headers = { Authorization: `Bearer ${access}` };
    Promise.all([load(), apiFetch(`${API}/knowledge/groups`, { headers }).then(response => response.json()).then(setGroups), apiFetch(`${API}/knowledge/documents/policy`).then(response => response.json()).then(setPolicy)]).catch(error => reportError(error, "知识库加载失败"));
  }, [load]);
  useEffect(() => {
    const timer = window.setInterval(() => load().catch(() => undefined), documents.some(documentProcessing) ? 3000 : 15000);
    const refresh = () => load().catch(() => undefined); window.addEventListener("focus", refresh);
    return () => { window.clearInterval(timer); window.removeEventListener("focus", refresh); };
  }, [documents, load]);
  const visibleDocuments = useMemo(() => documents.filter(item => {
    const inGroup = !selectedGroupId || (selectedGroupId === "ungrouped" ? !item.group_id : item.group_id === selectedGroupId);
    return inGroup && `${item.title} ${item.latest_version?.original_filename || ""}`.toLowerCase().includes(query.toLowerCase());
  }), [documents, query, selectedGroupId]);
  useEffect(() => {
    const observe = () => { acknowledgeVisible(visibleDocuments).catch(() => undefined); };
    observe(); document.addEventListener("visibilitychange", observe);
    return () => document.removeEventListener("visibilitychange", observe);
  }, [visibleDocuments]);
  const loadGroups = async () => { const response = await apiFetch(`${API}/knowledge/groups`, { headers: { Authorization: `Bearer ${getToken()}` } }); setGroups(await response.json()); await load(); };
  async function createGroup(event: FormEvent) {
    event.preventDefault(); const name = newGroupName.trim(); if (!name) return;
    try { const response = await apiFetch(`${API}/knowledge/groups`, { method: "POST", headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" }, body: JSON.stringify({ name }) }); const group = await response.json() as Group; setNewGroupName(""); setSelectedGroupId(group.id); await loadGroups(); }
    catch (error) { reportError(error, "创建分组失败"); }
  }
  async function renameGroup(group: Group) {
    const name = window.prompt("新的分组名称", group.name)?.trim(); if (!name || name === group.name) return;
    try { await apiFetch(`${API}/knowledge/groups/${group.id}`, { method: "PATCH", headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" }, body: JSON.stringify({ name, description: group.description }) }); await loadGroups(); } catch (error) { reportError(error, "重命名分组失败"); }
  }
  async function deleteGroup(group: Group) {
    if (!window.confirm(`删除分组“${group.name}”？分组内文档将变为未分组。`)) return;
    try { await apiFetch(`${API}/knowledge/groups/${group.id}`, { method: "DELETE", headers: { Authorization: `Bearer ${token}` } }); setSelectedGroupId(""); await loadGroups(); } catch (error) { reportError(error, "删除分组失败"); }
  }
  if (!token) return <><Navbar /><main className="workspace"><h1 className="page-title">请先登录</h1><p className="sub">登录后才能管理私人知识库。</p></main></>;
  const selectedGroup = groups.find(group => group.id === selectedGroupId);
  const counts = { ready: documents.filter(item => !item.deleted_at && item.active_version).length, processing: documents.filter(item => item.deleted_at ? item.cleanup_status !== "failed" : (["pending", "running"].includes(item.cleanup_status || "") || ["queued", "running"].includes(item.operation?.status || ""))).length, waiting: documents.filter(item => item.operation?.status === "waiting_embedding" && !item.deleted_at).length, failed: documents.filter(item => item.deleted_at ? item.cleanup_status === "failed" : (item.cleanup_status === "failed" || item.operation?.status === "failed")).length };
  return <><Navbar /><main className="workspace knowledge-page">
    <div className="knowledge-hero"><div><h1 className="page-title">知识库</h1><p className="sub">管理学习资料，查看从原文件保存到索引完成的每一步。</p>{policy && <p className="muted">{policy.format_description} · 单文件最多 {Math.round(policy.max_size_bytes / 1024 / 1024)} MB</p>}</div></div>
    {documents.length > 0 && <div className="knowledge-counts" aria-label="知识库文档状态"><span>可检索 <b>{counts.ready}</b></span><span>处理中 <b>{counts.processing}</b></span><span>等待配置 <b>{counts.waiting}</b></span><span>失败 <b>{counts.failed}</b></span></div>}
    {policy && <KnowledgeUpload groups={groups} defaultGroup={selectedGroupId} policy={policy} onStored={() => load().catch(() => undefined)} />}
    <section className="knowledge-groups panel" aria-label="知识库分组"><div className="knowledge-group-header"><strong>资料分组</strong><form onSubmit={createGroup}><input aria-label="新分组名称" placeholder="新分组名称" value={newGroupName} maxLength={100} onChange={event => setNewGroupName(event.target.value)} /><button className="icon-button" disabled={!newGroupName.trim()}>＋ 创建</button></form></div><div className="knowledge-group-list"><button className={selectedGroupId === "" ? "selected" : ""} onClick={() => setSelectedGroupId("")}>全部资料</button><button className={selectedGroupId === "ungrouped" ? "selected" : ""} onClick={() => setSelectedGroupId("ungrouped")}>未分组</button>{groups.map(group => <button key={group.id} className={selectedGroupId === group.id ? "selected" : ""} onClick={() => setSelectedGroupId(group.id)}>{group.name}</button>)}</div>{selectedGroup && <div className="knowledge-group-actions"><span>正在浏览“{selectedGroup.name}”</span><button className="icon-button" onClick={() => renameGroup(selectedGroup)}>重命名</button><button className="icon-button" onClick={() => deleteGroup(selectedGroup)}>删除分组</button></div>}</section>
    <section className="knowledge-list" style={{ marginTop: 28 }}><div className="knowledge-toolbar"><input value={query} onChange={event => setQuery(event.target.value)} placeholder="搜索文档、笔记或代码" /></div>{!visibleDocuments.length && <div className="panel empty-knowledge"><strong>{query ? "没有匹配文档" : "还没有资料"}</strong><p>{query ? "换个关键词试试。" : "点击上传文档，选择要加入知识库的资料。"}</p></div>}{visibleDocuments.map(doc => <article className="document-row panel" key={doc.id}>
      <div className="document-glyph">{doc.latest_version?.extension.slice(1).toUpperCase() || "DOC"}</div><div className="document-main">{doc.deleted_at ? <strong>{doc.title}</strong> : <Link href={`/knowledge/${doc.id}`}><strong>{doc.title}</strong></Link>}<div className="muted">{groups.find(group => group.id === doc.group_id)?.name || "未分组"} · {doc.latest_version?.original_filename} · {Math.ceil((doc.latest_version?.size_bytes || 0) / 1024)} KB</div><KnowledgeProgress document={doc} /></div>
      {!doc.deleted_at && <div className="document-row-actions"><Link className="icon-button" href={`/knowledge/${doc.id}`}>查看 →</Link><DocumentActions documentId={doc.id} status={doc.operation?.status === "failed" ? "failed" : doc.active_version ? "indexed" : "queued"} token={token} processing={documentProcessing(doc)} extension={doc.latest_version?.extension} supportedExtensions={policy?.extensions ?? []} onChanged={() => load().catch(() => undefined)} /></div>}
    </article>)}</section>
  </main></>;
}
