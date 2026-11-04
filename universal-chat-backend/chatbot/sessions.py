from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field


class SessionTenantMismatch(ValueError):
    pass


@dataclass
class Conversation:
    tenant_id: str
    expires_at: float
    messages: list[dict[str, str]] = field(default_factory=list)


class InMemorySessionStore:
    """Single-process development store; use shared storage for multi-worker production."""

    def __init__(self, ttl_seconds: int = 1800, max_messages: int = 10) -> None:
        self.ttl_seconds = ttl_seconds
        self.max_messages = max_messages
        self._sessions: dict[str, Conversation] = {}

    def get_or_create(self, tenant_id: str, session_id: str | None) -> tuple[str, list[dict[str, str]]]:
        self._purge_expired()
        if session_id is None:
            session_id = str(uuid.uuid4())
            self._sessions[session_id] = Conversation(tenant_id, time.time() + self.ttl_seconds)
        conversation = self._sessions.get(session_id)
        if conversation is None:
            # Unknown client-provided ID starts a new tenant-bound context.
            conversation = Conversation(tenant_id, time.time() + self.ttl_seconds)
            self._sessions[session_id] = conversation
        elif conversation.tenant_id != tenant_id:
            raise SessionTenantMismatch("session is unavailable")
        conversation.expires_at = time.time() + self.ttl_seconds
        return session_id, list(conversation.messages)

    def append(self, tenant_id: str, session_id: str, user_message: str, assistant_message: str) -> None:
        conversation = self._sessions.get(session_id)
        if conversation is None or conversation.tenant_id != tenant_id:
            raise SessionTenantMismatch("session is unavailable")
        conversation.messages.extend([
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": assistant_message},
        ])
        conversation.messages = conversation.messages[-self.max_messages :]
        conversation.expires_at = time.time() + self.ttl_seconds

    def _purge_expired(self) -> None:
        now = time.time()
        for session_id in [key for key, value in self._sessions.items() if value.expires_at <= now]:
            del self._sessions[session_id]


class StatelessSessionStore:
    """Vercel-safe placeholder; keeps the response contract without claiming history."""
    def get_or_create(self, tenant_id: str, session_id: str | None) -> tuple[str, list[dict[str, str]]]:
        return session_id or str(uuid.uuid4()), []

    def append(self, tenant_id: str, session_id: str, user_message: str, assistant_message: str) -> None:
        return None
