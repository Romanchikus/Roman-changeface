import ctypes

from app.shared.errors import CudaUnavailableError

_CUDART = ("libcudart.so.13", "libcudart.so.12", "libcudart.so")
_DRIVER = ("libcuda.so.1", "libcuda.so")


def _load_any(names: tuple[str, ...]) -> None:
    errors: list[str] = []
    for name in names:
        try:
            ctypes.CDLL(name)
            return
        except OSError as exc:
            errors.append(f"{name}: {exc}")
    detail = "; ".join(errors)
    raise CudaUnavailableError(
        "CUDA libraries are missing. Inference did not run, and no video was written. "
        "A missing CUDA runtime is reported as an error instead of a black video. "
        f"Details: {detail}"
    )


def assert_cuda_libraries() -> None:
    _load_any(_CUDART)
    _load_any(_DRIVER)
