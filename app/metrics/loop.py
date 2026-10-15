import asyncio
import logging

from app.db.metrics import save_samples
from app.db.models import utcnow
from app.db.session import session_scope
from app.metrics.cache import cache
from app.metrics.traffic import traffic
from app.resources import sample_machine

log = logging.getLogger(__name__)

_subscribers: set[asyncio.Queue[dict]] = set()
_flush_lock = asyncio.Lock()


def subscribe() -> asyncio.Queue[dict]:
    queue: asyncio.Queue[dict] = asyncio.Queue(maxsize=32)
    _subscribers.add(queue)
    return queue


def unsubscribe(queue: asyncio.Queue[dict]) -> None:
    _subscribers.discard(queue)


def _publish(point: dict) -> None:
    for queue in _subscribers:
        if queue.full():
            try:
                queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
        queue.put_nowait(point)


async def _point() -> dict:
    machine = await sample_machine()
    return {
        "sampled_at": utcnow().isoformat(),
        "cpu_percent": machine.cpu_percent,
        "ram_used_bytes": machine.ram_used_bytes,
        "ram_total_bytes": machine.ram_total_bytes,
        "vram_used_bytes": machine.vram_used_bytes,
        "vram_total_bytes": machine.vram_total_bytes,
        "gpu_util_percent": machine.gpu_util_percent,
    }


async def persist() -> None:
    async with _flush_lock:
        points = await cache.all()
        if not points:
            return
        async with session_scope() as session:
            await save_samples(session, points)


async def run(stop: asyncio.Event) -> None:
    while not stop.is_set():
        try:
            point = await _point()
            await cache.add(point)
            _publish(point)
            if traffic.idle():
                await persist()
        except Exception:
            log.exception("resource sample failed")
        try:
            await asyncio.wait_for(stop.wait(), timeout=1)
        except TimeoutError:
            continue
