import { API, getToken, apiFetch as authenticatedFetch } from "./auth";
import { apiFetch } from "./errors";

export type Version = { id: string; original_filename: string; extension: string; version_no: number; size_bytes: number; status: string; error_message?: string | null; storage_deleted_at?: string | null; content_deleted_at?: string | null; cleanup_pending?: boolean; created_at?: string };
export type DocumentJob = { id: string; status: string; stage: string; total_chunks: number; completed_chunks: number; available_at: string; error_message?: string | null; acknowledged_at?: string | null };
export type KnowledgeDocument = { id: string; title: string; group_id: string | null; latest_version: Version | null; active_version: Version | null; operation: DocumentJob | null; deleted_at?: string | null; cleanup_status?: string | null; cleanup_error?: string | null };
export type Group = { id: string; name: string; description: string | null };
export type UploadPolicy = { extensions: string[]; max_size_bytes: number; format_description: string };
export type DocumentDetails = { preview: { document: KnowledgeDocument; version: Version; text: string }; versions: Version[] };
export async function loadDocumentDetails(id: string): Promise<DocumentDetails | null> {
  const headers = { Authorization: `Bearer ${getToken()}` };
  const responses = await Promise.all([
    authenticatedFetch(`${API}/knowledge/documents/${id}/preview`, { headers }),
    authenticatedFetch(`${API}/knowledge/documents/${id}/versions`, { headers }),
  ]);
  // Deletion can complete while a detail refresh is in flight.
  if (responses.some(response => response.status === 404)) return null;
  for (const response of responses) {
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      throw new Error(typeof body.detail === "string" ? body.detail : "文档加载失败，请重试");
    }
  }
  return { preview: await responses[0].json(), versions: await responses[1].json() };
}
export const KNOWLEDGE_CHANGED = "codeatlas:knowledge-changed";
export function knowledgeChanged() { window.dispatchEvent(new Event(KNOWLEDGE_CHANGED)); }
export function canLeaveBatch(states: string[]) { return states.every(state => state === "stored" || state === "skipped"); }
export function documentProcessing(doc: KnowledgeDocument) { return Boolean(doc.deleted_at || ["pending", "running", "failed"].includes(doc.cleanup_status || "") || (doc.operation && ["queued", "running", "waiting_embedding"].includes(doc.operation.status))); }
export function documentProgress(doc: KnowledgeDocument): { label: string; detail: string; percent?: number; failed?: boolean } {
  if (doc.deleted_at) return { label: doc.cleanup_status === "failed" ? "清理失败，将自动重试" : "删除中", detail: doc.cleanup_error || "已停止参与检索，正在清理原文件和索引", failed: doc.cleanup_status === "failed" };
  const job = doc.operation;
  const availability = doc.active_version ? "当前版本仍可检索。" : "目前不可检索。";
  if (!job) return { label: doc.active_version ? "可检索" : "原文件已保存", detail: doc.active_version ? "索引已完成" : availability, percent: doc.active_version ? 100 : undefined };
  if (job.status === "completed") {
    if (doc.active_version) return { label: "可检索", detail: "索引已完成", percent: 100 };
    return { label: doc.latest_version?.status === "failed" ? "处理失败" : "索引未启用", detail: doc.latest_version?.error_message || "暂不可检索，请检查文档处理状态", failed: doc.latest_version?.status === "failed" };
  }
  if (job.status === "failed") return { label: "处理失败", detail: `${job.error_message || "处理未完成，请重试"} ${availability}`, failed: true };
  if (job.status === "waiting_embedding") return { label: "等待配置", detail: `原文件已保存，等待配置并验证 Embedding。${availability}` };
  if (job.status === "queued") return { label: job.error_message ? "等待自动重试" : "等待处理", detail: job.error_message ? `${job.error_message} 下次重试：${new Date(job.available_at).toLocaleString("zh-CN")}。${availability}` : `原文件已保存，可离开页面，后台继续处理。${availability}` };
  const labels: Record<string, string> = { parsing: "解析文档", chunking: "划分文本块", embedding: "向量化", committing: "提交索引" };
  if (job.stage === "embedding" && job.total_chunks > 0) return { label: `向量化 ${job.completed_chunks} / ${job.total_chunks}`, detail: availability, percent: Math.min(95, 35 + 60 * job.completed_chunks / job.total_chunks) };
  return { label: labels[job.stage] || "处理中", detail: `原文件已保存，后台继续处理。${availability}`, percent: job.stage === "committing" ? 98 : undefined };
}
export async function acknowledgeVisible(documents: KnowledgeDocument[]) {
  const job_ids = documents.filter(doc => !doc.deleted_at && doc.operation?.status === "completed" && !doc.operation.acknowledged_at).map(doc => doc.operation!.id);
  if (!job_ids.length || document.visibilityState !== "visible") return;
  await apiFetch(`${API}/knowledge/documents/acknowledge`, { method: "POST", headers: { Authorization: `Bearer ${getToken()}`, "Content-Type": "application/json" }, body: JSON.stringify({ job_ids }) });
  knowledgeChanged();
}

export function uploadWithProgress(url: string, body: FormData, signal: AbortSignal, progress: (value: number) => void): Promise<KnowledgeDocument> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    const abort = () => xhr.abort();
    xhr.open("POST", url);
    xhr.setRequestHeader("Authorization", `Bearer ${getToken()}`);
    xhr.upload.onprogress = event => { if (event.lengthComputable) progress(Math.round(event.loaded / event.total * 100)); };
    xhr.onload = () => {
      signal.removeEventListener("abort", abort);
      let data;
      try { data = JSON.parse(xhr.responseText); } catch { reject(new Error("服务器响应无效，请重试")); return; }
      if (xhr.status >= 200 && xhr.status < 300) resolve(data);
      else reject(new Error(typeof data.detail === "string" ? data.detail : data.detail?.message || data.message || (xhr.status === 401 ? "登录已失效，请重新登录后重试" : "上传失败，请重试")));
    };
    xhr.onerror = () => { signal.removeEventListener("abort", abort); reject(new Error("文件传输失败，请检查网络后重试")); };
    xhr.onabort = () => { signal.removeEventListener("abort", abort); reject(new Error("未保存的文件传输已中断")); };
    signal.addEventListener("abort", abort, { once: true });
    if (signal.aborted) { reject(new Error("文件传输已中断")); return; }
    xhr.send(body);
  });
}
