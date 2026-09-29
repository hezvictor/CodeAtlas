export type AgentStep = { id: string; title: string; state: "running" | "retrying" | "ok" | "no_hit" | "failed"; count?: number; sequence: number };
type AgentEvent = { step_id?: string; tool?: string; status?: string; count?: number; sequence?: number; [key: string]: unknown };
const titles: Record<string, string> = { search_knowledge: "补充检索知识库", read_knowledge_context: "补充读取相关段落" };

export function reduceAgentEvent(steps: AgentStep[], name: string, data: AgentEvent): AgentStep[] {
  if (["run.completed", "run.failed", "run.interrupted", "run.waiting"].includes(name)) return steps.map(step => step.state === "running" || step.state === "retrying" ? { ...step, state: "failed" } : step);
  if (!data.step_id || !/^(tool|model|retrieval)\.(started|completed|retrying)$/.test(name)) return steps;
  const prior = steps.find(step => step.id === data.step_id);
  const sequence = data.sequence || 0;
  if (prior && prior.sequence >= sequence) return steps;
  const title = name.startsWith("retrieval.") ? "检索长期知识库" : name.startsWith("model.") ? "整理回答" : titles[data.tool || ""] || "调用知识库工具";
  const state = name.endsWith("started") ? "running" : name.endsWith("retrying") ? "retrying" : data.status === "no_hit" ? "no_hit" : data.status === "ok" ? "ok" : "failed";
  const step: AgentStep = { id: data.step_id, title, state, sequence, count: data.count };
  const settled = name === "model.started" ? steps.map(item => item.id.startsWith("model-") && (item.state === "running" || item.state === "retrying") ? { ...item, state: "failed" as const } : item) : steps;
  return prior ? settled.map(item => item.id === step.id ? step : item) : [...settled, step];
}

export type CapabilityModel = { status: string; capabilities?: Record<string, string> };
export function modelCanUseTools(model: CapabilityModel) {
  return model.status === "verified" && ["chat", "tool_calling", "tool_result"].every(key => model.capabilities?.[key] === "verified");
}
export function capabilityLabel(model: CapabilityModel) {
  if (modelCanUseTools(model)) return "可调用工具 · 已验证回传";
  return ({ unsupported: "当前连接不支持工具", incomplete: "检测未完成，请重试", failed: "能力验证未通过", verified: "需要重新检测工具能力" } as Record<string, string>)[model.status] || "工具能力待检测";
}

export function runErrorMessage(code?: string) {
  return ({ CONTEXT_CAPACITY_UNKNOWN: "请在模型配置页填写可信的上下文容量，再使用临时文件。", CONTEXT_CAPACITY_EXCEEDED: "上下文超过模型容量，请选择更大容量模型或减少会话资料。全文未被截断。", TEMPORARY_CONTEXT_LOST: "临时资料缓存已失效，请重新上传所需文件，再恢复同一次运行。", TEMPORARY_QUOTE_LIMIT: "回答引用临时原文超过保存限制，请调整问题后重试。", TEMPORARY_CONTENT_PERSISTENCE: "回答包含临时原文，已拦截保存，请调整问题后重试。", TEMPORARY_METADATA_PERSISTENCE: "回答含临时文件元数据，已拦截保存。", RUN_BUDGET_EXCEEDED: "本次运行达到次数或时间预算，请调整问题后重试。", CONTEXT_WAIT_EXPIRED: "等待补充临时资料已超过7天，本次运行结束。" } as Record<string, string>)[code || ""] || "生成失败，请检查模型连接后重试。";
}
