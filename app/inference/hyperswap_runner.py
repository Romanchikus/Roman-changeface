"""Run a swap through the FaceFusion checkout. License: OpenRAIL-AS, Copyright (c) 2026 Henry Ruhs."""

import subprocess
import sys
from pathlib import Path

from app.shared.errors import InferenceRuntimeError

ROOT = Path(__file__).resolve().parents[2] / "facefusion"
ORDERS = {
    "left-right",
    "right-left",
    "top-bottom",
    "bottom-top",
    "small-large",
    "large-small",
    "best-worst",
    "worst-best",
}


def run(
    sources: list[Path],
    target_video: Path,
    output_video: Path,
    weights: Path,
    face_order: str = "left-right",
) -> None:
    if not sources:
        raise InferenceRuntimeError("No source face was provided. No video was written.")
    order = face_order if face_order in ORDERS else "left-right"
    output_video.parent.mkdir(parents=True, exist_ok=True)
    if len(sources) == 1:
        _once(sources[0], target_video, output_video, weights, "many", order, 0)
    else:
        current = target_video
        temps: list[Path] = []
        try:
            for index, source in enumerate(sources):
                last = index == len(sources) - 1
                step = output_video if last else output_video.with_name(f".pass-{index}.mp4")
                _once(source, current, step, weights, "reference", order, index)
                if not last:
                    temps.append(step)
                current = step
        finally:
            for path in temps:
                path.unlink(missing_ok=True)
    _copy_audio(target_video, output_video)
    output_video.chmod(0o664)


def _once(
    source_image: Path,
    target_video: Path,
    output_video: Path,
    weights: Path,
    mode: str,
    face_order: str,
    position: int,
) -> None:
    model = weights / "hyperswap_1a_256.onnx" if weights.is_dir() else weights
    script = ROOT / "facefusion.py"
    if not script.is_file():
        raise InferenceRuntimeError("FaceFusion is not available. No video was written.")
    if not model.is_file():
        raise InferenceRuntimeError(f"HyperSwap weights are missing ({model}). No video was written.")
    proc = subprocess.run(
        [
            sys.executable,
            str(script),
            "headless-run",
            "-s",
            str(source_image),
            "-t",
            str(target_video),
            "-o",
            str(output_video),
            "--processors",
            "face_swapper",
            "--face-swapper-model",
            "hyperswap_1a_256",
            "--execution-providers",
            "cuda",
            "--execution-thread-count",
            "1",
            "--face-swapper-pixel-boost",
            "256x256",
            "--face-detector-model",
            "retinaface",
            "--face-detector-score",
            "0.3",
            "--face-selector-mode",
            mode,
            "--face-selector-order",
            face_order,
            "--reference-face-position",
            str(position),
            "--output-audio-volume",
            "100",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=1800,
        check=False,
    )
    if proc.returncode != 0 or not output_video.is_file() or output_video.stat().st_size == 0:
        output_video.unlink(missing_ok=True)
        detail = (proc.stderr or proc.stdout or "FaceFusion failed.").strip()[-1500:]
        raise InferenceRuntimeError(detail)


def _copy_audio(source: Path, output: Path) -> None:
    mixed = output.with_suffix(".mux.mp4")
    proc = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(output),
            "-i",
            str(source),
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-c",
            "copy",
            "-shortest",
            str(mixed),
        ],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    if proc.returncode == 0 and mixed.is_file() and mixed.stat().st_size > 0:
        mixed.replace(output)
        return
    mixed.unlink(missing_ok=True)
