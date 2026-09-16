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
};

export function citationViewModel(item: Citation) {
  return {
    title: item.document_title || "知识库文档",
    metadata: `${item.group_name || "未分组"}${item.file_name ? ` · ${item.file_name}` : ""}${item.locator?.page ? ` · 第 ${item.locator.page} 页` : ""}`,
    score: Math.round(item.score * 100),
    state: item.explicitly_cited ? "已引用" : "检索到的参考资料",
    quote: item.quote,
  };
}

export default function CitationPanel({ citations, loading = false }: { citations: Citation[]; loading?: boolean }) {
  return <aside className="context"><h3>回答依据</h3>{loading && <div className="source empty">正在加载回答依据…</div>}{!loading && citations.length === 0 && <div className="source empty">选择知识库范围后，回答依据会显示在这里。</div>}{!loading && citations.map((item) => <div className="source" key={item.chunk_id}><b>{item.document_title || "知识库文档"}</b><small>{item.group_name || "未分组"}{item.file_name ? ` · ${item.file_name}` : ""}{item.locator?.page ? ` · 第 ${item.locator.page} 页` : ""} · 相关度 {Math.round(item.score * 100)}%</small><p>{item.quote}</p><span className={`citation-state ${item.explicitly_cited ? "used" : ""}`}>{item.explicitly_cited ? "已引用" : "检索到的参考资料"}</span></div>)}</aside>;
}
