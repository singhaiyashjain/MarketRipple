"""Login: POST /api/auth/login, GET /api/auth/me, POST /api/auth/change-password."""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.auth import deps, users
from app.auth.security import DUMMY_HASH, make_token, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginIn(BaseModel):
    username: str = Field(max_length=64)
    password: str = Field(max_length=128)


class PasswordIn(BaseModel):
    current_password: str = Field(max_length=128)
    new_password: str = Field(max_length=128)


@router.post("/login")
def login(body: LoginIn, request: Request):
    deps.check_lockout(request, body.username)
    try:
        doc = users.get(body.username)
    except users.StorageUnavailable:
        raise HTTPException(503, "User database unavailable. Try again shortly.")
    ok = verify_password(body.password, doc["password_hash"] if doc else DUMMY_HASH)   # same work either way
    if not (doc and ok):
        deps.note_failure(request, body.username)
        raise HTTPException(401, "Wrong username or password.")
    if not doc["active"]:
        raise HTTPException(403, "This account is disabled. Ask an admin.")
    deps.clear_failures(request, body.username)
    users.record_login(doc["username"])
    token, exp = make_token(doc["username"])
    return {"token": token, "expires_at": exp, "user": users.public(users.get(doc["username"]))}


@router.get("/me")
def me(user: dict = Depends(deps.current_user)):
    return user


@router.post("/change-password")
def change_password(body: PasswordIn, user: dict = Depends(deps.current_user)):
    doc = users.get(user["username"])
    if not doc or not verify_password(body.current_password, doc["password_hash"]):
        raise HTTPException(400, "Current password is wrong.")
    try:
        users.update(user["username"], password=body.new_password)
    except ValueError as e:
        raise HTTPException(422, str(e))
    return {"ok": True}
