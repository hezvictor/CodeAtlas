"use client";

import { ChangeEvent, use, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import Navbar from "../../../components/Navbar";
import { API, getToken } from "../../../lib/auth";
import { apiFetch } from "../../../lib/errors";
import DocumentActions, { downloadRequest, uploadVersionRequest } from "../../../components/DocumentActions";
import DocumentPreview from "../../../components/DocumentPreview";

type Version = { id: string; original_filename: string; status: string; version_no: number; size_bytes?: number; error_message?: string | null };
type Preview = { document: { id: string; title: string; group_id: string }; version: Version; text: string };

export default function DocumentPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [preview, setPreview] = useState<Preview | null>(null); const [versions, setVersions] = useState<Version[]>([]); const [error, setError] = useState(""); const [token, setToken] = useState(""); const [uploading, setUploading] = useState(false);
  const load = useCallback(async (access = getToken()) => { if (!access) { setError("请先登录"); return; } setToken(access); const headers = { Authorization: `Bearer ${access}` }; const [previewResponse, versionsResponse] = await Promise.all([apiFetch(`${API}/knowledge/documents/${id}/preview`, { headers }), apiFetch(`${API}/knowledge/documents/${id}/versions`, { headers })]); setPreview(await previewResponse.json()); const data = await versionsResponse.json(); setVersions(Array.isArray(data) ? data : []); }, [id]);
  async function uploadVersion(event: ChangeEvent<HTMLInputElement>) { const file = event.target.files?.[0]; event.target.value = ""; if (!file || !token) return; setUploading(true); try { const body = new FormData(); body.append("file", file); await apiFetch(uploadVersionRequest(id).url, { ...uploadVersionRequest(id).init, headers: { Authorization: `Bearer ${token}` }, body }); await load(token); } catch (reason) { setError(reason instanceof Error ? reason.message : "版本上传失败"); } finally { setUploading(false); } }
  async function download() { if (!token) return; try { const response = await apiFetch(downloadRequest(id).url, { headers: { Authorization: `Bearer ${token}` } }); const data = await response.json() as { url?: string }; if (!data.url) throw new Error("下载地址不可用"); window.open(data.url, "_blank", "noopener,noreferrer"); } catch (reason) { setError(reason instanceof Error ? reason.message : "下载失败"); } }
  useEffect(() => { load().catch((reason) => setError(reason instanceof Error ? reason.message : "文档加载失败")); }, [load]);
  return <><Navbar /><main className="workspace document-page"><Link href="/knowledge" className="back-link">← 返回知识库</Link>{error && <div className="panel empty-knowledge"><strong>{error}</strong></div>}{preview && <><div className="eyebrow">DOCUMENT / VERSION {preview.version.version_no}</div><h1 className="page-title">{preview.document.title}</h1><p className="sub">{preview.version.original_filename} · {preview.version.status}</p><div className="document-toolbar"><DocumentActions documentId={id} status={preview.version.status} token={token} onChanged={() => load().catch(() => undefined)} onDeleted={() => window.location.assign("/knowledge")} /><button className="icon-button" type="button" onClick={download}>下载当前版本</button><label className={`icon-button ${uploading ? "disabled" : ""}`}><input type="file" accept=".md,.markdown,.pdf,.docx,.txt,.c,.cc,.cpp,.h,.hpp,.java,.py,.html,.htm" onChange={uploadVersion} disabled={uploading} />{uploading ? "上传中…" : "上传新版本"}</label></div><div className="version-list">{versions.map((version) => <span className={version.id === preview.version.id ? "active" : ""} key={version.id}>v{version.version_no} · {version.status}{version.error_message ? ` · ${version.error_message}` : ""}</span>)}</div><article className="document-preview panel"><DocumentPreview filename={preview.version.original_filename} text={preview.text} /></article></>}</main></>;
}
