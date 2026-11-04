from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Product:
    product_id: str
    title: str
    variant: str
    description: str
    price_amount: int | float
    currency: str
    pack: int | None
    variant_id: str = "default"


@dataclass(frozen=True)
class KnowledgeRecord:
    record_id: str
    topic: str
    question: str
    answer: str
    language: str = "en"


class CompanyConnector(Protocol):
    company_code: str

    async def search_products(self, query: str) -> list[Product]: ...

    async def validate_product(self, product_id: str, variant_id: str, pack: int | None = None) -> Product | None: ...

    async def search_knowledge(self, query: str) -> list[KnowledgeRecord]: ...

    async def search_public_knowledge(self, query: str) -> list[KnowledgeRecord]: ...


class KnowledgeOnlyConnector:
    """Tenant placeholder for companies without an authorized product catalog."""
    def __init__(self, company_code: str) -> None:
        self.company_code = company_code.upper()

    async def search_products(self, query: str) -> list[Product]:
        return []

    async def validate_product(self, product_id: str, variant_id: str, pack: int | None = None) -> Product | None:
        return None

    async def search_knowledge(self, query: str) -> list[KnowledgeRecord]:
        return []

    async def search_public_knowledge(self, query: str) -> list[KnowledgeRecord]:
        return []


class KnowledgeProvider(Protocol):
    async def search(self, company_code: str, query: str, *, public_only: bool = False) -> list[KnowledgeRecord]: ...
