class SwapError(Exception):
    code = "inference_failed"


class CudaUnavailableError(SwapError):
    code = "cuda_unavailable"


class InferenceRuntimeError(SwapError):
    code = "inference_runtime"


class GpuBusy(Exception):
    """Another job holds the single GPU slot."""


class MediaRejected(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


class Unavailable(Exception):
    code = "queue_unavailable"
    message = "Could not enqueue the job. Redis may be down."


class ModelInitError(Exception):
    pass


class GenerationError(Exception):
    pass


class CudaOutOfMemory(RuntimeError):
    pass


def classify_music_failure(exc: BaseException) -> tuple[str, str]:
    """Map a music-worker failure to a stored error code and a short message."""
    text = str(exc).lower()
    if type(exc).__name__ in {"OutOfMemoryError", "CudaOutOfMemory"} or "out of memory" in text:
        return "cuda_oom", "CUDA ran out of memory."
    if isinstance(exc, ModelInitError):
        return "model_init", str(exc)[:2000] or "ACE-Step failed to initialize."
    if isinstance(exc, GenerationError):
        return "generation", str(exc)[:2000] or "Music generation failed."
    return "generation", "Music generation failed."
