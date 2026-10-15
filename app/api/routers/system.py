from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import allow_signed_in
from app.db.jobs import latest_task
from app.db.models import utcnow
from app.db.session import get_db
from app.resources import sample_machine
from app.schemas import LimitsOut, ResourcesOut
from app.shared.config import get_settings

router = APIRouter(prefix="/api")


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def _elapsed_ms(job) -> int | None:
    start = job.started_at or job.created_at
    if start is None:
        return None
    end = job.finished_at if job.status in {"succeeded", "failed"} else utcnow()
    return max(0, int((end - start).total_seconds() * 1000))


@router.get("/resources", response_model=ResourcesOut)
async def resources(
    db: AsyncSession = Depends(get_db),
    _: object = Depends(allow_signed_in),
) -> ResourcesOut:
    machine = await sample_machine()
    job = await latest_task(db)
    return ResourcesOut(
        cpu_percent=machine.cpu_percent,
        ram_used_bytes=machine.ram_used_bytes,
        ram_total_bytes=machine.ram_total_bytes,
        vram_used_bytes=machine.vram_used_bytes,
        vram_total_bytes=machine.vram_total_bytes,
        gpu_util_percent=machine.gpu_util_percent,
        job_id=job.id if job else None,
        job_status=job.status if job else None,
        elapsed_ms=_elapsed_ms(job) if job else None,
    )


@router.get("/limits", response_model=LimitsOut)
def limits() -> LimitsOut:
    settings = get_settings()
    return LimitsOut(
        max_image_bytes=settings.max_image_bytes,
        max_video_bytes=settings.max_video_bytes,
        max_video_duration_sec=settings.max_video_duration_sec,
        inference_backend=settings.inference_backend,
    )
