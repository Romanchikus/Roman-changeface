from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.db.filters import PAGE_LIMIT, MediaFilter
from app.db.media_link import OUTPUT, VIDEO as VIDEO_ROLE, ids_with_role
from app.db.models import Media

IMAGE = "image"
VIDEO = "video"
AUDIO = "audio"
IMAGES = "images"
VIDEOS = "videos"
AUDIOS = "audios"
OUTPUTS = "outputs"

_AUDIO_TYPES = {
    ".wav": "audio/wav",
    ".flac": "audio/flac",
    ".ogg": "audio/ogg",
    ".mp3": "audio/mpeg",
}


def content_type_for(path: Path, kind: str) -> str:
    if kind == AUDIO:
        return _AUDIO_TYPES.get(path.suffix.lower(), "audio/flac")
    if kind != IMAGE:
        return "video/mp4"
    suffix = path.suffix.lower()
    if suffix in {".jpg", ".jpeg"}:
        return "image/jpeg"
    if suffix == ".webp":
        return "image/webp"
    return "image/png"


async def create_media(
    session: AsyncSession,
    kind: str,
    filename: str,
    path: Path,
    size_bytes: int,
    duration_sec: float | None = None,
) -> Media:
    media = Media(
        kind=kind,
        filename=filename,
        path=str(path),
        size_bytes=size_bytes,
        content_type=content_type_for(path, kind),
        duration_sec=duration_sec,
    )
    session.add(media)
    await session.flush()
    return media


def move_media(media: Media, path: Path, filename: str | None = None) -> None:
    media.path = str(path)
    if filename is not None:
        media.filename = filename


async def _listed(session: AsyncSession, listing: str):
    if listing == IMAGES:
        return select(Media).where(Media.kind == IMAGE)
    if listing == VIDEOS:
        return select(Media).where(Media.id.in_(await ids_with_role(session, VIDEO_ROLE)))
    if listing == AUDIOS:
        return select(Media).where(Media.kind == AUDIO)
    return select(Media).where(Media.id.in_(await ids_with_role(session, OUTPUT)))


async def get_media(session: AsyncSession, media_id: int, listing: str) -> Media | None:
    stmt = (await _listed(session, listing)).where(Media.id == media_id).options(joinedload(Media.thumbnail))
    result = await session.execute(stmt)
    return result.unique().scalar_one_or_none()


async def list_media(session: AsyncSession, listing: str, media_filter: MediaFilter) -> list[Media]:
    """List media using a fastapi-filter."""
    stmt = (await _listed(session, listing)).options(joinedload(Media.thumbnail))
    stmt = media_filter.sort(media_filter.filter(stmt)).limit(PAGE_LIMIT)
    result = await session.execute(stmt)
    return list(result.unique().scalars().all())
