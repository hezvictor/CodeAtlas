import { API, clearSession, getToken, type User } from "./auth";
import { apiFetch } from "./errors";

export async function patchProfile(fields: Record<string, FormDataEntryValue>): Promise<User> {
  const response = await apiFetch(`${API}/users/me`, {
    method: "PATCH",
    headers: { Authorization: `Bearer ${getToken()}`, "Content-Type": "application/json" },
    body: JSON.stringify(fields),
  });
  return response.json() as Promise<User>;
}

export async function patchPassword(fields: Record<string, FormDataEntryValue>): Promise<void> {
  await apiFetch(`${API}/users/me/password`, {
    method: "PATCH",
    headers: { Authorization: `Bearer ${getToken()}`, "Content-Type": "application/json" },
    body: JSON.stringify(fields),
  });
  clearSession();
}

export async function postAvatar(file: File): Promise<User> {
  const body = new FormData();
  body.append("file", file);
  const response = await apiFetch(`${API}/users/me/avatar`, {
    method: "POST", headers: { Authorization: `Bearer ${getToken()}` }, body,
  });
  return response.json() as Promise<User>;
}
