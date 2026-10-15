import asyncio
from collections.abc import Awaitable, Callable
from concurrent.futures import ThreadPoolExecutor

from app.db.session import dispose_loop_engine
from app.shared.errors import GpuBusy
from app.worker.celery_app import celery_app
from app.worker.gpu_lock import gpu_slot


def _drive(factory: Callable[[], Awaitable[None]]) -> None:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        asyncio.run(factory())
        return
    with ThreadPoolExecutor(max_workers=1) as pool:
        pool.submit(lambda: asyncio.run(factory())).result()


async def _run_locked(job_id: int) -> None:
    from app.services.jobs import execute_swap

    try:
        await execute_swap(job_id)
    finally:
        await dispose_loop_engine()


@celery_app.task(bind=True, name="changeface.swap", max_retries=60)
def run_swap(self, job_id: int) -> None:  # type: ignore[no-untyped-def]
    """Run one queued swap."""
    try:
        with gpu_slot():
            _drive(lambda: _run_locked(job_id))
    except GpuBusy as exc:
        raise self.retry(exc=exc, countdown=2) from exc
