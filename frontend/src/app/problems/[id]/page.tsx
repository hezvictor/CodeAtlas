"use client";

import Link from "next/link";
import { use, useEffect, useState } from "react";
import Navbar from "../../../components/Navbar";
import { API, apiFetch, getToken } from "../../../lib/auth";
import { reportError } from "../../../lib/errors";

type Problem = { id: string; title: string; difficulty: string; tags: string[]; statement: string; input_description: string; output_description: string; examples: { input: string; output: string }[]; constraints: string; supported_languages: string[] };

export default function ProblemDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params); const [problem, setProblem] = useState<Problem | null>(null); const [error, setError] = useState("");
  useEffect(() => { const token = getToken(); if (!token) { setError("请先登录"); return; } apiFetch(`${API}/problems/${id}`, { headers: { Authorization: `Bearer ${token}` } }).then((response) => response.json()).then(setProblem).catch((reason) => { setError(reason instanceof Error ? reason.message : "题目加载失败"); reportError(reason, "题目加载失败"); }); }, [id]);
  return <><Navbar /><main className="workspace problem-detail-page"><Link href="/problems" className="back-link">← 返回题库</Link>{error && <div className="panel problem-empty"><strong>{error}</strong></div>}{problem && <><div className="eyebrow">PROBLEM / {problem.difficulty}</div><div className="detail-heading"><div><h1 className="page-title">{problem.title}</h1><div className="problem-tags">{problem.tags.map((tag) => <span key={tag}>{tag}</span>)}</div></div><div className="detail-actions"><Link className="pill" href={`/chat?problem_id=${problem.id}&mode=acm_analysis`}>开始分析</Link><Link className="pill fill" href={`/chat?problem_id=${problem.id}&mode=acm_solution`}>开始解题</Link></div></div><article className="problem-statement panel"><section><h2>题目描述</h2><p>{problem.statement}</p></section><section><h2>输入描述</h2><p>{problem.input_description}</p></section><section><h2>输出描述</h2><p>{problem.output_description}</p></section><section><h2>样例</h2>{problem.examples.map((example, index) => <div className="example-block" key={index}><div><span>输入</span><pre>{example.input || "（无）"}</pre></div><div><span>输出</span><pre>{example.output}</pre></div></div>)}</section><section><h2>约束条件</h2><p>{problem.constraints}</p></section><section><h2>支持语言</h2><p>{problem.supported_languages.join(" · ")}</p></section></article></>}</main></>;
}
