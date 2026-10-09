export function rerankerPayload(baseUrl: string, modelName: string, key: string) {
  return {
    base_url: baseUrl,
    model_name: modelName,
    ...(key ? { api_key: key } : {}),
  };
}
