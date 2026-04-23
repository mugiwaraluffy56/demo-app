import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from app import store

router = APIRouter(prefix="/users", tags=["Users"])


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    role: str = "member"  # member | admin


class UserUpdate(BaseModel):
    name: str
    role: str


class UserOut(BaseModel):
    id: str
    name: str
    email: str
    role: str
    created_at: str


@router.post("", response_model=UserOut, status_code=201)
def create_user(body: UserCreate):
    for u in store.users.values():
        if u["email"] == body.email:
            raise HTTPException(409, f"Email {body.email!r} already registered")
    user = {
        "id": str(uuid.uuid4()),
        "name": body.name,
        "email": body.email,
        "role": body.role,
        "created_at": datetime.utcnow().isoformat(),
    }
    store.users[user["id"]] = user
    return user


@router.get("", response_model=list[UserOut])
def list_users(role: str | None = None):
    users = list(store.users.values())
    if role:
        users = [u for u in users if u["role"] == role]
    return users


@router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: str):
    user = store.users.get(user_id)
    if not user:
        raise HTTPException(404, "User not found")
    return user


@router.put("/{user_id}", response_model=UserOut)
def update_user(user_id: str, body: UserUpdate):
    user = store.users.get(user_id)
    if not user:
        raise HTTPException(404, "User not found")
    user.update({"name": body.name, "role": body.role})
    return user


@router.delete("/{user_id}", status_code=204)
def delete_user(user_id: str):
    if user_id not in store.users:
        raise HTTPException(404, "User not found")
    del store.users[user_id]
