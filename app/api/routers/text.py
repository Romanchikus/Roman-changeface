from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import allow_signed_in
from app.db.session import get_db
from app.db.text_jobs import get_text_job
from app.schemas import TextJobIn, TextJobOut, to_text_out
from app.services.text_jobs import queue_text
from app.shared.errors import MediaRejected, Unavailable

router = APIRouter(prefix="/api/v1/text", dependencies=[Depends(allow_signed_in)])


def _http(exc: MediaRejected) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": exc.message})


@router.post("", status_code=201, response_model=TextJobOut)
async def create(body: TextJobIn, db: AsyncSession = Depends(get_db)) -> TextJobOut:
    try:
        job = await queue_text(db, body)
    except MediaRejected as exc:
        raise _http(exc) from exc
    except Unavailable as exc:
        raise HTTPException(
            status_code=503,
            detail={"code": exc.code, "message": exc.message},
        ) from exc
    return to_text_out(job)


@router.get("/jobs/{job_id}", response_model=TextJobOut)
async def read_job(job_id: int, db: AsyncSession = Depends(get_db)) -> TextJobOut:
    job = await get_text_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Job not found."})
    return to_text_out(job)
