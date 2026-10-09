"use client";
import "../chat-overrides.css";

import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import Navbar from "../../components/Navbar";
import ModeSelector, { ChatMode, chatModeLabels } from "../../components/ModeSelector";
import LanguageDialog, { SolutionLanguage } from "../../components/LanguageDialog";
import ProblemMentionPicker from "../../components/ProblemMentionPicker";
import TemporaryFilePicker from "../../components/TemporaryFilePicker";
import ChatRunProgress from "../../components/ChatRunProgress";
import MessageContent from "../../components/MessageContent";
import ConversationMenu from "../../components/ConversationMenu";
import CitationPanel, { Citation, RetrievalStatus, SessionFile } from "../../components/CitationPanel";
import type { ProblemSummary } from "../../components/ProblemCard";
import { apiFetch, reportError } from "../../lib/errors";
import { restoreConversationContext } from "../../lib/chat-context";
import { updateAssistantMessage } from "../../lib/chat-run-state";
import { ChatSubmitGate, ConversationSelection, createDraftConversation, deriveConversationTitle, mergeMessagePage, parseChatLaunch, sortConversations, sortMessages } from "../../lib/chat-state";
import { useChatRun } from "../../hooks/useChatRun";

const API = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api/v1";
type Message = { id?: string; created_at?: string; position?: number; role: "user" | "assistant"; content: string; status?: string; problem_id?: string | null; mode?: ChatMode; solution_language?: SolutionLanguage | null };
type Conversation = { id: string; title: string; updated_at: string; pinned?: boolean; selected_chat_model_id?: string | null };
type ChatModelOption = { id: string; connection_id: string; connection_name?: string | null; name: string; status: string; is_default?: boolean };
type MessagePage = { items: Message[]; has_more: boolean; next_before: number | null };

function CopyButton({ text }: { text: string }) {
  const [done, setDone] = useState(false);
  return <button className="icon-button" onClick={() => { navigator.clipboard?.writeText(text); setDone(true); window.setTimeout(() => setDone(false), 1200); }}>▣ {done ? "已复制" : "复制"}</button>;
}

function stateLabel(mode?: ChatMode) {
  return mode && mode !== "normal" ? `已切换到${chatModeLabels[mode]}` : "普通聊天";
}

export default function ChatPage() {
  const [token, setToken] = useState("");
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [conversationsLoaded, setConversationsLoaded] = useState(false);
  const [active, setActive] = useState<Conversation | null>(null);
  const [draft, setDraft] = useState(createDraftConversation());
  const [messages, setMessages] = useState<Message[]>([]);
  const [query, setQuery] = useState("");
  const [mode, setMode] = useState<ChatMode>("normal");
  const [modeOpen, setModeOpen] = useState(false);
  const [solutionLanguage, setSolutionLanguage] = useState<SolutionLanguage | null>(null);
  const [languageOpen, setLanguageOpen] = useState(false);
  const [selectedProblem, setSelectedProblem] = useState<ProblemSummary | null>(null);
  const [chatModels, setChatModels] = useState<ChatModelOption[]>([]);
  const [selectedChatModelId, setSelectedChatModelId] = useState("");
  const [sessionFiles, setSessionFiles] = useState<SessionFile[]>([]);
  const [citations, setCitations] = useState<Citation[]>([]);
  const [citationLoading, setCitationLoading] = useState(false);
  const [retrievalStatus, setRetrievalStatus] = useState<RetrievalStatus>("not_requested");
  const [menuId, setMenuId] = useState<string | null>(null);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [nextBefore, setNextBefore] = useState<number | null>(null);
  const [hasMore, setHasMore] = useState(false);
  const [loadingOlder, setLoadingOlder] = useState(false);
  const [mentionQuery, setMentionQuery] = useState<string | null>(null);
  const conversationSelectionRef = useRef(new ConversationSelection());
  const submitGateRef = useRef(new ChatSubmitGate());
  const auth = useCallback(() => ({ Authorization: `Bearer ${token}` }), [token]);

  const loadMessagePage = useCallback(async (conversationId: string, before?: number): Promise<MessagePage> => {
    const suffix = before ? `&before=${encodeURIComponent(before)}` : "";
    const response = await apiFetch(`${API}/conversations/${conversationId}/messages?limit=30${suffix}`, { headers: auth() });
    return response.json();
  }, [auth]);

  const loadSources = useCallback(async (conversationId: string, messageId?: string) => {
    if (!messageId) return;
    setCitationLoading(true);
    try {
      const response = await apiFetch(`${API}/conversations/${conversationId}/messages/${messageId}/citations`, { headers: auth() });
      const data = await response.json();
      if (conversationSelectionRef.current.currentId === conversationId) setCitations(Array.isArray(data) ? data : data.items || []);
    } catch { /* citation loading is non-blocking */ } finally { setCitationLoading(false); }
  }, [auth]);

  const chatRun = useChatRun({
    auth,
    isCurrent: conversationId => conversationSelectionRef.current.currentId === conversationId,
    onFrame: (conversationId, view, event) => {
      setMessages(items => updateAssistantMessage(items, view));
      if (event === "retrieval.completed") setRetrievalStatus(view.retrievalStatus);
      if (event === "citations.validated") setCitations(view.citations);
    },
    onFinished: loadSources,
  });
  const { cancelReader, resetView, startPending, failPending, consumeReader, reconnect,
    stop: stopChatRun, resume: resumeChatRun } = chatRun;
  const activeRun = active ? chatRun.views[active.id] : undefined;
  const activeConversationId = active?.id;
  const waiting = activeRun?.status === "waiting_context";
  const running = Boolean(activeRun && ["generating", "queued", "running"].includes(activeRun.status));

  useEffect(() => {
    const currentToken = localStorage.getItem("codeatlas_access_token") || "";
    setToken(currentToken);
    if (!currentToken) return;
    let cancelled = false;
    Promise.all([
      apiFetch(`${API}/conversations`, { headers: { Authorization: `Bearer ${currentToken}` } }),
      apiFetch(`${API}/model-connections/available`, { headers: { Authorization: `Bearer ${currentToken}` } }),
    ]).then(async ([conversationResponse, modelsResponse]) => {
      const list = await conversationResponse.json();
      const models = await modelsResponse.json();
      if (cancelled) return;
      const items: Conversation[] = Array.isArray(list) ? list : [];
      setConversations(sortConversations(items));
      setChatModels(Array.isArray(models) ? models : []);
      const conversationId = parseChatLaunch(window.location.search).conversationId;
      if (conversationId) setActive(items.find(item => item.id === conversationId) || null);
      setConversationsLoaded(true);
    }).catch(error => { if (!cancelled) reportError(error, "会话列表加载失败，请稍后重试"); });
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    if (!conversationsLoaded) return;
    const url = new URL(window.location.href);
    if (activeConversationId) {
      url.searchParams.set("conversation_id", activeConversationId);
      url.searchParams.delete("problem_id");
      url.searchParams.delete("mode");
    } else {
      url.searchParams.delete("conversation_id");
    }
    const next = `${url.pathname}${url.search}${url.hash}`;
    if (next !== `${window.location.pathname}${window.location.search}${window.location.hash}`) {
      window.history.replaceState(window.history.state, "", next);
    }
  }, [activeConversationId, conversationsLoaded]);

  useEffect(() => {
    if (!token) return;
    const launch = parseChatLaunch(window.location.search);
    if (!launch.problemId) return;
    apiFetch(`${API}/problems/${encodeURIComponent(launch.problemId)}`, { headers: auth() })
      .then(response => response.json()).then((problem: ProblemSummary) => {
        setSelectedProblem(problem); setMode(launch.mode);
        if (launch.mode === "acm_solution") setLanguageOpen(true);
      }).catch(error => reportError(error, "题目加载失败"));
  }, [token, auth]);

  useEffect(() => {
    if (!conversationSelectionRef.current.select(active?.id || null)) return;
    cancelReader();
    if (!active || !token) return;
    const conversationId = active.id;
    resetView(conversationId);
    setSelectedChatModelId(active.selected_chat_model_id || chatModels.find(model => model.is_default)?.id || chatModels[0]?.id || "");
    setMessages([]); setHasMore(false); setNextBefore(null); setCitations([]); setRetrievalStatus("not_requested"); setSelectedProblem(null); setSessionFiles([]);
    loadMessagePage(conversationId).then(data => {
      const items = sortMessages<Message>(data.items || []);
      if (conversationSelectionRef.current.currentId !== conversationId) return;
      setMessages(items);
      setHasMore(Boolean(data.has_more)); setNextBefore(data.next_before);
      const context = restoreConversationContext(items);
      setMode(context.mode); setSolutionLanguage(context.solutionLanguage);
      const latest = [...items].reverse().find(item => item.role === "assistant");
      loadSources(conversationId, latest?.id);
      reconnect(conversationId);
    }).catch(error => { if (conversationSelectionRef.current.currentId === conversationId) reportError(error, "历史消息加载失败，请稍后重试"); });
    apiFetch(`${API}/conversations/${conversationId}/temporary-files`, { headers: auth() }).then(response => response.json()).then(items => {
      if (conversationSelectionRef.current.currentId === conversationId && Array.isArray(items)) { setSessionFiles(items); }
    }).catch(() => undefined);
  }, [active, token, chatModels, auth, loadMessagePage, loadSources, reconnect, cancelReader, resetView]);

  async function loadOlder() {
    if (!active || !nextBefore || loadingOlder) return;
    const conversationId = active.id;
    setLoadingOlder(true);
    try {
      const page = await loadMessagePage(conversationId, nextBefore);
      if (conversationSelectionRef.current.currentId !== conversationId) return;
      setMessages(current => mergeMessagePage(current, page.items || []));
      setHasMore(Boolean(page.has_more)); setNextBefore(page.next_before);
    } catch (error) { reportError(error, "较早消息加载失败"); }
    finally { setLoadingOlder(false); }
  }

  function createDraft() {
    setActive(null); setDraft(createDraftConversation()); setMessages([]); setMode("normal"); setSolutionLanguage(null); setSelectedProblem(null); setSelectedChatModelId(chatModels.find(model => model.is_default)?.id || chatModels[0]?.id || ""); setCitations([]); setRetrievalStatus("not_requested"); setSessionFiles([]);
  }

  async function ensureConversation(text: string) {
    if (active) return active;
    const response = await apiFetch(`${API}/conversations`, { method: "POST", headers: { ...auth(), "Content-Type": "application/json" }, body: JSON.stringify({ title: deriveConversationTitle(text), mode }) });
    const conversation = await response.json() as Conversation;
    conversationSelectionRef.current.created(conversation.id);
    setConversations(items => sortConversations([conversation, ...items]));
    setActive(conversation);
    return conversation;
  }

  async function ensureTemporaryConversation() { return (await ensureConversation("临时文件")).id; }

  async function send(event: FormEvent) {
    event.preventDefault();
    const text = query.trim();
    if (!text || running || waiting) return;
    if (!selectedChatModelId) { reportError(new Error("请先在模型配置页验证一个聊天模型")); return; }
    if (mode === "acm_solution" && !solutionLanguage) { setLanguageOpen(true); return; }
    await submitGateRef.current.submit(text, ensureConversation, run, {
      onStart: () => setQuery(""),
      onCreateFailure: (draft, error) => {
        setQuery(current => current || draft);
        reportError(error, "创建会话失败，请稍后重试");
      },
    });
  }

  async function run(conversation: Conversation, text: string, reuseLastUser = false, retryContext?: { mode?: ChatMode; solution_language?: SolutionLanguage | null; problem_id?: string | null }) {
    const runMode = retryContext?.mode || mode;
    const runLanguage = retryContext?.solution_language === undefined ? solutionLanguage : retryContext.solution_language;
    const runProblemId = retryContext?.problem_id === undefined ? selectedProblem?.id || null : retryContext.problem_id;
    setRetrievalStatus("pending");
    startPending(conversation.id);
    setCitations([]);
    const payload = { content: text, mode: runMode, solution_language: runLanguage, problem_id: runProblemId, chat_model_id: selectedChatModelId, reuse_last_user: reuseLastUser };
    setMessages(items => [...items, ...(reuseLastUser ? [] : [{ role: "user" as const, content: text, status: "completed", mode: runMode }]), { role: "assistant", content: "", status: "generating", mode: runMode }]);
    try {
      const response = await apiFetch(`${API}/conversations/${conversation.id}/messages/stream`, { method: "POST", headers: { ...auth(), "Content-Type": "application/json" }, body: JSON.stringify(payload) });
      const reader = response.body?.getReader();
      if (reader) await consumeReader(conversation.id, reader);
    } catch (error) {
      setMessages(items => { const next = [...items]; const index = next.map(item => item.role).lastIndexOf("assistant"); if (index >= 0 && next[index].status === "generating") next[index] = { ...next[index], status: "failed", content: "发送失败，请稍后重试" }; return next; });
      failPending(conversation.id);
      setQuery(text);
      reportError(error, "发送失败，请稍后重试");
    }
  }

  async function retryMessage(message: Message, editedContent?: string) {
    if (!active || !message.id || running || waiting || !selectedChatModelId) return;
    const conversationId = active.id;
    try {
      const response = await apiFetch(`${API}/conversations/${conversationId}/messages/${message.id}/retry`, { method: "POST", headers: { ...auth(), "Content-Type": "application/json" }, body: JSON.stringify(editedContent ? { content: editedContent } : {}) });
      const context = await response.json();
      const page = await loadMessagePage(conversationId);
      if (conversationSelectionRef.current.currentId !== conversationId) return;
      setMessages(sortMessages(page.items || [])); setHasMore(Boolean(page.has_more)); setNextBefore(page.next_before);
      setMode(context.mode || "normal"); setSolutionLanguage(context.solution_language || null);
      setSelectedProblem(null);
      await run(active, context.content, true, context);
    } catch (error) { reportError(error, "重试消息失败，请稍后再试"); }
  }

  async function stop() {
    if (!active || !activeRun || !["queued", "running", "waiting_context"].includes(activeRun.status)) return;
    await stopChatRun(active.id).catch(error => reportError(error, "停止生成失败，请稍后重试"));
  }

  async function resume() {
    if (!active || !waiting) return;
    try {
      await resumeChatRun(active.id);
    } catch (error) { reportError(error, "恢复失败，请先重新上传临时文件"); }
  }

  async function patchConversation(conversation: Conversation, values: Record<string, unknown>) {
    try {
      const response = await apiFetch(`${API}/conversations/${conversation.id}`, { method: "PATCH", headers: { ...auth(), "Content-Type": "application/json" }, body: JSON.stringify(values) });
      const next = await response.json();
      setConversations(items => sortConversations(items.map(item => item.id === conversation.id ? next : item)));
      if (active?.id === conversation.id) setActive(next);
    } catch (error) { reportError(error, "会话更新失败，请稍后重试"); }
  }

  async function remove(ids: string[]) {
    try {
      await apiFetch(`${API}/conversations/bulk`, { method: "POST", headers: { ...auth(), "Content-Type": "application/json" }, body: JSON.stringify({ conversation_ids: ids, action: "delete" }) });
      setConversations(items => items.filter(item => !ids.includes(item.id)));
      if (active && ids.includes(active.id)) { setActive(null); setDraft(createDraftConversation()); setMessages([]); setCitations([]); setRetrievalStatus("not_requested"); }
      setSelectedIds([]);
    } catch (error) { reportError(error, "删除会话失败，请稍后重试"); }
  }

  async function bulkPin(action: "pin" | "unpin") {
    if (!selectedIds.length) return;
    try {
      await apiFetch(`${API}/conversations/bulk`, { method: "POST", headers: { ...auth(), "Content-Type": "application/json" }, body: JSON.stringify({ conversation_ids: selectedIds, action }) });
      setConversations(items => sortConversations(items.map(item => selectedIds.includes(item.id) ? { ...item, pinned: action === "pin" } : item)));
      setSelectedIds([]);
    } catch (error) { reportError(error, "批量更新失败"); }
  }

  if (!token) return <><Navbar /><main className="workspace"><h1 className="page-title">请先登录</h1><p className="sub">登录后才能创建和管理你的私人会话。</p></main></>;
  const current = active || draft;
  return <>
    <Navbar />
    <main className="chat-layout">
      <aside className="chat-side">
        <button className="pill fill" onClick={createDraft}>＋ 新建会话</button>
        {selectedIds.length > 0 && <div className="bulk-head"><span>已选 {selectedIds.length} 个会话</span><button aria-label="退出多选" onClick={() => setSelectedIds([])}>×</button></div>}
        <div className="side-title">最近会话</div>
        {conversations.map(conversation => <div className={`conversation-row ${active?.id === conversation.id ? "active" : ""}`} key={conversation.id}>
          {selectedIds.length > 0 && <input type="checkbox" aria-label={`选择${conversation.title}`} checked={selectedIds.includes(conversation.id)} onChange={event => setSelectedIds(ids => event.target.checked ? [...ids, conversation.id] : ids.filter(id => id !== conversation.id))} />}
          {editingId === conversation.id ? <form className="conversation-edit-form" onSubmit={event => { event.preventDefault(); const title = editTitle.trim(); if (title) patchConversation(conversation, { title }); setEditingId(null); }}><input className="conversation-edit" aria-label="会话名称" autoFocus value={editTitle} maxLength={200} onChange={event => setEditTitle(event.target.value)} onKeyDown={event => { if (event.key === "Escape") setEditingId(null); }} /></form> : <button className="side-item" onClick={() => selectedIds.length ? setSelectedIds(ids => ids.includes(conversation.id) ? ids.filter(id => id !== conversation.id) : [...ids, conversation.id]) : setActive(conversation)}>{conversation.pinned ? "⌃ " : ""}{conversation.title}</button>}
          <button className="conversation-more" aria-label="会话操作" onClick={event => { event.stopPropagation(); setMenuId(menuId === conversation.id ? null : conversation.id); }}>•••</button>
          {menuId === conversation.id && <ConversationMenu pinned={Boolean(conversation.pinned)} onClose={() => setMenuId(null)} onRename={() => { setEditingId(conversation.id); setEditTitle(conversation.title); }} onTogglePin={() => patchConversation(conversation, { pinned: !conversation.pinned })} onMultiSelect={() => setSelectedIds([conversation.id])} onDelete={() => { if (window.confirm(`删除会话“${conversation.title}”？`)) remove([conversation.id]); }} />}
        </div>)}
        {selectedIds.length > 0 && <div className="bulk-actions"><button onClick={() => bulkPin("pin")}>置顶</button><button onClick={() => bulkPin("unpin")}>取消置顶</button><button className="danger" onClick={() => { if (window.confirm(`删除选中的 ${selectedIds.length} 个会话？`)) remove(selectedIds); }}>删除</button></div>}
      </aside>
      <section className="chat-main">
        <header className="chat-head"><div><b>{current.title}</b><div className="muted" style={{ fontSize: 11, marginTop: 4 }}>私人会话 · {chatModeLabels[mode]}</div></div>
          <div className="chat-controls"><label className="mode-select">模型<select aria-label="选择聊天模型" value={selectedChatModelId} disabled={running || waiting} onChange={event => setSelectedChatModelId(event.target.value)}><option value="">选择模型</option>{chatModels.map(model => <option key={model.id} value={model.id}>{model.connection_name || "连接"} / {model.name}</option>)}</select></label><ModeSelector mode={mode} open={modeOpen} disabled={running} onToggle={() => setModeOpen(value => !value)} onChange={next => { setMode(next); setModeOpen(false); if (next === "acm_solution") setLanguageOpen(true); }} /></div>
        </header>
        <div className="messages">
          {hasMore && <div className="older-messages"><button className="icon-button" disabled={loadingOlder} onClick={loadOlder}>{loadingOlder ? "加载中…" : "加载更早消息"}</button></div>}
          {!messages.length && <div className="msg"><div className="label">CODEATLAS / READY</div><p>从一个算法问题开始。你可以描述题意、贴出代码，或者告诉我哪里卡住了。</p></div>}
          {messages.map((message, index) => {
            const previous = messages[index - 1];
            const changed = index > 0 && message.mode !== previous?.mode;
            return <div key={message.id || index}>{changed && <div className="chat-state-divider">{stateLabel(message.mode)}</div>}<article className={`msg ${message.role}`}><div className="msg-heading"><div className="label">{message.role === "user" ? "你" : "CODEATLAS"}</div>{message.status === "generating" && <span className="msg-metrics">正在生成…</span>}</div>{message.role === "assistant" && index === messages.length - 1 && active && <ChatRunProgress steps={activeRun?.steps || []} />}{message.content ? message.role === "assistant" ? <MessageContent content={message.content} /> : <p className="message-plain">{message.content}</p> : <p className="message-plain">正在生成…</p>}<div className="msg-actions"><CopyButton text={message.content} />{message.id && !running && selectedChatModelId && message.role === "user" && <button className="icon-button" onClick={() => { const edited = window.prompt("修改消息并重新生成；此消息之后的对话会被清除", message.content); if (edited?.trim()) retryMessage(message, edited.trim()); }}>编辑并重试</button>}{message.id && !running && selectedChatModelId && message.role === "assistant" && index === messages.length - 1 && <button className="icon-button" onClick={() => retryMessage(message)}>重新生成</button>}</div></article></div>;
          })}
        </div>
        {active && activeRun?.disconnected && <div className="context-warning" role="status">连接已断开，后台运行继续。<button type="button" onClick={() => reconnect(active.id)}>重新连接</button></div>}
        <form className="composer" onSubmit={send}><div className="composer-input"><textarea value={query} onChange={event => { setQuery(event.target.value); const at = event.target.value.lastIndexOf("@"); setMentionQuery(at >= 0 ? event.target.value.slice(at + 1) : null); }} placeholder="向 CodeAtlas 提问，输入 @ 召回题库内容" disabled={running} />{mentionQuery !== null && <ProblemMentionPicker token={token} query={mentionQuery} onSelect={problem => { setSelectedProblem(problem); setMentionQuery(null); }} />}</div><div className="composer-foot"><TemporaryFilePicker conversationId={active?.id || ""} ensureConversation={ensureTemporaryConversation} token={token} items={sessionFiles} onItems={setSessionFiles} disabled={running} /><button type="button" disabled={running} onClick={() => setModeOpen(true)}>⌘ {chatModeLabels[mode]}</button>{waiting ? <><button type="button" onClick={stop}>结束运行</button><button type="button" className="send" onClick={resume}>恢复运行</button></> : running ? <button type="button" className="send" onClick={stop}>停止</button> : <button className="send" disabled={!selectedChatModelId}>发送 ↑</button>}</div></form>
      </section>
      <CitationPanel citations={citations} sessionFiles={sessionFiles} loading={citationLoading} retrievalStatus={retrievalStatus} />
    </main>
    {languageOpen && <LanguageDialog onClose={() => setLanguageOpen(false)} onSelect={language => { setSolutionLanguage(language); setLanguageOpen(false); }} />}
  </>;
}
