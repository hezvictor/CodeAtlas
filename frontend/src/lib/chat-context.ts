export type ChatMode = "normal" | "acm_analysis" | "acm_solution";
export type SolutionLanguage = "cpp" | "java" | "python";

export type ConversationContext = {
  mode: ChatMode;
  problemId: string | null;
  solutionLanguage: SolutionLanguage | null;
  citations: unknown[];
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
    before: null,
    hasMore: false,
  };
}

export function restoreConversationContext(messages: ContextMessage[]): ConversationContext {
  const context = emptyConversationContext();
  const latest = [...messages].reverse()[0];
  if (!latest) return context;
  const problem = [...messages].reverse().find((item) => item.problem_id);
  context.problemId = problem?.problem_id || null;
  context.mode = latest.mode || "normal";
  context.solutionLanguage = latest.solution_language || null;
  return context;
}
