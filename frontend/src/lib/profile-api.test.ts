import assert from "node:assert/strict";
import { test } from "node:test";
import { patchPassword, patchProfile, postAvatar } from "./profile-api";

function withResponse(response: Response, run: () => Promise<void>) {
  const originalFetch = globalThis.fetch;
  const originalStorage = globalThis.localStorage;
  const values = new Map<string, string>([["codeatlas_access_token", "access"], ["codeatlas_refresh_token", "refresh"]]);
  Object.defineProperty(globalThis, "localStorage", {
    configurable: true,
    value: {
      getItem: (key: string) => values.get(key) || null,
      setItem: (key: string, value: string) => values.set(key, value),
      removeItem: (key: string) => values.delete(key),
    },
  });
  globalThis.fetch = async () => response;
  return run().finally(() => {
    globalThis.fetch = originalFetch;
    Object.defineProperty(globalThis, "localStorage", { configurable: true, value: originalStorage });
  });
}

test("wrong current password is reported as failure and keeps the session", async () => {
  await withResponse(new Response(JSON.stringify({ detail: "Current password is incorrect" }), { status: 400 }), async () => {
    await assert.rejects(patchPassword({ current_password: "wrong", new_password: "newpassword" }), /Current password is incorrect/);
    assert.equal(localStorage.getItem("codeatlas_access_token"), "access");
  });
});

test("successful password change clears revoked local credentials", async () => {
  await withResponse(new Response(null, { status: 204 }), async () => {
    await patchPassword({ current_password: "old", new_password: "newpassword" });
    assert.equal(localStorage.getItem("codeatlas_access_token"), null);
    assert.equal(localStorage.getItem("codeatlas_refresh_token"), null);
  });
});

test("profile and avatar errors never become a user object", async () => {
  await withResponse(new Response(JSON.stringify({ detail: "Email already registered" }), { status: 409 }), async () => {
    await assert.rejects(patchProfile({ email: "taken@example.com", nickname: "Name" }), /Email already registered/);
  });
  await withResponse(new Response(JSON.stringify({ detail: "Avatar too large" }), { status: 413 }), async () => {
    await assert.rejects(postAvatar(new File(["x"], "avatar.png", { type: "image/png" })), /Avatar too large/);
  });
});
