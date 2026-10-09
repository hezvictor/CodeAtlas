import type { Citation, RetrievalStatus } from "../components/CitationPanel";
import { reduceAgentEvent, runErrorMessage, type AgentStep } from "./agent-events";

export type StreamPayload = {
  sequence?: number;
  step_id?: string;
  tool?: string;
  count?: number;
  code?: string;
  message_id?: string;
  run_id?: string;
  content?: string;
  status?: string;
  items?: Citation[];
  message?: string;
};

export type RunView = {
  runId: string;
  status: string;
  answer: string;
  messageId?: string;
  snapshotSequence: number;
  steps: AgentStep[];
  retrievalStatus: RetrievalStatus;
  citations: Citation[];
  disconnected: boolean;
};

export function emptyRunView(): RunView {
  return {
    runId: "", status: "", answer: "", snapshotSequence: 0,
    steps: [], retrievalStatus: "not_requested", citations: [], disconnected: false,
  };
}

export class RunStreamGate {
  private epochs = new Map<string, number>();

  begin(conversationId: string): number {
    const epoch = (this.epochs.get(conversationId) || 0) + 1;
    this.epochs.set(conversationId, epoch);
    return epoch;
  }

  invalidate(conversationId: string): void {
    this.epochs.set(conversationId, (this.epochs.get(conversationId) || 0) + 1);
  }

  isCurrent(conversationId: string, epoch: number): boolean {
    return this.epochs.get(conversationId) === epoch;
  }
}

export function updateAssistantMessage<T extends {
  id?: string; role: "user" | "assistant"; content: string; status?: string;
}>(messages: T[], view: RunView): T[] {
  return messages.map(item => {
    if (item.role !== "assistant" || (item.id && item.id !== view.messageId)) return item;
    return { ...item, ...(view.messageId ? { id: view.messageId } : {}),
      content: view.answer, status: view.status };
  });
}

export function reduceRunFrame(state: RunView, event: string, data: StreamPayload): RunView {
  if (event.startsWith("run.") && event !== "run.snapshot" &&
      data.sequence !== undefined && data.sequence <= state.snapshotSequence) return state;

  const next: RunView = {
    ...state,
    messageId: data.message_id || state.messageId,
    steps: reduceAgentEvent(state.steps, event, data),
  };
  if (event === "run.snapshot") {
    next.snapshotSequence = data.sequence || 0;
    next.runId = data.run_id || state.runId;
    next.status = data.status || state.status;
    next.answer = data.content || state.answer;
    if (next.status === "waiting_context" && data.code) next.answer = runErrorMessage(data.code);
  } else if (event === "run.started") {
    next.status = "running";
  } else if (event === "retrieval.completed") {
    next.retrievalStatus = (data.status || "ok") as RetrievalStatus;
  } else if (event === "message.final") {
    next.answer = data.content || state.answer;
  } else if (event === "citations.validated") {
    next.citations = data.items || [];
  } else if (event === "run.interrupted") {
    next.status = "cancelled";
  } else if (event === "run.waiting") {
    next.status = "waiting_context";
    next.answer = runErrorMessage(data.code);
  } else if (event === "run.failed") {
    next.status = "failed";
    next.answer = data.message || runErrorMessage(data.code);
  } else if (event === "run.completed") {
    next.status = "completed";
  }
  return next;
}
