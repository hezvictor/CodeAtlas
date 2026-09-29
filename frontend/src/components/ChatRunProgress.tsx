"use client";

import { useState } from "react";
import type { AgentStep } from "../lib/agent-events";

const labels = { running: "进行中…", retrying: "正在重试…", ok: "已完成", no_hit: "未找到相关资料", failed: "未完成" };

export default function ChatRunProgress({ steps }: { steps: AgentStep[] }) {
  const [expanded, setExpanded] = useState(true);
  if (!steps.length) return null;
  const active = [...steps].reverse().find(step => step.state === "running" || step.state === "retrying");
  return <details className="agent-progress" open={expanded} onToggle={event => setExpanded(event.currentTarget.open)}><summary aria-live="polite">{active ? `${active.title} · ${labels[active.state]}` : `处理步骤 · ${steps.length} 项`}</summary><ol>{steps.map(step => <li key={step.id}><span>{step.title}</span><small>{labels[step.state]}{step.count !== undefined ? ` · ${step.count} 条资料` : ""}</small></li>)}</ol></details>;
}
