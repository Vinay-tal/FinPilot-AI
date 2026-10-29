import time
from collections import defaultdict
from typing import Dict, List, Tuple
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette import status
from app.core.config import settings

MAX_BODY_SIZE_BYTES = 15 * 1024 * 1024  # 15 MB max request size

class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Rejects incoming HTTP requests that exceed maximum allowable payload size."""
    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                length = int(content_length)
                if length > MAX_BODY_SIZE_BYTES:
                    return JSONResponse(
                        status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                        content={
                            "status_code": 413,
                            "error_code": "PAYLOAD_TOO_LARGE",
                            "message": f"Request body exceeds maximum size limit of {MAX_BODY_SIZE_BYTES // (1024 * 1024)} MB.",
                            "details": {"max_bytes": MAX_BODY_SIZE_BYTES, "received_bytes": length},
                            "path": request.url.path,
                        },
                    )
            except ValueError:
                pass
        return await call_next(request)

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Applies modern defensive HTTP security headers to all server responses."""
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        return response

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    In-memory sliding window rate limiter.
    Distinguishes sensitive endpoints (auth, uploads, LLM) from standard queries.
    """
    def __init__(self, app):
        super().__init__(app)
        # client_key -> list of request timestamps
        self.requests: Dict[str, List[float]] = defaultdict(list)
        # Rate limit configurations: (window_seconds, max_requests)
        self.sensitive_routes = {
            "/api/v1/auth/login": (60, 20),
            "/api/v1/auth/register": (60, 15),
            "/api/v1/auth/demo-login": (60, 30),
            "/api/v1/ingestion/csv-preview": (60, 20),
            "/api/v1/ingestion/csv-import": (60, 20),
            "/api/v1/copilot/conversations": (60, 40),
        }
        self.default_limit = (60, 180)  # 180 requests/min for general API routes

    def _get_client_key(self, request: Request) -> str:
        # Prefer Authorization token subject or X-Forwarded-For if available
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            return f"token:{auth_header[7:30]}"
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return f"ip:{forwarded.split(',')[0].strip()}"
        client_ip = request.client.host if request.client else "unknown"
        return f"ip:{client_ip}"

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        # Exclude documentation and health check endpoints
        if path in {"/docs", "/redoc", "/openapi.json", "/api/v1/health", "/api/v1/ready", "/"}:
            return await call_next(request)

        # In hermetic test execution, avoid rate-limiting mock test loops unless explicitly tested
        if settings.ENVIRONMENT == "testing" and not request.headers.get("x-test-rate-limit"):
            return await call_next(request)

        now = time.time()
        client_key = self._get_client_key(request)
        route_key = f"{client_key}:{path}"

        window_seconds, max_reqs = self.default_limit
        for route_prefix, limit_tuple in self.sensitive_routes.items():
            if path.startswith(route_prefix):
                window_seconds, max_reqs = limit_tuple
                break

        timestamps = self.requests[route_key]
        # Prune old timestamps
        cutoff = now - window_seconds
        while timestamps and timestamps[0] < cutoff:
            timestamps.pop(0)

        if len(timestamps) >= max_reqs:
            retry_after = int(window_seconds - (now - timestamps[0])) + 1
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "status_code": 429,
                    "error_code": "RATE_LIMIT_EXCEEDED",
                    "message": "Too many requests. Please slow down and try again.",
                    "details": {
                        "limit": max_reqs,
                        "window_seconds": window_seconds,
                        "retry_after_seconds": retry_after,
                    },
                    "path": path,
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(max_reqs),
                    "X-RateLimit-Remaining": "0",
                },
            )

        timestamps.append(now)
        response: Response = await call_next(request)
        remaining = max(0, max_reqs - len(timestamps))
        response.headers["X-RateLimit-Limit"] = str(max_reqs)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response
