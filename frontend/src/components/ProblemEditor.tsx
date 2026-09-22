"use client";

import { FormEvent, useEffect, useState } from "react";
import { API, apiFetch, getToken } from "../lib/auth";
import { normalizeProblemForm, ProblemFormValues } from "../lib/problem-form";
import type { ProblemSummary } from "./ProblemCard";

export type ProblemDetail = ProblemSummary & {
  statement: string;
  input_description: string;
  output_description: string;
  examples: { input: string; output: string }[];
  constraints: string;
  created_at: string;
  updated_at: string;
};

type Props = { problem: ProblemDetail | ProblemSummary | null; onSaved: () => void; onClose: () => void };

const emptyForm: ProblemFormValues = { title: "", difficulty: "入门", tags: "", statement: "", input_description: "", output_description: "", examples: [{ input: "", output: "" }], constraints: "", supported_languages: ["cpp", "java", "python"] };

function toForm(problem: Props["problem"]): ProblemFormValues {
  if (!problem || !("statement" in problem)) return { ...emptyForm, examples: [{ input: "", output: "" }], supported_languages: [...emptyForm.supported_languages] };
  return { title: problem.title, difficulty: problem.difficulty, tags: problem.tags.join(", "), statement: problem.statement, input_description: problem.input_description, output_description: problem.output_description, examples: problem.examples.length ? problem.examples : [{ input: "", output: "" }], constraints: problem.constraints, supported_languages: problem.supported_languages };
}

export default function ProblemEditor({ problem, onSaved, onClose }: Props) {
  const [form, setForm] = useState<ProblemFormValues>(() => toForm(problem));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const isEditing = Boolean(problem);

  useEffect(() => { setForm(toForm(problem)); setError(""); }, [problem]);
  function update(field: keyof ProblemFormValues, value: string) { setForm((current) => ({ ...current, [field]: value })); }
  function updateExample(field: "input" | "output", value: string) { setForm((current) => ({ ...current, examples: [{ ...current.examples[0], [field]: value }] })); }
  function toggleLanguage(language: string) { setForm((current) => ({ ...current, supported_languages: current.supported_languages.includes(language) ? current.supported_languages.filter((item) => item !== language) : [...current.supported_languages, language] })); }
  async function submit(event: FormEvent) {
    event.preventDefault(); setSaving(true); setError("");
    try {
      const payload = normalizeProblemForm(form);
      const response = await apiFetch(`${API}/problems${problem ? `/${problem.id}` : ""}`, { method: problem ? "PATCH" : "POST", headers: { Authorization: `Bearer ${getToken()}`, "Content-Type": "application/json" }, body: JSON.stringify(payload) });
      if (!response.ok) throw new Error(problem ? "题目修改失败" : "题目创建失败");
      onSaved();
    } catch (reason) { setError(reason instanceof Error ? reason.message : "保存失败"); } finally { setSaving(false); }
  }
  return (
    <div className="drawer-backdrop" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <aside className="problem-editor" aria-label={isEditing ? "编辑题目" : "新建题目"}>
        <div className="drawer-heading"><div><span className="eyebrow">{isEditing ? "EDIT PROBLEM" : "NEW PROBLEM"}</span><h2>{isEditing ? "编辑题目" : "新建题目"}</h2></div><button className="dialog-close" type="button" aria-label="关闭" onClick={onClose}>×</button></div>
        {problem && <div className="editor-id">题目 ID <code>{problem.id}</code></div>}
        <form onSubmit={submit} className="problem-form">
          <label>标题<input value={form.title} onChange={(event) => update("title", event.target.value)} required /></label>
          <div className="form-grid-two"><label>难度<select value={form.difficulty} onChange={(event) => update("difficulty", event.target.value)}><option>入门</option><option>简单</option><option>中等</option><option>困难</option></select></label><label>标签<span className="field-hint">用逗号分隔</span><input value={form.tags} onChange={(event) => update("tags", event.target.value)} placeholder="数组, 模拟" /></label></div>
          <label>题目描述<textarea value={form.statement} onChange={(event) => update("statement", event.target.value)} required /></label>
          <label>输入描述<textarea value={form.input_description} onChange={(event) => update("input_description", event.target.value)} required /></label>
          <label>输出描述<textarea value={form.output_description} onChange={(event) => update("output_description", event.target.value)} required /></label>
          <div className="form-grid-two"><label>样例输入<textarea value={form.examples[0].input} onChange={(event) => updateExample("input", event.target.value)} /></label><label>样例输出<textarea value={form.examples[0].output} onChange={(event) => updateExample("output", event.target.value)} /></label></div>
          <label>约束条件<textarea value={form.constraints} onChange={(event) => update("constraints", event.target.value)} required /></label>
          <fieldset className="language-field"><legend>支持语言</legend><div className="language-checks">{["cpp", "java", "python"].map((language) => <label key={language}><input type="checkbox" checked={form.supported_languages.includes(language)} onChange={() => toggleLanguage(language)} />{language}</label>)}</div></fieldset>
          {error && <p className="form-error">{error}</p>}
          <div className="drawer-actions"><button className="pill" type="button" onClick={onClose}>取消</button><button className="pill fill" type="submit" disabled={saving}>{saving ? "保存中…" : "保存题目"}</button></div>
        </form>
      </aside>
    </div>
  );
}
