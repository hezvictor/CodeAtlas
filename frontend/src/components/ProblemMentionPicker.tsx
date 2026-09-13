import { forwardRef, useEffect, useImperativeHandle, useRef, useState } from "react";
import { API, apiFetch } from "../lib/auth";
import type { ProblemSummary } from "./ProblemCard";

export type ProblemMentionPickerHandle = { handleKey: (key: string) => boolean };

const ProblemMentionPicker = forwardRef<ProblemMentionPickerHandle, { token: string; query: string; onSelect: (problem: ProblemSummary) => void }>(({ token, query, onSelect }, ref) => {
  const [items, setItems] = useState<ProblemSummary[]>([]);
  const [activeIndex, setActiveIndex] = useState(0);
  const activeButton = useRef<HTMLButtonElement>(null);
  useEffect(() => { if (!token) return; const params = new URLSearchParams({ page: "1", page_size: "8" }); if (query) params.set("query", query); const timer = window.setTimeout(() => apiFetch(`${API}/problems?${params}`, { headers: { Authorization: `Bearer ${token}` } }).then((response) => response.json()).then((data) => setItems(data.items || [])).catch(() => setItems([])), 120); return () => window.clearTimeout(timer); }, [token, query]);
  useEffect(() => { setActiveIndex(0); }, [query, items.length]);
  useEffect(() => { activeButton.current?.scrollIntoView({ block: "nearest" }); }, [activeIndex]);
  useImperativeHandle(ref, () => ({
    handleKey(key) {
      if (!items.length) return false;
      if (key === "ArrowDown") { setActiveIndex((index) => (index + 1) % items.length); return true; }
      if (key === "ArrowUp") { setActiveIndex((index) => (index - 1 + items.length) % items.length); return true; }
      if (key === "Enter") { onSelect(items[activeIndex]); return true; }
      return false;
    },
  }), [activeIndex, items, onSelect]);
  if (!items.length) return <div className="mention-menu empty">没有找到题目</div>;
  return <div className="mention-menu" role="listbox" aria-label="题目候选列表">{items.map((problem, index) => <button type="button" role="option" aria-selected={index === activeIndex} className={index === activeIndex ? "active" : ""} key={problem.id} ref={index === activeIndex ? activeButton : null} onMouseEnter={() => setActiveIndex(index)} onClick={() => onSelect(problem)}><strong>{problem.title}</strong><small>{problem.difficulty} · {problem.tags.join("、")}</small></button>)}</div>;
});

ProblemMentionPicker.displayName = "ProblemMentionPicker";
export default ProblemMentionPicker;
