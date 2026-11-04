"""Vercel Python Function entry point for the existing FastAPI application."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from chatbot.main import app as fastapi_app  # noqa: E402


_CHATBOT_PATHS = {
    "/api/chat-api/health",
    "/api/chat-api/chat",
    "/api/chat-api/public/session",
    "/api/chat-api/internal/knowledge/search",
}


class VercelRewritePath:
    """Restore the original route after Vercel rewrites it to the /api function."""

    def __init__(self, application: Any) -> None:
        self.application = application

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.application(scope, receive, send)
            return

        query_items = parse_qsl(scope.get("query_string", b"").decode("latin-1"), keep_blank_values=True)
        forwarded_paths = [value for key, value in query_items if key == "__vercel_path"]
        if not forwarded_paths:
            await self.application(scope, receive, send)
            return

        path = forwarded_paths[0]
        if len(forwarded_paths) != 1 or path not in _CHATBOT_PATHS:
            await self._bad_request(send)
            return

        clean_query = urlencode([(key, value) for key, value in query_items if key != "__vercel_path"])
        rewritten_scope = dict(scope)
        rewritten_scope["path"] = path
        rewritten_scope["raw_path"] = path.encode("ascii")
        rewritten_scope["query_string"] = clean_query.encode("latin-1")
        await self.application(rewritten_scope, receive, send)

    @staticmethod
    async def _bad_request(send: Any) -> None:
        body = b'{"detail":"Invalid API route."}'
        await send({
            "type": "http.response.start",
            "status": 400,
            "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode("ascii"))],
        })
        await send({"type": "http.response.body", "body": body})


app = VercelRewritePath(fastapi_app)

