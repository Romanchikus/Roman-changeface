from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.db.media_link import INPUT, OUTPUT, SOURCE, VIDEO, models_for
from app.db.models import Job, Media, MusicJob, TextJob
from app.db.types import TextParameters


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    source_filename: str
    video_filename: str
    source_bytes: int
    video_bytes: int
    video_duration_sec: float
    error_code: str | None
    error_message: str | None
    model_name: str | None
    detector_name: str | None
    inference_ms: int | None
    simulated: bool
    face_order: str
    note: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    download_url: str | None
    source_media_id: int | None
    video_media_id: int | None
    output_media_id: int | None
    source_preview_url: str | None
    video_preview_url: str | None
    output_preview_url: str | None


class MediaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    kind: str
    filename: str
    size_bytes: int
    content_type: str
    duration_sec: float | None
    created_at: datetime
    thumbnail_id: int | None
    download_url: str
    preview_url: str | None


class ResourcesOut(BaseModel):
    cpu_percent: float | None
    ram_used_bytes: int
    ram_total_bytes: int
    vram_used_bytes: int | None
    vram_total_bytes: int | None
    gpu_util_percent: float | None
    job_id: int | None
    job_status: str | None
    elapsed_ms: int | None


class AuthIn(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    created_at: datetime
    last_activity_at: datetime


class MetricPoint(BaseModel):
    sampled_at: datetime
    cpu_percent: float | None
    ram_used_bytes: int
    ram_total_bytes: int
    vram_used_bytes: int | None
    vram_total_bytes: int | None
    gpu_util_percent: float | None


class MetricHistory(BaseModel):
    samples: list[MetricPoint]
    inflight: int
    requests_last_10s: int


class MusicParametersOut(BaseModel):
    task_type: str
    caption: str
    duration_sec: float
    seed: int
    audio_id: int | None


class MusicJobOut(BaseModel):
    id: int
    status: str
    prompt: str
    task_type: str
    duration_sec: float
    seed: int
    inference_steps: int
    shift: float
    parameters: MusicParametersOut
    error_code: str | None
    error_message: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    input_media_id: int | None
    output_media_id: int | None
    input_path: str
    output_path: str
    download_url: str | None


class TextParametersOut(BaseModel):
    model: str
    prompt: str
    max_new_tokens: int
    system: str | None = None
    temperature: float | None = None
    top_p: float | None = None
    top_k: int | None = None
    min_p: float | None = None
    typical_p: float | None = None
    do_sample: bool | None = None
    seed: int | None = None
    repetition_penalty: float | None = None
    presence_penalty: float | None = None
    frequency_penalty: float | None = None
    stop: list[str] | None = None
    ignore_eos: bool | None = None
    min_new_tokens: int | None = None


class TextJobIn(BaseModel):
    model: str
    prompt: str
    max_new_tokens: int
    system: str | None = None
    temperature: float | None = None
    top_p: float | None = None
    top_k: int | None = None
    min_p: float | None = None
    typical_p: float | None = None
    do_sample: bool | None = None
    seed: int | None = None
    repetition_penalty: float | None = None
    presence_penalty: float | None = None
    frequency_penalty: float | None = None
    stop: list[str] | None = None
    ignore_eos: bool | None = None
    min_new_tokens: int | None = None


class TextJobOut(BaseModel):
    id: int
    status: str
    prompt: str
    parameters: TextParametersOut
    output: str | None
    error_code: str | None
    error_message: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class LimitsOut(BaseModel):
    max_image_bytes: int
    max_video_bytes: int
    max_video_duration_sec: float
    inference_backend: str
    gpu_slots: int = 1


def job_note(job: Job) -> str | None:
    if not job.model_name or job.detector_name is None or job.inference_ms is None:
        return None
    kind = "simulated" if job.simulated else "gpu"
    return f"{job.model_name} with {job.detector_name} ({kind}), inference {job.inference_ms} ms"


def preview_url(media: Media | None, folder: str) -> str | None:
    if media is None or media.thumbnail is None:
        return None
    return f"/api/files/{folder}/{media.id}/preview"


def to_media_out(media: Media, folder: str) -> MediaOut:
    return MediaOut(
        id=media.id,
        kind=media.kind,
        filename=media.filename,
        size_bytes=media.size_bytes,
        content_type=media.content_type,
        duration_sec=media.duration_sec,
        created_at=media.created_at,
        thumbnail_id=media.thumbnail.id if media.thumbnail is not None else None,
        download_url=f"/api/files/{folder}/{media.id}/download",
        preview_url=preview_url(media, folder),
    )


def to_music_out(job: MusicJob) -> MusicJobOut:
    outputs = models_for(job, OUTPUT)
    inputs = models_for(job, INPUT)
    output = outputs[0] if outputs else None
    source = inputs[0] if inputs else None
    stored = job.parameters
    download = None
    if job.status == "succeeded" and output is not None:
        download = f"/api/files/audios/{output.id}/download"
    return MusicJobOut(
        id=job.id,
        status=job.status,
        prompt=job.prompt,
        task_type=job.task_type,
        duration_sec=output.duration_sec if output is not None and output.duration_sec is not None else 0,
        seed=job.seed,
        inference_steps=job.inference_steps,
        shift=job.shift,
        parameters=MusicParametersOut(
            task_type=stored.task_type,
            caption=stored.caption,
            duration_sec=stored.duration_sec,
            seed=stored.seed,
            audio_id=stored.audio_id,
        ),
        error_code=job.error_code,
        error_message=job.error_message,
        created_at=job.created_at,
        started_at=job.started_at,
        finished_at=job.finished_at,
        input_media_id=source.id if source is not None else None,
        output_media_id=output.id if output is not None else None,
        input_path=source.path if source is not None else "",
        output_path=output.path if output is not None else "",
        download_url=download,
    )


def _text_parameters_out(stored: TextParameters) -> TextParametersOut:
    return TextParametersOut(
        model=stored.model,
        prompt=stored.prompt,
        max_new_tokens=stored.max_new_tokens,
        system=stored.system,
        temperature=stored.temperature,
        top_p=stored.top_p,
        top_k=stored.top_k,
        min_p=stored.min_p,
        typical_p=stored.typical_p,
        do_sample=stored.do_sample,
        seed=stored.seed,
        repetition_penalty=stored.repetition_penalty,
        presence_penalty=stored.presence_penalty,
        frequency_penalty=stored.frequency_penalty,
        stop=stored.stop,
        ignore_eos=stored.ignore_eos,
        min_new_tokens=stored.min_new_tokens,
    )


def to_text_out(job: TextJob) -> TextJobOut:
    return TextJobOut(
        id=job.id,
        status=job.status,
        prompt=job.prompt,
        parameters=_text_parameters_out(job.parameters),
        output=job.output,
        error_code=job.error_code,
        error_message=job.error_message,
        created_at=job.created_at,
        started_at=job.started_at,
        finished_at=job.finished_at,
    )


def to_job_out(job: Job) -> JobOut:
    download = f"/api/jobs/{job.id}/download" if job.status == "succeeded" else None
    faces = models_for(job, SOURCE)
    source = faces[0]
    video = models_for(job, VIDEO)[0]
    output = models_for(job, OUTPUT)[0]
    return JobOut(
        id=job.id,
        status=job.status,
        source_filename=", ".join(face.filename for face in faces),
        video_filename=video.filename,
        source_bytes=source.size_bytes,
        video_bytes=video.size_bytes,
        video_duration_sec=video.duration_sec or 0,
        error_code=job.error_code,
        error_message=job.error_message,
        model_name=job.model_name,
        detector_name=job.detector_name,
        inference_ms=job.inference_ms,
        simulated=job.simulated,
        face_order=job.face_order,
        note=job_note(job),
        created_at=job.created_at,
        started_at=job.started_at,
        finished_at=job.finished_at,
        download_url=download,
        source_media_id=source.id,
        video_media_id=video.id,
        output_media_id=output.id,
        source_preview_url=preview_url(source, "images"),
        video_preview_url=preview_url(video, "videos"),
        output_preview_url=preview_url(output, "outputs"),
    )
