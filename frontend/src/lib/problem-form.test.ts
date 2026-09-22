import { strict as assert } from "node:assert";
import { test } from "node:test";
import { normalizeProblemForm } from "./problem-form";

test("normalizes editable problem fields before submitting", () => {
  const result = normalizeProblemForm({
    title: "  A+B  ",
    difficulty: "简单",
    tags: " 数学, 数学, 输入输出 ",
    statement: "题面",
    input_description: "输入",
    output_description: "输出",
    examples: [{ input: "1 2", output: "3" }],
    constraints: "约束",
    supported_languages: ["cpp", "cpp", "python"],
  });

  assert.deepEqual(result.tags, ["数学", "输入输出"]);
  assert.deepEqual(result.supported_languages, ["cpp", "python"]);
  assert.equal(result.title, "A+B");
});
