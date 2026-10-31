"""Admin panel API (admins only): /api/admin/users ..."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth import deps, users

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(deps.require_admin)])


class NewUser(BaseModel):
    username: str = Field(max_length=64)
    password: str = Field(max_length=128)
    role: str = "user"


class UserPatch(BaseModel):
    role: str | None = None
    active: bool | None = None
    password: str | None = Field(default=None, max_length=128)


def _storage(fn):
    try:
        return fn()
    except users.StorageUnavailable:
        raise HTTPException(503, "User database unavailable.")
    except users.UserNotFound:
        raise HTTPException(404, "No such user.")
    except users.UserExists:
        raise HTTPException(409, "That username is already taken.")
    except ValueError as e:
        raise HTTPException(422, str(e))


def _would_remove_last_admin(target: str, role: str | None, active: bool | None) -> bool:
    doc = users.get(target)
    if not doc or doc["role"] != "admin" or not doc["active"]:
        return False
    losing = (role is not None and role != "admin") or active is False
    return losing and users.active_admin_count() <= 1


@router.get("/users")
def list_users():
    rows = _storage(users.list_users)
    return {"users": rows, "total": len(rows),
            "admins": sum(1 for u in rows if u["role"] == "admin"),
            "active": sum(1 for u in rows if u["active"])}


@router.post("/users", status_code=201)
def create_user(body: NewUser):
    return _storage(lambda: users.create(body.username, body.password, body.role))


@router.patch("/users/{username}")
def patch_user(username: str, body: UserPatch, me: dict = Depends(deps.current_user)):
    if users.key(username) == users.key(me["username"]) and (body.active is False or (body.role and body.role != "admin")):
        raise HTTPException(400, "You cannot disable or demote your own account.")
    if _storage(lambda: _would_remove_last_admin(username, body.role, body.active)):
        raise HTTPException(400, "That would leave no active admin.")
    return _storage(lambda: users.update(username, role=body.role, active=body.active, password=body.password))


@router.delete("/users/{username}")
def delete_user(username: str, me: dict = Depends(deps.current_user)):
    if users.key(username) == users.key(me["username"]):
        raise HTTPException(400, "You cannot delete your own account.")
    if _storage(lambda: _would_remove_last_admin(username, "user", None)):
        raise HTTPException(400, "That would leave no active admin.")
    _storage(lambda: users.delete(username))
    return {"deleted": username}
