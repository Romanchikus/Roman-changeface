import logging
import threading
from dataclasses import dataclass
from typing import Protocol

from app.shared.config import get_settings
from app.shared.errors import CudaOutOfMemory, GenerationError, ModelInitError

log = logging.getLogger(__name__)

TASK_TEXT = "text2music"
TASK_COVER = "cover"


@dataclass(slots=True)
class GenerateRequest:
    prompt: str
    task_type: str
    src_audio: str
    duration_sec: float
    seed: int
    output_dir: str


@dataclass(slots=True)
class GeneratedAudio:
    path: str
    seed: int


class MusicModel(Protocol):
    def generate(self, request: GenerateRequest) -> GeneratedAudio:
        """Generate one track."""


def _load_api():  # type: ignore[no-untyped-def]
    from acestep.handler import AceStepHandler
    from acestep.inference import GenerationConfig, GenerationParams, generate_music

    return AceStepHandler, GenerationParams, GenerationConfig, generate_music


def _is_oom(exc: BaseException) -> bool:
    return type(exc).__name__ == "OutOfMemoryError" or "out of memory" in str(exc).lower()


def _release_cuda() -> None:
    try:
        import torch
    except ImportError:
        return
    cuda = getattr(torch, "cuda", None)
    if cuda is not None and cuda.is_available():
        cuda.empty_cache()


class AceStepRunner:
    """One DiT handler per process. The language model stays unloaded."""

    def __init__(self) -> None:
        self._handler = None
        self._lock = threading.Lock()

    def generate(self, request: GenerateRequest) -> GeneratedAudio:
        """Run ACE-Step DiT generation for one job."""
        if request.task_type == TASK_TEXT and request.src_audio:
            raise GenerationError("text2music does not use source audio.")
        if request.task_type == TASK_COVER and not request.src_audio:
            raise GenerationError("cover requires source audio.")
        if request.task_type not in {TASK_TEXT, TASK_COVER}:
            raise GenerationError(f"Unsupported task {request.task_type}.")
        self._ensure_loaded()
        _, GenerationParams, GenerationConfig, generate_music = _load_api()
        settings = get_settings()
        params = GenerationParams(
            task_type=request.task_type,
            caption=request.prompt,
            lyrics="[Instrumental]",
            instrumental=True,
            duration=request.duration_sec if request.task_type == TASK_TEXT else -1.0,
            inference_steps=settings.acestep_inference_steps,
            shift=settings.acestep_shift,
            guidance_scale=1.0,
            seed=request.seed,
            thinking=False,
            use_cot_metas=False,
            use_cot_caption=False,
            use_cot_language=False,
            use_cot_lyrics=False,
            src_audio=request.src_audio if request.task_type == TASK_COVER else None,
        )
        config = GenerationConfig(
            batch_size=1,
            allow_lm_batch=False,
            use_random_seed=request.seed < 0,
            seeds=None if request.seed < 0 else [request.seed],
            audio_format=settings.acestep_audio_format,
        )
        try:
            result = generate_music(
                self._handler, None, params, config, save_dir=request.output_dir
            )
        except Exception as exc:
            _release_cuda()
            if _is_oom(exc):
                raise CudaOutOfMemory(str(exc)) from exc
            raise GenerationError(str(exc)) from exc
        if not getattr(result, "success", False):
            error = getattr(result, "error", None) or "generation failed"
            if _is_oom(Exception(error)):
                raise CudaOutOfMemory(str(error))
            raise GenerationError(str(error))
        audios = getattr(result, "audios", None) or []
        if not audios or not audios[0].get("path"):
            raise GenerationError("ACE-Step returned no audio file.")
        audio_params = audios[0].get("params") or {}
        seed = audio_params.get("seed")
        if not isinstance(seed, int):
            seed = request.seed
        return GeneratedAudio(path=str(audios[0]["path"]), seed=seed)

    def _ensure_loaded(self) -> None:
        if self._handler is not None:
            return
        with self._lock:
            if self._handler is None:
                self._handler = self._initialize()

    def _initialize(self):  # type: ignore[no-untyped-def]
        settings = get_settings()
        try:
            AceStepHandler, _, _, _ = _load_api()
            handler = AceStepHandler()
            message, ok = handler.initialize_service(
                project_root=settings.acestep_project_root,
                config_path=settings.acestep_config_path,
                device=settings.acestep_device,
                use_flash_attention=False,
                compile_model=settings.acestep_compile_model,
                offload_to_cpu=settings.acestep_offload_to_cpu,
                offload_dit_to_cpu=settings.acestep_offload_dit_to_cpu,
                quantization=settings.acestep_quantization,
            )
        except Exception as exc:
            _release_cuda()
            if _is_oom(exc):
                raise CudaOutOfMemory(str(exc)) from exc
            raise ModelInitError(str(exc)) from exc
        if not ok:
            _release_cuda()
            if _is_oom(Exception(message)):
                raise CudaOutOfMemory(str(message))
            raise ModelInitError(str(message))
        applied = getattr(handler, "quantization", None)
        if applied != settings.acestep_quantization:
            raise ModelInitError(
                f"Requested quantization {settings.acestep_quantization}, handler has {applied}."
            )
        log.info(
            "ACE-Step loaded config=%s quantization=%s offload_cpu=%s offload_dit=%s",
            settings.acestep_config_path,
            applied,
            settings.acestep_offload_to_cpu,
            settings.acestep_offload_dit_to_cpu,
        )
        return handler


_runner: MusicModel | None = None
_runner_lock = threading.Lock()


def get_runner() -> MusicModel:
    global _runner
    if _runner is None:
        with _runner_lock:
            if _runner is None:
                _runner = AceStepRunner()
    return _runner


def set_runner(runner: MusicModel | None) -> None:
    global _runner
    _runner = runner
