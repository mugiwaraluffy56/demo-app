import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app import store

router = APIRouter(prefix="/tasks/{task_id}/comments", tags=["Comments"])


class CommentCreate(BaseModel):
    author_id: str
    body: str


class CommentUpdate(BaseModel):
    body: str


class CommentOut(BaseModel):
    id: str
    task_id: str
    author_id: str
    body: str
    created_at: str


@router.post("", response_model=CommentOut, status_code=201)
def add_comment(task_id: str, body: CommentCreate):
    if task_id not in store.tasks:
        raise HTTPException(404, "Task not found")
    if body.author_id not in store.users:
        raise HTTPException(404, f"Author {body.author_id!r} not found")
    comment = {
        "id": str(uuid.uuid4()),
        "task_id": task_id,
        "author_id": body.author_id,
        "body": body.body,
        "created_at": datetime.utcnow().isoformat(),
    }
    store.comments[comment["id"]] = comment
    return comment


@router.get("", response_model=list[CommentOut])
def list_comments(task_id: str):
    if task_id not in store.tasks:
        raise HTTPException(404, "Task not found")
    return [c for c in store.comments.values() if c["task_id"] == task_id]


@router.get("/{comment_id}", response_model=CommentOut)
def get_comment(task_id: str, comment_id: str):
    comment = store.comments.get(comment_id)
    if not comment or comment["task_id"] != task_id:
        raise HTTPException(404, "Comment not found")
    return comment


@router.put("/{comment_id}", response_model=CommentOut)
def update_comment(task_id: str, comment_id: str, body: CommentUpdate):
    comment = store.comments.get(comment_id)
    if not comment or comment["task_id"] != task_id:
        raise HTTPException(404, "Comment not found")
    comment["body"] = body.body
    return comment


@router.delete("/{comment_id}", status_code=204)
def delete_comment(task_id: str, comment_id: str):
    comment = store.comments.get(comment_id)
    if not comment or comment["task_id"] != task_id:
        raise HTTPException(404, "Comment not found")
    del store.comments[comment_id]
