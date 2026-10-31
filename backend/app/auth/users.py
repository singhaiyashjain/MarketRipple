"""User database. MongoDB collection "users" (in memory when MONGODB_URI is empty, e.g. local dev).

Document: {username, username_key (lowercase, unique), password_hash, role: "user"|"admin", active,
           created_at, last_login, login_count}
Passwords are stored only as scrypt hashes and never returned by any function that returns a "public" dict.
"""
import re
import threading
from datetime import datetime, timezone

from app.auth.security import hash_password
from app.config import settings
from app.graph import store

COLLECTION = "users"
ROLES = ("user", "admin")
USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{3,32}$")
MIN_PASSWORD, MAX_PASSWORD = 8, 128

_mem: dict[str, dict] = {}
_lock = threading.Lock()
_indexed_client = None


class UserExists(Exception): ...
class UserNotFound(Exception): ...
class StorageUnavailable(Exception): ...


def key(username: str) -> str:
    return username.strip().lower()


def validate(username: str | None = None, password: str | None = None) -> None:
    """Raises ValueError with a message that is safe to show to the person."""
    if username is not None and not USERNAME_RE.match(username.strip()):
        raise ValueError("Username must be 3-32 characters: letters, numbers, . _ -")
    if password is not None and not (MIN_PASSWORD <= len(password) <= MAX_PASSWORD):
        raise ValueError(f"Password must be {MIN_PASSWORD}-{MAX_PASSWORD} characters.")


def public(doc: dict | None) -> dict | None:
    if not doc:
        return None
    return {"username": doc["username"], "role": doc["role"], "active": doc["active"],
            "created_at": _iso(doc.get("created_at")), "last_login": _iso(doc.get("last_login")),
            "login_count": doc.get("login_count", 0)}


def _iso(v):
    return v.isoformat() if isinstance(v, datetime) else v


def _col():
    """The Mongo collection, or None when running in memory."""
    global _indexed_client
    if not settings.mongodb_uri:
        return None
    try:
        store.guard()
        col = store._collection(COLLECTION)
        if _indexed_client is not store._client_obj:
            col.create_index("username_key", unique=True)
            _indexed_client = store._client_obj
        return col
    except Exception as e:
        store.failed()
        raise StorageUnavailable(str(e))


def _run(fn):
    """Run a Mongo operation; any database failure becomes StorageUnavailable."""
    try:
        return fn()
    except (UserExists, UserNotFound, StorageUnavailable):
        raise
    except Exception as e:
        store.failed()
        raise StorageUnavailable(str(e))


def _now():
    return datetime.now(timezone.utc)


def get(username: str) -> dict | None:
    """Full document including password_hash (for login checks only)."""
    k = key(username)
    col = _col()
    if col is None:
        with _lock:
            d = _mem.get(k)
            return dict(d) if d else None
    d = _run(lambda: col.find_one({"username_key": k}, {"_id": 0}))
    return d


def list_users() -> list[dict]:
    col = _col()
    if col is None:
        with _lock:
            docs = [dict(d) for d in _mem.values()]
    else:
        docs = _run(lambda: list(col.find({}, {"_id": 0})))
    docs.sort(key=lambda d: d["username_key"])
    return [public(d) for d in docs]


def create(username: str, password: str, role: str = "user", active: bool = True) -> dict:
    validate(username, password)
    if role not in ROLES:
        raise ValueError("Role must be 'user' or 'admin'.")
    username = username.strip()
    doc = {"username": username, "username_key": key(username), "password_hash": hash_password(password),
           "role": role, "active": active, "created_at": _now(), "last_login": None, "login_count": 0}
    col = _col()
    if col is None:
        with _lock:
            if doc["username_key"] in _mem:
                raise UserExists(username)
            _mem[doc["username_key"]] = doc
    else:
        from pymongo.errors import DuplicateKeyError
        try:
            col.insert_one(dict(doc))
        except DuplicateKeyError:
            raise UserExists(username)
        except Exception as e:
            store.failed()
            raise StorageUnavailable(str(e))
    return public(doc)


def update(username: str, **fields) -> dict:
    """Change role / active / password (given as plain `password`). Returns the public user."""
    allowed = {}
    if "role" in fields and fields["role"] is not None:
        if fields["role"] not in ROLES:
            raise ValueError("Role must be 'user' or 'admin'.")
        allowed["role"] = fields["role"]
    if "active" in fields and fields["active"] is not None:
        allowed["active"] = bool(fields["active"])
    if fields.get("password") is not None:
        validate(password=fields["password"])
        allowed["password_hash"] = hash_password(fields["password"])
    k = key(username)
    col = _col()
    if col is None:
        with _lock:
            if k not in _mem:
                raise UserNotFound(username)
            _mem[k].update(allowed)
            return public(_mem[k])
    if allowed:
        res = _run(lambda: col.update_one({"username_key": k}, {"$set": allowed}))
        if res.matched_count == 0:
            raise UserNotFound(username)
    d = _run(lambda: col.find_one({"username_key": k}, {"_id": 0}))
    if not d:
        raise UserNotFound(username)
    return public(d)


def delete(username: str) -> None:
    k = key(username)
    col = _col()
    if col is None:
        with _lock:
            if _mem.pop(k, None) is None:
                raise UserNotFound(username)
        return
    res = _run(lambda: col.delete_one({"username_key": k}))
    if res.deleted_count == 0:
        raise UserNotFound(username)


def record_login(username: str) -> None:
    k = key(username)
    col = _col()
    if col is None:
        with _lock:
            if k in _mem:
                _mem[k]["last_login"] = _now()
                _mem[k]["login_count"] = _mem[k].get("login_count", 0) + 1
        return
    _run(lambda: col.update_one({"username_key": k}, {"$set": {"last_login": _now()}, "$inc": {"login_count": 1}}))


def active_admin_count() -> int:
    col = _col()
    if col is None:
        with _lock:
            return sum(1 for d in _mem.values() if d["role"] == "admin" and d["active"])
    return _run(lambda: col.count_documents({"role": "admin", "active": True}))


def ensure_bootstrap_admin() -> bool:
    """Create/refresh the admin named by ADMIN_USERNAME / ADMIN_PASSWORD. The env password is the source of truth,
    so changing the variable (and restarting) is the recovery path if the admin is locked out."""
    if not (settings.admin_username and settings.admin_password):
        return False
    validate(settings.admin_username, settings.admin_password)
    if get(settings.admin_username) is None:
        create(settings.admin_username, settings.admin_password, role="admin")
    else:
        update(settings.admin_username, password=settings.admin_password, role="admin", active=True)
    return True
