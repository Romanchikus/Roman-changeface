import asyncio
import logging
import uuid
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.jobs import get_job, insert_job, mark_failed, mark_running, mark_succeeded
from app.db.media import IMAGE, IMAGES, VIDEO, VIDEOS, create_media, get_media, move_media
from app.db.models import Job, Media, Thumbnail
from app.db.session import session_scope
from app.inference.pipeline import SwapRunner, swap_faces
from app.media import (
    IMAGE_SUFFIXES,
    VIDEO_SUFFIXES,
    assert_image,
    probe_duration_seconds,
    remove_tree,
    safe_filename,
    save_upload,
    suffix_for,
)
from app.shared.config import get_settings
from app.shared.errors import MediaRejected, SwapError, Unavailable
from app.thumbnails import thumbnail_file, write_thumbnail

log = logging.getLogger(__name__)

FACE_ORDERS = {
    "left-right",
    "right-left",
    "top-bottom",
    "bottom-top",
    "small-large",
    "large-small",
    "best-worst",
    "worst-best",
}


def _choice(message: str) -> MediaRejected:
    return MediaRejected(400, "media_choice", message)


def _enqueue(job_id: int) -> None:
    from app.worker.tasks import run_swap

    run_swap.delay(job_id)


async def _existing(db: AsyncSession, media_id: int, listing: str, label: str) -> Media:
    media = await get_media(db, media_id, listing)
    if media is None:
        raise MediaRejected(404, "not_found", f"{label} was not found.")
    return media


async def _attach_thumbnails(db: AsyncSession, medias: list[Media]) -> None:
    rows: list[Thumbnail] = []
    for media in medias:
        path = Path(media.path)
        if not path.is_file():
            continue
        dest = thumbnail_file(media.id)
        if await asyncio.to_thread(write_thumbnail, path, dest):
            rows.append(Thumbnail(media_id=media.id, path=str(dest)))
    if not rows:
        return
    db.add_all(rows)
    await db.commit()


async def queue_swap(
    db: AsyncSession,
    source_image: UploadFile | None,
    source_image_2: UploadFile | None,
    source_image_3: UploadFile | None,
    target_video: UploadFile | None,
    source_image_id: int | None,
    source_image_2_id: int | None,
    source_image_3_id: int | None,
    target_video_id: int | None,
    face_order: str,
) -> Job:
    """Store a swap and enqueue it after the files are on disk."""
    settings = get_settings()
    if face_order not in FACE_ORDERS:
        raise _choice("Choose a face order such as left to right or largest first.")
    slots = [
        (source_image, source_image_id),
        (source_image_2, source_image_2_id),
        (source_image_3, source_image_3_id),
    ]
    if any(upload is not None and media_id is not None for upload, media_id in slots):
        raise _choice("Each face is either a new image or one that was already uploaded.")
    present = [upload is not None or media_id is not None for upload, media_id in slots]
    if not present[0]:
        raise _choice("Send a new source image or choose one that was already uploaded.")
    if present[2] and not present[1]:
        raise _choice("Add the second face before the third.")
    if (target_video is None) == (target_video_id is None):
        raise _choice("Send a new target video or choose one that was already uploaded.")

    existing_faces: list[Media | None] = [None, None, None]
    for index, (upload, media_id) in enumerate(slots):
        if upload is None and media_id is not None:
            existing_faces[index] = await _existing(db, media_id, IMAGES, f"Source face {index + 1}")
    existing_video = None
    if target_video is None and target_video_id is not None:
        existing_video = await _existing(db, target_video_id, VIDEOS, "Target video")
    if any(face is not None for face in existing_faces) or existing_video is not None:
        await db.commit()

    directory = Path(settings.storage_dir) / "_incoming" / uuid.uuid4().hex
    directory.mkdir(parents=True, exist_ok=True)
    saved: list[tuple[int, str, Path, int]] = []
    video_saved: tuple[str, Path, int, float] | None = None
    try:
        for index, (upload, _media_id) in enumerate(slots, start=1):
            if upload is None:
                continue
            source_name = safe_filename(upload.filename, f"source-{index}.png")
            source_path = directory / f"source-{index}{suffix_for(source_name, IMAGE_SUFFIXES, '.png')}"
            source_bytes = await asyncio.to_thread(
                save_upload, upload, source_path, settings.max_image_bytes, f"Source face {index}"
            )
            await asyncio.to_thread(assert_image, source_path)
            saved.append((index, source_name, source_path, source_bytes))
        if target_video is not None:
            video_name = safe_filename(target_video.filename, "target.mp4")
            video_path = directory / f"target{suffix_for(video_name, VIDEO_SUFFIXES, '.mp4')}"
            video_bytes = await asyncio.to_thread(
                save_upload, target_video, video_path, settings.max_video_bytes, "Target video"
            )
            duration = await asyncio.to_thread(probe_duration_seconds, video_path)
            video_saved = (video_name, video_path, video_bytes, duration)
    except MediaRejected:
        await asyncio.to_thread(remove_tree, directory)
        raise

    images: list[Media | None] = [None, None, None]
    paths: list[Path | None] = [None, None, None]
    try:
        for index, source_name, source_path, source_bytes in saved:
            media = await create_media(db, IMAGE, source_name, source_path, source_bytes)
            images[index - 1] = media
            paths[index - 1] = source_path
        for index, face in enumerate(existing_faces):
            if face is not None:
                images[index] = face
        if video_saved is None:
            video = existing_video
            if video is None:
                raise _choice("Send a new target video or choose one that was already uploaded.")
            duration = video.duration_sec
            video_path = None
        else:
            video_name, video_path, video_bytes, duration = video_saved
            video = await create_media(db, VIDEO, video_name, video_path, video_bytes, duration)
        output = await create_media(db, VIDEO, "output.mp4", directory / "output.mp4", 0, duration)
        if images[0] is None:
            raise _choice("Send a new source image or choose one that was already uploaded.")
        job = await insert_job(
            db,
            Job(
                status="queued",
                input_image_id=images[0].id,
                input_image_2_id=images[1].id if images[1] is not None else None,
                input_image_3_id=images[2].id if images[2] is not None else None,
                input_video_id=video.id,
                output_video_id=output.id,
                face_order=face_order,
            ),
        )
        await db.commit()
    except Exception:
        await db.rollback()
        await asyncio.to_thread(remove_tree, directory)
        raise

    final_dir = Path(settings.storage_dir) / str(job.id)
    await asyncio.to_thread(remove_tree, final_dir)
    await asyncio.to_thread(directory.rename, final_dir)
    fresh: list[Media] = []
    for media, path in zip(images, paths, strict=True):
        if media is not None and path is not None:
            move_media(media, final_dir / path.name)
            fresh.append(media)
    if video_path is not None:
        move_media(video, final_dir / video_path.name)
        fresh.append(video)
    move_media(output, final_dir / "output.mp4", f"{job.id}.mp4")
    await db.commit()
    await _attach_thumbnails(db, fresh)

    try:
        _enqueue(job.id)
    except Exception as exc:
        await mark_failed(db, job.id, Unavailable.code, Unavailable.message)
        await db.commit()
        log.exception("job %s was not queued", job.id)
        raise Unavailable() from exc

    job_id = job.id
    log.info("job %s queued", job_id)
    db.expire_all()
    stored = await get_job(db, job_id)
    if stored is None:
        raise MediaRejected(500, "missing_job", "Job disappeared.")
    return stored


def _discard(path: Path) -> None:
    path.unlink(missing_ok=True)


async def execute_swap(job_id: int, runner: SwapRunner | None = None) -> None:
    """Run one swap with the database closed around the inference call."""
    swap = runner or swap_faces
    async with session_scope() as session:
        job = await get_job(session, job_id)
        if job is None or job.status in {"succeeded", "failed"}:
            return
        sources = [Path(job.input_image.path)]
        if job.input_image_2 is not None:
            sources.append(Path(job.input_image_2.path))
        if job.input_image_3 is not None:
            sources.append(Path(job.input_image_3.path))
        video = Path(job.input_video.path)
        output = Path(job.output_video.path)
        face_order = job.face_order
        output_id = job.output_video.id
        await mark_running(session, job)
    log.info("job %s running", job_id)

    try:
        result = swap(sources, video, output, face_order)
    except SwapError as exc:
        _discard(output)
        log.info("job %s failed: %s", job_id, exc)
        async with session_scope() as session:
            await mark_failed(session, job_id, exc.code, str(exc))
        return
    except Exception:
        _discard(output)
        log.exception("job %s crashed", job_id)
        async with session_scope() as session:
            await mark_failed(
                session,
                job_id,
                "inference_failed",
                "Inference failed before a video was saved.",
            )
        return

    size = output.stat().st_size if output.is_file() else None
    thumb_path = thumbnail_file(output_id)
    wrote = await asyncio.to_thread(write_thumbnail, output, thumb_path)
    async with session_scope() as session:
        await mark_succeeded(
            session,
            job_id,
            result,
            size,
            str(thumb_path) if wrote else None,
        )
    log.info("job %s succeeded", job_id)
