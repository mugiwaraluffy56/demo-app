import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from app import store

router = APIRouter(prefix="/projects", tags=["Projects"])


class ProjectCreate(BaseModel):
    name: str
    description: str | None = None
    owner_id: str
    status: str = "active"  # active | archived


class ProjectUpdate(BaseModel):
    name: str
    description: str | None = None
    status: str


class ProjectPatch(BaseModel):
    name: str | None = None
    description: str | None = None
    status: str | None = None


class ProjectOut(BaseModel):
    id: str
    name: str
    description: str | None
    owner_id: str
    status: str
    created_at: str


@router.post("", response_model=ProjectOut, status_code=201)
def create_project(body: ProjectCreate):
    if body.owner_id not in store.users:
        raise HTTPException(404, f"Owner user {body.owner_id!r} not found")
    project = {
        "id": str(uuid.uuid4()),
        "name": body.name,
        "description": body.description,
        "owner_id": body.owner_id,
        "status": body.status,
        "created_at": datetime.utcnow().isoformat(),
    }
    store.projects[project["id"]] = project
    return project


@router.get("", response_model=list[ProjectOut])
def list_projects(
    owner_id: str | None = Query(None),
    status: str | None = Query(None),
):
    projects = list(store.projects.values())
    if owner_id:
        projects = [p for p in projects if p["owner_id"] == owner_id]
    if status:
        projects = [p for p in projects if p["status"] == status]
    return projects


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: str):
    project = store.projects.get(project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    return project


@router.put("/{project_id}", response_model=ProjectOut)
def replace_project(project_id: str, body: ProjectUpdate):
    project = store.projects.get(project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    project.update({
        "name": body.name,
        "description": body.description,
        "status": body.status,
    })
    return project


@router.patch("/{project_id}", response_model=ProjectOut)
def patch_project(project_id: str, body: ProjectPatch):
    project = store.projects.get(project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    for field, value in body.model_dump(exclude_none=True).items():
        project[field] = value
    return project


@router.delete("/{project_id}", status_code=204)
def delete_project(project_id: str):
    if project_id not in store.projects:
        raise HTTPException(404, "Project not found")
    del store.projects[project_id]
