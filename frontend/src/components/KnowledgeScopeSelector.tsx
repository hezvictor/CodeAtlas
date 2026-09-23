import type { KnowledgeScope } from "../lib/chat-state";

const labels: Record<KnowledgeScope, string> = { none: "不引用知识库", all: "引用知识库" };

export default function KnowledgeScopeSelector({ scope, disabled = false, onChange }: { scope: KnowledgeScope; disabled?: boolean; onChange: (scope: KnowledgeScope) => void }) {
  return <div className="knowledge-scope" role="group" aria-label="知识库引用范围">
    {(Object.keys(labels) as KnowledgeScope[]).map((value) => <button key={value} type="button" className={value === scope ? "selected" : ""} aria-pressed={value === scope} disabled={disabled} onClick={() => onChange(value)}>{labels[value]}</button>)}
  </div>;
}

export { labels as knowledgeScopeLabels };
