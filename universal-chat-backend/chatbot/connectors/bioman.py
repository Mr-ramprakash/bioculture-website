from __future__ import annotations

import re

from .base import KnowledgeRecord, Product
from .bioman_knowledge import BIOMAN_KNOWLEDGE


# Reviewed catalog copy from src/data.js. `original` is intentionally omitted:
# the source does not establish that it is a verified MRP.
BIOMAN_PRODUCTS = (
    Product("bioculture-pack-1", "Bio-Culture", "1 packet", "1 packet of 500 gm", 895, "INR", 1, "pack-1"),
    Product("bioculture-pack-2", "Bio-Culture", "2 packets", "2 packets of 500 gm", 1649, "INR", 2, "pack-2"),
    Product("bioculture-pack-3", "Bio-Culture", "3 packets", "3 packets of 500 gm", 2449, "INR", 3, "pack-3"),
    Product("bioculture-pack-5", "Bio-Culture", "5 packets", "5 packets of 500 gm", 3900, "INR", 5, "pack-5"),
    Product("bioculture-pack-10", "Bio-Culture", "10 packets", "10 packets of 500 gm", 7605, "INR", 10, "pack-10"),
)

_TOKEN_RE = re.compile(r"[a-z0-9]+", re.I)
_BIOCULTURE_RE = re.compile(r"\bbio\s*[- ]?\s*culture\b", re.I)
_PACK_RE = re.compile(r"\b(\d+)\s*(?:packets?|packs?)\b", re.I)
_SIZE_RE = re.compile(r"\b500\s*(?:g|gm|grams?)\b", re.I)
_PRODUCT_INTENT_RE = re.compile(r"\b(?:buy|purchase|order|get|want|need|price|prices|cost|costs|much|catalog|available|mrp)\b", re.I)
_CATALOG_LIST_RE = re.compile(
    r"\b(?:products?|options?|packs?|catalog|list|show)\b|\bprice\s+list\b|\bwhat\s+do\s+you\s+have\b",
    re.I,
)
_QUERY_NOISE = {
    "a", "an", "and", "are", "can", "do", "does", "for", "how", "i", "in", "is", "it",
    "me", "of", "on", "or", "please", "tell", "that", "the", "this", "to", "what", "whats",
    "you", "explain", "describe", "tamil", "english",
}


def _tokens(value: str) -> set[str]:
    return {token.lower() for token in _TOKEN_RE.findall(value) if len(token) > 1}


class BiomanConnector:
    company_code = "BIOMAN"

    async def search_products(self, query: str) -> list[Product]:
        named_product = bool(_BIOCULTURE_RE.search(query))
        match = _PACK_RE.search(query)
        # In Bioman's catalog all verified packet variants are 500 gm Bio-Culture.
        # Requiring both an explicit size and pack count allows natural requests
        # such as "I want 2 packets of 500 gm" without accepting arbitrary items.
        catalog_list = bool(_CATALOG_LIST_RE.search(query))
        if not named_product and not (match and _SIZE_RE.search(query)) and not catalog_list:
            return []
        if match:
            pack = int(match.group(1))
            product = next((item for item in BIOMAN_PRODUCTS if item.pack == pack), None)
            return [product] if product else []
        if catalog_list:
            return list(BIOMAN_PRODUCTS)
        if not named_product or not _PRODUCT_INTENT_RE.search(query):
            return []
        return list(BIOMAN_PRODUCTS)

    async def validate_product(self, product_id: str, variant_id: str, pack: int | None = None) -> Product | None:
        return next(
            (item for item in BIOMAN_PRODUCTS if item.product_id == product_id and item.variant_id == variant_id and item.pack == pack),
            None,
        )

    async def search_knowledge(self, query: str) -> list[KnowledgeRecord]:
        query_tokens = _tokens(query) - _QUERY_NOISE
        if not query_tokens:
            return []
        ranked: list[tuple[float, KnowledgeRecord]] = []
        for entry in BIOMAN_KNOWLEDGE:
            best_score = 0.0
            best_question = ""
            for variation in entry.questions:
                variation_tokens = _tokens(variation) - _QUERY_NOISE
                matched = len(query_tokens & variation_tokens)
                if matched:
                    # Prefer phrases that cover more of the customer's wording,
                    # while retaining enough weight for short, clear questions.
                    score = matched + matched / len(query_tokens)
                    if score > best_score:
                        best_score = score
                        best_question = variation
            if best_score:
                ranked.append((best_score, KnowledgeRecord(
                    record_id=entry.record_id,
                    topic=entry.topic,
                    question=best_question,
                    answer=entry.answer,
                )))
        ranked.sort(key=lambda item: item[0], reverse=True)
        # One best-matching grouped entry avoids handing loosely related policy
        # or product facts to Groq for a single customer question.
        return [ranked[0][1]] if ranked else []

    async def search_seed_knowledge(self, query: str) -> list[KnowledgeRecord]:
        """Search the local seed for review/testing; never used as production knowledge."""
        return await self.search_knowledge(query)

    async def search_public_knowledge(self, query: str) -> list[KnowledgeRecord]:
        # This connector's seed is curated from approved, public Bioculture site content.
        return await self.search_knowledge(query)
