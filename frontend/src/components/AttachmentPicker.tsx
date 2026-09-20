"use client";

import { ChangeEvent, useEffect, useState } from "react";
import { API, apiFetch } from "../lib/auth";

export type Attachment = { id: string; document_version_id: string; document_id?: string; title?: string | null; original_filename?: string | null; extension?: string | null; status?: string | null; scope?: string | null; created_at: string };
type Props = { conversationId: string; token: string; onChange: (ids: string[]) => void; onItems?: (items: Attachment[]) => void; disabled?: boolean };

export function attachmentListRequest(conversationId: string) { return { url: `${API}/conversations/${conversationId}/attachments`, init: {} }; }
export function attachRequest(conversationId: string, versionId: string) { return { url: `${API}/conversations/${conversationId}/attachments/${versionId}`, init: { method: "POST" as const } }; }
export function detachRequest(conversationId: string, attachmentId: string) { return { url: `${API}/conversations/${conversationId}/attachments/${attachmentId}`, init: { method: "DELETE" as const } }; }
export async function resolveAttachmentConversationId(conversationId: string, ensureConversation?: () => Promise<string>) { return conversationId || await ensureConversation?.() || ""; }

export default function AttachmentPicker({ conversationId, token, onChange, onItems, disabled = false, ensureConversation }: Props & { ensureConversation?: () => Promise<string> }) {
  const [items, setItems] = useState<Attachment[]>([]);
  const [uploading, setUploading] = useState(false);
  const refresh = async () => {
    if (!conversationId) { setItems([]); onChange([]); onItems?.([]); return; }
    const response = await apiFetch(`${API}/conversations/${conversationId}/attachments`, { headers: { Authorization: `Bearer ${token}` } });
    const data = await response.json();
    if (Array.isArray(data)) { setItems(data); onChange(data.map((item: Attachment) => item.id)); onItems?.(data); }
  };
  useEffect(() => { refresh().catch(() => undefined); }, [conversationId, token]);
  async function upload(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]; event.target.value = "";
    if (!file) return;
    setUploading(true);
    try { const targetConversationId = await resolveAttachmentConversationId(conversationId, ensureConversation); if (!targetConversationId) return; const body = new FormData(); body.append("file", file); const response = await apiFetch(`${API}/conversations/${targetConversationId}/attachments/upload`, { method: "POST", headers: { Authorization: `Bearer ${token}` }, body }); const item = await response.json(); setItems((current) => { const next = [...current, item]; onChange(next.map((entry) => entry.id)); onItems?.(next); return next; }); }
    finally { setUploading(false); }
  }
  async function detach(id: string) {
    if (!window.confirm("删除这个会话临时文件吗？")) return;
    await apiFetch(detachRequest(conversationId, id).url, { method: "DELETE", headers: { Authorization: `Bearer ${token}` } });
    await refresh();
  }
  return <div className="attachment-picker"><label className="icon-button"><input type="file" hidden accept=".md,.markdown,.pdf,.docx,.txt,.c,.cc,.cpp,.h,.hpp,.java,.py,.html,.htm" onChange={upload} disabled={disabled || uploading} />{uploading ? "上传中…" : "＋ 临时文件"}</label>{items.length > 0 && <span className="muted">{items.length} 个会话文件</span>}{items.map((item) => <button type="button" className="attachment-chip" key={item.id} disabled={disabled} onClick={() => detach(item.id).catch(() => undefined)}>{item.original_filename || item.title || "临时文件"} ×</button>)}</div>;
}
