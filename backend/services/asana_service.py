import os
import base64
from datetime import date
from typing import Any

import httpx
from cryptography.fernet import Fernet

_FERNET_KEY_ENV = "FERNET_KEY"


def _get_fernet() -> Fernet:
    key = os.getenv(_FERNET_KEY_ENV)
    if not key:
        # Generate a stable key derived from a fixed seed for dev; in production set FERNET_KEY env var
        key = base64.urlsafe_b64encode(b"dashboard-builder-secret-key-padded!"[:32])
    return Fernet(key)


def encrypt_value(value: str) -> str:
    f = _get_fernet()
    return f.encrypt(value.encode()).decode()


def decrypt_value(encrypted: str) -> str:
    f = _get_fernet()
    return f.decrypt(encrypted.encode()).decode()


ASANA_BASE = "https://app.asana.com/api/1.0"


async def test_asana_token(pat: str) -> dict | None:
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{ASANA_BASE}/users/me",
                headers={"Authorization": f"Bearer {pat}"},
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                return {"name": data["data"].get("name"), "email": data["data"].get("email")}
    except Exception:
        pass
    return None


async def fetch_asana_data(pat: str) -> dict:
    headers = {"Authorization": f"Bearer {pat}"}
    async with httpx.AsyncClient(timeout=30) as client:
        # Fetch workspaces
        ws_resp = await client.get(f"{ASANA_BASE}/workspaces", headers=headers)
        ws_resp.raise_for_status()
        workspaces = ws_resp.json().get("data", [])
        workspace = workspaces[0] if workspaces else {"gid": "", "name": ""}

        workspace_id = workspace.get("gid", "")
        workspace_name = workspace.get("name", "")

        # Fetch projects
        projects_raw = []
        if workspace_id:
            proj_resp = await client.get(
                f"{ASANA_BASE}/projects",
                headers=headers,
                params={
                    "workspace": workspace_id,
                    "opt_fields": "name,current_status,due_date,members,completed",
                },
            )
            proj_resp.raise_for_status()
            projects_raw = proj_resp.json().get("data", [])

        projects = []
        all_tasks = []

        today = date.today().isoformat()

        for proj in projects_raw:
            proj_id = proj.get("gid", "")
            proj_name = proj.get("name", "")
            status_obj = proj.get("current_status") or {}
            status = status_obj.get("text", "") if isinstance(status_obj, dict) else ""
            due_date = proj.get("due_date") or ""
            members = [m.get("name", "") for m in (proj.get("members") or [])]

            # Fetch tasks for this project
            tasks_resp = await client.get(
                f"{ASANA_BASE}/tasks",
                headers=headers,
                params={
                    "project": proj_id,
                    "opt_fields": "name,assignee.name,due_on,completed,tags.name",
                },
            )
            tasks_resp.raise_for_status()
            tasks_raw = tasks_resp.json().get("data", [])

            total_tasks = len(tasks_raw)
            completed_tasks = sum(1 for t in tasks_raw if t.get("completed"))
            incomplete_tasks = total_tasks - completed_tasks
            overdue_tasks = sum(
                1 for t in tasks_raw
                if not t.get("completed") and t.get("due_on") and t["due_on"] < today
            )

            projects.append({
                "id": proj_id,
                "name": proj_name,
                "status": status,
                "due_date": due_date,
                "total_tasks": total_tasks,
                "completed_tasks": completed_tasks,
                "incomplete_tasks": incomplete_tasks,
                "overdue_tasks": overdue_tasks,
                "members": members,
            })

            for task in tasks_raw:
                assignee = task.get("assignee") or {}
                tags = [tag.get("name", "") for tag in (task.get("tags") or [])]
                all_tasks.append({
                    "id": task.get("gid", ""),
                    "name": task.get("name", ""),
                    "project": proj_name,
                    "assignee": assignee.get("name", "") if isinstance(assignee, dict) else "",
                    "due_date": task.get("due_on") or "",
                    "completed": task.get("completed", False),
                    "tags": tags,
                    "priority": "",
                })

        total_tasks = len(all_tasks)
        completed_count = sum(1 for t in all_tasks if t["completed"])
        overdue_count = sum(
            1 for t in all_tasks
            if not t["completed"] and t["due_date"] and t["due_date"] < today
        )

        return {
            "workspace": {"name": workspace_name, "id": workspace_id},
            "projects": projects,
            "tasks": all_tasks,
            "summary": {
                "total_projects": len(projects),
                "total_tasks": total_tasks,
                "completed_tasks": completed_count,
                "overdue_tasks": overdue_count,
                "completion_rate": round(completed_count / total_tasks * 100, 1) if total_tasks else 0.0,
            },
        }
