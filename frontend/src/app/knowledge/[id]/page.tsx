"use client";

import { use, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import "../knowledge-overrides.css";
import Navbar from "../../../components/Navbar";
import { API, getToken } from "../../../lib/auth";
import { apiFetch } from "../../../lib/errors";
import DocumentActions, { downloadRequest } from "../../../components/DocumentActions";
import DocumentPreview from "../../../components/DocumentPreview";
import KnowledgeProgress from "../../../components/KnowledgeProgress";
import KnowledgeUpload from "../../../components/KnowledgeUpload";
import { acknowledgeVisible, documentProcessing, loadDocumentDetails, KnowledgeDocument, UploadPolicy, Version } from "../../../lib/knowledge";

type Preview = { document: KnowledgeDocument; version: Version; text: string };
export default function DocumentPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params); const router = useRouter();
  const [preview, setPreview] = useState<Preview | null>(null);
  const [versions, setVersions] = useState<Version[]>([]);
  const [policy, setPolicy] = useState<UploadPolicy | null>(null);
  const [error, setError] = useState(""); const [token, setToken] = useState("");
  const load = useCallback(async () => {
    const access = getToken(); if (!access) { setError("请先登录"); return; } setToken(access);
    const details = await loadDocumentDetails(id);
    if (!details) { router.replace("/knowledge"); return; }
    setPreview(details.preview); setVersions(details.versions); setError("");
  }, [id, router]);
  useEffect(() => { load().catch(reason => setError(reason instanceof Error ? reason.message : "文档加载失败")); apiFetch(`${API}/knowledge/documents/policy`).then(response => response.json()).then(setPolicy).catch(() => undefined); }, [load]);
  useEffect(() => {
    const refresh = () => load().catch(reason => setError(reason instanceof Error ? reason.message : "刷新失败"));
    const timer = window.setInterval(refresh, preview && documentProcessing(preview.document) ? 3000 : 15000); window.addEventListener("focus", refresh);
    return () => { window.clearInterval(timer); window.removeEventListener("focus", refresh); };
  }, [preview, load]);
  useEffect(() => {
    const observe = () => { if (preview) acknowledgeVisible([preview.document]).catch(() => undefined); };
    observe(); document.addEventListener("visibilitychange", observe); return () => document.removeEventListener("visibilitychange", observe);
  }, [preview]);
  async function download() {
    try { const response = await apiFetch(downloadRequest(id).url, { headers: { Authorization: `Bearer ${getToken()}` } }); const data = await response.json() as { url?: string }; if (!data.url) throw new Error("下载地址不可用"); window.open(data.url, "_blank", "noopener,noreferrer"); } catch (reason) { setError(reason instanceof Error ? reason.message : "下载失败"); }
  }
  const doc = preview?.document;
  return <><Navbar /><main className="workspace document-page"><Link href="/knowledge" className="back-link">← 返回知识库</Link>{error && <p role="alert" className="upload-error">{error}</p>}{preview && doc && <>
    <h1 className="page-title">{doc.title}</h1><p className="sub">{doc.latest_version?.original_filename} · 最新 v{doc.latest_version?.version_no}{doc.active_version ? ` · 当前可检索 v${doc.active_version.version_no}` : ""}</p>
    <section className="panel document-pipeline"><KnowledgeProgress document={doc} /></section>
    <div className="document-toolbar"><DocumentActions documentId={id} status={doc.operation?.status === "failed" ? "failed" : doc.active_version ? "indexed" : "queued"} token={token} processing={documentProcessing(doc)} extension={doc.latest_version?.extension} onChanged={() => load().catch(() => undefined)} onDeleted={() => router.push("/knowledge")} /><button className="icon-button" onClick={download}>{doc.active_version ? "下载当前版本" : "下载原文件"}</button></div>
    {policy && !documentProcessing(doc) && <KnowledgeUpload groups={[]} policy={policy} versionDocumentId={id} onStored={() => load().catch(() => undefined)} />}
    <section className="version-history"><h2>简要版本记录</h2>{versions.map(version => <div key={version.id}><strong>v{version.version_no}</strong><span>{version.original_filename}</span><small>{version.id === doc.active_version?.id ? "当前可检索版本" : version.storage_deleted_at ? "内容已清理，无法恢复" : version.cleanup_pending ? "等待清理，无法恢复" : version.id === doc.latest_version?.id ? "最新提交版本" : "未启用版本"}</small></div>)}</section>
    <h2 className="preview-heading">{doc.active_version ? `当前可检索版本 v${preview.version.version_no} 预览` : "文本预览"}</h2><article className="document-preview panel">{preview.text ? <DocumentPreview filename={preview.version.original_filename} text={preview.text} /> : <p className="muted">尚无可预览的文本，请查看上方处理状态。</p>}</article>
  </>}</main></>;
}
