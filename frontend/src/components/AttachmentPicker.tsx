"use client";

import { useEffect, useState } from "react";
import { API, apiFetch } from "../lib/auth";

export type Attachment = { id: string; document_version_id: string; created_at: string };
type Props = { conversationId: string; token: string; onChange: (ids: string[]) => void; disabled?: boolean };

export function attachmentListRequest(conversationId: string) {
  return { url: `${API}/conversations/${conversationId}/attachments`, init: {} };
}
export function attachRequest(conversationId: string, versionId: string) {
  return { url: `${API}/conversations/${conversationId}/attachments/${versionId}`, init: { method: "POST" as const } };
}
export function detachRequest(conversationId: string, attachmentId: string) {
  return { url: `${API}/conversations/${conversationId}/attachments/${attachmentId}`, init: { method: "DELETE" as const } };
}

export default function AttachmentPicker({ conversationId, token, onChange, disabled = false }: Props) {
  const [items, setItems] = useState<Attachment[]>([]);
  const [versions, setVersions] = useState<{ id: string; name: string }[]>([]);
  const refresh = async () => {
    const response = await apiFetch(`${API}/conversations/${conversationId}/attachments`, { headers: { Authorization: `Bearer ${token}` } });
    const data = await response.json();
    if (Array.isArray(data)) { setItems(data); onChange(data.map((item: Attachment) => item.id)); }
  };
  useEffect(() => { setItems([]); setVersions([]); refresh().catch(() => undefined); }, [conversationId, token]);
  async function loadVersions() {
    const response = await apiFetch(`${API}/knowledge/documents`, { headers: { Authorization: `Bearer ${token}` } });
    const documents = await response.json();
    const next = Array.isArray(documents) ? documents.flatMap((document: { title: string; latest_version?: { id: string; status: string; original_filename: string } | null }) => document.latest_version?.status === "indexed" ? [{ id: document.latest_version.id, name: document.title || document.latest_version.original_filename }] : []) : [];
    setVersions(next);
  }
  async function attach(versionId: string) { await apiFetch(attachRequest(conversationId, versionId).url, { method: "POST", headers: { Authorization: `Bearer ${token}` } }); await refresh(); }
  async function detach(id: string) { await apiFetch(detachRequest(conversationId, id).url, { method: "DELETE", headers: { Authorization: `Bearer ${token}` } }); await refresh(); }
  return <div className="attachment-picker">
    <button type="button" className="icon-button" disabled={disabled} onClick={() => loadVersions().catch(() => undefined)}>附件 ({items.length})</button>
    {versions.length > 0 && <div className="attachment-menu">{versions.map((version) => <button type="button" key={version.id} onClick={() => attach(version.id).catch(() => undefined)}>{version.name}</button>)}</div>}
    {items.map((item) => <button type="button" className="attachment-chip" key={item.id} disabled={disabled} onClick={() => detach(item.id).catch(() => undefined)}>已挂载 · {item.document_version_id.slice(0, 8)} ×</button>)}
  </div>;
}
