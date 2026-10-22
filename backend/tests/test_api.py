from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health():
    assert client.get("/api/health").json()["status"] == "ok"


def test_samples():
    r = client.get("/api/samples")
    assert r.status_code == 200 and len(r.json()) >= 3


def test_analyze_returns_contract_shape():
    r = client.post("/api/analyze", json={"news": "Crude oil prices surge by 12% amid tensions.", "simulated": True})
    assert r.status_code == 200
    body = r.json()
    assert body["mode"] in ("live", "fallback", "mock")
    assert body["nodes"] and body["edges"] and body["paths"]
