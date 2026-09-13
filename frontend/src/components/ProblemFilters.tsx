type Props = { query: string; difficulty: string; tag: string; onQueryChange: (value: string) => void; onDifficultyChange: (value: string) => void; onTagChange: (value: string) => void };

export default function ProblemFilters({ query, difficulty, tag, onQueryChange, onDifficultyChange, onTagChange }: Props) {
  return <div className="problem-filters">
    <input value={query} onChange={(event) => onQueryChange(event.target.value)} placeholder="搜索题目、题面或标签" aria-label="搜索题目" />
    <select value={difficulty} onChange={(event) => onDifficultyChange(event.target.value)} aria-label="按难度筛选"><option value="">全部难度</option><option value="入门">入门</option><option value="简单">简单</option><option value="中等">中等</option><option value="困难">困难</option></select>
    <input value={tag} onChange={(event) => onTagChange(event.target.value)} placeholder="标签，例如 循环" aria-label="按标签筛选" />
  </div>;
}
