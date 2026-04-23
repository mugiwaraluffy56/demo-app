import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from app import store

router = APIRouter(prefix="/tasks", tags=["Tasks"])

VALID_STATUSES = {"todo", "in_progress", "done", "cancelled"}
VALID_PRIORITIES = {"low", "medium", "high"}


class TaskCreate(BaseModel):
    title: str
    description: str | None = None
    project_id: str
    assignee_id: str | None = None
    status: str = "todo"
    priority: str = "medium"
    due_date: str | None = None  # ISO date string


class TaskUpdate(BaseModel):
    title: str
    description: str | None = None
    assignee_id: str | None = None
    status: str
    priority: str
    due_date: str | None = None


class TaskPatch(BaseModel):
    title: str | None = None
    description: str | None = None
    assignee_id: str | None = None
    status: str | None = None
    priority: str | None = None
    due_date: str | None = None


class TaskOut(BaseModel):
    id: str
    title: str
    description: str | None
    project_id: str
    assignee_id: str | None
    status: str
    priority: str
    due_date: str | None
    created_at: str


@router.post("", response_model=TaskOut, status_code=201)
def create_task(body: TaskCreate):
    if body.project_id not in store.projects:
        raise HTTPException(404, f"Project {body.project_id!r} not found")
    if body.assignee_id and body.assignee_id not in store.users:
        raise HTTPException(404, f"Assignee {body.assignee_id!r} not found")
    if body.status not in VALID_STATUSES:
        raise HTTPException(400, f"status must be one of {VALID_STATUSES}")
    if body.priority not in VALID_PRIORITIES:
        raise HTTPException(400, f"priority must be one of {VALID_PRIORITIES}")

    task = {
        "id": str(uuid.uuid4()),
        "title": body.title,
        "description": body.description,
        "project_id": body.project_id,
        "assignee_id": body.assignee_id,
        "status": body.status,
        "priority": body.priority,
        "due_date": body.due_date,
        "created_at": datetime.utcnow().isoformat(),
    }
    store.tasks[task["id"]] = task
    return task


@router.get("", response_model=list[TaskOut])
def list_tasks(
    project_id: str | None = Query(None),
    assignee_id: str | None = Query(None),
    status: str | None = Query(None),
    priority: str | None = Query(None),
):
    tasks = list(store.tasks.values())
    if project_id:
        tasks = [t for t in tasks if t["project_id"] == project_id]
    if assignee_id:
        tasks = [t for t in tasks if t["assignee_id"] == assignee_id]
    if status:
        tasks = [t for t in tasks if t["status"] == status]
    if priority:
        tasks = [t for t in tasks if t["priority"] == priority]
    return tasks


@router.get("/{task_id}", response_model=TaskOut)
def get_task(task_id: str):
    task = store.tasks.get(task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    return task


@router.put("/{task_id}", response_model=TaskOut)
def replace_task(task_id: str, body: TaskUpdate):
    task = store.tasks.get(task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    if body.status not in VALID_STATUSES:
        raise HTTPException(400, f"status must be one of {VALID_STATUSES}")
    if body.priority not in VALID_PRIORITIES:
        raise HTTPException(400, f"priority must be one of {VALID_PRIORITIES}")
    if body.assignee_id and body.assignee_id not in store.users:
        raise HTTPException(404, f"Assignee {body.assignee_id!r} not found")
    task.update({
        "title": body.title,
        "description": body.description,
        "assignee_id": body.assignee_id,
        "status": body.status,
        "priority": body.priority,
        "due_date": body.due_date,
    })
    return task


@router.patch("/{task_id}", response_model=TaskOut)
def patch_task(task_id: str, body: TaskPatch):
    task = store.tasks.get(task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    updates = body.model_dump(exclude_none=True)
    if "status" in updates and updates["status"] not in VALID_STATUSES:
        raise HTTPException(400, f"status must be one of {VALID_STATUSES}")
    if "priority" in updates and updates["priority"] not in VALID_PRIORITIES:
        raise HTTPException(400, f"priority must be one of {VALID_PRIORITIES}")
    task.update(updates)
    return task


@router.delete("/{task_id}", status_code=204)
def delete_task(task_id: str):
    if task_id not in store.tasks:
        raise HTTPException(404, "Task not found")
    del store.tasks[task_id]
