import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.api.deps import allow_signed_in
from app.metrics.cache import cache
from app.metrics.loop import subscribe, unsubscribe
from app.metrics.traffic import traffic
from app.schemas import MetricHistory, MetricPoint

router = APIRouter(prefix="/api", dependencies=[Depends(allow_signed_in)])


def _event(name: str, payload: object) -> str:
    return f"event: {name}\ndata: {json.dumps(payload)}\n\n"


@router.get("/metrics", response_model=MetricHistory)
async def metric_history() -> MetricHistory:
    points = [MetricPoint.model_validate(item) for item in await cache.all()]
    return MetricHistory(
        samples=points,
        inflight=traffic.inflight,
        requests_last_10s=traffic.recent(),
    )


@router.get("/metrics/events")
async def metric_events() -> StreamingResponse:
    async def stream():
        queue = subscribe()
        try:
            history = [item.model_dump(mode="json") for item in (await metric_history()).samples]
            yield _event("history", history)
            while True:
                point = await queue.get()
                yield _event("sample", point)
        finally:
            unsubscribe(queue)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
