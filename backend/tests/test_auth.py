"""Login, user database and admin panel API (MongoDB is the in-memory fake from conftest)."""
import pytest
from fastapi.testclient import TestClient

from app.auth import deps, security, users
from app.config import settings
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    users._mem.clear()
    deps._fails.clear()
    monkeypatch.setattr(users, "_indexed_client", None)
    monkeypatch.setattr(settings, "auth_required", False)
    monkeypatch.setattr(settings, "auth_secret", "test-secret")
    monkeypatch.setattr(settings, "admin_username", "")
    monkeypatch.setattr(settings, "admin_password", "")


def login(u, p):
    return client.post("/api/auth/login", json={"username": u, "password": p})


def hdr(u, p):
    return {"Authorization": "Bearer " + login(u, p).json()["token"]}


@pytest.fixture
def admin():
    users.create("boss", "bosspass123", role="admin")
    return hdr("boss", "bosspass123")


def test_password_is_hashed_not_stored():
    users.create("alice", "password123")
    doc = users.get("alice")
    assert "password123" not in doc["password_hash"] and doc["password_hash"].startswith("scrypt$")
    assert security.verify_password("password123", doc["password_hash"])
    assert not security.verify_password("wrong", doc["password_hash"])


def test_login_ok_and_wrong_password():
    users.create("alice", "password123")
    r = login("ALICE", "password123")                      # username is case-insensitive
    assert r.status_code == 200 and r.json()["user"]["username"] == "alice"
    assert "password" not in str(r.json()["user"])
    assert login("alice", "nope").status_code == 401
    assert login("ghost", "nope").status_code == 401       # same message for unknown users
    assert users.get("alice")["login_count"] == 1


def test_me_needs_valid_token():
    users.create("alice", "password123")
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/auth/me", headers={"Authorization": "Bearer junk"}).status_code == 401
    assert client.get("/api/auth/me", headers=hdr("alice", "password123")).json()["username"] == "alice"


def test_expired_and_tampered_tokens_rejected():
    users.create("alice", "password123")
    tok, _ = security.make_token("alice", hours=-1)
    assert security.read_token(tok) is None
    good, _ = security.make_token("alice")
    assert security.read_token(good) == "alice"
    assert security.read_token(good[:-2] + "xx") is None


def test_disabled_user_cannot_log_in_or_use_old_token():
    users.create("alice", "password123")
    h = hdr("alice", "password123")
    users.update("alice", active=False)
    assert login("alice", "password123").status_code == 403
    assert client.get("/api/auth/me", headers=h).status_code == 401


def test_lockout_after_repeated_failures(monkeypatch):
    monkeypatch.setattr(settings, "auth_max_failures", 3)
    users.create("alice", "password123")
    for _ in range(3):
        assert login("alice", "bad").status_code == 401
    assert login("alice", "password123").status_code == 429


def test_admin_endpoints_need_admin(admin):
    users.create("alice", "password123")
    assert client.get("/api/admin/users").status_code == 401
    assert client.get("/api/admin/users", headers=hdr("alice", "password123")).status_code == 403
    r = client.get("/api/admin/users", headers=admin)
    assert r.status_code == 200 and r.json()["total"] == 2
    assert all("password" not in u for u in r.json()["users"])


def test_admin_creates_updates_deletes(admin):
    r = client.post("/api/admin/users", headers=admin, json={"username": "bob", "password": "bobpass123"})
    assert r.status_code == 201 and r.json()["role"] == "user"
    assert client.post("/api/admin/users", headers=admin, json={"username": "BOB", "password": "bobpass123"}).status_code == 409
    assert client.post("/api/admin/users", headers=admin, json={"username": "x", "password": "bobpass123"}).status_code == 422
    assert client.post("/api/admin/users", headers=admin, json={"username": "carol", "password": "short"}).status_code == 422
    assert client.patch("/api/admin/users/bob", headers=admin, json={"password": "newpass1234"}).status_code == 200
    assert login("bob", "bobpass123").status_code == 401 and login("bob", "newpass1234").status_code == 200
    assert client.patch("/api/admin/users/bob", headers=admin, json={"active": False}).json()["active"] is False
    assert client.delete("/api/admin/users/bob", headers=admin).status_code == 200
    assert client.delete("/api/admin/users/bob", headers=admin).status_code == 404


def test_cannot_remove_or_lock_out_last_admin(admin):
    assert client.delete("/api/admin/users/boss", headers=admin).status_code == 400
    assert client.patch("/api/admin/users/boss", headers=admin, json={"active": False}).status_code == 400
    assert client.patch("/api/admin/users/boss", headers=admin, json={"role": "user"}).status_code == 400
    users.create("boss2", "bosspass123", role="admin")
    assert client.delete("/api/admin/users/boss2", headers=admin).status_code == 200


def test_change_own_password():
    users.create("alice", "password123")
    h = hdr("alice", "password123")
    body = {"current_password": "wrong", "new_password": "brandnew123"}
    assert client.post("/api/auth/change-password", headers=h, json=body).status_code == 400
    body["current_password"] = "password123"
    assert client.post("/api/auth/change-password", headers=h, json=body).status_code == 200
    assert login("alice", "brandnew123").status_code == 200


def test_bootstrap_admin_from_env(monkeypatch):
    monkeypatch.setattr(settings, "admin_username", "root")
    monkeypatch.setattr(settings, "admin_password", "rootpass123")
    assert users.ensure_bootstrap_admin()
    assert login("root", "rootpass123").json()["user"]["role"] == "admin"
    monkeypatch.setattr(settings, "admin_password", "changed12345")      # env is the source of truth
    users.ensure_bootstrap_admin()
    assert login("root", "changed12345").status_code == 200 and len(users.list_users()) == 1


def test_data_routes_open_by_default_and_locked_when_required(monkeypatch):
    users.create("alice", "password123")
    assert client.get("/api/samples").status_code == 200
    monkeypatch.setattr(settings, "auth_required", True)
    assert client.get("/api/samples").status_code == 401
    assert client.get("/api/samples", headers=hdr("alice", "password123")).status_code == 200
    assert client.get("/api/health").status_code == 200                  # health check stays public


def test_works_in_memory_without_mongodb(monkeypatch):
    monkeypatch.setattr(settings, "mongodb_uri", "")
    users.create("alice", "password123")
    assert login("alice", "password123").status_code == 200
    with pytest.raises(users.UserExists):
        users.create("Alice", "password123")
