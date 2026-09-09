"use client";
import { FormEvent, useState } from "react";
import Link from "next/link";
import Navbar from "../../../components/Navbar";
import { API, saveSession } from "../../../lib/auth";
export default function LoginPage() { const [error, setError] = useState(""); async function submit(e: FormEvent<HTMLFormElement>) { e.preventDefault(); const r = await fetch(`${API}/auth/login`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(Object.fromEntries(new FormData(e.currentTarget))) }); if (!r.ok) { const body = await r.json().catch(() => ({})); setError(body.message || "邮箱或密码错误"); return; } saveSession(await r.json()); location.href = "/chat"; } return <><Navbar /><main className="auth"><form className="auth-box" onSubmit={submit}><h1>登录你的训练场</h1><div className="field"><label>邮箱</label><input name="email" type="email" required /></div><div className="field"><label>密码</label><input name="password" type="password" required /></div><button className="pill fill">登录</button>{error && <p className="auth-error">{error}</p>}<Link className="auth-link" href="/auth/register">还没有账号？注册一个</Link></form></main></>; }
