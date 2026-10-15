import logging
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from app.inference.cuda import assert_cuda_libraries
from app.inference.hyperswap_runner import run as run_hyperswap
from app.shared.config import get_settings
from app.shared.errors import InferenceRuntimeError

log = logging.getLogger(__name__)

MODEL_NAME = "HyperSwap"
DETECTOR_NAME = "RetinaFace"


@dataclass(frozen=True, slots=True)
class InferenceResult:
    model_name: str
    detector_name: str
    inference_ms: int
    simulated: bool


class SwapRunner(Protocol):
    def __call__(
        self,
        source_image: Path | list[Path],
        target_video: Path,
        output_video: Path,
        face_order: str = "left-right",
    ) -> InferenceResult: ...


def swap_faces(
    source_image: Path | list[Path],
    target_video: Path,
    output_video: Path,
    face_order: str = "left-right",
) -> InferenceResult:
    sources = [source_image] if isinstance(source_image, Path) else list(source_image)
    if not sources or any(not path.is_file() for path in sources) or not target_video.is_file():
        raise InferenceRuntimeError("Input files are missing. No video was written.")
    backend = get_settings().inference_backend
    if backend == "simulator":
        return _simulate(target_video, output_video)
    if backend == "hyperswap":
        return _hyperswap(sources, target_video, output_video, face_order)
    raise InferenceRuntimeError(f"Unknown inference backend '{backend}'. No video was written.")


def _simulate(target_video: Path, output_video: Path) -> InferenceResult:
    started = time.perf_counter()
    output_video.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(target_video),
            "-c",
            "copy",
            "-movflags",
            "+faststart",
            str(output_video),
        ],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    elapsed_ms = max(1, int((time.perf_counter() - started) * 1000))
    if proc.returncode != 0 or not output_video.is_file() or output_video.stat().st_size == 0:
        output_video.unlink(missing_ok=True)
        log.error("simulator ffmpeg failed: %s", proc.stderr[-2000:])
        raise InferenceRuntimeError("Simulator failed to write a video.")
    return InferenceResult(MODEL_NAME, DETECTOR_NAME, elapsed_ms, True)


def _hyperswap(
    sources: list[Path],
    target_video: Path,
    output_video: Path,
    face_order: str,
) -> InferenceResult:
    assert_cuda_libraries()
    weights = get_settings().hyperswap_weights.strip()
    if not weights:
        raise InferenceRuntimeError("HYPERSWAP_WEIGHTS is unset. Refusing to write a video.")
    weight_path = Path(weights)
    if not weight_path.exists():
        raise InferenceRuntimeError(
            f"HYPERSWAP_WEIGHTS does not exist ({weight_path}). Refusing to write a video."
        )
    output_video.parent.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    try:
        run_hyperswap(sources, target_video, output_video, weight_path, face_order)
    except Exception:
        output_video.unlink(missing_ok=True)
        raise
    elapsed_ms = max(1, int((time.perf_counter() - started) * 1000))
    if not output_video.is_file() or output_video.stat().st_size == 0:
        output_video.unlink(missing_ok=True)
        raise InferenceRuntimeError("HyperSwap produced no video.")
    return InferenceResult(MODEL_NAME, DETECTOR_NAME, elapsed_ms, False)
