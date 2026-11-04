from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Any


class TenantTokenError(ValueError):
    pass


@dataclass(frozen=True)
class TenantPrincipal:
    tenant_id: str
    company_code: str
    connector_name: str
    public_only: bool = False


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def mint_tenant_token(
    tenant_id: str,
    signing_key: str,
    *,
    expires_at: int,
    origin: str | None = None,
    scope: str = "tenant",
) -> str:
    """Server-side helper for a company's trusted token-minting service."""
    issued_at = int(time.time())
    if expires_at <= issued_at or expires_at - issued_at > 900:
        raise ValueError("tenant token expiry must be within 15 minutes")
    if scope not in {"tenant", "public"}:
        raise ValueError("tenant token scope is invalid")
    claims: dict[str, Any] = {"tenant_id": tenant_id, "exp": int(expires_at), "iat": issued_at, "scope": scope}
    if origin:
        claims["origin"] = origin
    payload = _b64encode(json.dumps(claims, separators=(",", ":")).encode())
    signature = hmac.new(signing_key.encode(), payload.encode(), hashlib.sha256).digest()
    return payload + "." + _b64encode(signature)


def verify_tenant_token(
    token: str,
    signing_keys: dict[str, str],
    registry: dict[str, dict[str, Any]],
    *,
    request_origin: str | None = None,
    now: int | None = None,
) -> TenantPrincipal:
    try:
        payload_segment, signature_segment = token.split(".", 1)
        claims = json.loads(_b64decode(payload_segment))
        tenant_id = claims["tenant_id"]
        exp = int(claims["exp"])
        issued_at = int(claims["iat"])
        key = signing_keys[tenant_id]
        tenant_config = registry[tenant_id]
    except (ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        raise TenantTokenError("invalid token") from exc

    expected = hmac.new(key.encode(), payload_segment.encode(), hashlib.sha256).digest()
    try:
        actual = _b64decode(signature_segment)
    except (ValueError, TypeError) as exc:
        raise TenantTokenError("invalid token") from exc
    if not hmac.compare_digest(expected, actual):
        raise TenantTokenError("invalid token")
    current_time = int(time.time()) if now is None else now
    if exp <= current_time or issued_at > current_time + 30 or exp - issued_at > 900:
        raise TenantTokenError("expired token")
    if tenant_config.get("active") is not True:
        raise TenantTokenError("inactive tenant")
    scope = claims.get("scope", "tenant")
    if scope not in {"tenant", "public"}:
        raise TenantTokenError("invalid token scope")
    bound_origin = claims.get("origin")
    if bound_origin and request_origin != bound_origin:
        raise TenantTokenError("origin mismatch")
    public_only = scope == "public"
    if public_only and (
        not bound_origin
        or tenant_config.get("public_session_enabled") is not True
        or tenant_config.get("public_knowledge_only") is not True
        or tenant_config.get("public_products") is not True
    ):
        raise TenantTokenError("public access is not configured")
    connector_name = tenant_config.get("connector_key", tenant_id)
    if not isinstance(connector_name, str) or not connector_name:
        raise TenantTokenError("connector is not configured")
    company_code = tenant_config.get("company_code", tenant_id)
    if not isinstance(company_code, str) or not company_code:
        raise TenantTokenError("company code is not configured")
    return TenantPrincipal(tenant_id, company_code, connector_name, public_only)
