import sys

import pytest

from app.inference.acestep import TASK_COVER, TASK_TEXT, AceStepRunner, GenerateRequest
from app.shared.errors import CudaOutOfMemory, GenerationError, ModelInitError


class Handler:
    init_calls = 0

    def initialize_service(self, **kwargs):  # type: ignore[no-untyped-def]
        Handler.init_calls += 1
        self.kwargs = kwargs
        self.quantization = kwargs["quantization"]
        return "loaded", True


class Params:
    def __init__(self, **kwargs):  # type: ignore[no-untyped-def]
        self.kwargs = kwargs


class Config:
    def __init__(self, **kwargs):  # type: ignore[no-untyped-def]
        self.kwargs = kwargs


class Result:
    def __init__(self, success: bool = True, error: str | None = None) -> None:
        self.success = success
        self.error = error
        self.audios = [{"path": "/tmp/generated.flac", "params": {"seed": 9}}]


def _install(
    monkeypatch, result: Result | None = None, explode: BaseException | None = None
) -> dict:
    seen: dict = {}

    def generate_music(handler, llm, params, config, save_dir=None):  # type: ignore[no-untyped-def]
        seen["handler"] = handler
        seen["llm"] = llm
        seen["params"] = params.kwargs
        seen["config"] = config.kwargs
        seen["save_dir"] = save_dir
        if explode is not None:
            raise explode
        return result or Result()

    monkeypatch.setattr(
        "app.inference.acestep._load_api",
        lambda: (Handler, Params, Config, generate_music),
    )
    return seen


def _request(task: str, src: str = "") -> GenerateRequest:
    return GenerateRequest(
        prompt="piano",
        task_type=task,
        src_audio=src,
        duration_sec=30,
        seed=5,
        output_dir="/tmp/music-out",
    )


def test_model_package_is_not_imported():
    assert "acestep" not in sys.modules


def test_loads_once_with_low_vram_settings(monkeypatch):
    Handler.init_calls = 0
    seen = _install(monkeypatch)
    runner = AceStepRunner()
    first = runner.generate(_request(TASK_TEXT))
    second = runner.generate(_request(TASK_TEXT))
    assert first.seed == 9
    assert second.path.endswith(".flac")
    assert Handler.init_calls == 1
    init = seen["handler"].kwargs
    assert init["config_path"] == "acestep-v15-turbo"
    assert init["device"] == "cuda"
    assert init["quantization"] == "int8_weight_only"
    assert init["offload_to_cpu"] is True
    assert init["offload_dit_to_cpu"] is True
    assert init["compile_model"] is True
    assert seen["llm"] is None
    assert seen["params"]["thinking"] is False
    assert seen["params"]["use_cot_metas"] is False
    assert seen["params"]["use_cot_caption"] is False
    assert seen["params"]["use_cot_language"] is False
    assert seen["params"]["use_cot_lyrics"] is False
    assert seen["params"]["src_audio"] is None
    assert seen["params"]["inference_steps"] == 8
    assert seen["params"]["shift"] == 3.0
    assert seen["config"]["batch_size"] == 1


def test_cover_passes_source_audio(monkeypatch):
    seen = _install(monkeypatch)
    AceStepRunner().generate(_request(TASK_COVER, src="/tmp/source.wav"))
    assert seen["params"]["task_type"] == TASK_COVER
    assert seen["params"]["src_audio"] == "/tmp/source.wav"
    assert seen["params"]["duration"] == -1.0


def test_text_task_refuses_source_audio():
    with pytest.raises(GenerationError, match="does not use source audio"):
        AceStepRunner().generate(_request(TASK_TEXT, src="/tmp/source.wav"))


def test_cover_requires_source_audio():
    with pytest.raises(GenerationError, match="requires source audio"):
        AceStepRunner().generate(_request(TASK_COVER, src=""))


def test_init_failure(monkeypatch):
    class Broken(Handler):
        def initialize_service(self, **kwargs):  # type: ignore[no-untyped-def]
            return "missing weights", False

    monkeypatch.setattr(
        "app.inference.acestep._load_api",
        lambda: (Broken, Params, Config, lambda *args, **kwargs: None),
    )
    with pytest.raises(ModelInitError, match="missing weights"):
        AceStepRunner().generate(_request(TASK_TEXT))


def test_quantization_not_applied(monkeypatch):
    class Unquantized(Handler):
        def initialize_service(self, **kwargs):  # type: ignore[no-untyped-def]
            self.quantization = None
            return "loaded", True

    monkeypatch.setattr(
        "app.inference.acestep._load_api",
        lambda: (Unquantized, Params, Config, lambda *args, **kwargs: None),
    )
    with pytest.raises(ModelInitError, match="quantization"):
        AceStepRunner().generate(_request(TASK_TEXT))


def test_cuda_oom_from_generate(monkeypatch):
    class OutOfMemoryError(RuntimeError):
        pass

    _install(monkeypatch, explode=OutOfMemoryError("CUDA out of memory"))
    with pytest.raises(CudaOutOfMemory):
        AceStepRunner().generate(_request(TASK_TEXT))


def test_generation_error_result(monkeypatch):
    _install(monkeypatch, result=Result(success=False, error="decoder failed"))
    with pytest.raises(GenerationError, match="decoder failed"):
        AceStepRunner().generate(_request(TASK_TEXT))
