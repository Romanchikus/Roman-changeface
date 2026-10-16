import asyncio
import logging
import uuid
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.media import AUDIO, AUDIOS, create_media, get_media, move_media
from app.db.media_link import INPUT, OUTPUT, assign, models_for, refresh
from app.db.models import Media, MusicJob, utcnow
from app.db.types import MusicParameters
from app.db.music import get_music, insert_music, mark_failed, mark_succeeded
from app.db.session import session_scope
from app.inference.acestep import TASK_COVER, TASK_TEXT
from app.media import remove_tree
from app.shared.config import get_settings
from app.shared.errors import MediaRejected, Unavailable

log = logging.getLogger(__name__)


def _choice(message: str) -> MediaRejected:
    return MediaRejected(400, "media_choice", message)


def _enqueue(job_id: int) -> None:
    from app.worker.tasks import run_music

    run_music.delay(job_id)


async def queue_music(
    db: AsyncSession,
    prompt: str,
    audio_id: int | None,
    duration_sec: float | None,
    seed: int,
) -> MusicJob:
    """Store the job under its directory and enqueue it. Audio is an existing media id."""
    settings = get_settings()
    prompt = prompt.strip()
    if len(prompt) > settings.max_prompt_chars:
        raise MediaRejected(400, "prompt", "The prompt is too long.")
    if seed < -1:
        raise MediaRejected(400, "seed", "Seed must be -1 or greater.")
    if not prompt and audio_id is None:
        raise _choice("Send a prompt, an audio id, or both.")

    existing = None
    if audio_id is not None:
        existing = await get_media(db, audio_id, AUDIOS)
        if existing is None or existing.duration_sec is None:
            raise MediaRejected(404, "not_found", "Audio was not found.")
        await db.commit()
        duration = float(existing.duration_sec)
    else:
        duration = settings.default_duration_sec if duration_sec is None else duration_sec
        if duration < settings.min_duration_sec or duration > settings.max_duration_sec:
            raise MediaRejected(
                400,
                "duration",
                "Duration must be between "
                f"{settings.min_duration_sec:g} and {settings.max_duration_sec:g} seconds.",
            )

    directory = Path(settings.storage_dir) / "_incoming" / uuid.uuid4().hex
    directory.mkdir(parents=True, exist_ok=True)
    task_type = TASK_COVER if existing is not None else TASK_TEXT
    parameters = MusicParameters(
        task_type=task_type,
        caption=prompt,
        duration_sec=duration,
        seed=seed,
        audio_id=existing.id if existing is not None else None,
    )
    try:
        output = await create_media(
            db, AUDIO, "output.flac", directory / "output.flac", 0, duration
        )
        linked: list[tuple[Media, int, str]] = []
        if existing is not None:
            linked.append((existing, 0, INPUT))
        linked.append((output, 1 if existing is not None else 0, OUTPUT))
        job = MusicJob(
            status="queued",
            prompt=prompt,
            task_type=task_type,
            seed=seed,
            inference_steps=settings.acestep_inference_steps,
            shift=settings.acestep_shift,
            parameters=parameters,
        )
        assign(job, linked)
        job = await insert_music(db, job)
        await db.commit()
    except Exception:
        await db.rollback()
        await asyncio.to_thread(remove_tree, directory)
        raise

    final_dir = Path(settings.storage_dir) / str(job.id)
    await asyncio.to_thread(remove_tree, final_dir)
    await asyncio.to_thread(directory.rename, final_dir)
    move_media(output, final_dir / "output.flac", f"{job.id}.flac")
    refresh(job, output)
    await db.commit()

    try:
        _enqueue(job.id)
    except Exception as exc:
        await mark_failed(db, job.id, Unavailable.code, Unavailable.message)
        await db.commit()
        log.exception("music job %s was not queued", job.id)
        raise Unavailable() from exc

    job_id = job.id
    log.info("music job %s queued task_type=%s", job_id, task_type)
    db.expire_all()
    stored = await get_music(db, job_id)
    if stored is None:
        raise MediaRejected(500, "missing_job", "Job disappeared.")
    return stored


async def execute_music(job_id: int) -> None:
    """Finish the job. Generation is a no-op until the model is wired in."""
    async with session_scope() as session:
        job = await get_music(session, job_id)
        if job is None or job.status in {"succeeded", "failed"}:
            return
        if not models_for(job, OUTPUT):
            return
        seed = job.seed
        job.status = "running"
        job.started_at = utcnow()
    log.info("music job %s running", job_id)
    async with session_scope() as session:
        await mark_succeeded(session, job_id, 0, seed)
    log.info("music job %s passed", job_id)
