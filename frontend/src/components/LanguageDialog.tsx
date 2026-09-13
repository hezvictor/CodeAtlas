export type SolutionLanguage = "cpp" | "java" | "python";
const languages: { value: SolutionLanguage; label: string; detail: string }[] = [{ value: "cpp", label: "C++", detail: "适合大多数竞赛题" }, { value: "java", label: "Java", detail: "标准 Main 类入口" }, { value: "python", label: "Python", detail: "简洁的竞赛输入输出" }];

export default function LanguageDialog({ onSelect, onClose }: { onSelect: (language: SolutionLanguage) => void; onClose: () => void }) {
  return <div className="dialog-backdrop" role="presentation" onMouseDown={onClose}><section className="language-dialog" role="dialog" aria-modal="true" aria-labelledby="language-title" onMouseDown={(event) => event.stopPropagation()}><div className="dialog-heading"><div><span className="eyebrow">ACM SOLUTION</span><h2 id="language-title">选择编程语言</h2></div><button className="dialog-close" onClick={onClose} aria-label="关闭语言选择">×</button></div><p className="muted">选择后将使用对应语言生成竞赛代码。</p><div className="language-options">{languages.map((language) => <button key={language.value} onClick={() => onSelect(language.value)}><strong>{language.label}</strong><small>{language.detail}</small></button>)}</div></section></div>;
}
