from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import allow_signed_in
from app.db.music import get_music
from app.db.session import get_db
from app.schemas import MusicJobOut, to_music_out
from app.services.music import queue_music
from app.shared.errors import MediaRejected, Unavailable

router = APIRouter(prefix="/api/v1/music", dependencies=[Depends(allow_signed_in)])


def _http(exc: MediaRejected) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": exc.message})


@router.post("", status_code=201, response_model=MusicJobOut)
async def create(
    prompt: Annotated[str, Form()] = "",
    duration_sec: Annotated[float | None, Form()] = None,
    seed: Annotated[int, Form()] = -1,
    audio_id: Annotated[int | None, Form()] = None,
    db: AsyncSession = Depends(get_db),
) -> MusicJobOut:
    try:
        job = await queue_music(db, prompt, audio_id, duration_sec, seed)
    except MediaRejected as exc:
        raise _http(exc) from exc
    except Unavailable as exc:
        raise HTTPException(
            status_code=503,
            detail={"code": exc.code, "message": exc.message},
        ) from exc
    return to_music_out(job)


@router.get("/jobs/{job_id}", response_model=MusicJobOut)
async def read_job(job_id: int, db: AsyncSession = Depends(get_db)) -> MusicJobOut:
    job = await get_music(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Job not found."})
    return to_music_out(job)
