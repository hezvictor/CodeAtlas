export type KnowledgeScope = "none" | "all";

export type ConversationLike = {
  id: string;
  title: string;
  updated_at: string;
  pinned?: boolean;
  knowledge_scope?: KnowledgeScope;
};

export type DraftConversation = {
  id: null;
  title: "新对话";
  updated_at: string;
  pinned: false;
  knowledge_scope: "none";
};

export function createDraftConversation(): DraftConversation {
  return { id: null, title: "新对话", updated_at: new Date().toISOString(), pinned: false, knowledge_scope: "none" };
}

export function deriveConversationTitle(question: string): string {
  const normalized = question.trim().replace(/\s+/g, " ");
  return normalized.length > 24 ? `${normalized.slice(0, 24)}…` : normalized;
}

export function buildKnowledgePayload(scope: KnowledgeScope) {
  return { knowledge_scope: scope };
}

export function parseChatLaunch(search: string): { problemId: string | null; mode: "normal" | "acm_analysis" | "acm_solution" } {
  const params = new URLSearchParams(search);
  const problemId = params.get("problem_id");
  const requested = params.get("mode");
  const mode = problemId && (requested === "acm_analysis" || requested === "acm_solution") ? requested : "normal";
  return { problemId, mode };
}

export type MessageLike = { role: "user" | "assistant"; created_at?: string; };

export function sortMessages<T extends MessageLike>(items: T[]): T[] {
  return [...items].sort((a, b) => {
    const aTime = a.created_at ? Date.parse(a.created_at) : Number.NaN;
    const bTime = b.created_at ? Date.parse(b.created_at) : Number.NaN;
    if (Number.isNaN(aTime) || Number.isNaN(bTime)) return 0;
    if (aTime !== bTime) return aTime - bTime;
    if (a.role !== b.role) return a.role === "user" ? -1 : 1;
    return 0;
  });
}

export function mergeMessagePage<T extends MessageLike & { id?: string }>(current: T[], older: T[]): T[] {
  const ids = new Set(current.map(item => item.id).filter(Boolean));
  return sortMessages([...older.filter(item => !item.id || !ids.has(item.id)), ...current]);
}

export function sortConversations<T extends ConversationLike>(items: T[]): T[] {
  return [...items].sort((a, b) => {
    if (Boolean(a.pinned) !== Boolean(b.pinned)) return a.pinned ? -1 : 1;
    return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime();
  });
}
