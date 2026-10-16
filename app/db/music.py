from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.media_link import OUTPUT, attach_media, models_for
from app.db.models import MusicJob, utcnow


async def insert_music(session: AsyncSession, job: MusicJob) -> MusicJob:
    session.add(job)
    await session.flush()
    return job


async def get_music(session: AsyncSession, job_id: int) -> MusicJob | None:
    result = await session.execute(select(MusicJob).where(MusicJob.id == job_id))
    job = result.scalar_one_or_none()
    if job is not None:
        await attach_media(session, [job])
    return job


async def mark_failed(session: AsyncSession, job_id: int, code: str, message: str) -> None:
    """Record a music failure. The caller commits."""
    result = await session.execute(select(MusicJob).where(MusicJob.id == job_id))
    job = result.scalar_one_or_none()
    if job is None or job.status in {"succeeded", "failed"}:
        return
    job.status = "failed"
    job.error_code = code
    job.error_message = message
    job.finished_at = utcnow()


async def mark_succeeded(session: AsyncSession, job_id: int, size_bytes: int, seed: int) -> None:
    """Record a finished music job. The caller commits."""
    job = await get_music(session, job_id)
    if job is None or job.status == "failed":
        return
    outputs = models_for(job, OUTPUT)
    if not outputs:
        return
    job.status = "succeeded"
    job.seed = seed
    job.error_code = None
    job.error_message = None
    job.finished_at = utcnow()
    outputs[0].size_bytes = size_bytes
