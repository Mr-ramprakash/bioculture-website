from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any


class ConfigurationError(RuntimeError):
    pass


def _json_env(name: str, default: str) -> Any:
    value = os.getenv(name, default)
    try:
        return json.loads(value)
    except json.JSONDecodeError as exc:
        raise ConfigurationError(f"{name} must contain valid JSON") from exc


@dataclass(frozen=True)
class Settings:
    groq_api_key: str = ""
    groq_model_id: str = ""
    cors_origins: tuple[str, ...] = ("http://localhost:5173",)
    signing_keys: dict[str, str] = field(default_factory=dict)
    tenant_registry: dict[str, dict[str, Any]] = field(default_factory=dict)
    rate_limit_requests: int = 30
    rate_limit_window_seconds: int = 60
    session_ttl_seconds: int = 1800
    max_message_length: int = 2000
    max_history_messages: int = 10
    groq_timeout_seconds: float = 20
    dev_session_enabled: bool = False
    dev_tenant_id: str = "BIOMAN"
    app_env: str = "development"
    public_session_enabled: bool = False
    public_tenant_id: str = "BIOMAN"
    public_origins: tuple[str, ...] = ()

    @classmethod
    def from_environment(cls) -> "Settings":
        signing_keys = _json_env("CHAT_TENANT_SIGNING_KEYS_JSON", "{}")
        registry = _json_env("CHAT_TENANT_REGISTRY_JSON", "{}")
        if not isinstance(signing_keys, dict) or not all(isinstance(k, str) and isinstance(v, str) and v for k, v in signing_keys.items()):
            raise ConfigurationError("CHAT_TENANT_SIGNING_KEYS_JSON must map tenant IDs to non-empty keys")
        if not isinstance(registry, dict) or not all(isinstance(k, str) and isinstance(v, dict) for k, v in registry.items()):
            raise ConfigurationError("CHAT_TENANT_REGISTRY_JSON must map tenant IDs to objects")
        dev_session_raw = os.getenv("CHAT_DEV_SESSION_ENABLED", "false").strip().lower()
        if dev_session_raw not in {"true", "false"}:
            raise ConfigurationError("CHAT_DEV_SESSION_ENABLED must be true or false")
        vercel_env = os.getenv("VERCEL_ENV", "").strip().lower()
        default_app_env = "production" if vercel_env == "production" else "development"
        try:
            cors = tuple(item.strip() for item in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if item.strip())
            settings = cls(
                groq_api_key=os.getenv("GROQ_API_KEY", ""),
                groq_model_id=os.getenv("GROQ_MODEL_ID", ""),
                cors_origins=cors,
                signing_keys=signing_keys,
                tenant_registry=registry,
                rate_limit_requests=int(os.getenv("CHAT_RATE_LIMIT_REQUESTS", "30")),
                rate_limit_window_seconds=int(os.getenv("CHAT_RATE_LIMIT_WINDOW_SECONDS", "60")),
                session_ttl_seconds=int(os.getenv("CHAT_SESSION_TTL_SECONDS", "1800")),
                max_message_length=int(os.getenv("CHAT_MAX_MESSAGE_LENGTH", "2000")),
                max_history_messages=int(os.getenv("CHAT_MAX_HISTORY_MESSAGES", "10")),
                groq_timeout_seconds=float(os.getenv("GROQ_TIMEOUT_SECONDS", "20")),
                dev_session_enabled=dev_session_raw == "true",
                dev_tenant_id=os.getenv("CHAT_DEV_TENANT_ID", "BIOMAN").strip(),
                app_env=os.getenv("APP_ENV", default_app_env).strip().lower(),
                public_session_enabled=os.getenv("CHAT_PUBLIC_SESSION_ENABLED", "false").strip().lower() == "true",
                public_tenant_id=os.getenv("CHAT_PUBLIC_TENANT_ID", "BIOMAN").strip(),
                public_origins=tuple(item.strip() for item in os.getenv("CHAT_PUBLIC_ORIGINS", "").split(",") if item.strip()),
            )
        except ValueError as exc:
            raise ConfigurationError("Chat numeric settings must be valid numbers") from exc
        if settings.rate_limit_requests <= 0 or settings.rate_limit_window_seconds <= 0:
            raise ConfigurationError("Rate limit settings must be positive")
        if settings.session_ttl_seconds <= 0 or settings.max_history_messages < 2:
            raise ConfigurationError("Session settings are out of range")
        if not 1 <= settings.max_message_length <= 10000:
            raise ConfigurationError("CHAT_MAX_MESSAGE_LENGTH is out of range")
        if not 1 <= settings.groq_timeout_seconds <= 120:
            raise ConfigurationError("GROQ_TIMEOUT_SECONDS is out of range")
        if settings.app_env not in {"development", "production", "test"}:
            raise ConfigurationError("APP_ENV must be development, production, or test")
        if settings.app_env == "production" and settings.dev_session_enabled:
            raise ConfigurationError("CHAT_DEV_SESSION_ENABLED must be false in production")
        public_session_raw = os.getenv("CHAT_PUBLIC_SESSION_ENABLED", "false").strip().lower()
        if public_session_raw not in {"true", "false"}:
            raise ConfigurationError("CHAT_PUBLIC_SESSION_ENABLED must be true or false")
        for tenant_id, config in registry.items():
            if tenant_id not in signing_keys:
                raise ConfigurationError(f"No signing key configured for tenant {tenant_id}")
            if config.get("connector") not in {"bioman", "rest", "knowledge"}:
                raise ConfigurationError(f"Unsupported connector configured for tenant {tenant_id}")
            knowledge_company = config.get("knowledge_company_code", config.get("company_code", tenant_id))
            if not isinstance(knowledge_company, str) or knowledge_company.upper() != tenant_id.upper():
                raise ConfigurationError(f"Knowledge company code must match tenant ID for {tenant_id}")
            company_code = config.get("company_code", tenant_id)
            if not isinstance(company_code, str) or company_code.upper() != tenant_id.upper():
                raise ConfigurationError(f"Company code must match tenant ID for {tenant_id}")
        if settings.dev_session_enabled:
            if not settings.dev_tenant_id or settings.dev_tenant_id not in signing_keys or settings.dev_tenant_id not in registry:
                raise ConfigurationError("CHAT_DEV_TENANT_ID must identify a configured tenant")
            if registry[settings.dev_tenant_id].get("active") is not True:
                raise ConfigurationError("CHAT_DEV_TENANT_ID must identify an active tenant")
        if settings.public_session_enabled:
            public_tenant = registry.get(settings.public_tenant_id, {})
            if settings.app_env != "production":
                raise ConfigurationError("Public sessions can only be enabled when APP_ENV=production")
            if not settings.public_tenant_id or settings.public_tenant_id not in signing_keys:
                raise ConfigurationError("CHAT_PUBLIC_TENANT_ID must identify a configured tenant")
            if public_tenant.get("active") is not True:
                raise ConfigurationError("CHAT_PUBLIC_TENANT_ID must identify an active tenant")
            if any(public_tenant.get(flag) is not True for flag in ("public_session_enabled", "public_knowledge_only", "public_products")):
                raise ConfigurationError("Public tenant must explicitly enable public sessions, public knowledge, and public products")
            if not settings.public_origins or any(not origin.startswith("https://") for origin in settings.public_origins):
                raise ConfigurationError("CHAT_PUBLIC_ORIGINS must contain exact HTTPS origins")
            if not set(settings.public_origins).issubset(set(settings.cors_origins)):
                raise ConfigurationError("CHAT_PUBLIC_ORIGINS must also be listed in CORS_ORIGINS")
        return settings
