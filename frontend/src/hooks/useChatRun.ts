"use client";

import { useCallback, useRef, useState } from "react";
import { apiFetch } from "../lib/errors";
import { emptyRunView, reduceRunFrame, RunStreamGate, type RunView, type StreamPayload } from "../lib/chat-run-state";
import { SseDecoder } from "../lib/sse";

const API = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api/v1";
const ACTIVE_STATUSES = new Set(["generating", "queued", "running"]);

type Options = {
  auth: () => Record<string, string>;
  isCurrent: (conversationId: string) => boolean;
  onFrame: (conversationId: string, view: RunView, event: string) => void;
  onFinished: (conversationId: string, messageId?: string) => void;
};

export function useChatRun(options: Options) {
  const [views, setViews] = useState<Record<string, RunView>>({});
  const viewsRef = useRef<Record<string, RunView>>({});
  const readerRef = useRef<ReadableStreamDefaultReader<Uint8Array> | null>(null);
  const readerConversationRef = useRef<string | null>(null);
  const gateRef = useRef(new RunStreamGate());
  const lastRunIdsRef = useRef<Record<string, string>>({});
  const optionsRef = useRef(options);
  optionsRef.current = options;

  const updateView = useCallback((conversationId: string, view: RunView) => {
    viewsRef.current = { ...viewsRef.current, [conversationId]: view };
    setViews(viewsRef.current);
  }, []);

  const cancelReader = useCallback(() => {
    const reader = readerRef.current;
    const conversationId = readerConversationRef.current;
    if (conversationId) gateRef.current.invalidate(conversationId);
    readerRef.current = null;
    readerConversationRef.current = null;
    reader?.cancel().catch(() => undefined);
  }, []);

  const resetView = useCallback((conversationId: string) => {
    gateRef.current.invalidate(conversationId);
    updateView(conversationId, emptyRunView());
  }, [updateView]);

  const startPending = useCallback((conversationId: string) => {
    gateRef.current.invalidate(conversationId);
    updateView(conversationId, {
      ...emptyRunView(), status: "queued", retrievalStatus: "pending",
    });
  }, [updateView]);

  const failPending = useCallback((conversationId: string) => {
    gateRef.current.invalidate(conversationId);
    updateView(conversationId, emptyRunView());
  }, [updateView]);

  const consumeReader = useCallback(async (
    conversationId: string, reader: ReadableStreamDefaultReader<Uint8Array>, initial = "",
  ) => {
    const epoch = gateRef.current.begin(conversationId);
    readerRef.current = reader;
    readerConversationRef.current = conversationId;
    const decoder = new SseDecoder();
    let view = viewsRef.current[conversationId] || emptyRunView();
    view = { ...view, answer: initial || view.answer, disconnected: false };
    updateView(conversationId, view);
    try {
      while (true) {
        const chunk = await reader.read();
        if (!gateRef.current.isCurrent(conversationId, epoch)) break;
        if (chunk.done) break;
        for (const { event, data } of decoder.push(chunk.value)) {
          if (!gateRef.current.isCurrent(conversationId, epoch)) break;
          view = reduceRunFrame(view, event, data as StreamPayload);
          if (view.runId) lastRunIdsRef.current[conversationId] = view.runId;
          updateView(conversationId, view);
          if (optionsRef.current.isCurrent(conversationId)) {
            optionsRef.current.onFrame(conversationId, view, event);
          }
        }
      }
    } catch {
      if (gateRef.current.isCurrent(conversationId, epoch)) {
        view = { ...view, disconnected: true };
        updateView(conversationId, view);
      }
    } finally {
      if (gateRef.current.isCurrent(conversationId, epoch)) {
        if (ACTIVE_STATUSES.has(view.status)) {
          view = { ...view, disconnected: true };
          updateView(conversationId, view);
        }
        if (view.messageId) optionsRef.current.onFinished(conversationId, view.messageId);
      }
      if (readerRef.current === reader) {
        readerRef.current = null;
        readerConversationRef.current = null;
      }
    }
  }, [updateView]);

  const consumeStream = useCallback(async (conversationId: string, runId: string, initial = "") => {
    const response = await apiFetch(`${API}/conversations/${conversationId}/runs/${runId}/stream`, {
      headers: optionsRef.current.auth(),
    });
    const reader = response.body?.getReader();
    if (reader) await consumeReader(conversationId, reader, initial);
  }, [consumeReader]);

  const reconnect = useCallback(async (conversationId: string) => {
    try {
      const response = await apiFetch(`${API}/conversations/${conversationId}/runs/active`, {
        headers: optionsRef.current.auth(),
      });
      const data = await response.json() as StreamPayload;
      const runId = data.run_id || lastRunIdsRef.current[conversationId];
      if (!runId) return;
      updateView(conversationId, {
        ...(viewsRef.current[conversationId] || emptyRunView()),
        runId, status: data.status || "running", answer: data.content || "", disconnected: false,
      });
      await consumeStream(conversationId, runId, data.content || "");
    } catch {
      const current = viewsRef.current[conversationId] || emptyRunView();
      updateView(conversationId, { ...current, disconnected: true });
    }
  }, [consumeStream, updateView]);

  const stop = useCallback(async (conversationId: string) => {
    await apiFetch(`${API}/conversations/${conversationId}/run/stop`, {
      method: "POST", headers: optionsRef.current.auth(),
    });
  }, []);

  const resume = useCallback(async (conversationId: string) => {
    gateRef.current.invalidate(conversationId);
    const response = await apiFetch(`${API}/conversations/${conversationId}/run/resume`, {
      method: "POST", headers: optionsRef.current.auth(),
    });
    const data = await response.json() as StreamPayload;
    if (!data.run_id) throw new Error("恢复运行缺少运行 ID");
    lastRunIdsRef.current[conversationId] = data.run_id;
    updateView(conversationId, {
      ...emptyRunView(), runId: data.run_id, status: data.status || "queued", retrievalStatus: "pending",
    });
    await consumeStream(conversationId, data.run_id);
  }, [consumeStream, updateView]);

  return { views, cancelReader, resetView, startPending, failPending, consumeReader, reconnect, stop, resume };
}
