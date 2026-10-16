import pytest

from app.db.models import TextJob
from app.inference.llama import LLAMA_31, LLAMA_33
from app.services import text_jobs


def test_required_parameters_round_trip(signed_in):
    response = signed_in.post(
        "/api/v1/text",
        json={"model": LLAMA_31, "prompt": "Say hello", "max_new_tokens": 32},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "succeeded"
    assert body["output"] == ""
    assert body["prompt"] == "Say hello"
    parameters = body["parameters"]
    assert parameters["model"] == LLAMA_31
    assert parameters["prompt"] == "Say hello"
    assert parameters["max_new_tokens"] == 32
    assert parameters["temperature"] is None
    assert parameters["top_p"] is None
    assert parameters["system"] is None
    assert signed_in.get("/api/jobs").json() == []
    follow = signed_in.get(f"/api/v1/text/jobs/{body['id']}")
    assert follow.status_code == 200
    assert follow.json()["parameters"]["model"] == LLAMA_31


def test_optional_llama_parameters(signed_in):
    response = signed_in.post(
        "/api/v1/text",
        json={
            "model": LLAMA_33,
            "prompt": "Write a verse",
            "max_new_tokens": 64,
            "system": "You are brief.",
            "temperature": 0.6,
            "top_p": 0.9,
            "top_k": 40,
            "min_p": 0.05,
            "typical_p": 1,
            "do_sample": True,
            "seed": 7,
            "repetition_penalty": 1.1,
            "presence_penalty": 0,
            "frequency_penalty": 0.2,
            "stop": ["\n\n"],
            "ignore_eos": False,
            "min_new_tokens": 1,
        },
    )
    assert response.status_code == 201, response.text
    parameters = response.json()["parameters"]
    assert parameters["model"] == LLAMA_33
    assert parameters["temperature"] == 0.6
    assert parameters["top_p"] == 0.9
    assert parameters["do_sample"] is True
    assert parameters["ignore_eos"] is False
    assert parameters["presence_penalty"] == 0
    assert parameters["stop"] == ["\n\n"]
    assert parameters["seed"] == 7


def test_rejects_unknown_model(signed_in):
    response = signed_in.post(
        "/api/v1/text",
        json={"model": "other", "prompt": "hello", "max_new_tokens": 8},
    )
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "model"


def test_rejects_empty_prompt(signed_in):
    response = signed_in.post(
        "/api/v1/text",
        json={"model": LLAMA_31, "prompt": "  ", "max_new_tokens": 8},
    )
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "prompt"


def test_rejects_temperature(signed_in):
    response = signed_in.post(
        "/api/v1/text",
        json={"model": LLAMA_31, "prompt": "hello", "max_new_tokens": 8, "temperature": 3},
    )
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "temperature"


def test_missing_job(signed_in):
    assert signed_in.get("/api/v1/text/jobs/999").status_code == 404


def test_requires_sign_in(client):
    response = client.post(
        "/api/v1/text",
        json={"model": LLAMA_31, "prompt": "hello", "max_new_tokens": 8},
    )
    assert response.status_code == 401


def test_failed_insert_rolls_back(signed_in, monkeypatch):
    async def boom(session, job: TextJob) -> TextJob:
        session.add(job)
        await session.flush()
        raise RuntimeError("fail the insert")

    monkeypatch.setattr(text_jobs, "insert_text_job", boom)
    with pytest.raises(RuntimeError, match="fail the insert"):
        signed_in.post(
            "/api/v1/text",
            json={"model": LLAMA_31, "prompt": "hello", "max_new_tokens": 8},
        )
    assert signed_in.get("/api/v1/text/jobs/1").status_code == 404
