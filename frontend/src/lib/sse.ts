export type SseFrame = { event: string; data: Record<string, unknown> };

export class SseDecoder {
  private decoder = new TextDecoder();
  private buffer = "";

  push(bytes: Uint8Array): SseFrame[] {
    this.buffer += this.decoder.decode(bytes, { stream: true });
    this.buffer = this.buffer.replace(/\r\n/g, "\n");
    const blocks = this.buffer.split("\n\n");
    this.buffer = blocks.pop() || "";
    return blocks.flatMap(block => {
      const lines = block.split("\n");
      const event = lines.find(line => line.startsWith("event:"))?.slice(6).trim() || "message";
      const payload = lines.filter(line => line.startsWith("data:")).map(line => line.slice(5).trimStart()).join("\n");
      if (!payload) return [];
      const data: unknown = JSON.parse(payload);
      if (!data || typeof data !== "object" || Array.isArray(data)) throw new Error("Invalid SSE payload");
      return [{ event, data: data as Record<string, unknown> }];
    });
  }
}
