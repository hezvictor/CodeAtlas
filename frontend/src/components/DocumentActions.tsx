"use client";

import { useState } from "react";
import { API, apiFetch } from "../lib/auth";

export function retryRequest(documentId: string) { return { url: `${API}/knowledge/documents/${documentId}/retry`, init: { method: "POST" as const } }; }
export function reindexRequest(documentId: string) { return { url: `${API}/knowledge/documents/${documentId}/reindex`, init: { method: "POST" as const } }; }
export function deleteRequest(documentId: string) { return { url: `${API}/knowledge/documents/${documentId}`, init: { method: "DELETE" as const } }; }
export function uploadVersionRequest(documentId: string) { return { url: `${API}/knowledge/documents/${documentId}/versions`, init: { method: "POST" as const } }; }
export function downloadRequest(documentId: string) { return { url: `${API}/knowledge/documents/${documentId}/download`, init: { method: "GET" as const } }; }

export default function DocumentActions({ documentId, status, token, onChanged, onDeleted }: { documentId: string; status: string; token: string; onChanged: () => void; onDeleted?: () => void }) {
  const [busy, setBusy] = useState(false);
  async function action(url: string, method: string) { setBusy(true); try { const response = await apiFetch(url, { method, headers: { Authorization: `Bearer ${token}` } }); if (!response.ok) throw Error("操作失败"); onChanged(); } finally { setBusy(false); } }
  return <div className="document-actions">
    {(status === "failed" || status === "uploaded") && <button className="icon-button" disabled={busy} onClick={() => action(retryRequest(documentId).url, "POST")}>重试</button>}
    {status === "indexed" && <button className="icon-button" disabled={busy} onClick={() => action(reindexRequest(documentId).url, "POST")}>重新索引</button>}
    <button className="icon-button" disabled={busy} onClick={async () => { if (!window.confirm("确定删除此文档？")) return; await action(deleteRequest(documentId).url, "DELETE"); onDeleted?.(); }}>删除</button>
  </div>;
}
