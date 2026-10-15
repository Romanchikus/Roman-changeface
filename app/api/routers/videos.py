from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi_filter import FilterDepends

from app.api.deps import allow_signed_in
from app.db.filters import MediaFilter
from app.db.media import VIDEOS, get_media, list_media
from app.db.models import Media
from app.db.session import get_db
from app.schemas import MediaOut, to_media_out

router = APIRouter(prefix="/api/files/videos", dependencies=[Depends(allow_signed_in)])


async def _load(media_id: int, db: AsyncSession) -> Media:
    media = await get_media(db, media_id, VIDEOS)
    if media is None:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "File not found."})
    return media


@router.get("", response_model=list[MediaOut])
async def index(
    media_filter: MediaFilter = FilterDepends(MediaFilter),
    db: AsyncSession = Depends(get_db),
) -> list[MediaOut]:
    rows = await list_media(db, VIDEOS, media_filter)
    return [to_media_out(item, VIDEOS) for item in rows]


@router.get("/{media_id}", response_model=MediaOut)
async def detail(media_id: int, db: AsyncSession = Depends(get_db)) -> MediaOut:
    return to_media_out(await _load(media_id, db), VIDEOS)


@router.get("/{media_id}/download")
async def download(media_id: int, db: AsyncSession = Depends(get_db)) -> FileResponse:
    media = await _load(media_id, db)
    path = Path(media.path)
    if not path.is_file():
        raise HTTPException(status_code=404, detail={"code": "missing_file", "message": "File is missing."})
    return FileResponse(
        path,
        media_type=media.content_type,
        filename=media.filename,
        content_disposition_type="inline",
    )


@router.get("/{media_id}/preview")
async def preview(media_id: int, db: AsyncSession = Depends(get_db)) -> FileResponse:
    media = await _load(media_id, db)
    if media.thumbnail is None:
        raise HTTPException(status_code=404, detail={"code": "missing_preview", "message": "Preview is missing."})
    path = Path(media.thumbnail.path)
    if not path.is_file():
        raise HTTPException(status_code=404, detail={"code": "missing_preview", "message": "Preview is missing."})
    return FileResponse(path, media_type="image/jpeg", filename=f"{media.id}.jpg")
