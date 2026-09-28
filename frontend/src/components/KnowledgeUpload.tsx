"use client";

import Link from "next/link";
import { ChangeEvent, useEffect, useRef, useState } from "react";
import { API, getToken } from "../lib/auth";
import { apiFetch } from "../lib/errors";
import { canLeaveBatch, Group, knowledgeChanged, UploadPolicy, uploadWithProgress } from "../lib/knowledge";

type Conflict = { document_id: string; title: string; filename: string; same_content: boolean };
type Entry = { id: string; file: File; state: string; percent: number; error?: string; conflicts?: Conflict[]; action?: string; target?: string; documentId?: string; savedName?: string };
type Props = { groups: Group[]; defaultGroup?: string; policy: UploadPolicy; onStored: () => void; versionDocumentId?: string };

export default function KnowledgeUpload({ groups, defaultGroup = "", policy, onStored, versionDocumentId }: Props) {
  const [open, setOpen] = useState(false);
  const [groupId, setGroupId] = useState(defaultGroup === "ungrouped" ? "" : defaultGroup);
  const [entries, setEntries] = useState<Entry[]>([]);
  const [busy, setBusy] = useState(false);
  const controllers = useRef(new Set<AbortController>());
  const mounted = useRef(true);
  const running = useRef(false);
  const unsafe = entries.length > 0 && !canLeaveBatch(entries.map(entry => entry.state));
  const patch = (id: string, data: Partial<Entry>) => { if (mounted.current) setEntries(current => current.map(entry => entry.id === id ? { ...entry, ...data } : entry)); };
  useEffect(() => {
    mounted.current = true;
    const active = controllers.current;
    return () => { mounted.current = false; active.forEach(controller => controller.abort()); };
  }, []);
  useEffect(() => {
    if (!unsafe) return;
    const beforeUnload = (event: BeforeUnloadEvent) => { event.preventDefault(); event.returnValue = ""; };
    const navigation = (event: MouseEvent) => {
      const link = (event.target as Element).closest?.("a[href]") as HTMLAnchorElement | null;
      if (!link || link.target === "_blank" || link.href === window.location.href || event.ctrlKey || event.metaKey) return;
      if (!window.confirm("仍有文件未保存。离开会中断未完成的上传；已保存的文件会继续后台处理。确定离开？")) { event.preventDefault(); event.stopPropagation(); }
      else controllers.current.forEach(controller => controller.abort());
    };
    window.addEventListener("beforeunload", beforeUnload);
    document.addEventListener("click", navigation, true);
    return () => { window.removeEventListener("beforeunload", beforeUnload); document.removeEventListener("click", navigation, true); };
  }, [unsafe]);

  function chooseFiles(event: ChangeEvent<HTMLInputElement>) {
    const files = Array.from(event.target.files || []); event.target.value = "";
    setEntries(current => [...current, ...files.map(file => {
      const extension = `.${file.name.split(".").pop()?.toLowerCase()}`;
      const error = !policy.extensions.includes(extension) ? "文件类型不受支持，请选择界面列出的类型" : file.size > policy.max_size_bytes ? "文件超出大小限制" : undefined;
      return { id: crypto.randomUUID(), file, state: error ? "failed" : "ready", percent: 0, error };
    })]);
  }
  async function start() {
    if (running.current) return;
    running.current = true; setBusy(true);
    try {
      for (const entry of entries) {
        if (!mounted.current) break;
        if (["stored", "skipped"].includes(entry.state) || (entry.state === "conflict" && !entry.action)) continue;
        const controller = new AbortController(); controllers.current.add(controller);
        try {
          const extension = `.${entry.file.name.split(".").pop()?.toLowerCase()}`;
          if (!policy.extensions.includes(extension) || entry.file.size > policy.max_size_bytes) throw new Error("请重新选择符合格式和大小限制的文件，或跳过此文件");
          patch(entry.id, { state: "checking", error: undefined, percent: 0 });
          if (!versionDocumentId) {
            const hash = await crypto.subtle.digest("SHA-256", await entry.file.arrayBuffer());
            const sha256 = Array.from(new Uint8Array(hash)).map(value => value.toString(16).padStart(2, "0")).join("");
            const response = await apiFetch(`${API}/knowledge/documents/preflight`, { method: "POST", signal: controller.signal, headers: { Authorization: `Bearer ${getToken()}`, "Content-Type": "application/json" }, body: JSON.stringify({ filename: entry.file.name, sha256, group_id: groupId || null }) });
            const { conflicts } = await response.json() as { conflicts: Conflict[] };
            if (conflicts.length && !entry.action) {
              const same = conflicts.find(conflict => conflict.same_content);
              patch(entry.id, { state: "conflict", conflicts, action: same ? "skip" : undefined, target: (same || conflicts[0]).document_id });
              continue;
            }
            if (entry.action === "skip") { patch(entry.id, { state: "skipped", documentId: entry.target }); continue; }
          }
          if (controller.signal.aborted || !mounted.current) break;
          const body = new FormData(); body.append("file", entry.file); body.append("upload_token", entry.id);
          if (groupId && !versionDocumentId) body.append("group_id", groupId);
          if (entry.action) body.append("conflict_action", entry.action);
          if (entry.target) body.append("target_document_id", entry.target);
          patch(entry.id, { state: "uploading" });
          const result = await uploadWithProgress(versionDocumentId ? `${API}/knowledge/documents/${versionDocumentId}/versions` : `${API}/knowledge/documents`, body, controller.signal, percent => patch(entry.id, { percent, state: percent === 100 ? "saving" : "uploading" }));
          patch(entry.id, { state: "stored", percent: 100, documentId: versionDocumentId || result.id, savedName: result.latest_version?.original_filename });
          knowledgeChanged(); onStored();
        } catch (error) { patch(entry.id, { state: "failed", error: error instanceof Error ? error.message : "上传失败，请重试" }); }
        finally { controllers.current.delete(controller); }
      }
    } finally { running.current = false; if (mounted.current) setBusy(false); }
  }
  const labels: Record<string, string> = { ready: "等待上传", checking: "检查文件和同名冲突", conflict: "等待选择", uploading: "传输中", saving: "传输完成，等待服务器保存确认", stored: "原文件已保存，后台处理已安排", skipped: "已跳过", failed: "未确认保存" };
  return <>
    <button className="pill fill upload-cta" onClick={() => { if (!entries.length) setGroupId(defaultGroup === "ungrouped" ? "" : defaultGroup); setOpen(true); }}>{versionDocumentId ? "上传新版本" : "＋ 上传文档"}</button>
    {open && <section className="panel knowledge-upload" aria-label="上传文档">
      <div className="knowledge-upload-heading"><h2>{versionDocumentId ? "上传新版本" : "批量上传文档"}</h2><button className="icon-button" disabled={busy} onClick={() => setOpen(false)}>收起</button></div>
      {versionDocumentId ? <p className="upload-warning">新版本索引成功后才切换；旧版本原文件和索引会被删除，无法恢复。失败时当前版本仍可用。</p> : <label className="upload-destination">上传到分组 <select value={groupId} disabled={entries.length > 0} onChange={event => setGroupId(event.target.value)}><option value="">未分组</option>{groups.map(group => <option key={group.id} value={group.id}>{group.name}</option>)}</select><small>上传目标与列表筛选互相独立</small></label>}
      <p className="muted">{policy.format_description} · 单文件最多 {Math.round(policy.max_size_bytes / 1024 / 1024)} MB</p>
      <label className="icon-button upload-select"><input type="file" multiple={!versionDocumentId} accept={policy.extensions.join(",")} onChange={chooseFiles} disabled={busy || Boolean(versionDocumentId && entries.length)} />选择{versionDocumentId ? "文件" : "多个文件"}</label>
      <div className="upload-entries">{entries.map(entry => <div key={entry.id} className="upload-entry">
        <strong>{entry.savedName || entry.file.name}</strong><small>{labels[entry.state]}{entry.state === "uploading" ? ` ${entry.percent}%` : ""}</small>
        {["uploading", "saving", "stored"].includes(entry.state) && <progress aria-label={`${entry.file.name} 上传进度`} max={100} value={entry.percent} />}
        {entry.error && <p className="upload-error">{entry.error} · 已保存的文件继续处理，未保存的文件可在本页面重试；离开后需重新选择。</p>}
        {entry.state === "conflict" && <div className="upload-conflict">
          <p>{entry.conflicts?.some(item => item.same_content) ? "此分组已有内容相同的同名文件，默认跳过。也可以创建独立文档。" : "此分组已有同名文件，请选择处理方式。"}</p>
          <select aria-label={`${entry.file.name} 对应文档`} value={entry.target || ""} onChange={event => patch(entry.id, { target: event.target.value, action: entry.action === "skip" && !entry.conflicts?.find(item => item.document_id === event.target.value)?.same_content ? undefined : entry.action })}>{entry.conflicts?.map(item => <option key={item.document_id} value={item.document_id}>{item.title}{item.same_content ? "（内容相同）" : ""}</option>)}</select>
          <select aria-label={`${entry.file.name} 冲突处理方式`} value={entry.action || ""} onChange={event => patch(entry.id, { action: event.target.value })}>
            <option value="">选择处理方式</option>{entry.conflicts?.some(item => item.same_content) && <option value="skip">跳过，使用已有文档</option>}<option value="new_version">作为该文档的新版本</option><option value="independent">创建独立文档（名称增加时间戳）</option>
          </select>
          {entry.action === "new_version" && <p className="upload-warning">切换成功后旧版本文件和索引会被删除，无法恢复。</p>}
        </div>}
        {entry.documentId && <Link href={`/knowledge/${entry.documentId}`}>查看文档 →</Link>}
        {!busy && !["stored", "skipped"].includes(entry.state) && <button className="icon-button" onClick={() => patch(entry.id, { state: "skipped" })}>跳过此文件</button>}
      </div>)}</div>
      {entries.length > 0 && <p role="status" className={unsafe ? "upload-warning" : "upload-safe"}>{unsafe ? "仍有文件未保存，离开会中断这些文件。已保存的文件会继续后台处理。" : "全部文件已保存或跳过，可以安全离开。索引是否完成请查看文档状态。"}</p>}
      <div className="document-toolbar"><button className="pill fill" disabled={busy || !entries.some(entry => !["stored", "skipped"].includes(entry.state))} onClick={start}>{busy ? "上传中…" : "开始 / 继续上传"}</button>{!busy && entries.length > 0 && <button className="icon-button" onClick={() => { if (unsafe && !window.confirm("清空未保存的文件选择？已保存的文件会继续处理。")) return; setEntries([]); }}>清空本批次</button>}</div>
    </section>}
    {!open && unsafe && <button className="upload-warning icon-button" onClick={() => setOpen(true)}>本批次还有文件未保存 · 查看上传</button>}
  </>;
}
