import asyncio
from datetime import datetime
from pathlib import Path

from sqlalchemy import text

from app.db.session import session_scope
from app.shared.config import get_settings


def test_swap_enqueues_without_running_inference(signed_in, sample_media, monkeypatch):
    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("inference must not run inside the HTTP request")

    monkeypatch.setattr("app.worker.tasks.run_swap.delay", lambda job_id: job_id)
    monkeypatch.setattr("app.services.jobs.swap_faces", fail_if_called)

    response = signed_in.post(
        "/api/swap",
        files={
            "source_image": ("face.png", sample_media["image"].read_bytes(), "image/png"),
            "target_video": ("clip.mp4", sample_media["video"].read_bytes(), "video/mp4"),
        },
    )

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "queued"
    assert body["model_name"] is None

    listed = signed_in.get("/api/jobs")
    assert listed.status_code == 200
    assert listed.json()[0]["id"] == body["id"]

    reused = signed_in.post(
        "/api/swap",
        data={
            "source_image_id": body["source_media_id"],
            "target_video_id": body["video_media_id"],
        },
    )
    assert reused.status_code == 202
    again = reused.json()
    assert again["source_media_id"] == body["source_media_id"]
    assert again["video_media_id"] == body["video_media_id"]
    assert again["id"] != body["id"]

    mixed = signed_in.post(
        "/api/swap",
        data={"source_image_id": body["source_media_id"]},
        files={"target_video": ("clip.mp4", sample_media["video"].read_bytes(), "video/mp4")},
    )
    assert mixed.status_code == 202
    mixed_body = mixed.json()
    assert mixed_body["source_media_id"] == body["source_media_id"]
    assert mixed_body["video_media_id"] != body["video_media_id"]

    other = signed_in.post(
        "/api/swap",
        data={"target_video_id": body["video_media_id"]},
        files={"source_image": ("face.png", sample_media["image"].read_bytes(), "image/png")},
    )
    assert other.status_code == 202
    other_body = other.json()
    assert other_body["video_media_id"] == body["video_media_id"]
    assert other_body["source_media_id"] != body["source_media_id"]

    ordered = signed_in.post(
        "/api/swap",
        data={"face_order": "left-right", "target_video_id": body["video_media_id"]},
        files={
            "source_image": ("face.png", sample_media["image"].read_bytes(), "image/png"),
            "source_image_2": ("second.png", sample_media["image"].read_bytes(), "image/png"),
        },
    )
    assert ordered.status_code == 202
    ordered_body = ordered.json()
    assert ordered_body["face_order"] == "left-right"
    assert ordered_body["source_filename"] == "face.png, second.png"


def test_worker_records_model_and_inference_time(signed_in, sample_media):
    created = signed_in.post(
        "/api/swap",
        files={
            "source_image": ("face.png", sample_media["image"].read_bytes(), "image/png"),
            "target_video": ("clip.mp4", sample_media["video"].read_bytes(), "video/mp4"),
        },
    )
    assert created.status_code == 202
    job = created.json()
    assert isinstance(job["id"], int)
    assert job["status"] == "succeeded"
    assert datetime.fromisoformat(job["created_at"].replace("Z", "+00:00")).tzinfo is not None
    assert datetime.fromisoformat(job["finished_at"].replace("Z", "+00:00")).tzinfo is not None
    async def created_at() -> str:
        async with session_scope() as session:
            result = await session.execute(
                text("select created_at from jobs where id = :id"),
                {"id": job["id"]},
            )
            return result.scalar_one()

    stored = asyncio.run(created_at())
    assert isinstance(stored, str)
    assert stored.endswith("+00:00")
    assert job["model_name"] == "HyperSwap"
    assert job["detector_name"] == "RetinaFace"
    assert job["inference_ms"] >= 1
    assert job["simulated"] is True
    assert "HyperSwap" in job["note"]
    assert "RetinaFace" in job["note"]
    assert "ms" in job["note"]

    downloaded = signed_in.get(job["download_url"])
    assert downloaded.status_code == 200
    assert downloaded.headers["content-type"].startswith("video/mp4")
    assert downloaded.content[:8] != b""
    assert Path(get_settings().storage_dir, str(job["id"]), "output.mp4").stat().st_size > 0


def test_rejects_oversized_image(signed_in, sample_media, monkeypatch):
    monkeypatch.setattr(get_settings(), "max_image_bytes", 32)
    response = signed_in.post(
        "/api/swap",
        files={
            "source_image": ("face.png", sample_media["image"].read_bytes(), "image/png"),
            "target_video": ("clip.mp4", sample_media["video"].read_bytes(), "video/mp4"),
        },
    )
    assert response.status_code == 413
    assert response.json()["detail"]["code"] == "file_too_large"


def test_rejects_long_video(signed_in, sample_media, monkeypatch):
    monkeypatch.setattr(get_settings(), "max_video_duration_sec", 0.2)
    response = signed_in.post(
        "/api/swap",
        files={
            "source_image": ("face.png", sample_media["image"].read_bytes(), "image/png"),
            "target_video": ("clip.mp4", sample_media["video"].read_bytes(), "video/mp4"),
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "video_too_long"


def test_download_before_ready_is_conflict(signed_in, sample_media, monkeypatch):
    monkeypatch.setattr("app.worker.tasks.run_swap.delay", lambda job_id: job_id)
    created = signed_in.post(
        "/api/swap",
        files={
            "source_image": ("face.png", sample_media["image"].read_bytes(), "image/png"),
            "target_video": ("clip.mp4", sample_media["video"].read_bytes(), "video/mp4"),
        },
    )
    job_id = created.json()["id"]
    response = signed_in.get(f"/api/jobs/{job_id}/download")
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "not_ready"


def test_job_filters_match_status_and_filename(signed_in, sample_media, monkeypatch):
    monkeypatch.setattr("app.worker.tasks.run_swap.delay", lambda job_id: job_id)
    created = signed_in.post(
        "/api/swap",
        files={
            "source_image": ("face.png", sample_media["image"].read_bytes(), "image/png"),
            "target_video": ("clip.mp4", sample_media["video"].read_bytes(), "video/mp4"),
        },
    )
    job_id = created.json()["id"]
    matched = signed_in.get("/api/jobs", params={"status": "queued", "q": "face.png"})
    assert matched.status_code == 200
    assert [row["id"] for row in matched.json()] == [job_id]
    missed = signed_in.get("/api/jobs", params={"status": "succeeded"})
    assert missed.json() == []
