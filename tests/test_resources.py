def test_resources_reports_memory_and_task(signed_in, sample_media, monkeypatch):
    monkeypatch.setattr("app.worker.tasks.run_swap.delay", lambda job_id: job_id)
    empty = signed_in.get("/api/resources")
    assert empty.status_code == 200
    assert empty.json()["ram_total_bytes"] > 0
    assert empty.json()["job_id"] is None

    created = signed_in.post(
        "/api/swap",
        files={
            "source_image": ("face.png", sample_media["image"].read_bytes(), "image/png"),
            "target_video": ("clip.mp4", sample_media["video"].read_bytes(), "video/mp4"),
        },
    )
    assert created.status_code == 202
    body = signed_in.get("/api/resources").json()
    assert body["job_id"] == created.json()["id"]
    assert body["job_status"] == "queued"
    assert body["elapsed_ms"] >= 0
