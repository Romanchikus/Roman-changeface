from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.db.models import Job, Media, MusicJob
from app.db.types import MediaSnapshot

SOURCE = "source"
VIDEO = "video"
OUTPUT = "output"
INPUT = "input"

_loaded: dict[tuple[type[Job | MusicJob], int], dict[int, Media]] = {}


def snapshot(media: Media, order: int, role: str) -> MediaSnapshot:
    """One stored file: id, path, filename, and order."""
    return MediaSnapshot(media.id, media.path, media.filename, order, role)


def assign(owner: Job | MusicJob, items: list[tuple[Media, int, str]]) -> None:
    """Replace the job's media list with the current file properties."""
    owner.media_ids = [snapshot(media, order, role) for media, order, role in items]


def refresh(owner: Job | MusicJob, media: Media) -> None:
    """Write this media's path and filename into the job's media list."""
    owner.media_ids = [
        snapshot(media, row.order, row.role) if row.id == media.id else row
        for row in owner.media_ids
    ]


def rows_for(owner: Job | MusicJob, role: str) -> list[MediaSnapshot]:
    return sorted((row for row in owner.media_ids if row.role == role), key=lambda row: row.order)


def models_for(owner: Job | MusicJob, role: str) -> list[Media]:
    """Media models prefetched for this role, in stored order."""
    by_id = _loaded.get((type(owner), owner.id), {})
    return [by_id[row.id] for row in rows_for(owner, role) if row.id in by_id]


def ids_for(owner: Job | MusicJob, role: str) -> list[int]:
    return [row.id for row in rows_for(owner, role)]


async def attach_media(session: AsyncSession, owners: list[Job | MusicJob]) -> None:
    """Load the media rows named by `media_ids`, including thumbnails."""
    ids = [row.id for owner in owners for row in owner.media_ids]
    by_id: dict[int, Media] = {}
    if ids:
        result = await session.execute(
            select(Media).where(Media.id.in_(ids)).options(joinedload(Media.thumbnail))
        )
        by_id = {media.id: media for media in result.unique().scalars()}
    for owner in owners:
        _loaded[(type(owner), owner.id)] = by_id


async def ids_with_role(session: AsyncSession, role: str) -> list[int]:
    result = await session.scalars(select(Job.media_ids))
    found: list[int] = []
    for rows in result:
        for row in rows or []:
            if row.role == role:
                found.append(row.id)
    return found
