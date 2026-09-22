type NamedModel = { name: string };

export function filterModels<T extends NamedModel>(models: T[], query: string): T[] {
  const normalizedQuery = query.trim().toLocaleLowerCase();
  if (!normalizedQuery) return models;
  return models.filter(model => model.name.toLocaleLowerCase().includes(normalizedQuery));
}
