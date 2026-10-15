from app.metrics.traffic import Traffic


def test_idle_after_quiet_window():
    load = Traffic()
    assert load.idle()
    load.enter()
    load.leave()
    assert load.inflight == 0
    assert load.recent() == 1
    assert not load.idle()


def test_metrics_returns_cached_series(signed_in):
    body = signed_in.get("/api/metrics")
    assert body.status_code == 200
    payload = body.json()
    assert isinstance(payload["samples"], list)
    assert "inflight" in payload
    assert "requests_last_10s" in payload
    stamps = [item["sampled_at"] for item in payload["samples"]]
    assert stamps == sorted(stamps)
