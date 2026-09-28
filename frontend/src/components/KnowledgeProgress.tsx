import { documentProgress, KnowledgeDocument } from "../lib/knowledge";

export default function KnowledgeProgress({ document: doc }: { document: KnowledgeDocument }) {
  const state = documentProgress(doc);
  const steps = ["原文件保存", "解析", "切块", "向量化", "提交索引", "可检索"];
  const current = doc.operation?.status === "completed" || (!doc.operation && doc.active_version) ? 5 : Math.max(1, ["saved", "parsing", "chunking", "embedding", "committing", "indexed"].indexOf(doc.operation?.stage || "parsing"));
  return <div className={`knowledge-progress ${state.failed ? "failed" : ""}`} role="status">
    {!doc.deleted_at && <ol className="ingestion-steps" aria-label="文档处理阶段">{steps.map((step, index) => <li key={step} className={index < current || current === 5 ? "done" : index === current ? "current" : ""} aria-current={index === current ? "step" : undefined}>{step}</li>)}</ol>}
    <strong>{state.label}</strong>
    {state.percent !== undefined ? <progress aria-label={state.label} max={100} value={state.percent} /> : !state.failed && doc.operation?.status === "running" ? <progress aria-label={state.label} /> : null}
    <small>{state.detail}</small>
    {!doc.deleted_at && doc.cleanup_status === "failed" && <small className="upload-error">{doc.cleanup_error} · 当前版本可检索</small>}
    {!doc.deleted_at && ["pending", "running"].includes(doc.cleanup_status || "") && <small>旧版本内容正在清理，无法恢复</small>}
    {doc.latest_version?.cleanup_pending && !doc.deleted_at && <small>旧版本内容正在清理，无法恢复</small>}
  </div>;
}
