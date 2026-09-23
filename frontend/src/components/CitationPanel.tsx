"use client";

export type Citation = {
  chunk_id: string;
  quote: string;
  score: number;
  locator?: Record<string, unknown>;
  document_title?: string | null;
  file_name?: string | null;
  group_name?: string | null;
  explicitly_cited?: boolean;
  source_scope?: string;
};

export type SessionFile = { id: string; original_filename?: string | null; title?: string | null; extension?: string | null; status?: string | null };

export function citationViewModel(item: Citation) {
  return {
    title: item.document_title || "知识库文档",
    metadata: `${item.group_name || "未分组"}${item.file_name ? ` · ${item.file_name}` : ""}${item.locator?.page ? ` · 第 ${item.locator.page} 页` : ""}`,
    score: Math.round(item.score * 100),
    state: item.explicitly_cited ? "已引用" : "检索到的参考资料",
    quote: item.quote,
  };
}

export type RetrievalStatus = "not_requested" | "pending" | "no_hit" | "ok" | "failed";

export default function CitationPanel({ citations, sessionFiles = [], loading = false, retrievalStatus = "not_requested" }: { citations: Citation[]; sessionFiles?: SessionFile[]; loading?: boolean; retrievalStatus?: RetrievalStatus }) {
  const statusText: Record<string, string> = { uploaded: "等待处理", waiting_embedding: "等待 Embedding 配置", parsing: "解析中", chunking: "切块中", embedding: "向量化", indexed: "已就绪", failed: "处理失败" };
  const retrievalLabel: Record<RetrievalStatus, string> = { not_requested: "本次未检索知识库", pending: "正在检索知识库…", no_hit: "未找到相关资料，回答基于当前对话", ok: "已完成知识库检索", failed: "知识库检索失败，本次回答未完成" };
  return <aside className="context"><h3>本会话文件</h3>{sessionFiles.length === 0 && <div className="source empty">尚未上传临时文件。</div>}{sessionFiles.map((item) => <div className="source session-file" key={item.id}><b>{item.original_filename || item.title || "临时文件"}</b><small>{statusText[item.status || "uploaded"] || item.status || "等待处理"}</small></div>)}<h3 style={{ marginTop: 26 }}>本次回答引用</h3>{retrievalStatus !== "not_requested" && <div className={`citation-state ${retrievalStatus === "ok" ? "used" : ""}`}>{retrievalLabel[retrievalStatus]}</div>}{loading && <div className="source empty">正在加载回答依据…</div>}{!loading && citations.length === 0 && <div className="source empty">本次回答未引用已索引资料。</div>}{!loading && citations.map((item) => <div className="source" key={item.chunk_id}><b>{item.document_title || "知识库文档"}</b><small>{item.source_scope === "session" ? "本会话文件" : "长期资料"}{item.file_name ? ` · ${item.file_name}` : ""}{item.locator?.page ? ` · 第 ${item.locator.page} 页` : ""} · 相关度 {Math.round(item.score * 100)}%</small><p>{item.quote}</p><span className={`citation-state ${item.explicitly_cited ? "used" : ""}`}>{item.explicitly_cited ? "已引用" : "检索到的参考资料"}</span></div>)}</aside>;
}
