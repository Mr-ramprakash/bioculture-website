from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str = Field(min_length=1, max_length=2000)
    session_id: str | None = Field(default=None, min_length=1, max_length=80)

    @field_validator("message")
    @classmethod
    def strip_message(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("message cannot be blank")
        if any(ord(char) < 32 and char not in "\n\r\t" for char in value):
            raise ValueError("message contains unsupported control characters")
        return value


class InternalKnowledgeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tenant_id: str = Field(min_length=1, max_length=40)
    company_code: str = Field(min_length=1, max_length=40)
    query: str = Field(min_length=1, max_length=2000)
    public_only: bool = False

    @field_validator("query")
    @classmethod
    def strip_query(cls, value: str) -> str:
        value = value.strip()
        if not value or any(ord(char) < 32 and char not in "\n\r\t" for char in value):
            raise ValueError("query is invalid")
        return value


class Price(BaseModel):
    amount: int | float
    currency: str
    label: str = "current"


class ProductButton(BaseModel):
    type: str = "buy_now"
    label: str = "Buy Now"
    product_id: str
    variant_id: str
    pack: int | None = None


class ProductCard(BaseModel):
    type: str = "product"
    product_id: str
    title: str
    variant: str
    description: str
    price: Price
    buttons: list[ProductButton]


class ChatResponse(BaseModel):
    answer: str
    company_code: str
    source: str
    session_id: str
    cards: list[ProductCard] = Field(default_factory=list)
    actions: list[ProductButton] = Field(default_factory=list)


class HealthResponse(BaseModel):
    status: str = "ok"


class DevSessionResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    company_code: str


class PublicSessionResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    company_code: str
