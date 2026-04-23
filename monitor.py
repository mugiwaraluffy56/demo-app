"""
Middleware that logs every request/response from the demo app into api-monitor.
Fire-and-forget — never blocks or crashes the app.
"""

import os
import time
import asyncio
import httpx
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

MONITOR_URL = os.environ.get("MONITOR_URL", "http://localhost:8000")
INGEST_URL  = f"{MONITOR_URL}/v1/logs"

# Paths to skip — avoid logging calls to api-monitor itself
_SKIP = {"/health", "/static", "/docs", "/openapi.json", "/redoc"}


class ApiMonitorMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, api_key: str):
        super().__init__(app)
        self.headers = {"Authorization": f"Bearer {api_key}"}

    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip noise
        if any(request.url.path.startswith(p) for p in _SKIP):
            return await call_next(request)

        body_bytes = await request.body()
        req_body = body_bytes.decode("utf-8", errors="replace") if body_bytes else None

        start = time.perf_counter()
        error_msg = None

        try:
            response = await call_next(request)
        except Exception as exc:
            error_msg = str(exc)
            raise
        finally:
            latency_ms = (time.perf_counter() - start) * 1000

        # Buffer response body
        chunks = []
        async for chunk in response.body_iterator:
            chunks.append(chunk if isinstance(chunk, bytes) else chunk.encode())
        resp_bytes = b"".join(chunks)

        rebuilt = Response(
            content=resp_bytes,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.media_type,
        )

        asyncio.ensure_future(
            self._send(request, rebuilt, req_body, resp_bytes, latency_ms, error_msg)
        )
        return rebuilt

    async def _send(self, req, resp, req_body, resp_bytes, latency_ms, error):
        resp_body = resp_bytes.decode("utf-8", errors="replace")[:2000] if resp_bytes else None
        payload = {
            "method": req.method,
            "url": str(req.url),
            "path": req.url.path,
            "query_params": dict(req.query_params) or None,
            "request_headers": _redact(dict(req.headers)),
            "request_body": req_body,
            "status_code": resp.status_code,
            "response_headers": _redact(dict(resp.headers)),
            "response_body": resp_body,
            "latency_ms": round(latency_ms, 2),
            "error": error,
            "source_ip": req.client.host if req.client else None,
            "tags": ["demo-app"],
        }
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                await client.post(INGEST_URL, json=payload, headers=self.headers)
        except Exception:
            pass


def _redact(headers: dict) -> dict:
    sensitive = {"authorization", "cookie", "set-cookie"}
    return {k: ("***" if k.lower() in sensitive else v) for k, v in headers.items()}
