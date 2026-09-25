"""Reject oversized request bodies before multipart parsing and block foreign origins."""

import asyncio

from starlette.responses import JSONResponse

ALLOWED_ORIGINS = {
    "http://127.0.0.1:5173",
    "http://localhost:5173",
    "http://127.0.0.1:8000",
    "http://localhost:8000",
}


class RequestGuards:
    def __init__(self, app, max_body_bytes: int):
        self.app = app
        self.max_body_bytes = max_body_bytes
        self.receiving = False

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        headers = dict(scope["headers"])
        origin = headers.get(b"origin", b"").decode("latin1")
        if origin and origin not in ALLOWED_ORIGINS:
            return await JSONResponse({"detail": "origin_not_allowed"}, 403)(scope, receive, send)
        if scope["method"] != "POST" or scope["path"] != "/documents":
            return await self.app(scope, receive, send)
        if self.receiving:
            return await JSONResponse({"detail": "upload_busy"}, 429)(scope, receive, send)
        self.receiving = True
        try:
            # Bound the entire multipart body even when Content-Length is absent or dishonest.
            body = bytearray()
            while True:
                try:
                    message = await asyncio.wait_for(receive(), timeout=15)
                except TimeoutError:
                    return await JSONResponse({"detail": "upload_timeout"}, 408)(
                        scope, receive, send
                    )
                if message["type"] == "http.disconnect":
                    return
                block = message.get("body", b"")
                if len(body) + len(block) > self.max_body_bytes:
                    return await JSONResponse({"detail": "upload_limit"}, 413)(scope, receive, send)
                body.extend(block)
                if not message.get("more_body", False):
                    break
            delivered = False

            async def replay():
                nonlocal delivered
                if not delivered:
                    delivered = True
                    return {"type": "http.request", "body": bytes(body), "more_body": False}
                return await receive()

            await self.app(scope, replay, send)
        finally:
            self.receiving = False
