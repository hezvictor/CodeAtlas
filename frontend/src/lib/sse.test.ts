import assert from "node:assert/strict";
import { test } from "node:test";
import { SseDecoder } from "./sse";

test("SSE decoder preserves Chinese text split across UTF-8 chunks", () => {
  const bytes = new TextEncoder().encode('event: message.delta\ndata: {"content":"你好"}\n\n');
  const decoder = new SseDecoder();
  const first = decoder.push(bytes.slice(0, 40));
  const second = decoder.push(bytes.slice(40));
  assert.deepEqual([...first, ...second], [{ event: "message.delta", data: { content: "你好" } }]);
});

test("SSE decoder handles CRLF and multiple frames per chunk", () => {
  const decoder = new SseDecoder();
  const bytes = new TextEncoder().encode('event: run.started\r\ndata: {"run_id":"r"}\r\n\r\nevent: run.completed\r\ndata: {}\r\n\r\n');
  assert.deepEqual(decoder.push(bytes).map(frame => frame.event), ["run.started", "run.completed"]);
});
