import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import TextJob, utcnow
from app.db.text_jobs import get_text_job, insert_text_job, mark_failed, mark_succeeded
from app.db.session import session_scope
from app.db.types import TextParameters
from app.inference.llama import MODELS
from app.schemas import TextJobIn
from app.shared.config import get_settings
from app.shared.errors import MediaRejected, Unavailable

log = logging.getLogger(__name__)


def _reject(code: str, message: str) -> MediaRejected:
    return MediaRejected(400, code, message)


def _span(name: str, value: float | int | None, low: float, high: float) -> None:
    if value is None:
        return
    if value < low or value > high:
        raise _reject(name, f"{name} must be between {low:g} and {high:g}.")


def _parameters(body: TextJobIn) -> TextParameters:
    settings = get_settings()
    prompt = body.prompt.strip()
    system = body.system.strip() if body.system is not None else None
    if body.model not in MODELS:
        raise _reject("model", "Choose llama-3.1-8b-instruct or llama-3.3-8b.")
    if not prompt:
        raise _reject("prompt", "Send a prompt.")
    if len(prompt) > settings.max_text_chars:
        raise _reject("prompt", "The prompt is too long.")
    if system is not None and len(system) > settings.max_text_chars:
        raise _reject("system", "The system prompt is too long.")
    _span("max_new_tokens", body.max_new_tokens, 1, settings.max_new_tokens)
    _span("temperature", body.temperature, 0, 2)
    _span("top_p", body.top_p, 0, 1)
    _span("top_k", body.top_k, 0, 1000)
    _span("min_p", body.min_p, 0, 1)
    _span("typical_p", body.typical_p, 0, 1)
    _span("seed", body.seed, 0, 2**31 - 1)
    _span("repetition_penalty", body.repetition_penalty, 0.1, 2)
    _span("presence_penalty", body.presence_penalty, -2, 2)
    _span("frequency_penalty", body.frequency_penalty, -2, 2)
    _span("min_new_tokens", body.min_new_tokens, 0, body.max_new_tokens)
    stop = body.stop
    if stop is not None and (
        not stop or len(stop) > 16 or any(item == "" or len(item) > 200 for item in stop)
    ):
        raise _reject("stop", "Send 1 to 16 stop strings, each 1 to 200 characters.")
    return TextParameters(
        model=body.model,
        prompt=prompt,
        max_new_tokens=body.max_new_tokens,
        system=system,
        temperature=body.temperature,
        top_p=body.top_p,
        top_k=body.top_k,
        min_p=body.min_p,
        typical_p=body.typical_p,
        do_sample=body.do_sample,
        seed=body.seed,
        repetition_penalty=body.repetition_penalty,
        presence_penalty=body.presence_penalty,
        frequency_penalty=body.frequency_penalty,
        stop=stop,
        ignore_eos=body.ignore_eos,
        min_new_tokens=body.min_new_tokens,
    )


def _enqueue(job_id: int) -> None:
    from app.worker.tasks import run_text

    run_text.delay(job_id)


async def queue_text(db: AsyncSession, body: TextJobIn) -> TextJob:
    """Store the job and enqueue it. Generation is a no-op until the model is wired in."""
    parameters = _parameters(body)
    job = await insert_text_job(
        db,
        TextJob(status="queued", prompt=parameters.prompt, parameters=parameters),
    )
    await db.commit()
    try:
        _enqueue(job.id)
    except Exception as exc:
        await mark_failed(db, job.id, Unavailable.code, Unavailable.message)
        await db.commit()
        log.exception("text job %s was not queued", job.id)
        raise Unavailable() from exc
    job_id = job.id
    log.info("text job %s queued model=%s", job_id, parameters.model)
    db.expire_all()
    stored = await get_text_job(db, job_id)
    if stored is None:
        raise MediaRejected(500, "missing_job", "Job disappeared.")
    return stored


async def execute_text(job_id: int) -> None:
    """Finish the job. Generation is a no-op until the model is wired in."""
    async with session_scope() as session:
        job = await get_text_job(session, job_id)
        if job is None or job.status in {"succeeded", "failed"}:
            return
        job.status = "running"
        job.started_at = utcnow()
    log.info("text job %s running", job_id)
    async with session_scope() as session:
        await mark_succeeded(session, job_id, "")
    log.info("text job %s passed", job_id)
