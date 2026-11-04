from __future__ import annotations

import ipaddress
import hmac
import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Any
from urllib.parse import urlsplit

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from .auth import TenantTokenError, mint_tenant_token, verify_tenant_token
from .config import ConfigurationError, Settings
from .connectors.bioman import BiomanConnector
from .connectors.base import KnowledgeOnlyConnector
from .connectors.generic_rest import GenericRestConnector
from .groq_client import GroqChatClient, GroqConfigurationError
from .knowledge_api import configured_knowledge_provider
from .rate_limit import DevelopmentRateLimiter
from .schemas import ChatRequest, ChatResponse, DevSessionResponse, HealthResponse, InternalKnowledgeRequest, PublicSessionResponse
from .service import ChatDependencyError, ChatService
from .knowledge_store import KnowledgeFileError, search_approved_knowledge
from .sessions import InMemorySessionStore, SessionTenantMismatch, StatelessSessionStore

logger = logging.getLogger("automategenie.chat")
load_dotenv()


def _build_connectors(settings: Settings) -> dict[str, Any]:
    connectors: dict[str, Any] = {}
    for tenant_id, config in settings.tenant_registry.items():
        name = config["connector"]
        connector_key = config.get("connector_key", tenant_id)
        if name == "bioman":
            connectors[connector_key] = BiomanConnector()
        elif name == "knowledge":
            connectors[connector_key] = KnowledgeOnlyConnector(str(config.get("company_code", tenant_id)))
        elif name == "rest":
            token_env = config.get("api_token_env")
            catalog_url = config.get("catalog_url")
            knowledge_url = config.get("knowledge_url")
            if not all(isinstance(value, str) and value for value in (token_env, catalog_url, knowledge_url)):
                raise ConfigurationError(f"REST connector config is incomplete for {tenant_id}")
            api_token = os.getenv(token_env, "")
            connectors[connector_key] = GenericRestConnector(
                company_code=str(config.get("company_code", tenant_id)),
                catalog_url=catalog_url,
                knowledge_url=knowledge_url,
                api_token=api_token,
            )
    return connectors


def create_app(
    *,
    settings: Settings | None = None,
    connectors: dict[str, Any] | None = None,
    groq_client: Any | None = None,
    session_store: InMemorySessionStore | None = None,
    rate_limiter: DevelopmentRateLimiter | None = None,
    knowledge_provider: Any | None = None,
) -> FastAPI:
    config = settings or Settings.from_environment()
    company_connectors = connectors if connectors is not None else _build_connectors(config)
    provider = groq_client
    if provider is None and config.groq_api_key and config.groq_model_id:
        try:
            provider = GroqChatClient(config.groq_api_key, config.groq_model_id, config.groq_timeout_seconds)
        except GroqConfigurationError:
            provider = None
    if session_store is not None:
        sessions = session_store
    elif os.getenv("VERCEL") == "1":
        sessions = StatelessSessionStore()
    else:
        sessions = InMemorySessionStore(config.session_ttl_seconds, config.max_history_messages)
    limiter = rate_limiter or DevelopmentRateLimiter(config.rate_limit_requests, config.rate_limit_window_seconds)
    remote_knowledge_provider = knowledge_provider
    if remote_knowledge_provider is None and (config.app_env == "production" or os.getenv("VERCEL") == "1"):
        remote_knowledge_provider = configured_knowledge_provider()
    service = ChatService(
        company_connectors, provider, sessions, config.max_history_messages,
        knowledge_provider=remote_knowledge_provider,
    )

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        yield

    app = FastAPI(title="AutomateGenie Universal Chat API", version="0.1.0", lifespan=lifespan)
    app.state.chat_service = service
    app.state.settings = config
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(config.cors_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )

    @app.get("/chat-api/health", response_model=HealthResponse, include_in_schema=False)
    @app.get("/api/chat-api/health", response_model=HealthResponse, include_in_schema=False)
    @app.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        # Liveness only: deliberately does not expose tenant/configuration details or
        # make a Groq/company API request.
        return HealthResponse()

    @app.post("/chat-api/internal/knowledge/search", include_in_schema=False)
    @app.post("/api/chat-api/internal/knowledge/search", include_in_schema=False)
    @app.post("/internal/knowledge/search", include_in_schema=False)
    async def internal_knowledge_search(body: InternalKnowledgeRequest, request: Request) -> dict[str, Any]:
        expected_key = os.getenv("KNOWLEDGE_API_SHARED_SECRET", "")
        supplied_key = request.headers.get("authorization", "")
        scheme, _, supplied_secret = supplied_key.partition(" ")
        if not expected_key or scheme.lower() != "bearer" or not hmac.compare_digest(supplied_secret, expected_key):
            raise HTTPException(status_code=401, detail="Knowledge API authentication required.")
        company_code = body.company_code.upper()
        tenant_id = body.tenant_id.upper()
        if tenant_id != company_code or company_code not in {"BIOMAN", "ROCOTILE"}:
            raise HTTPException(status_code=403, detail="Knowledge access is unavailable.")
        tenant_config = config.tenant_registry.get(tenant_id, {})
        if tenant_config.get("active") is not True:
            raise HTTPException(status_code=404, detail="Knowledge access is unavailable.")
        if body.public_only and any(tenant_config.get(flag) is not True for flag in ("public_session_enabled", "public_knowledge_only")):
            raise HTTPException(status_code=403, detail="Knowledge access is unavailable.")
        try:
            records = search_approved_knowledge(company_code, body.query, public_only=body.public_only)
        except KnowledgeFileError:
            raise HTTPException(status_code=503, detail="Knowledge is temporarily unavailable.") from None
        return {
            "company_code": company_code,
            "records": [
                {"record_id": item.record_id, "topic": item.topic, "question": item.question,
                 "answer": item.answer, "language": item.language, "approved": True,
                 "public": body.public_only or False}
                for item in records
            ],
        }

    @app.post("/dev/session", response_model=DevSessionResponse)
    async def dev_session(request: Request) -> DevSessionResponse:
        # This bootstrap is for a local Vite development server only. It is
        # disabled by default and refuses remote clients or non-local origins.
        if config.app_env == "production" or not config.dev_session_enabled:
            raise HTTPException(status_code=404, detail="Not found.")
        client_host = request.client.host if request.client else ""
        try:
            is_loopback_client = ipaddress.ip_address(client_host).is_loopback
        except ValueError:
            is_loopback_client = client_host.lower() == "localhost"
        origin = request.headers.get("origin", "")
        parsed_origin = urlsplit(origin)
        is_loopback_origin = (
            origin in config.cors_origins
            and parsed_origin.scheme == "http"
            and parsed_origin.hostname in {"localhost", "127.0.0.1", "::1"}
        )
        if not is_loopback_client or not is_loopback_origin:
            raise HTTPException(status_code=403, detail="Local development session is unavailable.")
        if not limiter.allow(client_host):
            raise HTTPException(status_code=429, detail="Too many requests. Please try again shortly.")

        tenant_id = config.dev_tenant_id
        tenant_config = config.tenant_registry.get(tenant_id, {})
        signing_key = config.signing_keys.get(tenant_id)
        connector_name = tenant_config.get("connector_key", tenant_id)
        if (
            tenant_config.get("active") is not True
            or not signing_key
            or connector_name not in company_connectors
        ):
            raise HTTPException(status_code=404, detail="Local development session is unavailable.")
        expires_in = 300
        access_token = mint_tenant_token(
            tenant_id,
            signing_key,
            expires_at=int(time.time()) + expires_in,
            origin=origin,
        )
        company_code = str(tenant_config.get("company_code", tenant_id))
        return DevSessionResponse(
            access_token=access_token,
            expires_in=expires_in,
            company_code=company_code,
        )

    @app.post("/chat-api/public/session", response_model=PublicSessionResponse, include_in_schema=False)
    @app.post("/api/chat-api/public/session", response_model=PublicSessionResponse, include_in_schema=False)
    @app.post("/public/session", response_model=PublicSessionResponse)
    async def public_session(request: Request) -> PublicSessionResponse:
        # Public sessions are fixed to a server-configured tenant and require
        # exact HTTPS origin binding plus explicit public-data declarations.
        if config.app_env != "production" or not config.public_session_enabled:
            raise HTTPException(status_code=404, detail="Not found.")
        client_host = request.client.host if request.client else "unknown"
        origin = request.headers.get("origin", "")
        parsed_origin = urlsplit(origin)
        if (
            origin not in config.public_origins
            or origin not in config.cors_origins
            or parsed_origin.scheme != "https"
            or not parsed_origin.hostname
        ):
            raise HTTPException(status_code=403, detail="Public chat session is unavailable.")
        if not limiter.allow(client_host):
            raise HTTPException(status_code=429, detail="Too many requests. Please try again shortly.")

        tenant_id = config.public_tenant_id
        tenant_config = config.tenant_registry.get(tenant_id, {})
        signing_key = config.signing_keys.get(tenant_id)
        connector_name = tenant_config.get("connector_key", tenant_id)
        if (
            tenant_config.get("active") is not True
            or tenant_config.get("public_session_enabled") is not True
            or tenant_config.get("public_knowledge_only") is not True
            or tenant_config.get("public_products") is not True
            or not signing_key
            or connector_name not in company_connectors
        ):
            raise HTTPException(status_code=404, detail="Public chat session is unavailable.")
        expires_in = 300
        access_token = mint_tenant_token(
            tenant_id,
            signing_key,
            expires_at=int(time.time()) + expires_in,
            origin=origin,
            scope="public",
        )
        return PublicSessionResponse(
            access_token=access_token,
            expires_in=expires_in,
            company_code=str(tenant_config.get("company_code", tenant_id)),
        )

    @app.post("/chat-api/chat", response_model=ChatResponse, include_in_schema=False)
    @app.post("/api/chat-api/chat", response_model=ChatResponse, include_in_schema=False)
    @app.post("/chat", response_model=ChatResponse)
    async def chat(body: ChatRequest, request: Request) -> ChatResponse:
        client_host = request.client.host if request.client else "unknown"
        if not limiter.allow(client_host):
            raise HTTPException(status_code=429, detail="Too many requests. Please try again shortly.")

        authorization = request.headers.get("authorization", "")
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token:
            raise HTTPException(status_code=401, detail="A valid chat session token is required.")
        try:
            principal = verify_tenant_token(
                token,
                config.signing_keys,
                config.tenant_registry,
                request_origin=request.headers.get("origin"),
            )
        except TenantTokenError:
            raise HTTPException(status_code=401, detail="A valid chat session token is required.") from None

        if len(body.message) > config.max_message_length:
            raise HTTPException(status_code=413, detail="Message is too long.")
        try:
            return await service.answer(
                tenant_id=principal.tenant_id,
                company_code=principal.company_code,
                connector_name=principal.connector_name,
                message=body.message,
                session_id=body.session_id,
                public_only=principal.public_only,
            )
        except SessionTenantMismatch:
            raise HTTPException(status_code=404, detail="Conversation is unavailable.") from None
        except ChatDependencyError as exc:
            logger.warning("Chat dependency unavailable: %s", str(exc))
            raise HTTPException(status_code=503, detail="AI chatbot is temporarily unavailable. Please try again later.") from None
        except Exception:
            logger.error("Unexpected chat request failure")
            raise HTTPException(status_code=500, detail="Chat could not process the request.") from None

    return app


def _create_runtime_app() -> FastAPI:
    configuration_valid = True
    configuration_error = None
    try:
        runtime_app = create_app()
    except ConfigurationError as exc:
        # Keep health probes available, but make the effective fallback visible
        # in server logs instead of silently hiding invalid production settings.
        configuration_valid = False
        configuration_error = str(exc)
        runtime_app = create_app(settings=Settings())

    runtime_app.state.configuration_valid = configuration_valid
    config = runtime_app.state.settings
    bioman_config = config.tenant_registry.get("BIOMAN", {})
    bioman_publicly_enabled = all(
        bioman_config.get(flag) is True
        for flag in ("public_session_enabled", "public_knowledge_only", "public_products")
    )
    session_route_registered = any(
        getattr(route, "path", None) == "/api/chat-api/public/session"
        for route in runtime_app.routes
    )
    logger.warning(
        "CHATBOT_RUNTIME_DIAGNOSTICS app_env=%s public_session_enabled=%s "
        "bioman_active=%s bioman_publicly_enabled=%s "
        "public_session_route_registered=%s configuration_valid=%s",
        config.app_env,
        config.public_session_enabled,
        bioman_config.get("active") is True,
        bioman_publicly_enabled,
        session_route_registered,
        configuration_valid,
    )
    if configuration_error:
        # ConfigurationError messages name settings/tenant IDs only; never log
        # environment values, signing keys, API tokens, or credentials.
        logger.error("CHATBOT_CONFIGURATION_ERROR %s", configuration_error)
    return runtime_app


app = _create_runtime_app()
