export type ChatMode = "normal" | "acm_analysis" | "acm_solution";
export type SolutionLanguage = "cpp" | "java" | "python";

export type ConversationContext = {
  mode: ChatMode;
  problemId: string | null;
  solutionLanguage: SolutionLanguage | null;
  citations: unknown[];
  attachmentIds: string[];
  before: string | null;
  hasMore: boolean;
};

type ContextMessage = {
  problem_id?: string | null;
  mode?: ChatMode;
  solution_language?: SolutionLanguage | null;
};

export function emptyConversationContext(): ConversationContext {
  return {
    mode: "normal",
    problemId: null,
    solutionLanguage: null,
    citations: [],
    attachmentIds: [],
    before: null,
    hasMore: false,
  };
}

export function restoreConversationContext(messages: ContextMessage[]): ConversationContext {
  const context = emptyConversationContext();
  const message = [...messages].reverse().find((item) => item.problem_id);
  if (!message) return context;
  context.problemId = message.problem_id || null;
  context.mode = message.mode || "normal";
  context.solutionLanguage = message.solution_language || null;
  return context;
}
