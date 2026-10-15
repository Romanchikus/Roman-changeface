from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.db.filters import PAGE_LIMIT, JobFilter
from app.db.models import Job, Media, Thumbnail, utcnow
from app.inference.pipeline import InferenceResult


async def insert_job(session: AsyncSession, job: Job) -> Job:
    session.add(job)
    await session.flush()
    return job


def _load_media():
    return (
        joinedload(Job.input_image).joinedload(Media.thumbnail),
        joinedload(Job.input_image_2).joinedload(Media.thumbnail),
        joinedload(Job.input_image_3).joinedload(Media.thumbnail),
        joinedload(Job.input_video).joinedload(Media.thumbnail),
        joinedload(Job.output_video).joinedload(Media.thumbnail),
    )


async def latest_task(session: AsyncSession) -> Job | None:
    running = (
        select(Job)
        .where(Job.status.in_(("running", "queued")))
        .order_by(Job.created_at.desc())
        .limit(1)
    )
    result = await session.execute(running)
    job = result.scalar_one_or_none()
    if job is not None:
        return job
    latest = select(Job).order_by(Job.created_at.desc()).limit(1)
    result = await session.execute(latest)
    return result.scalar_one_or_none()


async def get_job(session: AsyncSession, job_id: int) -> Job | None:
    stmt = select(Job).where(Job.id == job_id).options(*_load_media())
    result = await session.execute(stmt)
    return result.unique().scalar_one_or_none()


async def list_jobs(session: AsyncSession, job_filter: JobFilter) -> list[Job]:
    """List jobs using a fastapi-filter."""
    stmt = select(Job).options(*_load_media())
    stmt = job_filter.sort(job_filter.filter(stmt)).limit(PAGE_LIMIT)
    result = await session.execute(stmt)
    return list(result.unique().scalars().all())


async def mark_running(session: AsyncSession, job: Job) -> None:
    """Record that the job started. The caller commits."""
    job.status = "running"
    job.started_at = utcnow()


async def mark_failed(session: AsyncSession, job_id: int, code: str, message: str) -> None:
    """Record a failure. The caller commits."""
    stmt = select(Job).where(Job.id == job_id)
    result = await session.execute(stmt)
    job = result.scalar_one_or_none()
    if job is None or job.status in {"succeeded", "failed"}:
        return
    job.status = "failed"
    job.error_code = code
    job.error_message = message
    job.finished_at = utcnow()


async def mark_succeeded(
    session: AsyncSession,
    job_id: int,
    result: InferenceResult,
    size_bytes: int | None,
    thumb: str | None,
) -> None:
    """Record a finished swap. The caller commits."""
    job = await get_job(session, job_id)
    if job is None or job.status == "failed":
        return
    job.status = "succeeded"
    job.model_name = result.model_name
    job.detector_name = result.detector_name
    job.inference_ms = result.inference_ms
    job.simulated = result.simulated
    job.error_code = None
    job.error_message = None
    job.finished_at = utcnow()
    if size_bytes is not None:
        job.output_video.size_bytes = size_bytes
    if thumb is not None and job.output_video.thumbnail is None:
        session.add(Thumbnail(media_id=job.output_video.id, path=thumb))
