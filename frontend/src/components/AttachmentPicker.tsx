"use client";

import { ChangeEvent, useCallback, useEffect, useState } from "react";
import { API } from "../lib/auth";
import { apiFetch, reportError } from "../lib/errors";

export type Attachment = { id: string; document_version_id: string; document_id?: string; title?: string | null; original_filename?: string | null; extension?: string | null; status?: string | null; scope?: string | null; created_at: string };
type DocumentOption = { id: string; title: string; latest_version: { id: string; status: string } | null; active_version?: { id: string; status: string } | null; deleted_at?: string | null };
type Props = { conversationId: string; token: string; onChange: (ids: string[]) => void; onItems?: (items: Attachment[]) => void; disabled?: boolean };

export function attachmentListRequest(conversationId: string) { return { url: `${API}/conversations/${conversationId}/attachments`, init: {} }; }
export function attachRequest(conversationId: string, versionId: string) { return { url: `${API}/conversations/${conversationId}/attachments/${versionId}`, init: { method: "POST" as const } }; }
export function detachRequest(conversationId: string, attachmentId: string) { return { url: `${API}/conversations/${conversationId}/attachments/${attachmentId}`, init: { method: "DELETE" as const } }; }
export async function resolveAttachmentConversationId(conversationId: string, ensureConversation?: () => Promise<string>) { return conversationId || await ensureConversation?.() || ""; }
export function indexedDocumentOptions<T extends DocumentOption>(documents: T[]): T[] { return documents.filter(item => !item.deleted_at && (item.active_version === undefined ? item.latest_version : item.active_version)?.status === "indexed"); }

export default function AttachmentPicker({ conversationId, token, onChange, onItems, disabled = false, ensureConversation }: Props & { ensureConversation?: () => Promise<string> }) {
  const [items, setItems] = useState<Attachment[]>([]);
  const [uploading, setUploading] = useState(false);
  const [showDocuments, setShowDocuments] = useState(false);
  const [documents, setDocuments] = useState<DocumentOption[]>([]);
  const [selectedVersionId, setSelectedVersionId] = useState("");
  const refresh = useCallback(async () => {
    if (!conversationId) { setItems([]); onChange([]); onItems?.([]); return; }
    const response = await apiFetch(`${API}/conversations/${conversationId}/attachments`, { headers: { Authorization: `Bearer ${token}` } });
    const data = await response.json();
    if (Array.isArray(data)) { setItems(data); onChange(data.map((item: Attachment) => item.id)); onItems?.(data); }
  }, [conversationId, token, onChange, onItems]);
  useEffect(() => { refresh().catch(() => undefined); }, [refresh]);
  async function upload(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]; event.target.value = "";
    if (!file) return;
    setUploading(true);
    try { const targetConversationId = await resolveAttachmentConversationId(conversationId, ensureConversation); if (!targetConversationId) return; const body = new FormData(); body.append("file", file); const response = await apiFetch(`${API}/conversations/${targetConversationId}/attachments/upload`, { method: "POST", headers: { Authorization: `Bearer ${token}` }, body }); const item = await response.json(); setItems((current) => { const next = [...current, item]; onChange(next.map((entry) => entry.id)); onItems?.(next); return next; }); }
    catch (error) { reportError(error, "临时文件上传失败"); }
    finally { setUploading(false); }
  }
  async function openDocuments() {
    try {
      const response = await apiFetch(`${API}/knowledge/documents`, { headers: { Authorization: `Bearer ${token}` } });
      setDocuments(indexedDocumentOptions(await response.json()));
      setShowDocuments(true);
    } catch (error) { reportError(error, "长期资料加载失败"); }
  }
  async function attachSelected() {
    if (!selectedVersionId) return;
    setUploading(true);
    try {
      const targetConversationId = await resolveAttachmentConversationId(conversationId, ensureConversation);
      if (!targetConversationId) throw new Error("无法创建会话");
      const request = attachRequest(targetConversationId, selectedVersionId);
      await apiFetch(request.url, { ...request.init, headers: { Authorization: `Bearer ${token}` } });
      setShowDocuments(false); setSelectedVersionId("");
      const response = await apiFetch(attachmentListRequest(targetConversationId).url, { headers: { Authorization: `Bearer ${token}` } });
      const data = await response.json() as Attachment[];
      setItems(data); onChange(data.map(item => item.id)); onItems?.(data);
    } catch (error) { reportError(error, "关联长期资料失败"); }
    finally { setUploading(false); }
  }
  async function detach(id: string) {
    if (!window.confirm("删除这个会话临时文件吗？")) return;
    await apiFetch(detachRequest(conversationId, id).url, { method: "DELETE", headers: { Authorization: `Bearer ${token}` } });
    await refresh();
  }
  return <div className="attachment-picker"><label className="icon-button"><input type="file" hidden accept=".md,.markdown,.docx,.txt,.c,.cc,.cpp,.h,.hpp,.java,.py,.html,.htm" onChange={upload} disabled={disabled || uploading} />{uploading ? "上传中…" : "＋ 临时文件"}</label><button type="button" className="icon-button" disabled={disabled || uploading} onClick={openDocuments}>＋ 长期资料</button>{showDocuments && <div className="attachment-document-select"><select aria-label="选择长期资料" value={selectedVersionId} onChange={event => setSelectedVersionId(event.target.value)}><option value="">选择已索引文档</option>{documents.map(item => <option key={item.id} value={item.active_version?.id || item.latest_version?.id}>{item.title}</option>)}</select><button type="button" disabled={!selectedVersionId || uploading} onClick={attachSelected}>关联</button><button type="button" onClick={() => setShowDocuments(false)}>取消</button></div>}{items.length > 0 && <span className="muted">{items.length} 个会话文件</span>}{items.map(item => <button type="button" className="attachment-chip" key={item.id} disabled={disabled} onClick={() => detach(item.id).catch(error => reportError(error, "移除附件失败"))}>{item.original_filename || item.title || "会话文件"} ×</button>)}</div>;
}
