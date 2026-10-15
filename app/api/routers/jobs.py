from pathlib import Path

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi_filter import FilterDepends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import allow_signed_in
from app.db.filters import JobFilter
from app.db.jobs import get_job, list_jobs
from app.db.session import get_db
from app.schemas import JobOut, to_job_out
from app.services.jobs import queue_swap
from app.shared.errors import MediaRejected, Unavailable

router = APIRouter(prefix="/api", dependencies=[Depends(allow_signed_in)])


def _http(exc: MediaRejected) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": exc.message})


@router.post("/swap", status_code=202, response_model=JobOut)
async def swap(
    source_image: Annotated[UploadFile | None, File()] = None,
    source_image_2: Annotated[UploadFile | None, File()] = None,
    source_image_3: Annotated[UploadFile | None, File()] = None,
    target_video: Annotated[UploadFile | None, File()] = None,
    source_image_id: Annotated[int | None, Form()] = None,
    source_image_2_id: Annotated[int | None, Form()] = None,
    source_image_3_id: Annotated[int | None, Form()] = None,
    target_video_id: Annotated[int | None, Form()] = None,
    face_order: Annotated[str, Form()] = "left-right",
    db: AsyncSession = Depends(get_db),
) -> JobOut:
    try:
        job = await queue_swap(
            db,
            source_image,
            source_image_2,
            source_image_3,
            target_video,
            source_image_id,
            source_image_2_id,
            source_image_3_id,
            target_video_id,
            face_order,
        )
    except MediaRejected as exc:
        raise _http(exc) from exc
    except Unavailable as exc:
        raise HTTPException(
            status_code=503,
            detail={"code": exc.code, "message": exc.message},
        ) from exc
    return to_job_out(job)


@router.get("/jobs", response_model=list[JobOut])
async def jobs(
    job_filter: JobFilter = FilterDepends(JobFilter),
    db: AsyncSession = Depends(get_db),
) -> list[JobOut]:
    return [to_job_out(job) for job in await list_jobs(db, job_filter)]


@router.get("/jobs/{job_id}", response_model=JobOut)
async def job_detail(job_id: int, db: AsyncSession = Depends(get_db)) -> JobOut:
    job = await get_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Job not found."})
    return to_job_out(job)


@router.get("/jobs/{job_id}/download")
async def download(job_id: int, db: AsyncSession = Depends(get_db)) -> FileResponse:
    job = await get_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Job not found."})
    if job.status != "succeeded":
        raise HTTPException(
            status_code=409,
            detail={"code": "not_ready", "message": "The video is not ready."},
        )
    path = Path(job.output_video.path)
    if not path.is_file():
        raise HTTPException(status_code=404, detail={"code": "missing_file", "message": "Output file is missing."})
    return FileResponse(
        path,
        media_type="video/mp4",
        filename=f"{job.id}.mp4",
        content_disposition_type="inline",
    )
