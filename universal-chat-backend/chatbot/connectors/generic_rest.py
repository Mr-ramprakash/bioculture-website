"""Generic HTTPS REST adapter for authorized company catalog/knowledge APIs."""

from __future__ import annotations

import math
from urllib.parse import quote, urlparse

import httpx

from .base import KnowledgeRecord, Product


class ConnectorConfigurationError(ValueError):
    pass


class GenericRestConnector:
    """Configured only by trusted backend settings; never accepts URLs from chat."""

    def __init__(
        self,
        company_code: str,
        catalog_url: str,
        knowledge_url: str,
        api_token: str,
        timeout_seconds: float = 8.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        for url in (catalog_url, knowledge_url):
            parsed = urlparse(url)
            if parsed.scheme != "https" or not parsed.hostname:
                raise ConnectorConfigurationError("Connector URLs must be absolute HTTPS URLs")
        if not company_code or not api_token:
            raise ConnectorConfigurationError("Company code and API token are required")
        self.company_code = company_code.upper()
        self.catalog_url = catalog_url
        self.knowledge_url = knowledge_url
        self._headers = {"Authorization": f"Bearer {api_token}", "Accept": "application/json"}
        self._timeout = httpx.Timeout(timeout_seconds, connect=min(timeout_seconds, 3.0))
        self._transport = transport

    async def search_products(self, query: str) -> list[Product]:
        async with httpx.AsyncClient(timeout=self._timeout, transport=self._transport) as client:
            response = await client.get(self.catalog_url, params={"q": query, "limit": 5}, headers=self._headers)
            response.raise_for_status()
            rows = response.json()
        if not isinstance(rows, list):
            raise ValueError("Catalog connector returned invalid data")
        result: list[Product] = []
        return self._parse_products(rows[:5])

    async def validate_product(self, product_id: str, variant_id: str, pack: int | None = None) -> Product | None:
        url = self.catalog_url.rstrip("/") + "/" + quote(product_id, safe="")
        async with httpx.AsyncClient(timeout=self._timeout, transport=self._transport) as client:
            response = await client.get(url, headers=self._headers)
            if response.status_code == 404:
                return None
            response.raise_for_status()
            row = response.json()
        products = self._parse_products([row])
        return products[0] if products and products[0].pack == pack and products[0].variant_id == variant_id and products[0].product_id == product_id else None

    async def search_knowledge(self, query: str) -> list[KnowledgeRecord]:
        return await self._search_knowledge(query, public_only=False)

    async def search_public_knowledge(self, query: str) -> list[KnowledgeRecord]:
        return await self._search_knowledge(query, public_only=True)

    async def _search_knowledge(self, query: str, *, public_only: bool) -> list[KnowledgeRecord]:
        async with httpx.AsyncClient(timeout=self._timeout, transport=self._transport) as client:
            response = await client.get(self.knowledge_url, params={"q": query, "limit": 5}, headers=self._headers)
            response.raise_for_status()
            rows = response.json()
        if not isinstance(rows, list):
            raise ValueError("Knowledge connector returned invalid data")
        result: list[KnowledgeRecord] = []
        for row in rows[:5]:
            if isinstance(row, dict) and row.get("approved") is True and (not public_only or row.get("public") is True):
                try:
                    result.append(KnowledgeRecord(
                        record_id=str(row["record_id"]),
                        topic=str(row["topic"]),
                        question=str(row["question"]),
                        answer=str(row["answer"]),
                        language=str(row.get("language") or "en"),
                    ))
                except KeyError:
                    continue
        return result

    @staticmethod
    def _parse_products(rows: list[dict]) -> list[Product]:
        # Keep product-response validation identical to catalog search.
        result = []
        for row in rows:
            try:
                price = float(row["price_amount"])
                pack_value = row.get("pack")
                pack = int(pack_value) if pack_value is not None else None
                variant_id = str(row.get("variant_id") or "default").strip()
                if not math.isfinite(price) or price < 0 or (pack is not None and pack <= 0) or not variant_id:
                    continue
                if not str(row.get("product_id", "")).strip() or not str(row.get("title", "")).strip():
                    continue
                result.append(Product(
                    product_id=str(row["product_id"]),
                    title=str(row["title"]),
                    variant=str(row.get("variant") or ""),
                    description=str(row.get("description") or ""),
                    price_amount=price,
                    currency=str(row["currency"]).upper(),
                    pack=pack,
                    variant_id=variant_id,
                ))
            except (KeyError, TypeError, ValueError):
                continue
        return result
