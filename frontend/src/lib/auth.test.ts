import assert from "node:assert/strict";
import { test } from "node:test";
import { withCurrentAccessToken } from "./auth";

test("authenticated requests replace a stale bearer after refresh", () => {
  const init = withCurrentAccessToken({ headers: { Authorization: "Bearer old", "Content-Type": "application/json" } }, "new");
  const headers = new Headers(init.headers);
  assert.equal(headers.get("Authorization"), "Bearer new");
  assert.equal(headers.get("Content-Type"), "application/json");
});

test("unauthenticated requests stay unauthenticated", () => {
  const init = withCurrentAccessToken({ method: "POST" }, "new");
  assert.equal(new Headers(init.headers).has("Authorization"), false);
});
