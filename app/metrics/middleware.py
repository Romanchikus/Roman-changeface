from app.metrics.traffic import traffic


class TrafficMiddleware:
    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        path = scope.get("path", "")
        if path.startswith("/api/metrics") or scope.get("method") == "OPTIONS":
            await self.app(scope, receive, send)
            return
        traffic.enter()
        try:
            await self.app(scope, receive, send)
        finally:
            traffic.leave()
