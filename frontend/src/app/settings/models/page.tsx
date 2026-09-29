"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import Navbar from "../../../components/Navbar";
import { API, apiFetch, getToken } from "../../../lib/auth";
import { filterModels } from "./model-list";
import { capabilityLabel, modelCanUseTools } from "../../../lib/agent-events";

type Connection = { id: string; name: string; base_url: string; status: string; last_error?: string | null };
type Model = { id: string; connection_id: string; name: string; source: string; status: string; capabilities?: Record<string, string>; context_window_tokens?: number | null; verification_error?: string | null; is_default?: boolean };
type Embedding = { model_name: string; status: string; verification_error?: string | null; configured: boolean; source: string };
type Reranker = { base_url?: string | null; model_name: string; status: string; verification_error?: string | null; configured: boolean; source: string };

async function responseJson<T>(response: Response): Promise<T> {
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.message || body.detail || "请求失败");
  return body as T;
}

export default function ModelSettingsPage() {
  const [token, setToken] = useState("");
  const [connections, setConnections] = useState<Connection[]>([]);
  const [models, setModels] = useState<Model[]>([]);
  const [embedding, setEmbedding] = useState<Embedding | null>(null);
  const [reranker, setReranker] = useState<Reranker | null>(null);
  const [rerankerBaseUrl, setRerankerBaseUrl] = useState("");
  const [rerankerKey, setRerankerKey] = useState("");
  const [rerankerModel, setRerankerModel] = useState("");
  const [name, setName] = useState("");
  const [baseUrl, setBaseUrl] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [modelNames, setModelNames] = useState<Record<string, string>>({});
  const [modelListOpen, setModelListOpen] = useState<Record<string, boolean>>({});
  const [modelSearches, setModelSearches] = useState<Record<string, string>>({});
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [testingModel, setTestingModel] = useState<string | null>(null);
  const [capacities, setCapacities] = useState<Record<string, string>>({});
  const headers = () => ({ Authorization: `Bearer ${token}`, "Content-Type": "application/json" });

  const load = useCallback(async () => {
    const requestHeaders = { Authorization: `Bearer ${getToken()}`, "Content-Type": "application/json" };
    const [connectionsResponse, embeddingResponse, rerankerResponse] = await Promise.all([
      apiFetch(`${API}/model-connections`, { headers: requestHeaders }),
      apiFetch(`${API}/model-connections/embedding-config`, { headers: requestHeaders }),
      apiFetch(`${API}/model-connections/reranker-config`, { headers: requestHeaders }),
    ]);
    const connectionRows = await responseJson<Connection[]>(connectionsResponse);
    const modelRows = await Promise.all(connectionRows.map(async connection => responseJson<Model[]>(
      await apiFetch(`${API}/model-connections/${connection.id}/models`, { headers: requestHeaders }),
    )));
    setConnections(connectionRows);
    setModels(modelRows.flat());
    setEmbedding(await responseJson<Embedding>(embeddingResponse));
    const rerankerConfig = await responseJson<Reranker>(rerankerResponse);
    setReranker(rerankerConfig); setRerankerBaseUrl(rerankerConfig.base_url || ""); setRerankerModel(rerankerConfig.model_name || "");
  }, []);

  useEffect(() => {
    const value = getToken();
    setToken(value);
    if (value) load().catch(() => setError("模型配置加载失败"));
  }, [load]);

  function resetConnectionForm() { setEditingId(null); setName(""); setBaseUrl(""); setApiKey(""); }

  async function saveConnection(event: FormEvent) {
    event.preventDefault(); setError(""); setMessage("");
    try {
      const payload: Record<string, string> = { name, base_url: baseUrl };
      if (apiKey) payload.api_key = apiKey;
      if (!editingId && !apiKey) throw new Error("请输入 API Key");
      const response = await apiFetch(editingId ? `${API}/model-connections/${editingId}` : `${API}/model-connections`, { method: editingId ? "PATCH" : "POST", headers: headers(), body: JSON.stringify(payload) });
      await responseJson<Connection>(response);
      setMessage(editingId ? "连接已更新，模型需要重新验证" : "连接已保存");
      resetConnectionForm(); await load();
    } catch (caught) { setError(caught instanceof Error ? caught.message : "连接保存失败"); }
  }

  function editConnection(connection: Connection) { setEditingId(connection.id); setName(connection.name); setBaseUrl(connection.base_url); setApiKey(""); setError(""); setMessage(""); }

  async function deleteConnection(connection: Connection) {
    if (!window.confirm(`删除连接“${connection.name}”及其模型配置吗？`)) return;
    try {
      await responseJson<void>(await apiFetch(`${API}/model-connections/${connection.id}`, { method: "DELETE", headers: headers() }));
      if (editingId === connection.id) resetConnectionForm();
      setMessage("连接已删除"); await load();
    } catch (caught) { setError(caught instanceof Error ? caught.message : "删除连接失败"); }
  }

  async function discover(connectionId: string) {
    try {
      const data = await responseJson<{ error?: string | null }>(await apiFetch(`${API}/model-connections/${connectionId}/discover-models`, { method: "POST", headers: headers() }));
      setMessage(data.error || "模型列表已更新");
      setModelListOpen(current => ({ ...current, [connectionId]: false }));
      setModelSearches(current => ({ ...current, [connectionId]: "" }));
      await load();
    } catch (caught) { setError(caught instanceof Error ? caught.message : "模型发现失败"); }
  }

  async function addModel(connectionId: string) {
    const value = (modelNames[connectionId] || "").trim(); if (!value) return;
    try {
      await responseJson<Model>(await apiFetch(`${API}/model-connections/${connectionId}/models`, { method: "POST", headers: headers(), body: JSON.stringify({ name: value }) }));
      setModelNames(current => ({ ...current, [connectionId]: "" })); await load();
    } catch (caught) { setError(caught instanceof Error ? caught.message : "添加模型失败"); }
  }

  async function testModel(connectionId: string, modelId: string) {
    if (testingModel) return;
    setTestingModel(modelId); setError("");
    setMessage("正在检测普通聊天、工具调用与结果回传，会发送少量测试请求并产生模型费用。");
    try {
      const data = await responseJson<Model>(await apiFetch(`${API}/model-connections/${connectionId}/models/${modelId}/test`, { method: "POST", headers: headers() }));
      setMessage(capabilityLabel(data)); await load();
    } catch (caught) { setError(caught instanceof Error ? caught.message : "模型测试失败"); }
    finally { setTestingModel(null); }
  }

  async function saveCapacity(model: Model) {
    const value = capacities[model.id] ?? String(model.context_window_tokens || "");
    const capacity = value ? Number(value) : null;
    if (capacity !== null && (!Number.isInteger(capacity) || capacity < 256 || capacity > 2_000_000)) { setError("容量须为256到2000000之间的整数"); return; }
    try {
      await responseJson<Model>(await apiFetch(`${API}/model-connections/${model.connection_id}/models/${model.id}`, { method: "PATCH", headers: headers(), body: JSON.stringify({ context_window_tokens: capacity }) }));
      setMessage("上下文容量已保存；请按该连接服务商的模型规格填写，能力测试不代表容量检测。"); await load();
    } catch (caught) { setError(caught instanceof Error ? caught.message : "容量保存失败"); }
  }

  async function setDefaultModel(connectionId: string, modelId: string) {
    try {
      await responseJson<Model>(await apiFetch(`${API}/model-connections/${connectionId}/models/${modelId}/default`, { method: "PATCH", headers: headers() }));
      setMessage("已设为默认聊天模型"); await load();
    } catch (caught) { setError(caught instanceof Error ? caught.message : "设置默认模型失败"); }
  }

  async function saveEmbedding(event: FormEvent) {
    event.preventDefault(); const key = String(new FormData(event.currentTarget as HTMLFormElement).get("api_key") || "");
    try {
      await responseJson<Embedding>(await apiFetch(`${API}/model-connections/embedding-config`, { method: "PATCH", headers: headers(), body: JSON.stringify({ api_key: key }) }));
      setMessage("Embedding Key 已保存，请完成测试后启用知识库检索"); await load();
    } catch (caught) { setError(caught instanceof Error ? caught.message : "Embedding 配置失败"); }
  }

  async function testEmbedding() {
    try {
      const data = await responseJson<Embedding>(await apiFetch(`${API}/model-connections/embedding-config/test`, { method: "POST", headers: headers() }));
      setEmbedding(data); setMessage(data.status === "verified" ? "Embedding 连接成功，待处理文件将开始索引" : data.verification_error || "Embedding 测试失败");
    } catch (caught) { setError(caught instanceof Error ? caught.message : "Embedding 测试失败"); }
  }

  async function saveReranker(event: FormEvent) {
    event.preventDefault();
    try {
      const data = await responseJson<Reranker>(await apiFetch(`${API}/model-connections/reranker-config`, { method: "PATCH", headers: headers(), body: JSON.stringify({ base_url: rerankerBaseUrl, api_key: rerankerKey, model_name: rerankerModel }) }));
      setReranker(data); setRerankerKey(""); setMessage("Reranker 已保存，后续检索立即生效");
    } catch (caught) { setError(caught instanceof Error ? caught.message : "Reranker 配置失败"); }
  }

  async function testReranker() {
    try {
      const data = await responseJson<Reranker>(await apiFetch(`${API}/model-connections/reranker-config/test`, { method: "POST", headers: headers() }));
      setReranker(data); setMessage(data.status === "verified" ? "Reranker 连接成功" : data.verification_error || "Reranker 测试失败");
    } catch (caught) { setError(caught instanceof Error ? caught.message : "Reranker 测试失败"); }
  }

  if (!token) return <><Navbar /><main className="workspace"><h1 className="page-title">请先登录</h1></main></>;
  return <>
    <Navbar />
    <main className="workspace model-settings-page">
      <div className="eyebrow">MODEL SETTINGS</div>
      <h1 className="page-title">模型配置</h1>
      <p className="sub">聊天页面仅显示通过聊天、工具调用和结果回传检测的模型。能力取决于当前连接与模型组合；修改地址或 Key 后需重新检测。</p>
      <section className="panel profile-form">
        <h3>{editingId ? "编辑模型连接" : "添加模型连接"}</h3>
        <form className="model-connection-form" onSubmit={saveConnection}>
          <label className="model-connection-field">
            <span>连接名称</span>
            <input value={name} onChange={event => setName(event.target.value)} placeholder="例如 OpenRouter" required />
          </label>
          <label className="model-connection-field">
            <span>Base URL</span>
            <input value={baseUrl} onChange={event => setBaseUrl(event.target.value)} placeholder="https://api.example.com/v1" required />
          </label>
          <label className="model-connection-field">
            <span>API Key</span>
            <input value={apiKey} onChange={event => setApiKey(event.target.value)} type="password" autoComplete="new-password" placeholder={editingId ? "留空则保持原 Key" : "API Key"} required={!editingId} />
          </label>
          <button className="pill fill">{editingId ? "保存修改" : "保存连接"}</button>
          {editingId ? <button className="pill" type="button" onClick={resetConnectionForm}>取消编辑</button> : null}
        </form>
      </section>
      <section className="panel profile-form">
        <h3>知识库 Reranker（可选）</h3>
        <p className="muted">配置后会对混合召回结果进行精排；未配置或调用失败时自动回退到 RRF。当前来源：{reranker?.source === "project" ? "项目默认" : "用户覆盖"}。</p>
        <form onSubmit={saveReranker} className="model-connection-form">
          <input value={rerankerBaseUrl} onChange={event => setRerankerBaseUrl(event.target.value)} placeholder="Reranker Base URL，例如 https://api.example.com/v1" required />
          <input value={rerankerModel} onChange={event => setRerankerModel(event.target.value)} placeholder="Reranker 模型名" required />
          <input value={rerankerKey} onChange={event => setRerankerKey(event.target.value)} type="password" autoComplete="new-password" placeholder="API Key" required={!reranker?.configured} />
          <button className="pill fill">保存 Reranker</button>
        </form>
        {reranker?.configured && reranker.source === "user" ? <button className="pill" type="button" onClick={testReranker}>测试 Reranker 连接</button> : null}
        <small className="muted">状态：{reranker?.status || "未配置"}</small>
      </section>
      {connections.map(connection => {
        const connectionModels = models.filter(model => model.connection_id === connection.id);
        const isModelListOpen = modelListOpen[connection.id] || false;
        const search = modelSearches[connection.id] || "";
        const visibleModels = filterModels(connectionModels, search);
        const modelSummary = connectionModels.slice(0, 2).map(model => model.name).join(" · ");
        const listId = `model-list-${connection.id}`;

        return <section className="panel model-connection-card" key={connection.id}>
          <div className="model-connection-head">
            <div><h3>{connection.name}</h3><small>{connection.base_url} · key 已加密保存</small></div>
            <div>
              <button className="icon-button" type="button" onClick={() => editConnection(connection)}>编辑</button>
              <button className="icon-button" type="button" onClick={() => deleteConnection(connection)}>删除</button>
              <button className="pill" type="button" onClick={() => discover(connection.id)}>发现模型</button>
            </div>
          </div>
          <div className="model-list">
            <button
              aria-controls={listId}
              aria-expanded={isModelListOpen}
              className="model-list-toggle"
              type="button"
              onClick={() => setModelListOpen(current => ({ ...current, [connection.id]: !isModelListOpen }))}
            >
              <span className="model-list-summary">
                <span>已配置 <b>{connectionModels.length}</b> 个模型</span>
                {connectionModels.length ? <span className="model-list-names">{modelSummary}{connectionModels.length > 2 ? " 等" : ""}</span> : null}
              </span>
              <span className="model-list-toggle-action">{isModelListOpen ? "收起详情" : "查看模型详情"}</span>
            </button>
            {isModelListOpen ? <div className="model-list-content" id={listId}>
              <label className="model-list-search">
                <span>搜索模型</span>
                <input
                  value={search}
                  onChange={event => setModelSearches(current => ({ ...current, [connection.id]: event.target.value }))}
                  placeholder="按模型名称筛选"
                  type="search"
                />
              </label>
              {visibleModels.length ? <div className="model-list-scroll">
                {visibleModels.map(model => <div className="model-row" key={model.id}>
                  <span>{model.name}{model.is_default ? "（默认）" : ""}</span>
                  <span className={`model-status ${model.status}`} title={model.verification_error || undefined}>{capabilityLabel(model)}</span>
                  <button className="icon-button" type="button" disabled={Boolean(testingModel)} onClick={() => testModel(connection.id, model.id)}>{testingModel === model.id ? "检测中…" : "检测连接与工具"}</button>
                  {modelCanUseTools(model) && !model.is_default ? <button className="icon-button" type="button" onClick={() => setDefaultModel(connection.id, model.id)}>设为默认</button> : null}
                  <label className="model-capacity">上下文容量（tokens）<input type="number" min={256} max={2_000_000} placeholder="按服务商规格填写" value={capacities[model.id] ?? model.context_window_tokens ?? ""} onChange={event => setCapacities(current => ({ ...current, [model.id]: event.target.value }))} /></label><button type="button" className="icon-button" onClick={() => saveCapacity(model)}>保存容量</button>
                </div>)}
              </div> : <p className="model-list-empty">{connectionModels.length ? "没有匹配的模型" : "尚未添加模型，可点击发现模型或手动添加。"}</p>}
            </div> : null}
          </div>
          <div className="model-add-row">
            <input value={modelNames[connection.id] || ""} onChange={event => setModelNames(current => ({ ...current, [connection.id]: event.target.value }))} placeholder="手动添加模型名称" />
            <button className="pill" type="button" onClick={() => addModel(connection.id)}>添加</button>
          </div>
        </section>;
      })}
      <section className="panel profile-form">
        <h3>知识库 Embedding</h3>
        <p className="muted">当前模型为 {embedding?.model_name || "text-embedding-v3"}。来源：{embedding?.source === "project" ? "项目默认配置" : "用户覆盖配置"}。用户配置验证成功后会覆盖项目默认值。</p>
        <form onSubmit={saveEmbedding}><input name="api_key" type="password" autoComplete="new-password" placeholder="百炼 API Key" required /><button className="pill fill">保存 Embedding Key</button></form>
        {embedding?.source === "user" ? <button className="pill" type="button" onClick={testEmbedding}>测试 Embedding 连接</button> : null}
        <small className="muted">状态：{embedding?.status || "未配置"}</small>
      </section>
      {message || error ? <div className={`toast ${error ? "error" : "success"}`} role={error ? "alert" : "status"}>{error || message}</div> : null}
    </main>
  </>;
}
