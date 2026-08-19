from redis.exceptions import RedisError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

WINDOW_SECONDS = 60


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, requests_per_minute: int) -> None:
        super().__init__(app)
        self._limit = requests_per_minute

    async def dispatch(self, request: Request, call_next):
        client_host = request.client.host if request.client else "unknown"
        key = f"ratelimit:{client_host}"
        cache = request.app.state.cache

        try:
            count = await cache.incr(key)
            if count == 1:
                await cache.expire(key, WINDOW_SECONDS)
        except RedisError:
            # Fail open — ARCHITECTURE.md §13: Redis down means slower/uncached,
            # never a hard failure of the gateway itself.
            return await call_next(request)

        if count > self._limit:
            return JSONResponse(
                {"code": "rate_limited", "message": "Too many requests"}, status_code=429
            )

        return await call_next(request)
