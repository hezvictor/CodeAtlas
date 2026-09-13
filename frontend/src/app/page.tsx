"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import Navbar from "../components/Navbar";
import { API, apiFetch, getToken } from "../lib/auth";

type Conversation = { id: string; title: string; updated_at: string };
type Dashboard = { today_conversation_count: number; recent_conversations: Conversation[]; latest_conversation: Conversation | null };

export default function HomePage() {
  const [token, setToken] = useState(""); const [dashboard, setDashboard] = useState<Dashboard | null>(null); const [error, setError] = useState("");
  useEffect(() => { const access = getToken(); setToken(access); if (access) apiFetch(`${API}/dashboard`, { headers: { Authorization: `Bearer ${access}` } }).then((response) => response.json()).then(setDashboard).catch(() => setError("首页数据暂时无法加载")); }, []);
  return <><Navbar /><main className="workspace home-workspace"><div className="eyebrow">PERSONAL ALGORITHM COACH / 01</div><h1 className="display">把每一道题，<br /><em>变成自己的方法。</em></h1><p className="sub">从读题、推导到复盘，CodeAtlas 连接你的题解、模板和错题记录，陪你把“会做”变成可迁移的竞赛能力。</p>{!token && <div className="home-grid"><section className="panel"><h3>开始训练</h3><p className="muted">登录后管理会话、题库和私人知识库。</p><Link className="pill fill" href="/auth/login">进入训练场</Link></section><section className="panel"><h3>题库与工作流</h3><p className="muted">从基础题开始，逐步进入 ACM 分析和解题模式。</p><Link className="pill" href="/problems">浏览题库</Link></section></div>}{token && dashboard && <div className="home-grid"><section className="panel"><h3>今日学习轨迹</h3><strong className="stat">{dashboard.today_conversation_count} <small>个会话</small></strong><p className="muted">今天已开启 {dashboard.today_conversation_count} 个 AI 会话</p><div className="bar"><i style={{ width: `${Math.min(100, dashboard.today_conversation_count * 20)}%` }} /></div></section><section className="panel"><h3>继续上次的思考</h3>{dashboard.latest_conversation ? <><b>{dashboard.latest_conversation.title}</b><p className="muted">最近更新于 {new Date(dashboard.latest_conversation.updated_at).toLocaleString("zh-CN")}</p><Link className="pill fill" href={`/chat?conversation_id=${dashboard.latest_conversation.id}`}>继续对话 →</Link></> : <><b>还没有会话</b><p className="muted">从题库选择一道题，开始第一次分析。</p><Link className="pill fill" href="/problems">浏览题库 →</Link></>}</section></div>}{token && !dashboard && !error && <section className="panel home-loading">正在加载你的学习数据…</section>}{error && <section className="panel home-loading">{error}</section>}</main></>;
}
