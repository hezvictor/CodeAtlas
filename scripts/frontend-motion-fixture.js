// External API fixture for the isolated browser regression session only.
// Next.js, React, components, state updates and DOM interaction remain real.
(() => {
  if (!["127.0.0.1", "localhost"].includes(location.hostname)) return;
  localStorage.setItem("codeatlas_access_token", "motion-test-only");
  const originalFetch = window.fetch.bind(window);
  const conversation = { id: "motion-conversation", title: "动效回归会话", updated_at: "2026-09-29T00:00:00Z", selected_chat_model_id: "motion-model" };
  const items = Array.from({ length: 12 }, (_, index) => ({
    id: `motion-problem-${index}`, slug: `motion-${index}`, title: `回归题目 ${index + 1}`,
    owner_user_id: "motion-user", source_type: "user", difficulty: "入门", tags: ["测试"],
    supported_languages: ["cpp"], statement: "测试题面", input_description: "输入", output_description: "输出",
    examples: [{ input: "1", output: "1" }], constraints: "测试约束", created_at: "2026-09-29", updated_at: "2026-09-29",
  }));
  const json = value => new Response(JSON.stringify(value), { headers: { "Content-Type": "application/json" } });
  const fixture = {
    holdProblems: false, pendingProblems: null, nextProblemItems: items,
    stream: null, requests: [],
    emit(name, data) {
      this.stream.enqueue(new TextEncoder().encode(`event: ${name}\ndata: ${JSON.stringify(data)}\n\n`));
    },
    finish() { this.stream.close(); this.stream = null; },
  };
  window.__motionFixture = fixture;
  window.fetch = async (input, init) => {
    const url = new URL(input instanceof Request ? input.url : String(input), location.href);
    if (!url.pathname.startsWith("/api/v1/")) return originalFetch(input, init);
    const route = url.pathname.slice("/api/v1".length);
    fixture.requests.push(route);
    if (route === "/users/me") return json({ id: "motion-user", nickname: "测试", email: "motion@example.invalid", avatar_url: null, created_at: "2026-09-29" });
    if (route === "/knowledge/documents/summary") return json({ processing: 0, failed: 0, waiting: 0, completed: 0 });
    if (route === "/problems") {
      const response = () => json({ items: fixture.nextProblemItems, page: Number(url.searchParams.get("page") || 1), page_size: 12, total: 24 });
      if (fixture.holdProblems) return new Promise(resolve => { fixture.pendingProblems = () => { fixture.pendingProblems = null; resolve(response()); }; });
      return response();
    }
    if (route.startsWith("/problems/")) return json(items.find(item => route.endsWith(item.id)) || items[0]);
    if (route === "/conversations") return json(init?.method === "POST" ? conversation : [conversation]);
    if (route === "/model-connections/available") return json([{ id: "motion-model", connection_id: "motion-connection", connection_name: "回归测试", name: "测试模型", status: "verified", is_default: true }]);
    if (route.endsWith("/messages/stream")) {
      const body = new ReadableStream({ start(controller) {
        fixture.stream = controller;
        fixture.emit("retrieval.started", { step_id: "retrieval-1", sequence: 1 });
      } });
      return new Response(body, { headers: { "Content-Type": "text/event-stream" } });
    }
    if (route.endsWith("/runs/active")) return json(null);
    if (route.endsWith("/messages")) return json({ items: [], has_more: false, next_before: null });
    if (route.endsWith("/temporary-files") || route.endsWith("/citations")) return json([]);
    return json({ detail: `Unconfigured motion-test API route: ${route}` });
  };
})();
