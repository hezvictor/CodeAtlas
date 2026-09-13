import Link from "next/link";

export type ProblemSummary = {
  id: string;
  slug: string;
  title: string;
  difficulty: string;
  tags: string[];
  supported_languages: string[];
};

export default function ProblemCard({ problem }: { problem: ProblemSummary }) {
  return (
    <article className="problem-card panel">
      <div className="problem-card-top"><span className="problem-difficulty">{problem.difficulty}</span><span className="muted problem-slug">{problem.slug}</span></div>
      <Link href={`/problems/${problem.id}`} className="problem-title">{problem.title}</Link>
      <div className="problem-tags">{problem.tags.map((tag) => <span key={tag}>{tag}</span>)}</div>
      <div className="problem-card-foot"><span className="muted">{problem.supported_languages.join(" · ")}</span><Link className="icon-button" href={`/problems/${problem.id}`}>查看题目 →</Link></div>
    </article>
  );
}
