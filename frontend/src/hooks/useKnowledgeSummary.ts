"use client";
import { useCallback, useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import { API, apiFetch, getToken } from "../lib/auth";
import { KNOWLEDGE_CHANGED } from "../lib/knowledge";

type Summary = { processing: number; failed: number; waiting: number; completed: number };
export default function useKnowledgeSummary() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const path = usePathname();
  const load = useCallback(async () => {
    if (!getToken()) { setSummary(null); return; }
    const response = await apiFetch(`${API}/knowledge/documents/summary`, { headers: { Authorization: `Bearer ${getToken()}` } });
    if (response.ok) setSummary(await response.json());
  }, []);
  useEffect(() => {
    const refresh = () => { if (document.visibilityState === "visible") load().catch(() => undefined); };
    refresh(); const timer = window.setInterval(refresh, 10000);
    window.addEventListener("focus", refresh); window.addEventListener(KNOWLEDGE_CHANGED, refresh); document.addEventListener("visibilitychange", refresh);
    return () => { window.clearInterval(timer); window.removeEventListener("focus", refresh); window.removeEventListener(KNOWLEDGE_CHANGED, refresh); document.removeEventListener("visibilitychange", refresh); };
  }, [load, path]);
  return summary;
}
