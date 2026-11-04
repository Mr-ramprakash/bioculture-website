from __future__ import annotations

import os
from typing import Any


class GroqConfigurationError(RuntimeError):
    pass


class GroqChatClient:
    def __init__(self, api_key: str, model_id: str, timeout_seconds: float = 20) -> None:
        if not api_key:
            raise GroqConfigurationError("GROQ_API_KEY is required")
        if not model_id:
            raise GroqConfigurationError("GROQ_MODEL_ID must be set to a currently available model")
        try:
            from groq import AsyncGroq
        except ImportError as exc:
            raise GroqConfigurationError("Install the groq package") from exc
        self.model_id = model_id
        self._client = AsyncGroq(api_key=api_key, timeout=timeout_seconds, max_retries=0)

    @classmethod
    def from_environment(cls) -> "GroqChatClient":
        try:
            timeout = float(os.getenv("GROQ_TIMEOUT_SECONDS", "20"))
        except ValueError as exc:
            raise GroqConfigurationError("GROQ_TIMEOUT_SECONDS must be numeric") from exc
        if timeout <= 0 or timeout > 120:
            raise GroqConfigurationError("GROQ_TIMEOUT_SECONDS is out of range")
        return cls(os.getenv("GROQ_API_KEY", ""), os.getenv("GROQ_MODEL_ID", ""), timeout)

    async def complete(self, *, system: str, messages: list[dict[str, str]], max_tokens: int = 350) -> str:
        result: Any = await self._client.chat.completions.create(
            model=self.model_id,
            messages=[{"role": "system", "content": system}, *messages],
            temperature=0.2,
            max_tokens=max_tokens,
        )
        choices = getattr(result, "choices", None)
        if not isinstance(choices, list) or not choices:
            raise ValueError("Groq returned no choices")
        choice = choices[0]
        finish_reason = getattr(choice, "finish_reason", None)
        message = getattr(choice, "message", None)
        content = getattr(message, "content", None)
        if finish_reason == "content_filter":
            raise ValueError("Groq response was filtered")
        if not isinstance(content, str) or not content.strip():
            raise ValueError("Groq returned an invalid response")
        return content.strip()[:3000]
