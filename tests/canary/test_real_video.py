import os
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"
SOURCE = FIXTURES / "source.png"
VIDEO = FIXTURES / "target.mp4"


@pytest.mark.canary
def test_real_video_swap(signed_in):
    """Drop a real source.png and target.mp4 into tests/canary/fixtures, then run:

    CHANGEFACE_CANARY=1 INFERENCE_BACKEND=hyperswap HYPERSWAP_WEIGHTS=/path/to/weights \\
        uv run pytest -m canary
    """
    if os.environ.get("CHANGEFACE_CANARY") != "1":
        pytest.skip("Canary is off. Set CHANGEFACE_CANARY=1 when the real clip and weights are ready.")
    if not SOURCE.is_file() or not VIDEO.is_file():
        pytest.skip("Add tests/canary/fixtures/source.png and target.mp4.")
    if not os.environ.get("HYPERSWAP_WEIGHTS"):
        pytest.skip("Set HYPERSWAP_WEIGHTS to the mounted HyperSwap weights.")

    response = signed_in.post(
        "/api/swap",
        files={
            "source_image": ("source.png", SOURCE.read_bytes(), "image/png"),
            "target_video": ("target.mp4", VIDEO.read_bytes(), "video/mp4"),
        },
    )
    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "succeeded"
    assert body["simulated"] is False
    assert body["model_name"] == "HyperSwap"
    assert body["detector_name"] == "RetinaFace"
    assert body["inference_ms"] >= 1
    downloaded = signed_in.get(body["download_url"])
    assert downloaded.status_code == 200
    assert len(downloaded.content) > 0
