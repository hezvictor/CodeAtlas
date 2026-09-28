import assert from "node:assert/strict";
import test from "node:test";
import { loadDocumentDetails } from "./knowledge";

test("deleted detail refresh returns unavailable without a global failure notification", async () => {
  const originalFetch = globalThis.fetch;
  const originalStorage = globalThis.localStorage;
  const originalWindow = globalThis.window;
  let notifications = 0;
  globalThis.localStorage = { getItem: () => "token" } as unknown as Storage;
  globalThis.window = { dispatchEvent: () => { notifications++; return true; } } as unknown as Window & typeof globalThis;
  globalThis.fetch = async () => new Response('{"detail":"Document not found"}', { status: 404 });
  try {
    assert.equal(await loadDocumentDetails("deleted-document"), null);
    assert.equal(notifications, 0);
  } finally {
    globalThis.fetch = originalFetch; globalThis.localStorage = originalStorage; globalThis.window = originalWindow;
  }
});

test("detail refresh preserves server errors for the inline error state", async () => {
  const originalFetch = globalThis.fetch;
  const originalStorage = globalThis.localStorage;
  globalThis.localStorage = { getItem: () => "token" } as unknown as Storage;
  globalThis.fetch = async () => new Response('{"detail":"Storage unavailable"}', { status: 503 });
  try { await assert.rejects(loadDocumentDetails("document"), /Storage unavailable/); }
  finally { globalThis.fetch = originalFetch; globalThis.localStorage = originalStorage; }
});
