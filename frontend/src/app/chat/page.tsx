"use client";
import "../chat-overrides.css";

import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import Navbar from "../../components/Navbar";
import ModeSelector, { ChatMode, chatModeLabels } from "../../components/ModeSelector";
import KnowledgeScopeSelector from "../../components/KnowledgeScopeSelector";
import LanguageDialog, { SolutionLanguage } from "../../components/LanguageDialog";
import ProblemMentionPicker from "../../components/ProblemMentionPicker";
import AttachmentPicker from "../../components/AttachmentPicker";
import MessageContent from "../../components/MessageContent";
import ConversationMenu from "../../components/ConversationMenu";
import CitationPanel, { Citation, RetrievalStatus, SessionFile } from "../../components/CitationPanel";
import type { ProblemSummary } from "../../components/ProblemCard";
import { apiFetch, reportError } from "../../lib/errors";
import { restoreConversationContext } from "../../lib/chat-context";
import { createDraftConversation, deriveConversationTitle, mergeMessagePage, parseChatLaunch, sortConversations, sortMessages, type KnowledgeScope } from "../../lib/chat-state";
import { SseDecoder } from "../../lib/sse";

const API = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api/v1";
type Message = { id?: string; created_at?: string; role: "user" | "assistant"; content: string; status?: string; problem_id?: string | null; mode?: ChatMode; knowledge_scope?: KnowledgeScope; solution_language?: SolutionLanguage | null };
type Conversation = { id: string; title: string; updated_at: string; pinned?: boolean; knowledge_scope?: KnowledgeScope; selected_chat_model_id?: string | null };
type ChatModelOption = { id: string; connection_id: string; connection_name?: string | null; name: string; status: string; is_default?: boolean };
type MessagePage = { items: Message[]; has_more: boolean; next_before: string | null };
type StreamPayload = { message_id?: string; run_id?: string; content?: string; delta?: string; status?: string; items?: Citation[]; message?: string };

function CopyButton({ text }: { text: string }) {
  const [done, setDone] = useState(false);
  return <button className="icon-button" onClick={() => { navigator.clipboard?.writeText(text); setDone(true); window.setTimeout(() => setDone(false), 1200); }}>▣ {done ? "已复制" : "复制"}</button>;
}

function stateLabel(mode?: ChatMode, scope?: KnowledgeScope) {
  if (mode && mode !== "normal") return `已切换到${chatModeLabels[mode]}`;
  if (scope === "all") return "本条消息使用知识库";
  if (scope === "none") return "本条消息不使用知识库";
  return "";
}

export default function ChatPage() {
  const [token, setToken] = useState("");
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [active, setActive] = useState<Conversation | null>(null);
  const [draft, setDraft] = useState(createDraftConversation());
  const [messages, setMessages] = useState<Message[]>([]);
  const [query, setQuery] = useState("");
  const [runs, setRuns] = useState<Record<string, { runId: string }>>({});
  const [mode, setMode] = useState<ChatMode>("normal");
  const [modeOpen, setModeOpen] = useState(false);
  const [knowledgeScope, setKnowledgeScope] = useState<KnowledgeScope>("none");
  const [solutionLanguage, setSolutionLanguage] = useState<SolutionLanguage | null>(null);
  const [languageOpen, setLanguageOpen] = useState(false);
  const [selectedProblem, setSelectedProblem] = useState<ProblemSummary | null>(null);
  const [chatModels, setChatModels] = useState<ChatModelOption[]>([]);
  const [selectedChatModelId, setSelectedChatModelId] = useState("");
  const [attachmentIds, setAttachmentIds] = useState<string[]>([]);
  const [sessionFiles, setSessionFiles] = useState<SessionFile[]>([]);
  const [citations, setCitations] = useState<Citation[]>([]);
  const [citationLoading, setCitationLoading] = useState(false);
  const [retrievalStatus, setRetrievalStatus] = useState<RetrievalStatus>("not_requested");
  const [menuId, setMenuId] = useState<string | null>(null);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [nextBefore, setNextBefore] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(false);
  const [loadingOlder, setLoadingOlder] = useState(false);
  const [mentionQuery, setMentionQuery] = useState<string | null>(null);
  const activeConversationIdRef = useRef<string | null>(null);
  const readerRef = useRef<ReadableStreamDefaultReader<Uint8Array> | null>(null);
  const auth = useCallback(() => ({ Authorization: `Bearer ${token}` }), [token]);
  const running = Boolean(active && runs[active.id]);

  const loadMessagePage = useCallback(async (conversationId: string, before?: string): Promise<MessagePage> => {
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
      if (activeConversationIdRef.current === conversationId) setCitations(Array.isArray(data) ? data : data.items || []);
    } catch { /* citation loading is non-blocking */ } finally { setCitationLoading(false); }
  }, [auth]);

  const consumeReader = useCallback(async (conversationId: string, reader: ReadableStreamDefaultReader<Uint8Array>, initial = "") => {
    readerRef.current = reader;
    const decoder = new SseDecoder();
    let answer = initial;
    let status = "generating";
    let messageId: string | undefined;
    const update = () => {
      if (activeConversationIdRef.current !== conversationId) return;
      setMessages(items => items.map(item => item.id === messageId || (!item.id && item.role === "assistant") ? { ...item, id: messageId || item.id, content: answer, status } : item));
    };
    try {
      while (true) {
        const chunk = await reader.read();
        if (chunk.done) break;
        for (const { event, data: rawData } of decoder.push(chunk.value)) {
          const data = rawData as StreamPayload;
          messageId = data.message_id || messageId;
          if (event === "run.snapshot") {
            answer = data.content || answer;
            status = data.status || status;
            const runId = data.run_id;
            if (runId) setRuns(current => ({ ...current, [conversationId]: { runId } }));
          } else if (event === "retrieval.completed") setRetrievalStatus((data.status || "ok") as RetrievalStatus);
          else if (event === "message.delta") answer += data.content || data.delta || "";
          else if (event === "message.final") answer = data.content || answer;
          else if (event === "citations.validated" && activeConversationIdRef.current === conversationId) setCitations(data.items || []);
          else if (event === "run.interrupted") status = "cancelled";
          else if (event === "run.failed") { status = "failed"; answer = data.message || "生成失败"; }
          else if (event === "run.completed") status = "completed";
          update();
        }
      }
    } finally {
      readerRef.current = null;
      if (status !== "generating") setRuns(current => { const next = { ...current }; delete next[conversationId]; return next; });
      if (messageId) loadSources(conversationId, messageId);
    }
  }, [loadSources]);

  const consumeStream = useCallback(async (conversationId: string, runId: string, initial = "") => {
    const response = await apiFetch(`${API}/conversations/${conversationId}/runs/${runId}/stream`, { headers: auth() });
    const reader = response.body?.getReader();
    if (reader) await consumeReader(conversationId, reader, initial);
  }, [auth, consumeReader]);

  const reconnect = useCallback(async (conversationId: string) => {
    try {
      const response = await apiFetch(`${API}/conversations/${conversationId}/runs/active`, { headers: auth() });
      if (!response.ok) return;
      const data = await response.json();
      if (!data?.run_id) return;
      setRuns(current => ({ ...current, [conversationId]: { runId: data.run_id } }));
      await consumeStream(conversationId, data.run_id, data.content || "");
    } catch { /* best effort reconnect */ }
  }, [auth, consumeStream]);

  useEffect(() => {
    const currentToken = localStorage.getItem("codeatlas_access_token") || "";
    setToken(currentToken);
    if (!currentToken) return;
    Promise.all([
      apiFetch(`${API}/conversations`, { headers: { Authorization: `Bearer ${currentToken}` } }),
      apiFetch(`${API}/model-connections/available`, { headers: { Authorization: `Bearer ${currentToken}` } }),
    ]).then(async ([conversationResponse, modelsResponse]) => {
      const list = await conversationResponse.json();
      const models = await modelsResponse.json();
      setConversations(sortConversations(Array.isArray(list) ? list : []));
      setChatModels(Array.isArray(models) ? models : []);
    }).catch(error => reportError(error, "会话列表加载失败，请稍后重试"));
  }, []);

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
    activeConversationIdRef.current = active?.id || null;
    if (!active || !token) return;
    const conversationId = active.id;
    setSelectedChatModelId(active.selected_chat_model_id || chatModels.find(model => model.is_default)?.id || chatModels[0]?.id || "");
    setMessages([]); setHasMore(false); setNextBefore(null); setCitations([]); setRetrievalStatus("not_requested"); setSelectedProblem(null); setAttachmentIds([]); setSessionFiles([]);
    loadMessagePage(conversationId).then(data => {
      const items = sortMessages<Message>(data.items || []);
      if (activeConversationIdRef.current !== conversationId) return;
      setMessages(items);
      setHasMore(Boolean(data.has_more)); setNextBefore(data.next_before);
      const context = restoreConversationContext(items);
      setMode(context.mode); setKnowledgeScope(context.knowledgeScope); setSolutionLanguage(context.solutionLanguage);
      const latest = [...items].reverse().find(item => item.role === "assistant");
      loadSources(conversationId, latest?.id);
      reconnect(conversationId);
    }).catch(error => { if (activeConversationIdRef.current === conversationId) reportError(error, "历史消息加载失败，请稍后重试"); });
    apiFetch(`${API}/conversations/${conversationId}/attachments`, { headers: auth() }).then(response => response.json()).then(items => {
      if (activeConversationIdRef.current === conversationId && Array.isArray(items)) { setAttachmentIds(items.map((item: { id: string }) => item.id)); setSessionFiles(items); }
    }).catch(() => undefined);
  }, [active, token, chatModels, auth, loadMessagePage, loadSources, reconnect]);

  async function loadOlder() {
    if (!active || !nextBefore || loadingOlder) return;
    const conversationId = active.id;
    setLoadingOlder(true);
    try {
      const page = await loadMessagePage(conversationId, nextBefore);
      if (activeConversationIdRef.current !== conversationId) return;
      setMessages(current => mergeMessagePage(current, page.items || []));
      setHasMore(Boolean(page.has_more)); setNextBefore(page.next_before);
    } catch (error) { reportError(error, "较早消息加载失败"); }
    finally { setLoadingOlder(false); }
  }

  function createDraft() {
    setActive(null); setDraft(createDraftConversation()); setMessages([]); setMode("normal"); setKnowledgeScope("none"); setSolutionLanguage(null); setSelectedProblem(null); setSelectedChatModelId(chatModels.find(model => model.is_default)?.id || chatModels[0]?.id || ""); setCitations([]); setRetrievalStatus("not_requested"); setSessionFiles([]);
  }

  async function ensureConversation(text: string) {
    if (active) return active;
    const response = await apiFetch(`${API}/conversations`, { method: "POST", headers: { ...auth(), "Content-Type": "application/json" }, body: JSON.stringify({ title: deriveConversationTitle(text), mode, knowledge_scope: knowledgeScope }) });
    const conversation = await response.json() as Conversation;
    setConversations(items => sortConversations([conversation, ...items]));
    setActive(conversation);
    return conversation;
  }

  async function ensureAttachmentConversation() { return (await ensureConversation("临时文件")).id; }

  async function send(event: FormEvent) {
    event.preventDefault();
    const text = query.trim();
    if (!text || running) return;
    if (!selectedChatModelId) { reportError(new Error("请先在模型配置页验证一个聊天模型")); return; }
    if (mode === "acm_solution" && !solutionLanguage) { setLanguageOpen(true); return; }
    setQuery("");
    const conversation = await ensureConversation(text);
    await run(conversation, text);
  }

  async function run(conversation: Conversation, text: string, reuseLastUser = false, retryContext?: { mode?: ChatMode; knowledge_scope?: KnowledgeScope; solution_language?: SolutionLanguage | null; problem_id?: string | null }) {
    const runMode = retryContext?.mode || mode;
    const runScope = retryContext?.knowledge_scope || knowledgeScope;
    const runLanguage = retryContext?.solution_language === undefined ? solutionLanguage : retryContext.solution_language;
    const runProblemId = retryContext?.problem_id === undefined ? selectedProblem?.id || null : retryContext.problem_id;
    setRetrievalStatus(runScope === "all" ? "pending" : "not_requested");
    setCitations([]);
    const payload = { content: text, mode: runMode, knowledge_scope: runScope, solution_language: runLanguage, problem_id: runProblemId, chat_model_id: selectedChatModelId, attachment_ids: attachmentIds, reuse_last_user: reuseLastUser };
    setMessages(items => [...items, ...(reuseLastUser ? [] : [{ role: "user" as const, content: text, status: "completed", mode: runMode, knowledge_scope: runScope }]), { role: "assistant", content: "", status: "generating", mode: runMode, knowledge_scope: runScope }]);
    try {
      const response = await apiFetch(`${API}/conversations/${conversation.id}/messages/stream`, { method: "POST", headers: { ...auth(), "Content-Type": "application/json" }, body: JSON.stringify(payload) });
      const reader = response.body?.getReader();
      if (reader) await consumeReader(conversation.id, reader);
    } catch (error) {
      setMessages(items => { const next = [...items]; const index = next.map(item => item.role).lastIndexOf("assistant"); if (index >= 0 && next[index].status === "generating") next[index] = { ...next[index], status: "failed", content: "发送失败，请稍后重试" }; return next; });
      reportError(error, "发送失败，请稍后重试");
    }
  }

  async function retryMessage(message: Message, editedContent?: string) {
    if (!active || !message.id || running || !selectedChatModelId) return;
    const conversationId = active.id;
    try {
      const response = await apiFetch(`${API}/conversations/${conversationId}/messages/${message.id}/retry`, { method: "POST", headers: { ...auth(), "Content-Type": "application/json" }, body: JSON.stringify(editedContent ? { content: editedContent } : {}) });
      const context = await response.json();
      const page = await loadMessagePage(conversationId);
      if (activeConversationIdRef.current !== conversationId) return;
      setMessages(sortMessages(page.items || [])); setHasMore(Boolean(page.has_more)); setNextBefore(page.next_before);
      setMode(context.mode || "normal"); setKnowledgeScope(context.knowledge_scope || "none"); setSolutionLanguage(context.solution_language || null);
      setSelectedProblem(null);
      await run(active, context.content, true, context);
    } catch (error) { reportError(error, "重试消息失败，请稍后再试"); }
  }

  async function stop() {
    if (!active || !runs[active.id]) return;
    await apiFetch(`${API}/conversations/${active.id}/run/stop`, { method: "POST", headers: auth() }).catch(error => reportError(error, "停止生成失败，请稍后重试"));
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
          <div className="chat-controls"><label className="mode-select">模型<select aria-label="选择聊天模型" value={selectedChatModelId} disabled={running} onChange={event => setSelectedChatModelId(event.target.value)}><option value="">选择模型</option>{chatModels.map(model => <option key={model.id} value={model.id}>{model.connection_name || "连接"} / {model.name}</option>)}</select></label><ModeSelector mode={mode} open={modeOpen} disabled={running} onToggle={() => setModeOpen(value => !value)} onChange={next => { setMode(next); setModeOpen(false); if (next === "acm_solution") setLanguageOpen(true); }} /><KnowledgeScopeSelector scope={knowledgeScope} disabled={running} onChange={setKnowledgeScope} /></div>
        </header>
        <div className="messages">
          {hasMore && <div className="older-messages"><button className="icon-button" disabled={loadingOlder} onClick={loadOlder}>{loadingOlder ? "加载中…" : "加载更早消息"}</button></div>}
          {!messages.length && <div className="msg"><div className="label">CODEATLAS / READY</div><p>从一个算法问题开始。你可以描述题意、贴出代码，或者告诉我哪里卡住了。</p></div>}
          {messages.map((message, index) => {
            const previous = messages[index - 1];
            const changed = index > 0 && (message.mode !== previous?.mode || message.knowledge_scope !== previous?.knowledge_scope);
            return <div key={message.id || index}>{changed && <div className="chat-state-divider">{stateLabel(message.mode, message.knowledge_scope)}</div>}<article className={`msg ${message.role}`}><div className="msg-heading"><div className="label">{message.role === "user" ? "你" : "CODEATLAS"}</div>{message.status === "generating" && <span className="msg-metrics">正在生成…</span>}</div>{message.content ? message.role === "assistant" ? <MessageContent content={message.content} /> : <p className="message-plain">{message.content}</p> : <p className="message-plain">正在生成…</p>}<div className="msg-actions"><CopyButton text={message.content} />{message.id && !running && selectedChatModelId && message.role === "user" && <button className="icon-button" onClick={() => { const edited = window.prompt("修改消息并重新生成；此消息之后的对话会被清除", message.content); if (edited?.trim()) retryMessage(message, edited.trim()); }}>编辑并重试</button>}{message.id && !running && selectedChatModelId && message.role === "assistant" && index === messages.length - 1 && <button className="icon-button" onClick={() => retryMessage(message)}>重新生成</button>}</div></article></div>;
          })}
        </div>
        <form className="composer" onSubmit={send}><div className="composer-input"><textarea value={query} onChange={event => { setQuery(event.target.value); const at = event.target.value.lastIndexOf("@"); setMentionQuery(at >= 0 ? event.target.value.slice(at + 1) : null); }} placeholder="向 CodeAtlas 提问，输入 @ 召回题库内容" disabled={running} />{mentionQuery !== null && <ProblemMentionPicker token={token} query={mentionQuery} onSelect={problem => { setSelectedProblem(problem); setMentionQuery(null); }} />}</div><div className="composer-foot"><AttachmentPicker conversationId={active?.id || ""} ensureConversation={ensureAttachmentConversation} token={token} onChange={setAttachmentIds} onItems={setSessionFiles} disabled={running} /><button type="button" disabled={running} onClick={() => setModeOpen(true)}>⌘ {chatModeLabels[mode]}</button>{running ? <button type="button" className="send" onClick={stop}>停止</button> : <button className="send" disabled={!selectedChatModelId}>发送 ↑</button>}</div></form>
      </section>
      <CitationPanel citations={citations} sessionFiles={sessionFiles} loading={citationLoading} retrievalStatus={retrievalStatus} />
    </main>
    {languageOpen && <LanguageDialog onClose={() => setLanguageOpen(false)} onSelect={language => { setSolutionLanguage(language); setLanguageOpen(false); }} />}
  </>;
}
