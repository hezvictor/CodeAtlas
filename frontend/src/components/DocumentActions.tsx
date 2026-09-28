"use client";

import { useState } from "react";
import { API } from "../lib/auth";
import { apiFetch, reportError } from "../lib/errors";
import { knowledgeChanged } from "../lib/knowledge";

export function retryRequest(documentId: string) { return { url: `${API}/knowledge/documents/${documentId}/retry`, init: { method: "POST" as const } }; }
export function reindexRequest(documentId: string) { return { url: `${API}/knowledge/documents/${documentId}/reindex`, init: { method: "POST" as const } }; }
export function deleteRequest(documentId: string) { return { url: `${API}/knowledge/documents/${documentId}`, init: { method: "DELETE" as const } }; }
export function uploadVersionRequest(documentId: string) { return { url: `${API}/knowledge/documents/${documentId}/versions`, init: { method: "POST" as const } }; }
export function downloadRequest(documentId: string) { return { url: `${API}/knowledge/documents/${documentId}/download`, init: { method: "GET" as const } }; }

export default function DocumentActions({ documentId, status, token, onChanged, onDeleted, processing = false, extension }: { documentId: string; status: string; token: string; onChanged: () => void; onDeleted?: () => void; processing?: boolean; extension?: string }) {
  const [busy, setBusy] = useState(false);
  async function action(url: string, method: string) { setBusy(true); try { await apiFetch(url, { method, headers: { Authorization: `Bearer ${token}` } }); knowledgeChanged(); if (method === "DELETE" && onDeleted) onDeleted(); else onChanged(); } catch (error) { reportError(error, "操作失败"); } finally { setBusy(false); } }
  return <div className="document-actions">
    {extension !== ".pdf" && status === "failed" && <button className="icon-button" disabled={busy || processing} onClick={() => action(retryRequest(documentId).url, "POST")}>重试</button>}
    {extension !== ".pdf" && status === "indexed" && <button className="icon-button" disabled={busy || processing} onClick={() => action(reindexRequest(documentId).url, "POST")}>重新索引</button>}
    <button className="icon-button" disabled={busy} onClick={async () => { if (!window.confirm("删除此文档及原文件、文本和向量索引？删除后无法恢复，后台任务会停止，历史引用仅保留摘要。")) return; await action(deleteRequest(documentId).url, "DELETE"); }}>删除</button>
  </div>;
}
