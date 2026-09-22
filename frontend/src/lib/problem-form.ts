export type ProblemExample = { input: string; output: string };

export type ProblemFormValues = {
  title: string;
  difficulty: string;
  tags: string;
  statement: string;
  input_description: string;
  output_description: string;
  examples: ProblemExample[];
  constraints: string;
  supported_languages: string[];
};

export type ProblemPayload = Omit<ProblemFormValues, "tags"> & { tags: string[] };

export function normalizeProblemForm(values: ProblemFormValues): ProblemPayload {
  const tags = values.tags
    .split(",")
    .map((tag) => tag.trim())
    .filter((tag, index, all) => tag && all.indexOf(tag) === index);
  const supported_languages = values.supported_languages.filter(
    (language, index, all) => language && all.indexOf(language) === index,
  );
  return {
    ...values,
    title: values.title.trim(),
    difficulty: values.difficulty.trim(),
    tags,
    statement: values.statement.trim(),
    input_description: values.input_description.trim(),
    output_description: values.output_description.trim(),
    constraints: values.constraints.trim(),
    supported_languages,
  };
}
