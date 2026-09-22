"use client";

import Link from "next/link";
import { use, useEffect, useState } from "react";
import Navbar from "../../../components/Navbar";
import ProblemEditor, { ProblemDetail } from "../../../components/ProblemEditor";
import { API, apiFetch, getToken } from "../../../lib/auth";
import { reportError } from "../../../lib/errors";

export default function ProblemDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [problem, setProblem] = useState<ProblemDetail | null>(null);
  const [error, setError] = useState("");
  const [editing, setEditing] = useState(false);
  async function load() {
    const token = getToken();
    if (!token) { setError("请先登录"); return; }
    try {
      const response = await apiFetch(`${API}/problems/${id}`, { headers: { Authorization: `Bearer ${token}` } });
      if (!response.ok) throw new Error("题目不存在或无权访问");
      setProblem(await response.json());
    } catch (reason) { setError(reason instanceof Error ? reason.message : "题目加载失败"); reportError(reason, "题目加载失败"); }
  }
  useEffect(() => { void load(); }, [id]);
  async function remove() {
    if (!problem || !window.confirm(`确定删除“${problem.title}”吗？删除后不可恢复。`)) return;
    try {
      const response = await apiFetch(`${API}/problems/${problem.id}`, { method: "DELETE", headers: { Authorization: `Bearer ${getToken()}` } });
      if (!response.ok) throw new Error("题目删除失败");
      window.location.href = "/problems";
    } catch (reason) { reportError(reason, "题目删除失败"); }
  }
  return <><Navbar /><main className="workspace problem-detail-page"><Link href="/problems" className="back-link">← 返回我的题库</Link>{error && <div className="panel problem-empty"><strong>{error}</strong></div>}{problem && <>
    <div className="eyebrow">PROBLEM / {problem.id}</div>
    <div className="detail-heading"><div><h1 className="page-title">{problem.title}</h1><div className="problem-tags">{problem.tags.map((tag) => <span key={tag}>{tag}</span>)}</div></div><div className="detail-actions"><Link className="pill" href={`/chat?problem_id=${problem.id}&mode=acm_analysis`}>开始分析</Link><Link className="pill fill" href={`/chat?problem_id=${problem.id}&mode=acm_solution`}>开始解题</Link></div></div>
    <div className="problem-detail-layout"><article className="problem-statement panel"><section><h2>题目描述</h2><p>{problem.statement}</p></section><section><h2>输入格式</h2><p>{problem.input_description}</p></section><section><h2>输出格式</h2><p>{problem.output_description}</p></section><section><h2>样例</h2>{problem.examples.map((example, index) => <div className="example-block" key={index}><div><span>输入数据 {index + 1}</span><pre>{example.input || "（无）"}</pre></div><div><span>输出数据 {index + 1}</span><pre>{example.output}</pre></div></div>)}</section><section><h2>约束条件</h2><p>{problem.constraints}</p></section></article><aside className="problem-sidebar"><section className="panel problem-meta-panel"><dl><div><dt>题目 ID</dt><dd>{problem.id}</dd></div><div><dt>难度</dt><dd>{problem.difficulty}</dd></div><div><dt>来源</dt><dd>{problem.source_type === "default" ? "注册默认题目" : "个人题目"}</dd></div><div><dt>语言</dt><dd>{problem.supported_languages.join(" · ")}</dd></div></dl></section><section className="panel detail-side-actions"><button className="side-action" type="button" onClick={() => setEditing(true)}>✎ 编辑题目</button><button className="side-action danger" type="button" onClick={remove}>⌫ 删除题目</button></section></aside></div>
  </>}</main>{editing && problem && <ProblemEditor problem={problem} onClose={() => setEditing(false)} onSaved={() => { setEditing(false); void load(); }} />}</>;
}
