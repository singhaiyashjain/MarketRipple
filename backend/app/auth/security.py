"""Password hashing and signed login tokens. Standard library only (no new dependencies).

Passwords: scrypt with a random salt per user. Tokens: base64url(JSON) + "." + HMAC-SHA256, with an expiry.
"""
import base64
import binascii
import hashlib
import hmac
import json
import logging
import os
import secrets
import time

from app.config import settings

log = logging.getLogger("marketripple.auth")

_N, _R, _P = 2 ** 14, 8, 1
_runtime_secret = secrets.token_hex(32)       # used only when AUTH_SECRET is not configured
_warned = False


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.scrypt(password.encode(), salt=salt, n=_N, r=_R, p=_P, dklen=32)
    return f"scrypt${_N}${_R}${_P}${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, n, r, p, salt, dk = stored.split("$")
        calc = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=int(n), r=int(r), p=int(p), dklen=32)
        return hmac.compare_digest(calc, bytes.fromhex(dk))
    except (ValueError, TypeError):
        return False


DUMMY_HASH = hash_password("not-a-real-password")   # compared against when the user does not exist (same timing)


def _secret() -> bytes:
    global _warned
    if settings.auth_secret:
        return settings.auth_secret.encode()
    if not _warned:
        log.warning("AUTH_SECRET is not set: using a random one, so every login ends when the server restarts.")
        _warned = True
    return _runtime_secret.encode()


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def _unb64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def make_token(username: str, hours: float | None = None) -> tuple[str, int]:
    """Returns (token, expires_at_unix_seconds)."""
    exp = int(time.time() + 3600 * (hours if hours is not None else settings.auth_token_hours))
    body = _b64(json.dumps({"sub": username, "exp": exp}, separators=(",", ":")).encode())
    sig = _b64(hmac.new(_secret(), body.encode(), hashlib.sha256).digest())
    return f"{body}.{sig}", exp


def read_token(token: str) -> str | None:
    """Returns the username if the token is genuine and not expired, else None."""
    try:
        body, sig = token.split(".")
        good = _b64(hmac.new(_secret(), body.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(sig, good):
            return None
        data = json.loads(_unb64(body))
        if data["exp"] < time.time():
            return None
        return str(data["sub"])
    except (ValueError, KeyError, TypeError, binascii.Error):
        return None
