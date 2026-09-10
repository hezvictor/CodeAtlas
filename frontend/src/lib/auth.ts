"use client";
export const API = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api/v1";
export type User = { id: string; email: string; nickname: string; avatar_url: string | null; created_at: string };
export function getToken() { return localStorage.getItem("codeatlas_access_token") || ""; }
export function getRefresh() { return localStorage.getItem("codeatlas_refresh_token") || ""; }
export function saveSession(v: { access_token: string; refresh_token: string; user: User }) { localStorage.setItem("codeatlas_access_token", v.access_token); localStorage.setItem("codeatlas_refresh_token", v.refresh_token); localStorage.setItem("codeatlas_user", JSON.stringify(v.user)); }
export function clearSession() { localStorage.removeItem("codeatlas_access_token"); localStorage.removeItem("codeatlas_refresh_token"); localStorage.removeItem("codeatlas_user"); }
let refreshing: Promise<string> | null = null;
async function refresh() { if (!getRefresh()) throw Error("登录已失效，请重新登录"); if (!refreshing) refreshing = fetch(`${API}/auth/refresh`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ refresh_token: getRefresh() }) }).then(async (r) => { if (!r.ok) throw Error("登录已失效，请重新登录"); const v = await r.json(); saveSession(v); return v.access_token; }).finally(() => { refreshing = null; }); return refreshing; }
export async function apiFetch(input: RequestInfo | URL, init: RequestInit = {}) { let response = await fetch(input, init); if (response.status !== 401) return response; try { const access = await refresh(); const headers = new Headers(init.headers); headers.set("Authorization", `Bearer ${access}`); response = await fetch(input, { ...init, headers }); if (response.status === 401) throw Error("登录已失效，请重新登录"); return response; } catch (error) { clearSession(); throw error; } }
