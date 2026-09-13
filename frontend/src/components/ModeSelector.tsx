export type ChatMode = "normal" | "acm_analysis" | "acm_solution";
const labels: Record<ChatMode, string> = { normal: "普通模式", acm_analysis: "ACM 分析", acm_solution: "ACM 解题" };
const descriptions: Record<ChatMode, string> = { normal: "通用问答，可选题目和知识库", acm_analysis: "拆解题目，不输出完整代码", acm_solution: "选择语言后生成竞赛代码" };

export default function ModeSelector({ mode, open, onToggle, onChange }: { mode: ChatMode; open: boolean; onToggle: () => void; onChange: (mode: ChatMode) => void }) {
  return <div className="mode-picker"><button className="mode" onClick={onToggle} aria-expanded={open}>⌘ {labels[mode]}</button>{open && <div className="mode-menu">{(Object.keys(labels) as ChatMode[]).map((value) => <button key={value} className={value === mode ? "selected" : ""} onClick={() => onChange(value)}>{labels[value]}<small>{descriptions[value]}</small></button>)}</div>}</div>;
}

export { labels as chatModeLabels };
