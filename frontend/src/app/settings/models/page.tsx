"use client";

import { FormEvent, useEffect, useState } from "react";
import Navbar from "../../../components/Navbar";
import { API, apiFetch, getToken } from "../../../lib/auth";

type Connection = { id: string; name: string; base_url: string; status: string; last_error?: string | null };
type Model = { id: string; connection_id: string; name: string; source: string; status: string; verification_error?: string | null; is_default?: boolean };
type Embedding = { model_name: string; status: string; verification_error?: string | null; configured: boolean };

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
  const [name, setName] = useState("");
  const [baseUrl, setBaseUrl] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [modelNames, setModelNames] = useState<Record<string, string>>({});
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const headers = () => ({ Authorization: `Bearer ${token}`, "Content-Type": "application/json" });

  async function load() {
    const [connectionsResponse, embeddingResponse] = await Promise.all([
      apiFetch(`${API}/model-connections`, { headers: headers() }),
      apiFetch(`${API}/model-connections/embedding-config`, { headers: headers() }),
    ]);
    const connectionRows = await responseJson<Connection[]>(connectionsResponse);
    const modelRows = await Promise.all(connectionRows.map(async connection => responseJson<Model[]>(
      await apiFetch(`${API}/model-connections/${connection.id}/models`, { headers: headers() }),
    )));
    setConnections(connectionRows);
    setModels(modelRows.flat());
    setEmbedding(await responseJson<Embedding>(embeddingResponse));
  }

  useEffect(() => {
    const value = getToken();
    setToken(value);
    if (value) load().catch(() => setError("模型配置加载失败"));
  }, []);

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
      setMessage(data.error || "模型列表已更新"); await load();
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
    try {
      const data = await responseJson<Model>(await apiFetch(`${API}/model-connections/${connectionId}/models/${modelId}/test`, { method: "POST", headers: headers() }));
      setMessage(data.status === "verified" ? "模型验证成功" : data.verification_error || "模型验证失败"); await load();
    } catch (caught) { setError(caught instanceof Error ? caught.message : "模型测试失败"); }
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

  if (!token) return <><Navbar /><main className="workspace"><h1 className="page-title">请先登录</h1></main></>;
  return <><Navbar /><main className="workspace model-settings-page"><div className="eyebrow">MODEL SETTINGS</div><h1 className="page-title">模型配置</h1><p className="sub">聊天页面只显示验证通过的模型。修改连接地址或 Key 后，需要重新验证模型。</p><section className="panel profile-form"><h3>{editingId ? "编辑模型连接" : "添加模型连接"}</h3><form onSubmit={saveConnection}><label>连接名称</label><input value={name} onChange={event => setName(event.target.value)} placeholder="例如 OpenRouter" required /><label>Base URL</label><input value={baseUrl} onChange={event => setBaseUrl(event.target.value)} placeholder="https://api.example.com/v1" required /><label>API Key</label><input value={apiKey} onChange={event => setApiKey(event.target.value)} type="password" autoComplete="new-password" placeholder={editingId ? "留空则保持原 Key" : "API Key"} required={!editingId} /><button className="pill fill">{editingId ? "保存修改" : "保存连接"}</button>{editingId && <button className="pill" type="button" onClick={resetConnectionForm}>取消编辑</button>}</form></section>{connections.map(connection => <section className="panel model-connection-card" key={connection.id}><div className="model-connection-head"><div><h3>{connection.name}</h3><small>{connection.base_url} · key 已加密保存</small></div><div><button className="icon-button" type="button" onClick={() => editConnection(connection)}>编辑</button><button className="icon-button" type="button" onClick={() => deleteConnection(connection)}>删除</button><button className="pill" type="button" onClick={() => discover(connection.id)}>发现模型</button></div></div><div className="model-list">{models.filter(model => model.connection_id === connection.id).map(model => <div className="model-row" key={model.id}><span>{model.name}{model.is_default ? "（默认）" : ""}</span><span className={`model-status ${model.status}`}>{model.status === "verified" ? "已验证" : model.status === "invalid" ? "不可用" : "待验证"}</span><button className="icon-button" type="button" onClick={() => testModel(connection.id, model.id)}>测试</button>{model.status === "verified" && !model.is_default && <button className="icon-button" type="button" onClick={() => setDefaultModel(connection.id, model.id)}>设为默认</button>}</div>)}</div><div className="model-add-row"><input value={modelNames[connection.id] || ""} onChange={event => setModelNames(current => ({ ...current, [connection.id]: event.target.value }))} placeholder="手动添加模型名称" /><button className="pill" type="button" onClick={() => addModel(connection.id)}>添加</button></div></section>)}<section className="panel profile-form"><h3>知识库 Embedding</h3><p className="muted">模型固定为 {embedding?.model_name || "text-embedding-v3"}，仅支持填写百炼 API Key。只有验证成功后，长期资料和会话文件才会参与检索。</p><form onSubmit={saveEmbedding}><input name="api_key" type="password" autoComplete="new-password" placeholder="百炼 API Key" required /><button className="pill fill">保存 Embedding Key</button></form><button className="pill" type="button" onClick={testEmbedding}>测试 Embedding 连接</button><small className="muted">状态：{embedding?.status || "未配置"}</small></section>{(message || error) && <div className={`toast ${error ? "error" : "success"}`} role={error ? "alert" : "status"}>{error || message}</div>}</main></>;
}
