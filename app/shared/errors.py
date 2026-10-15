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
