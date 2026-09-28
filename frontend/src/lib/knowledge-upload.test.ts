import assert from "node:assert/strict";
import test from "node:test";
import { uploadWithProgress } from "./knowledge";

test("100 percent transfer still waits for storage acknowledgement and abort stops transfer", async () => {
  const original = globalThis.XMLHttpRequest;
  const originalStorage = globalThis.localStorage;
  const instances: FakeXHR[] = [];
  class FakeXHR {
    upload: { onprogress?: (event: { lengthComputable: boolean; loaded: number; total: number }) => void } = {};
    status = 202; responseText = '{"id":"stored-document"}';
    onload?: () => void; onabort?: () => void; onerror?: () => void;
    open() {} setRequestHeader() {} send() {} abort() { this.onabort?.(); }
    constructor() { instances.push(this); }
  }
  globalThis.XMLHttpRequest = FakeXHR as unknown as typeof XMLHttpRequest;
  globalThis.localStorage = { getItem: () => "token" } as unknown as Storage;
  try {
    let complete = false; let percent = 0;
    const request = uploadWithProgress("/upload", new FormData(), new AbortController().signal, value => { percent = value; }).then(value => { complete = true; return value; });
    instances[0].upload.onprogress?.({ lengthComputable: true, loaded: 100, total: 100 });
    await Promise.resolve();
    assert.equal(percent, 100); assert.equal(complete, false);
    instances[0].onload?.();
    assert.equal((await request).id, "stored-document");
    const controller = new AbortController();
    const aborted = uploadWithProgress("/upload", new FormData(), controller.signal, () => {});
    controller.abort();
    await assert.rejects(aborted, /中断/);
  } finally { globalThis.XMLHttpRequest = original; globalThis.localStorage = originalStorage; }
});
