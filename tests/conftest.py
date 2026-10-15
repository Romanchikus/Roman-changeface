import asyncio
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / ".test-runtime"
RUNTIME.mkdir(parents=True, exist_ok=True)
(RUNTIME / "storage").mkdir(parents=True, exist_ok=True)

os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{RUNTIME / 'test.db'}"
os.environ["STORAGE_DIR"] = str(RUNTIME / "storage")
os.environ["REDIS_URL"] = ""
os.environ["HYPERSWAP_WEIGHTS"] = ""

if os.environ.get("CHANGEFACE_CANARY") != "1":
    os.environ["INFERENCE_BACKEND"] = "simulator"
    os.environ["CELERY_TASK_ALWAYS_EAGER"] = "true"
else:
    os.environ.setdefault("CELERY_TASK_ALWAYS_EAGER", "true")

import pytest
from fastapi.testclient import TestClient

from app.db.models import Base
from app.db.session import dispose_loop_engine, get_engine
from app.main import app
from app.media import remove_tree


@pytest.fixture(scope="session")
def sample_media(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    folder = tmp_path_factory.mktemp("media")
    image = folder / "source.png"
    video = folder / "target.mp4"
    subprocess.check_call(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=0x336699:s=32x32:d=1",
            "-frames:v",
            "1",
            str(image),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    subprocess.check_call(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=0x336699:s=64x64:d=1",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(video),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return {"image": image, "video": video}


@pytest.fixture
def client():
    async def reset() -> None:
        engine = get_engine()
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
            await connection.run_sync(Base.metadata.create_all)
        await dispose_loop_engine()

    asyncio.run(reset())
    remove_tree(Path(os.environ["STORAGE_DIR"]))
    Path(os.environ["STORAGE_DIR"]).mkdir(parents=True, exist_ok=True)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def signed_in(client):
    response = client.post(
        "/api/register",
        json={"email": "runner@example.com", "password": "secret"},
    )
    assert response.status_code == 200, response.text
    return client
