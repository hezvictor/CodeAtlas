"use client";
/* eslint-disable @next/next/no-img-element -- Avatar URLs are short-lived user media URLs. */
import Link from "next/link";
import { useEffect, useState } from "react";
import { API, apiFetch, clearSession, getRefresh, getToken, User } from "../lib/auth";
import useKnowledgeSummary from "../hooks/useKnowledgeSummary";
const links = [["首页", "/"], ["聊天", "/chat"], ["题库", "/problems"], ["知识库", "/knowledge"], ["模型配置", "/settings/models"]];
export default function Navbar() {
  const summary = useKnowledgeSummary();
  const [user, setUser] = useState<User | null>(null); const [open, setOpen] = useState(false);
  useEffect(() => { if (getToken()) apiFetch(`${API}/users/me`, { headers: { Authorization: `Bearer ${getToken()}` } }).then(response => response.ok ? response.json() : null).then(setUser).catch(() => { clearSession(); setUser(null); }); }, []);
  async function logout() { const refresh = getRefresh(); try { if (refresh) await fetch(`${API}/auth/logout`, { method: "POST", headers: { Authorization: `Bearer ${getToken()}`, "Content-Type": "application/json" }, body: JSON.stringify({ refresh_token: refresh }) }); } finally { clearSession(); location.href = "/auth/login"; } }
  return <header className="topbar"><Link className="brand" href="/"><i />CodeAtlas</Link><nav className="nav">{links.map(([label, href]) => <Link key={href} href={href}>{label}{href === "/knowledge" && summary && <span className="knowledge-nav-badges">{summary.processing > 0 && <small title="后台处理中">处理中 {summary.processing}</small>}{summary.waiting > 0 && <small title="等待配置 Embedding">待配置 {summary.waiting}</small>}{summary.failed > 0 && <small className="failed" title="处理或清理失败">失败 {summary.failed}</small>}{summary.completed > 0 && <small className="complete" title="尚未查看的索引完成任务">完成 {summary.completed}</small>}</span>}</Link>)}</nav><div className="top-actions">{user ? <div className="profile-wrap"><button aria-label="打开个人中心菜单" className="profile" onClick={() => setOpen(value => !value)}>{user.avatar_url ? <img src={user.avatar_url} alt="头像" /> : user.nickname.slice(0, 1)}</button>{open && <div className="profile-menu"><Link href="/profile">个人中心</Link><button onClick={logout}>退出登录</button></div>}</div> : <><Link className="pill" href="/auth/login">登录</Link><Link className="pill fill" href="/auth/register">注册</Link></>}</div></header>;
}
