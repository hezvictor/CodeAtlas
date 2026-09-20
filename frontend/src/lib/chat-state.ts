export type KnowledgeScope = "none" | "all" | "groups";

export type ConversationLike = {
  id: string;
  title: string;
  updated_at: string;
  pinned?: boolean;
};

export type DraftConversation = {
  id: null;
  title: "新对话";
  updated_at: string;
  pinned: false;
};

export function createDraftConversation(): DraftConversation {
  return { id: null, title: "新对话", updated_at: new Date().toISOString(), pinned: false };
}

export function deriveConversationTitle(question: string): string {
  const normalized = question.trim().replace(/\s+/g, " ");
  return normalized.length > 24 ? `${normalized.slice(0, 24)}…` : normalized;
}

export function buildKnowledgePayload(scope: KnowledgeScope, groupId: string) {
  return {
    knowledge_scope: scope,
    knowledge_group_ids: scope === "groups" && groupId ? [groupId] : [],
  };
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

export function sortConversations<T extends ConversationLike>(items: T[]): T[] {
  return [...items].sort((a, b) => {
    if (Boolean(a.pinned) !== Boolean(b.pinned)) return a.pinned ? -1 : 1;
    return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime();
  });
}
