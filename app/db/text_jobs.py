from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import TextJob, utcnow


async def insert_text_job(session: AsyncSession, job: TextJob) -> TextJob:
    session.add(job)
    await session.flush()
    return job


async def get_text_job(session: AsyncSession, job_id: int) -> TextJob | None:
    result = await session.execute(select(TextJob).where(TextJob.id == job_id))
    return result.scalar_one_or_none()


async def mark_failed(session: AsyncSession, job_id: int, code: str, message: str) -> None:
    """Record a text failure. The caller commits."""
    result = await session.execute(select(TextJob).where(TextJob.id == job_id))
    job = result.scalar_one_or_none()
    if job is None or job.status in {"succeeded", "failed"}:
        return
    job.status = "failed"
    job.error_code = code
    job.error_message = message
    job.finished_at = utcnow()


async def mark_succeeded(session: AsyncSession, job_id: int, output: str) -> None:
    """Record a finished text job. The caller commits."""
    job = await get_text_job(session, job_id)
    if job is None or job.status == "failed":
        return
    job.status = "succeeded"
    job.output = output
    job.error_code = None
    job.error_message = None
    job.finished_at = utcnow()
