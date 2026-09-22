"use client";

import { useEffect, useState } from "react";
import Navbar from "../../components/Navbar";
import ProblemCard, { ProblemSummary } from "../../components/ProblemCard";
import ProblemEditor, { ProblemDetail } from "../../components/ProblemEditor";
import ProblemFilters from "../../components/ProblemFilters";
import { API, apiFetch, getToken } from "../../lib/auth";
import { reportError } from "../../lib/errors";

type ProblemPage = { items: ProblemSummary[]; page: number; page_size: number; total: number };

export default function ProblemsPage() {
  const [token, setToken] = useState("");
  const [query, setQuery] = useState("");
  const [difficulty, setDifficulty] = useState("");
  const [tag, setTag] = useState("");
  const [page, setPage] = useState(1);
  const [result, setResult] = useState<ProblemPage | null>(null);
  const [loading, setLoading] = useState(false);
  const [editorProblem, setEditorProblem] = useState<ProblemDetail | ProblemSummary | null | undefined>(undefined);
  const [error, setError] = useState("");

  useEffect(() => { setToken(getToken()); }, []);
  async function loadProblems() {
    const access = token || getToken();
    if (!access) return;
    const params = new URLSearchParams({ page: String(page), page_size: "12" });
    if (query.trim()) params.set("query", query.trim());
    if (difficulty) params.set("difficulty", difficulty);
    if (tag.trim()) params.set("tag", tag.trim());
    setLoading(true);
    try {
      const response = await apiFetch(`${API}/problems?${params}`, { headers: { Authorization: `Bearer ${access}` } });
      if (!response.ok) throw new Error("题库加载失败");
      setResult(await response.json());
      setError("");
    } catch (reason) { setError(reason instanceof Error ? reason.message : "题库加载失败"); reportError(reason, "题库加载失败"); } finally { setLoading(false); }
  }
  useEffect(() => { if (!token) return; const timer = window.setTimeout(() => { void loadProblems(); }, 180); return () => window.clearTimeout(timer); }, [token, query, difficulty, tag, page]);
  function changeFilter(setter: (value: string) => void, value: string) { setPage(1); setter(value); }
  async function edit(problem: ProblemSummary) {
    try {
      const response = await apiFetch(`${API}/problems/${problem.id}`, { headers: { Authorization: `Bearer ${token}` } });
      if (!response.ok) throw new Error("题目加载失败");
      setEditorProblem(await response.json());
    } catch (reason) { reportError(reason, "题目加载失败"); }
  }
  async function remove(problem: ProblemSummary) {
    if (!window.confirm(`确定删除“${problem.title}”吗？删除后不可恢复。`)) return;
    try {
      const response = await apiFetch(`${API}/problems/${problem.id}`, { method: "DELETE", headers: { Authorization: `Bearer ${token}` } });
      if (!response.ok) throw new Error("题目删除失败");
      if (result?.items.length === 1 && page > 1) setPage((value) => value - 1); else await loadProblems();
    } catch (reason) { reportError(reason, "题目删除失败"); }
  }
  if (!token) return <><Navbar /><main className="workspace"><h1 className="page-title">请先登录</h1><p className="sub">登录后才能浏览和管理自己的题库。</p></main></>;
  return <>
    <Navbar />
    <main className="workspace problems-page">
      <div className="eyebrow">PERSONAL PROBLEM INDEX / 04</div>
      <div className="problems-hero"><div><h1 className="page-title">我的题库</h1><p className="sub">注册默认题目和你创建的题目，都可以在这里持续整理。</p></div><div className="problem-hero-actions"><div className="problem-count">{result ? `${result.total} 道题目` : "加载题目…"}</div><button className="pill fill" type="button" onClick={() => setEditorProblem(null)}>＋ 新建题目</button></div></div>
      <ProblemFilters query={query} difficulty={difficulty} tag={tag} onQueryChange={(value) => changeFilter(setQuery, value)} onDifficultyChange={(value) => changeFilter(setDifficulty, value)} onTagChange={(value) => changeFilter(setTag, value)} />
      {error && <div className="panel problem-empty"><strong>{error}</strong><p className="muted">请刷新页面后重试。</p></div>}
      {!error && loading && <div className="panel problem-empty">正在加载题库…</div>}
      {!error && !loading && result && !result.items.length && <div className="panel problem-empty"><strong>没有找到匹配题目</strong><p className="muted">换个关键词或创建一道新题目。</p></div>}
      {!error && !loading && result && !!result.items.length && <>
        <div className="problem-list-head"><span>唯一 ID</span><span>题目与分类</span><span>来源 / 语言</span><span>操作</span></div>
        <div className="problem-list">{result.items.map((problem) => <ProblemCard key={problem.id} problem={problem} onEdit={edit} onDelete={remove} />)}</div>
        <div className="problem-pagination"><button className="pill" disabled={page <= 1} onClick={() => setPage((value) => value - 1)}>上一页</button><span className="muted">第 {page} 页</span><button className="pill" disabled={page * result.page_size >= result.total} onClick={() => setPage((value) => value + 1)}>下一页</button></div>
      </>}
    </main>
    {editorProblem !== undefined && <ProblemEditor problem={editorProblem} onClose={() => setEditorProblem(undefined)} onSaved={() => { setEditorProblem(undefined); void loadProblems(); }} />}
  </>;
}
