import httpx

from .url_validation import pin_provider_base_url


class RerankerProvider:
    def __init__(self, base_url: str, api_key: str, model: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model

    async def rerank(self, query: str, documents: list[str]) -> list[tuple[int, float]]:
        if not documents:
            return []
        base_url, host, extensions = pin_provider_base_url(self.base_url)
        async with httpx.AsyncClient(timeout=httpx.Timeout(30, connect=10), trust_env=False) as client:
            response = await client.post(
                base_url + "/rerank",
                headers={"Authorization": f"Bearer {self.api_key}", **host}, extensions=extensions,
                json={"model": self.model, "query": query, "documents": documents, "top_n": len(documents), "return_documents": False},
            )
            response.raise_for_status()
        rows = response.json().get("results") or response.json().get("data") or []
        return [(int(row.get("index", 0)), float(row.get("relevance_score", row.get("score", 0)))) for row in rows]
