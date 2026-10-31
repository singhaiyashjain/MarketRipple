"""FastAPI dependencies: who is calling, and are they allowed."""
import threading
import time

from fastapi import Depends, HTTPException, Request

from app.auth import users
from app.auth.security import read_token
from app.config import settings

_fail_lock = threading.Lock()
_fails: dict[str, list[float]] = {}          # "ip|username" -> [failed attempt times]


def client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")        # Render puts the real client first
    return (fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "?"))


def _fail_key(request: Request, username: str) -> str:
    return f"{client_ip(request)}|{users.key(username)}"


def check_lockout(request: Request, username: str) -> None:
    now = time.time()
    with _fail_lock:
        recent = [t for t in _fails.get(_fail_key(request, username), []) if now - t < settings.auth_lockout_seconds]
        if len(recent) >= settings.auth_max_failures:
            wait = int(settings.auth_lockout_seconds - (now - recent[0])) + 1
            raise HTTPException(429, f"Too many wrong attempts. Try again in {wait} seconds.")


def note_failure(request: Request, username: str) -> None:
    with _fail_lock:
        _fails.setdefault(_fail_key(request, username), []).append(time.time())


def clear_failures(request: Request, username: str) -> None:
    with _fail_lock:
        _fails.pop(_fail_key(request, username), None)


def current_user(request: Request) -> dict:
    """The logged-in, active user (public dict). 401 otherwise."""
    h = request.headers.get("authorization", "")
    name = read_token(h[7:]) if h.lower().startswith("bearer ") else None
    if not name:
        raise HTTPException(401, "Please sign in.", headers={"WWW-Authenticate": "Bearer"})
    try:
        doc = users.get(name)
    except users.StorageUnavailable:
        raise HTTPException(503, "User database unavailable.")
    if not doc or not doc["active"]:
        raise HTTPException(401, "Please sign in.", headers={"WWW-Authenticate": "Bearer"})
    return users.public(doc)


def require_admin(user: dict = Depends(current_user)) -> dict:
    if user["role"] != "admin":
        raise HTTPException(403, "Admins only.")
    return user


def gate(request: Request) -> None:
    """Put on the data routers. Does nothing unless AUTH_REQUIRED=true."""
    if settings.auth_required:
        current_user(request)
