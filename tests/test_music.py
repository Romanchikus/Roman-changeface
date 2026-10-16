import asyncio
from pathlib import Path

import pytest

from app.db.media import AUDIO, create_media
from app.db.models import MusicJob
from app.db.session import session_scope
from app.inference.acestep import TASK_COVER, TASK_TEXT
from app.services import music
from app.shared.config import get_settings


async def _store_audio(path: Path) -> int:
    async with session_scope() as session:
        media = await create_media(session, AUDIO, path.name, path, path.stat().st_size, 2.0)
        return media.id


def test_text_prompt_uses_job_directory(signed_in):
    response = signed_in.post("/api/v1/music", data={"prompt": "soft piano", "seed": "4"})
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "succeeded"
    assert body["task_type"] == TASK_TEXT
    assert body["output_path"].endswith(f"/{body['id']}/output.flac")
    assert body["input_path"] == ""
    assert body["input_media_id"] is None
    assert body["parameters"]["audio_id"] is None
    assert signed_in.get("/api/jobs").json() == []
    follow = signed_in.get(f"/api/v1/music/jobs/{body['id']}")
    assert follow.status_code == 200
    assert follow.json()["download_url"] == f"/api/files/audios/{body['output_media_id']}/download"


def test_reuses_audio_id(signed_in, tmp_path: Path):
    source = tmp_path / "tone.wav"
    source.write_bytes(b"tone")
    audio_id = asyncio.run(_store_audio(source))
    first = signed_in.post("/api/v1/music", data={"audio_id": str(audio_id)})
    assert first.status_code == 201, first.text
    assert first.json()["input_media_id"] == audio_id
    assert first.json()["input_path"] == str(source)
    assert first.json()["task_type"] == TASK_COVER
    second = signed_in.post(
        "/api/v1/music",
        data={"prompt": "strings", "audio_id": str(audio_id)},
    )
    assert second.status_code == 201, second.text
    body = second.json()
    assert body["input_media_id"] == audio_id
    assert body["input_path"] == str(source)
    assert body["output_path"].endswith(f"/{body['id']}/output.flac")
    assert body["output_media_id"] != first.json()["output_media_id"]
    listed = signed_in.get("/api/files/audios")
    assert listed.status_code == 200
    names = {item["filename"] for item in listed.json()}
    assert "tone.wav" in names
    assert f"{body['id']}.flac" in names


def test_rejects_empty_input(signed_in):
    response = signed_in.post("/api/v1/music", data={"prompt": "  "})
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "media_choice"


def test_rejects_missing_audio(signed_in):
    response = signed_in.post("/api/v1/music", data={"audio_id": "99"})
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "not_found"


def test_missing_job(signed_in):
    assert signed_in.get("/api/v1/music/jobs/999").status_code == 404


def test_failed_insert_removes_incoming_files(signed_in, monkeypatch):
    async def boom(session, job: MusicJob) -> MusicJob:
        session.add(job)
        await session.flush()
        raise RuntimeError("fail the insert")

    monkeypatch.setattr(music, "insert_music", boom)
    with pytest.raises(RuntimeError, match="fail the insert"):
        signed_in.post("/api/v1/music", data={"prompt": "piano"})
    storage = Path(get_settings().storage_dir)
    assert list(storage.glob("_incoming/*")) == []
