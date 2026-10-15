def test_register_and_login(client):
    created = client.post("/api/register", json={"email": "Ada@Example.com", "password": "secret"})
    assert created.status_code == 200
    body = created.json()
    assert body["email"] == "ada@example.com"
    assert "password" not in body

    again = client.post("/api/register", json={"email": "ada@example.com", "password": "secret"})
    assert again.status_code == 409

    logged = client.post("/api/login", json={"email": "ada@example.com", "password": "secret"})
    assert logged.status_code == 200
    assert logged.json()["id"] == body["id"]

    wrong = client.post("/api/login", json={"email": "ada@example.com", "password": "nope"})
    assert wrong.status_code == 401

    cookie = logged.headers["set-cookie"]
    assert "session=" in cookie
    assert "HttpOnly" in cookie
    assert client.get("/api/me").json()["email"] == "ada@example.com"

    assert client.post("/api/logout").status_code == 204
    assert client.get("/api/me").status_code == 401
    assert client.get("/api/jobs").status_code == 401
    assert client.get("/api/files/images").status_code == 401
    assert client.get("/api/metrics").status_code == 401
    assert client.get("/api/resources").status_code == 401
