"use client";

import { useEffect, useState } from "react";
import Navbar from "../../components/Navbar";
import ProblemCard, { ProblemSummary } from "../../components/ProblemCard";
import ProblemFilters from "../../components/ProblemFilters";
import { API, apiFetch, getToken } from "../../lib/auth";
import { reportError } from "../../lib/errors";

type ProblemPage = { items: ProblemSummary[]; page: number; page_size: number; total: number };

export default function ProblemsPage() {
  const [token, setToken] = useState(""); const [query, setQuery] = useState(""); const [difficulty, setDifficulty] = useState(""); const [tag, setTag] = useState(""); const [page, setPage] = useState(1); const [result, setResult] = useState<ProblemPage | null>(null); const [loading, setLoading] = useState(false);
  useEffect(() => { setToken(getToken()); }, []);
  useEffect(() => { if (!token) return; const timer = window.setTimeout(() => { const params = new URLSearchParams({ page: String(page), page_size: "12" }); if (query.trim()) params.set("query", query.trim()); if (difficulty) params.set("difficulty", difficulty); if (tag.trim()) params.set("tag", tag.trim()); setLoading(true); apiFetch(`${API}/problems?${params}`).then((response) => response.json()).then(setResult).catch((error) => reportError(error, "题库加载失败")).finally(() => setLoading(false)); }, 180); return () => window.clearTimeout(timer); }, [token, query, difficulty, tag, page]);
  function changeFilter(setter: (value: string) => void, value: string) { setPage(1); setter(value); }
  if (!token) return <><Navbar /><main className="workspace"><h1 className="page-title">请先登录</h1><p className="sub">登录后才能浏览题库并把题目带入 ACM 工作流。</p></main></>;
  return <><Navbar /><main className="workspace problems-page"><div className="eyebrow">PROBLEM SET / 04</div><div className="problems-hero"><div><h1 className="page-title">题库</h1><p className="sub">从一道清晰的题目开始，进入分析或解题流程。</p></div><div className="problem-count">{result ? `${result.total} 道题目` : "加载题目…"}</div></div><ProblemFilters query={query} difficulty={difficulty} tag={tag} onQueryChange={(value) => changeFilter(setQuery, value)} onDifficultyChange={(value) => changeFilter(setDifficulty, value)} onTagChange={(value) => changeFilter(setTag, value)} />{loading && <div className="panel problem-empty">正在加载题库…</div>}{!loading && result && !result.items.length && <div className="panel problem-empty"><strong>没有找到匹配题目</strong><p className="muted">换个关键词或清除筛选条件试试。</p></div>}{!loading && result && !!result.items.length && <><div className="problem-grid">{result.items.map((problem) => <ProblemCard key={problem.id} problem={problem} />)}</div><div className="problem-pagination"><button className="pill" disabled={page <= 1} onClick={() => setPage((value) => value - 1)}>上一页</button><span className="muted">第 {page} 页</span><button className="pill" disabled={page * result.page_size >= result.total} onClick={() => setPage((value) => value + 1)}>下一页</button></div></>}</main></>;
}
