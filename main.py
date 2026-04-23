import pathlib
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.routers import users, projects, tasks, comments, external
from monitor import ApiMonitorMiddleware

API_KEY = "mkey_0QnuZABji7verNyv-2MfJIvwpirurnAT-eymNkdpl08"

app = FastAPI(title="TaskBoard API", version="1.0.0")
app.add_middleware(ApiMonitorMiddleware, api_key=API_KEY)

app.include_router(users.router)
app.include_router(projects.router)
app.include_router(tasks.router)
app.include_router(comments.router)
app.include_router(external.router)


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok"}


# Serve frontend
_frontend = pathlib.Path(__file__).parent / "frontend"
app.mount("/static", StaticFiles(directory=str(_frontend)), name="static")


@app.get("/", include_in_schema=False)
def ui():
    return FileResponse(str(_frontend / "index.html"))
