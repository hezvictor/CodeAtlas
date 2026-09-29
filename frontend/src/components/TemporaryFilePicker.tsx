"use client";
import { useRef, useState } from "react";
import { apiFetch, reportError } from "../lib/errors";
import type { SessionFile } from "./CitationPanel";

const API = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api/v1";
export default function TemporaryFilePicker({ conversationId, ensureConversation, token, items, onItems, disabled = false }: { conversationId: string; ensureConversation: () => Promise<string>; token: string; items: SessionFile[]; onItems: (items: SessionFile[]) => void; disabled?: boolean }) {
  const input = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  async function refresh(id: string) {
    const response = await apiFetch(`${API}/conversations/${id}/temporary-files`, { headers: { Authorization: `Bearer ${token}` } });
    onItems(await response.json());
  }
  async function upload(file?: File) {
    if (!file) return;
    setBusy(true);
    try {
      const id = conversationId || await ensureConversation();
      await apiFetch(`${API}/conversations/${id}/temporary-files`, { method: "POST", headers: { Authorization: `Bearer ${token}`, "X-File-Name": encodeURIComponent(file.name), "Content-Type": "application/octet-stream" }, body: file });
      await refresh(id);
    } catch (error) { reportError(error, "临时文件上传失败"); }
    finally { setBusy(false); if (input.current) input.current.value = ""; }
  }
  async function detach(id: string) {
    setBusy(true);
    try {
      await apiFetch(`${API}/conversations/${conversationId}/temporary-files/${id}`, { method: "DELETE", headers: { Authorization: `Bearer ${token}` } });
      await refresh(conversationId);
    } catch (error) { reportError(error, "移除临时文件失败"); }
    finally { setBusy(false); }
  }
  return <div className="temporary-picker"><input hidden ref={input} type="file" accept=".md,.markdown,.docx,.txt,.c,.cc,.cpp,.h,.hpp,.java,.py,.html,.htm" onChange={event => upload(event.target.files?.[0])} /><button type="button" disabled={disabled || busy} onClick={() => input.current?.click()}>{busy ? "解析全文…" : "＋ 临时文件"}</button>{items.length ? <details><summary>{items.length} 个会话文件</summary>{items.map(item => <div key={item.id}>{item.original_filename}<button type="button" disabled={disabled || busy} aria-label={`移除${item.original_filename}`} onClick={() => detach(item.id)}>×</button></div>)}</details> : null}</div>;
}
