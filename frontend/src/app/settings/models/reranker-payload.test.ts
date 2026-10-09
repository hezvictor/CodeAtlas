import assert from "node:assert/strict";
import { test } from "node:test";
import { rerankerPayload } from "./reranker-payload";

test("editing a reranker without a new key omits the secret field", () => {
  assert.deepEqual(rerankerPayload("https://provider.example/v1", "ranker", ""), {
    base_url: "https://provider.example/v1", model_name: "ranker",
  });
});

test("a new reranker key is included when supplied", () => {
  assert.deepEqual(rerankerPayload("https://provider.example/v1", "ranker", "new-key"), {
    base_url: "https://provider.example/v1", model_name: "ranker", api_key: "new-key",
  });
});
