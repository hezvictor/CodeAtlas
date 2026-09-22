import assert from "node:assert/strict";
import { test } from "node:test";

import { filterModels } from "./model-list";

test("filters model names without case sensitivity", () => {
  const models = [
    { id: "1", name: "gpt-4o" },
    { id: "2", name: "Qwen3-32B" },
    { id: "3", name: "gpt-4o-mini" },
  ];

  assert.deepEqual(
    filterModels(models, " GPT-4O ").map(model => model.id),
    ["1", "3"],
  );
});
