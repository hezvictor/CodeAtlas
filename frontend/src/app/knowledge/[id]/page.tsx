"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import Navbar from "../../../components/Navbar";
import { API, apiFetch, getToken } from "../../../lib/auth";

type Preview = { document: { title: string; group_id: string }; version: { original_filename: string; status: string; version_no: number }; text: string };

export default function DocumentPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [preview, setPreview] = useState<Preview | null>(null); const [error, setError] = useState("");
  useEffect(() => { const token = getToken(); if (!token) { setError("请先登录"); return; } apiFetch(`${API}/knowledge/documents/${id}/preview`, { headers: { Authorization: `Bearer ${token}` } }).then((response) => response.json()).then(setPreview).catch((reason) => setError(reason instanceof Error ? reason.message : "文档加载失败")); }, [id]);
  return <><Navbar /><main className="workspace document-page"><Link href="/knowledge" className="back-link">← 返回知识库</Link>{error && <div className="panel empty-knowledge"><strong>{error}</strong></div>}{preview && <><div className="eyebrow">DOCUMENT / VERSION {preview.version.version_no}</div><h1 className="page-title">{preview.document.title}</h1><p className="sub">{preview.version.original_filename} · {preview.version.status}</p><article className="document-preview panel"><pre>{preview.text || "文档尚未完成解析，稍后刷新。"}</pre></article></>}</main></>;
}
