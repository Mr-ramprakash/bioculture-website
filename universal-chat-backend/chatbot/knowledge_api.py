"""HMAC-authenticated client for the standalone EC2 Knowledge API."""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import os
import re
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from .connectors.base import KnowledgeRecord

logger = logging.getLogger("automategenie.knowledge")
KNOWLEDGE_API_PATH = "/knowledge/search"
BIOMAN_COMPANY_CODE = "BIOMAN"
MAX_QUERY_LENGTH = 2000
MAX_RESULTS = 5
MAX_RESPONSE_BYTES = 256_000
_KEY_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,40}$")


class KnowledgeApiError(RuntimeError):
    pass


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        # Never forward service authentication headers to a redirect target.
        return None


def _open_without_redirect(request: urllib.request.Request, timeout: float):
    opener = urllib.request.build_opener(_NoRedirectHandler)
    return opener.open(request, timeout=timeout)


def _hmac_headers(
    body: bytes,
    key_id: str,
    secret: str,
    timestamp: str,
    nonce: str,
) -> dict[str, str]:
    """Sign the EC2 service's canonical request and exact body bytes."""
    canonical = f"{timestamp}\n{nonce}\nPOST\n{KNOWLEDGE_API_PATH}\n".encode("ascii") + body
    signature = hmac.new(secret.encode("utf-8"), canonical, hashlib.sha256).hexdigest()
    return {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-Knowledge-Key-Id": key_id,
        "X-Knowledge-Timestamp": timestamp,
        "X-Knowledge-Nonce": nonce,
        "X-Knowledge-Signature": signature,
    }


def _signed_request(url: str, body: bytes, key_id: str, secret: str, timeout: float) -> bytes:
    """POST a bounded JSON request to EC2 using a fresh timestamp and nonce."""
    timestamp = str(int(time.time()))
    nonce = secrets.token_urlsafe(24)
    request = urllib.request.Request(
        url,
        data=body,
        headers=_hmac_headers(body, key_id, secret, timestamp, nonce),
        method="POST",
    )
    try:
        with _open_without_redirect(request, timeout=timeout) as response:
            raw = response.read(MAX_RESPONSE_BYTES + 1)
        if len(raw) > MAX_RESPONSE_BYTES:
            raise KnowledgeApiError("Knowledge service response is too large")
        return raw
    except urllib.error.HTTPError as exc:
        if exc.code in {400, 401, 403, 404, 413, 415, 422}:
            logger.warning("Knowledge service rejected request status=%s", exc.code)
            raise KnowledgeApiError("Knowledge request was rejected") from exc
        logger.warning("Knowledge service unavailable status=%s", exc.code)
        raise KnowledgeApiError("Knowledge service is unavailable") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        logger.warning("Knowledge service unavailable category=%s", type(exc).__name__)
        raise KnowledgeApiError("Knowledge service is unavailable") from exc


class KnowledgeServiceClient:
    """Client for the fixed, public BIOMAN Knowledge API endpoint."""

    def __init__(self, endpoint_url: str, key_id: str, hmac_secret: str, timeout_seconds: float = 5.0) -> None:
        parsed = urllib.parse.urlsplit(endpoint_url)
        # Accessing .port forces urllib to validate malformed port text.
        _ = parsed.port
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.path != KNOWLEDGE_API_PATH
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("Knowledge service URL must be an HTTPS /knowledge/search endpoint")
        if not _KEY_ID_RE.fullmatch(key_id):
            raise ValueError("Knowledge service key ID is invalid")
        if len(hmac_secret.encode("utf-8")) < 32:
            raise ValueError("Knowledge service HMAC secret must be at least 32 bytes")
        if not 1 <= timeout_seconds <= 30:
            raise ValueError("Knowledge service timeout is out of range")
        self.url = endpoint_url
        self.key_id = key_id
        self.hmac_secret = hmac_secret
        self.timeout_seconds = timeout_seconds

    async def search(self, company_code: str, query: str, *, public_only: bool = False) -> list[KnowledgeRecord]:
        # This EC2 deployment serves BIOMAN only. Never let another verified
        # tenant select its data or issue an ambiguous request to this service.
        if company_code.upper() != BIOMAN_COMPANY_CODE:
            return []
        clean_query = query.strip()
        if not clean_query or len(clean_query) > MAX_QUERY_LENGTH:
            raise KnowledgeApiError("Knowledge query is invalid")
        body = json.dumps({"query": clean_query}, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        raw = await asyncio.to_thread(
            _signed_request, self.url, body, self.key_id, self.hmac_secret, self.timeout_seconds,
        )
        try:
            data: Any = json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise KnowledgeApiError("Knowledge service returned invalid data") from exc
        if (
            not isinstance(data, dict)
            or data.get("company_code") != BIOMAN_COMPANY_CODE
            or not isinstance(data.get("records"), list)
        ):
            raise KnowledgeApiError("Knowledge service returned invalid data")

        records: list[KnowledgeRecord] = []
        for row in data["records"][:MAX_RESULTS]:
            if (
                not isinstance(row, dict)
                or row.get("approved") is not True
                or row.get("status") != "approved"
                or row.get("public") is not True
            ):
                continue
            fields = (row.get("record_id"), row.get("topic"), row.get("question"), row.get("answer"))
            if any(not isinstance(value, str) or not value.strip() for value in fields):
                continue
            language = row.get("language", "en")
            if not isinstance(language, str):
                continue
            records.append(KnowledgeRecord(*fields, language or "en"))
        return records


class KnowledgeServiceProvider:
    """Adapter consumed by ChatService; no local fallback in production."""

    def __init__(self, client: KnowledgeServiceClient | None) -> None:
        self.client = client

    async def search(self, company_code: str, query: str, *, public_only: bool = False) -> list[KnowledgeRecord]:
        if self.client is None:
            raise KnowledgeApiError("Knowledge service is not configured")
        return await self.client.search(company_code, query, public_only=public_only)


def configured_knowledge_provider() -> KnowledgeServiceProvider:
    endpoint_url = os.getenv("KNOWLEDGE_SERVICE_URL", "").strip()
    key_id = os.getenv("KNOWLEDGE_SERVICE_KEY_ID", "").strip()
    # Preserve exact HMAC secret bytes and never include them in logs.
    hmac_secret = os.getenv("KNOWLEDGE_SERVICE_HMAC_SECRET", "")
    client = None
    if endpoint_url and key_id and hmac_secret:
        try:
            client = KnowledgeServiceClient(endpoint_url, key_id, hmac_secret)
        except ValueError:
            logger.warning("Knowledge service configuration is invalid")
    else:
        logger.warning("Knowledge service configuration is incomplete")
    return KnowledgeServiceProvider(client)
