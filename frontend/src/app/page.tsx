"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
const nav = [["首页", "/"], ["聊天", "/chat"], ["题库", "/problems"], ["知识库", "/knowledge"]];
export default function HomePage() { const [user,setUser]=useState<string|null>(null); useEffect(()=>setUser(localStorage.getItem("codeatlas_user")),[]); return <main className="page"><header><Link className="brand" href="/">● CodeAtlas</Link><nav>{nav.map(([label,href])=><Link key={href} href={href}>{label}</Link>)}</nav><div className="account">{user?<Link href="/account">{user}</Link>:<><Link href="/auth/login">登录</Link><Link className="button" href="/auth/register">注册</Link></>}</div></header><section className="hero"><small>PERSONAL ALGORITHM COACH / 01</small><h1>把每一道题，<em>变成自己的方法。</em></h1><p>从读题、推导到复盘，CodeAtlas 连接你的题解、模板和错题记录。</p><div className="actions"><Link className="button" href="/chat">开始对话</Link><Link href="/knowledge">查看知识库 →</Link></div></section></main>; }
