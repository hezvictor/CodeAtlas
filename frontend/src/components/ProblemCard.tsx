import Link from "next/link";

export type ProblemSummary = {
  id: string;
  owner_user_id: string;
  source_type: "default" | "user" | string;
  slug: string;
  title: string;
  difficulty: string;
  tags: string[];
  supported_languages: string[];
};

type Props = {
  problem: ProblemSummary;
  onEdit: (problem: ProblemSummary) => void;
  onDelete: (problem: ProblemSummary) => void;
};

function sourceLabel(source: string) {
  return source === "default" ? "注册默认" : "我创建的";
}

export default function ProblemCard({ problem, onEdit, onDelete }: Props) {
  return (
    <article className="problem-card panel">
      <div className="problem-index-id" title={problem.id}>
        <span>ID</span>
        <code>{problem.id}</code>
      </div>
      <div className="problem-row-main">
        <Link href={`/problems/${problem.id}`} className="problem-title">{problem.title}</Link>
        <div className="problem-row-meta">
          <span className="problem-difficulty">{problem.difficulty}</span>
          <span className="problem-source">{sourceLabel(problem.source_type)}</span>
          <span className="muted">{problem.supported_languages.join(" · ")}</span>
        </div>
        <div className="problem-tags">{problem.tags.map((tag) => <span key={tag}>{tag}</span>)}</div>
      </div>
      <div className="problem-row-actions">
        <Link className="icon-button" href={`/problems/${problem.id}`}>查看</Link>
        <button className="icon-button" type="button" onClick={() => onEdit(problem)}>编辑</button>
        <button className="icon-button danger" type="button" onClick={() => onDelete(problem)}>删除</button>
      </div>
    </article>
  );
}
