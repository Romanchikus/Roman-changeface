import asyncio
import ctypes
from pathlib import Path

from app.db.jobs import get_job
from app.db.models import Job
from app.db.session import session_scope
from app.inference.cuda import assert_cuda_libraries
from app.inference.pipeline import swap_faces
from app.shared.config import get_settings
from app.shared.errors import CudaUnavailableError, GpuBusy
from app.worker.gpu_lock import gpu_slot
from app.worker.tasks import run_swap


def test_missing_cuda_names_the_libraries(monkeypatch):
    def boom(name: str):
        raise OSError(f"cannot load {name}")

    monkeypatch.setattr(ctypes, "CDLL", boom)
    with pytest_raises_cuda():
        assert_cuda_libraries()


def pytest_raises_cuda():
    import pytest

    return pytest.raises(CudaUnavailableError, match="no video was written")


def test_hyperswap_without_cuda_does_not_write_a_video(tmp_path, monkeypatch):
    monkeypatch.setattr(get_settings(), "inference_backend", "hyperswap")
    monkeypatch.setattr(get_settings(), "hyperswap_weights", str(tmp_path / "weights.onnx"))
    (tmp_path / "weights.onnx").write_bytes(b"weights")
    source = tmp_path / "source.png"
    video = tmp_path / "target.mp4"
    output = tmp_path / "output.mp4"
    source.write_bytes(b"img")
    video.write_bytes(b"vid")

    def boom(name: str):
        raise OSError(f"cannot load {name}")

    monkeypatch.setattr("app.inference.cuda.ctypes.CDLL", boom)

    with pytest_raises_cuda():
        swap_faces(source, video, output)

    assert not output.exists()


def test_worker_stores_cuda_error_and_leaves_no_file(signed_in, sample_media, monkeypatch):
    monkeypatch.setattr(get_settings(), "inference_backend", "hyperswap")
    monkeypatch.setattr(get_settings(), "hyperswap_weights", str(sample_media["image"]))

    def boom(name: str):
        raise OSError(f"cannot load {name}")

    monkeypatch.setattr("app.inference.cuda.ctypes.CDLL", boom)
    monkeypatch.setattr("app.worker.tasks.gpu_slot", _noop_slot())

    created = signed_in.post(
        "/api/swap",
        files={
            "source_image": ("face.png", sample_media["image"].read_bytes(), "image/png"),
            "target_video": ("clip.mp4", sample_media["video"].read_bytes(), "video/mp4"),
        },
    )
    body = created.json()
    assert body["status"] == "failed"
    assert body["error_code"] == "cuda_unavailable"
    assert "no video was written" in body["error_message"]
    assert "black video" in body["error_message"]
    output = Path(get_settings().storage_dir) / str(body["id"]) / "output.mp4"
    assert not output.exists()


def test_gpu_slot_refuses_a_second_hyperswap_without_redis(monkeypatch):
    monkeypatch.setattr(get_settings(), "inference_backend", "hyperswap")
    monkeypatch.setattr(get_settings(), "redis_url", "")
    try:
        with gpu_slot():
            raise AssertionError("slot should not be acquired")
    except GpuBusy as exc:
        assert "Redis" in str(exc)


def test_stuck_import_is_not_required_for_task_registration():
    assert run_swap.name == "changeface.swap"


def _noop_slot():
    from contextlib import contextmanager

    @contextmanager
    def _slot():
        yield

    return _slot


def test_job_row_matches_api(signed_in, sample_media):
    created = signed_in.post(
        "/api/swap",
        files={
            "source_image": ("face.png", sample_media["image"].read_bytes(), "image/png"),
            "target_video": ("clip.mp4", sample_media["video"].read_bytes(), "video/mp4"),
        },
    )
    job_id = created.json()["id"]
    async def load() -> Job:
        async with session_scope() as session:
            row = await get_job(session, job_id)
            assert row is not None
            return row

    job = asyncio.run(load())
    assert isinstance(job, Job)
    assert isinstance(job.id, int)
    assert job.created_at.tzinfo is not None
    assert job.finished_at is not None and job.finished_at.tzinfo is not None
    assert job.model_name == "HyperSwap"
    assert job.detector_name == "RetinaFace"
