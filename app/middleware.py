"""Small in-process limits for the local/demo API."""

from collections import defaultdict, deque
from time import monotonic
from starlette.responses import JSONResponse


class RequestLimitsMiddleware:
    """Bound request bodies and apply per-IP fixed-window API limits."""

    def __init__(
        self,
        app,
        max_body_bytes: int = 65536,
        route_limits: dict[str, int] | None = None,
        window_seconds: int = 60,
    ):
        self.app = app
        self.max_body_bytes = max_body_bytes
        self.route_limits = route_limits or {"/api/ingest": 10, "/api/chat": 30}
        self.window_seconds = window_seconds
        self.hits: dict[tuple[str, str], deque[float]] = defaultdict(deque)

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = {key.lower(): value for key, value in scope.get("headers", [])}
        content_length = headers.get(b"content-length")
        if content_length:
            try:
                if int(content_length) > self.max_body_bytes:
                    await JSONResponse(
                        {"detail": "Request body exceeds the allowed size."}, status_code=413
                    )(scope, receive, send)
                    return
            except ValueError:
                await JSONResponse(
                    {"detail": "Invalid Content-Length header."}, status_code=400
                )(scope, receive, send)
                return

        path = scope.get("path", "")
        limit = self.route_limits.get(path) if scope.get("method") == "POST" else None
        if limit:
            client = scope.get("client") or ("unknown", 0)
            key = (path, client[0])
            now = monotonic()
            recent = self.hits[key]
            while recent and now - recent[0] >= self.window_seconds:
                recent.popleft()
            if len(recent) >= limit:
                await JSONResponse(
                    {"detail": "Rate limit exceeded. Try again shortly."},
                    status_code=429,
                    headers={"Retry-After": str(self.window_seconds)},
                )(scope, receive, send)
                return
            recent.append(now)

        body = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            body.extend(message.get("body", b""))
            if len(body) > self.max_body_bytes:
                await JSONResponse(
                    {"detail": "Request body exceeds the allowed size."}, status_code=413
                )(scope, receive, send)
                return
            if not message.get("more_body", False):
                break

        body_sent = False

        async def replay_receive():
            nonlocal body_sent
            if not body_sent:
                body_sent = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}
            return await receive()

        await self.app(scope, replay_receive, send)
