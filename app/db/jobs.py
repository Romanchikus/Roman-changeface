from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.filters import PAGE_LIMIT, JobFilter
from app.db.media_link import OUTPUT, attach_media, models_for
from app.db.models import Job, Thumbnail, utcnow
from app.inference.pipeline import InferenceResult


async def insert_job(session: AsyncSession, job: Job) -> Job:
    session.add(job)
    await session.flush()
    return job


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
    result = await session.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if job is not None:
        await attach_media(session, [job])
    return job


async def list_jobs(session: AsyncSession, job_filter: JobFilter) -> list[Job]:
    """List face-swap jobs using a fastapi-filter."""
    stmt = job_filter.sort(job_filter.filter(select(Job))).limit(PAGE_LIMIT)
    result = await session.execute(stmt)
    jobs = list(result.scalars().all())
    await attach_media(session, jobs)
    return jobs


async def mark_failed(session: AsyncSession, job_id: int, code: str, message: str) -> None:
    """Record a failure. The caller commits."""
    result = await session.execute(select(Job).where(Job.id == job_id))
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
    outputs = models_for(job, OUTPUT)
    if not outputs:
        return
    output = outputs[0]
    if size_bytes is not None:
        output.size_bytes = size_bytes
    if thumb is not None and output.thumbnail is None:
        session.add(Thumbnail(media_id=output.id, path=thumb))
