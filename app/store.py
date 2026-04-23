"""In-memory data store shared across routers."""
from typing import Any

users: dict[str, Any] = {}
projects: dict[str, Any] = {}
tasks: dict[str, Any] = {}
comments: dict[str, Any] = {}
