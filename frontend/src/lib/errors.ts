export const ERROR_EVENT = "codeatlas:error";
export type ErrorDetail = { message: string; technical?: string };
export function friendlyError(error: unknown, fallback = "操作失败，请稍后重试"): ErrorDetail { if (error instanceof Error) return { message: error.message || fallback }; return { message: fallback }; }
export function reportError(error: unknown, fallback?: string) { const detail = friendlyError(error, fallback); if (typeof window !== "undefined") window.dispatchEvent(new CustomEvent<ErrorDetail>(ERROR_EVENT, { detail })); return detail; }
import {apiFetch as authenticatedFetch} from "./auth";
export async function apiFetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response> { try { const response = await authenticatedFetch(input, init); if (response.ok) return response; let message = "请求失败，请稍后重试"; try { const body = await response.json(); message = body.detail || body.message || message; } catch {} throw new Error(message); } catch (error) { const detail = reportError(error, "网络连接失败，请检查服务是否启动"); throw new Error(detail.message); } }
