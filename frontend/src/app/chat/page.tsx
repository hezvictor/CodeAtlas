"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import Navbar from "../../components/Navbar";
import ModeSelector, { ChatMode, chatModeLabels } from "../../components/ModeSelector";
import LanguageDialog, { SolutionLanguage } from "../../components/LanguageDialog";
import ProblemMentionPicker, { ProblemMentionPickerHandle } from "../../components/ProblemMentionPicker";
import AttachmentPicker from "../../components/AttachmentPicker";
import type { ProblemSummary } from "../../components/ProblemCard";
import MessageContent from "../../components/MessageContent";
import { apiFetch, reportError } from "../../lib/errors";
import { restoreConversationContext } from "../../lib/chat-context";

const API = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api/v1";
type Citation = { chunk_id: string; quote: string; score: number; locator: Record<string, unknown> };
type KnowledgeGroup = { id: string; name: string };
type Message = { id?: string; role: "user" | "assistant"; content: string; status?: string; duration_ms?: number | null; first_token_latency_ms?: number | null; problem_id?: string | null; mode?: ChatMode; solution_language?: SolutionLanguage | null };
type Conversation = { id: string; title: string; updated_at: string };
type RunContext = { mode: ChatMode; problemId: string | null; solutionLanguage: SolutionLanguage | null };
type RetryResponse = { content: string; mode: ChatMode; problem_id: string | null; solution_language: SolutionLanguage | null };

function CopyButton({ text }: { text: string }) {
  const [done, setDone] = useState(false);
  return <button className="icon-button" onClick={() => { navigator.clipboard?.writeText(text); setDone(true); window.setTimeout(() => setDone(false), 1200); }}>▣ {done ? "已复制" : "复制"}</button>;
}

export default function ChatPage() {
  const [token, setToken] = useState("");
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [active, setActive] = useState<Conversation | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [query, setQuery] = useState("");
  const [busy, setBusy] = useState(false);
  const [editing, setEditing] = useState<string | null>(null);
  const [modeOpen, setModeOpen] = useState(false);
  const [mode, setMode] = useState<ChatMode>("normal");
  const [solutionLanguage, setSolutionLanguage] = useState<SolutionLanguage | null>(null);
  const [languageOpen, setLanguageOpen] = useState(false);
  const [selectedProblem, setSelectedProblem] = useState<ProblemSummary | null>(null);
  const [mentionQuery, setMentionQuery] = useState<string | null>(null);
  const [mentionStart, setMentionStart] = useState(-1);
  const [routeConversationId, setRouteConversationId] = useState("");
  const [routeProblemId, setRouteProblemId] = useState("");
  const [before, setBefore] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [citations, setCitations] = useState<Citation[]>([]);
  const [groups, setGroups] = useState<KnowledgeGroup[]>([]);
  const [selectedGroup, setSelectedGroup] = useState("");
  const [attachmentIds, setAttachmentIds] = useState<string[]>([]);
  const messagesRef = useRef<HTMLDivElement>(null);
  const mentionPickerRef = useRef<ProblemMentionPickerHandle>(null);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    setRouteConversationId(params.get("conversation_id") || "");
    setRouteProblemId(params.get("problem_id") || "");
    const requestedMode = params.get("mode") as ChatMode | null;
    if (requestedMode && Object.keys(chatModeLabels).includes(requestedMode)) setMode(requestedMode);
  }, []);

  useEffect(() => {
    const currentToken = localStorage.getItem("codeatlas_access_token") || "";
    setToken(currentToken);
    if (!currentToken) return;
    Promise.all([
      apiFetch(`${API}/conversations`, { headers: { Authorization: `Bearer ${currentToken}` } }),
      apiFetch(`${API}/knowledge/groups`, { headers: { Authorization: `Bearer ${currentToken}` } }),
    ]).then(async ([conversationResponse, groupResponse]) => {
      const data = await conversationResponse.json();
      const groupData = await groupResponse.json();
      if (!Array.isArray(data)) throw Error("会话列表格式异常");
      setConversations(data);
      setActive(data.find((item: Conversation) => item.id === routeConversationId) || data[0] || null);
      if (Array.isArray(groupData)) setGroups(groupData);
    }).catch((error) => { setConversations([]); reportError(error, "会话列表加载失败，请稍后重试"); });
  }, [routeConversationId]);

  useEffect(() => {
    if (!token || !routeProblemId) return;
    apiFetch(`${API}/problems/${routeProblemId}`, { headers: { Authorization: `Bearer ${token}` } }).then((response) => response.json()).then(setSelectedProblem).catch((error) => reportError(error, "题目加载失败，请重新选择"));
  }, [routeProblemId, token]);

  useEffect(() => {
    if (!active || !token) return;
    setSelectedProblem(null); setMode("normal"); setSolutionLanguage(null); setCitations([]);
    setAttachmentIds([]); setBefore(null); setHasMore(false);
    loadMessages(active.id);
    const conversationId = active.id;
    apiFetch(`${API}/conversations/${conversationId}/attachments`, { headers: { Authorization: `Bearer ${token}` } })
      .then((response) => response.json())
      .then((items) => { if (active?.id === conversationId && Array.isArray(items)) setAttachmentIds(items.map((item: { id: string }) => item.id)); })
      .catch(() => undefined);
  }, [active?.id, token]);

  async function loadMessages(conversationId: string, cursor?: string) {
    const response = await apiFetch(`${API}/conversations/${conversationId}/messages?limit=30${cursor ? `&before=${encodeURIComponent(cursor)}` : ""}`, { headers: { Authorization: `Bearer ${token}` } });
    const data = await response.json();
    const items: Message[] = Array.isArray(data) ? data : data.items || [];
    if (active?.id !== conversationId) return;
    setMessages((current) => cursor ? [...items, ...current] : items);
    setHasMore(Boolean(data.has_more)); setBefore(data.next_before || null);
    const context = restoreConversationContext(items);
    setMode(context.mode); setSolutionLanguage(context.solutionLanguage);
    if (context.problemId) apiFetch(`${API}/problems/${context.problemId}`, { headers: { Authorization: `Bearer ${token}` } }).then((result) => result.json()).then((problem) => { if (active?.id === conversationId) setSelectedProblem(problem); }).catch(() => undefined);
  }

  async function older() {
    if (!active || !before || loadingMore) return;
    setLoadingMore(true); const element = messagesRef.current; const height = element?.scrollHeight || 0;
    try { await loadMessages(active.id, before); requestAnimationFrame(() => { if (element) element.scrollTop += element.scrollHeight - height; }); } catch (error) { reportError(error, "历史消息加载失败，请稍后重试"); } finally { setLoadingMore(false); }
  }

  async function create() {
    if (!token) { reportError(new Error("请先登录")); return; }
    try { const response = await apiFetch(`${API}/conversations`, { method: "POST", headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" }, body: "{}" }); const conversation = await response.json(); setConversations((items) => [conversation, ...items]); setActive(conversation); setMessages([]); } catch (error) { reportError(error, "新建会话失败，请稍后重试"); }
  }

  async function rename(conversation: Conversation, title: string) {
    if (!title.trim()) return;
    try { const response = await apiFetch(`${API}/conversations/${conversation.id}`, { method: "PATCH", headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" }, body: JSON.stringify({ title: title.trim() }) }); const next = await response.json(); setConversations((items) => items.map((item) => item.id === conversation.id ? next : item)); setActive((item) => item?.id === conversation.id ? next : item); setEditing(null); } catch (error) { reportError(error, "会话重命名失败，请稍后重试"); }
  }

  async function stop() { if (active) await apiFetch(`${API}/conversations/${active.id}/run/stop`, { method: "POST", headers: { Authorization: `Bearer ${token}` } }).catch((error) => reportError(error, "停止生成失败，请稍后重试")); }

  async function run(text: string, reuseLastUser = false, context?: RunContext) {
    if (!active) return;
    const runMode = context?.mode || mode;
    const runProblemId = context?.problemId ?? selectedProblem?.id ?? null;
    const runLanguage = context?.solutionLanguage ?? solutionLanguage;
    setBusy(true); setCitations([]); setMessages((items) => [...items, ...(reuseLastUser ? [] : [{ role: "user" as const, content: text, mode: runMode, problem_id: runProblemId, solution_language: runLanguage }]), { role: "assistant" as const, content: "", status: "generating", mode: runMode, problem_id: runProblemId, solution_language: runLanguage }]);
    try {
      const response = await apiFetch(`${API}/conversations/${active.id}/messages/stream`, { method: "POST", headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" }, body: JSON.stringify({ content: text, mode: runMode, solution_language: runLanguage, problem_id: runProblemId, knowledge_group_ids: selectedGroup ? [selectedGroup] : [], attachment_ids: attachmentIds, reuse_last_user: reuseLastUser }) });
      const reader = response.body?.getReader(); if (!reader) throw Error("无法读取回答流");
      const decoder = new TextDecoder(); let buffer = ""; let answer = ""; let status = "completed";
      while (true) { const chunk = await reader.read(); if (chunk.done) break; buffer += decoder.decode(chunk.value, { stream: true }); const events = buffer.split("\n\n"); buffer = events.pop() || ""; for (const raw of events) { const line = raw.split("\n").find((item) => item.startsWith("data: ")); if (!line) continue; const event = raw.split("\n").find((item) => item.startsWith("event: "))?.slice(7); const data = JSON.parse(line.slice(6)); if (event === "run.interrupted") status = "cancelled"; if (event === "run.failed") { status = "failed"; answer = data.message || "生成失败"; } if (event === "citations.validated") setCitations(data.items || []); if (event === "message.final") answer = data.content || answer; else if (data.content) answer += data.content; setMessages((items) => items.map((item, index) => index === items.length - 1 ? { ...item, content: answer, status } : item)); } }
      if (active.title === "新对话") await rename(active, text.slice(0, 24) + (text.length > 24 ? "…" : ""));
      await loadMessages(active.id);
    } catch (error) { setMessages((items) => items.map((item, index) => index === items.length - 1 ? { ...item, status: "failed", content: error instanceof Error ? error.message : "请求失败" } : item)); } finally { setBusy(false); }
  }

  async function send(event: FormEvent) { event.preventDefault(); if (!query.trim() || busy || !active) return; if (mode !== "normal" && !selectedProblem) { reportError(new Error("ACM 模式需要先选择题目")); return; } if (mode === "acm_solution" && !solutionLanguage) { setLanguageOpen(true); return; } const text = query.trim(); setQuery(""); await run(text); }
  async function retry(message: Message, index: number) { if (!active || busy || !message.id) return; try { const response = await apiFetch(`${API}/conversations/${active.id}/messages/${message.id}/retry`, { method: "POST", headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" }, body: JSON.stringify({ content: message.role === "user" ? message.content : undefined }) }); const data = await response.json() as RetryResponse; setMessages((items) => items.slice(0, index)); await run(data.content, true, { mode: data.mode || "normal", problemId: data.problem_id, solutionLanguage: data.solution_language }); } catch (error) { reportError(error, "重试失败，请稍后重试"); } }
  async function editRetry(message: Message, index: number) { if (message.role !== "user") return; const content = window.prompt("编辑消息", message.content)?.trim(); if (!content || content === message.content || !active || !message.id || busy) return; try { const response = await apiFetch(`${API}/conversations/${active.id}/messages/${message.id}/retry`, { method: "POST", headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" }, body: JSON.stringify({ content }) }); const data = await response.json() as RetryResponse; setMessages((items) => items.slice(0, index)); await run(data.content, true, { mode: data.mode || "normal", problemId: data.problem_id, solutionLanguage: data.solution_language }); } catch (error) { reportError(error, "编辑重试失败，请稍后重试"); } }

  function changeComposer(value: string) { setQuery(value); const at = value.lastIndexOf("@"); if (at >= 0 && (at === 0 || /\s/.test(value[at - 1]))) { setMentionStart(at); setMentionQuery(value.slice(at + 1)); } else { setMentionStart(-1); setMentionQuery(null); } }
  function handleComposerKeyDown(event: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (mentionQuery === null) return;
    if (event.key === "Escape") { event.preventDefault(); setMentionStart(-1); setMentionQuery(null); return; }
    if (["ArrowDown", "ArrowUp", "Enter"].includes(event.key) && mentionPickerRef.current?.handleKey(event.key)) event.preventDefault();
  }
  function selectProblem(problem: ProblemSummary) { setSelectedProblem(problem); if (mentionStart >= 0) setQuery((value) => `${value.slice(0, mentionStart).trimEnd()} `); setMentionStart(-1); setMentionQuery(null); }
  function changeMode(next: ChatMode) { setMode(next); setModeOpen(false); if (next === "normal" || next === "acm_analysis") setSolutionLanguage(null); if (next === "acm_solution") setLanguageOpen(true); }

  if (!token) return <><Navbar /><main className="workspace"><h1 className="page-title">请先登录</h1><p className="sub">登录后才能创建和管理你的私人会话。</p></main></>;
  return <><Navbar /><main className="chat-layout"><aside className="chat-side"><button className="pill fill" onClick={create}>＋ 新建会话</button><div className="side-title">最近会话</div>{conversations.map((conversation) => editing === conversation.id ? <input autoFocus className="conversation-edit" key={conversation.id} defaultValue={conversation.title} onBlur={(event) => rename(conversation, event.target.value)} onKeyDown={(event) => event.key === "Enter" && rename(conversation, event.currentTarget.value)} /> : <button className={`side-item ${active?.id === conversation.id ? "active" : ""}`} key={conversation.id} onClick={() => setActive(conversation)} onDoubleClick={() => setEditing(conversation.id)}>{conversation.title}</button>)}</aside><section className="chat-main"><header className="chat-head"><div><b>{active?.title || "选择一个会话"}</b><div className="muted" style={{ fontSize: 11, marginTop: 4 }}>{selectedProblem ? `题库题目 · ${selectedProblem.title}` : "私人会话"} · {chatModeLabels[mode]}</div></div><div className="chat-controls"><label className="mode-select">知识库<select aria-label="选择知识库分组" value={selectedGroup} onChange={(event) => setSelectedGroup(event.target.value)}><option value="">不使用知识库</option>{groups.map((group) => <option key={group.id} value={group.id}>{group.name}</option>)}</select></label><ModeSelector mode={mode} open={modeOpen} onToggle={() => setModeOpen((value) => !value)} onChange={changeMode} /></div></header><div className="messages" ref={messagesRef} onScroll={(event) => event.currentTarget.scrollTop === 0 && older()}>{hasMore && <button className="icon-button" onClick={older}>{loadingMore ? "加载中…" : "加载更早消息"}</button>}{!messages.length && <div className="msg"><div className="label">CODEATLAS / READY</div><p>从一个算法问题开始。你可以描述题意、贴出代码，或者告诉我哪里卡住了。</p></div>}{messages.map((message, index) => <article className={`msg ${message.role}`} key={message.id || index}><div className="msg-heading"><div className="label">{message.role === "user" ? "你" : "CODEATLAS"}</div>{message.duration_ms ? <span className="msg-metrics">耗时 {message.duration_ms} ms{message.first_token_latency_ms ? ` · 首 token ${message.first_token_latency_ms} ms` : ""}</span> : null}</div>{message.problem_id && <div className="message-context">题目关联 · {message.mode === "acm_solution" ? "ACM 解题" : message.mode === "acm_analysis" ? "ACM 分析" : "普通模式"}</div>}{message.content ? message.role === "assistant" ? <MessageContent content={message.content} /> : <p className="message-plain">{message.content}</p> : <p className="message-plain">正在生成…</p>}{message.status && message.status !== "completed" && message.status !== "generating" && <div className="muted">{message.status === "cancelled" ? "已停止生成" : "生成失败"}</div>}<div className="msg-actions"><CopyButton text={message.content} />{message.role === "user" && message.status === "completed" && <button className="icon-button" onClick={() => editRetry(message, index)}>编辑重试</button>}{(message.status === "failed" || message.status === "cancelled") && <button className="icon-button" onClick={() => retry(message, index)}>↻ 重试</button>}{message.role === "assistant" && message.status === "completed" && <button className="icon-button" onClick={() => retry(message, index)}>↻ 重新生成</button>}</div></article>)}</div><form className="composer" onSubmit={send}><div className="composer-input">{selectedProblem && <div className="selected-problem"><span>题目 · {selectedProblem.title}</span><button type="button" aria-label="移除已选题目" onClick={() => setSelectedProblem(null)}>×</button></div>}<textarea value={query} onChange={(event) => changeComposer(event.target.value)} onKeyDown={handleComposerKeyDown} placeholder="向 CodeAtlas 提问，输入 @ 召回题库内容" disabled={!active || busy} />{mentionQuery !== null && <ProblemMentionPicker ref={mentionPickerRef} token={token} query={mentionQuery} onSelect={selectProblem} />}</div><div className="composer-foot"><AttachmentPicker conversationId={active?.id || ""} token={token} onChange={setAttachmentIds} disabled={!active || busy} /><button type="button" onClick={() => setModeOpen(true)}>⌘ {chatModeLabels[mode]}</button>{busy ? <button type="button" className="send" onClick={stop}>停止</button> : <button className="send" disabled={!active}>发送 ↑</button>}</div></form></section><aside className="context"><h3>回答依据</h3>{citations.length ? citations.map((item) => <div className="source" key={item.chunk_id}><b>知识库切片</b><small>{item.locator.page ? `第 ${item.locator.page} 页 · ` : ""}相关度 {Math.round(item.score * 100)}%</small><p>{item.quote}</p></div>) : <div className="source empty">选择知识库分组后，回答依据会显示在这里。</div>}</aside></main>{languageOpen && <LanguageDialog onClose={() => setLanguageOpen(false)} onSelect={(language) => { setSolutionLanguage(language); setLanguageOpen(false); }} />}</>;
}
