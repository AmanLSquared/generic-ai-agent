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


# ── Internal helpers ──────────────────────────────────────────────────────────

async def _get_workspace(client: httpx.AsyncClient, headers: dict) -> dict:
    ws_resp = await client.get(f"{ASANA_BASE}/workspaces", headers=headers)
    ws_resp.raise_for_status()
    workspaces = ws_resp.json().get("data", [])
    workspace = workspaces[0] if workspaces else {"gid": "", "name": ""}
    return {"id": workspace.get("gid", ""), "name": workspace.get("name", "")}


async def _paginate_tasks(
    client: httpx.AsyncClient,
    headers: dict,
    params: dict,
    max_tasks: int = 1000,
) -> list:
    """Fetch ALL tasks across multiple pages (Asana default is 20/page, max 100/page)."""
    all_tasks: list = []
    fetch_params = {**params, "limit": 100}  # always request maximum page size
    offset: str | None = None

    while True:
        if offset:
            fetch_params["offset"] = offset
        resp = await client.get(f"{ASANA_BASE}/tasks", headers=headers, params=fetch_params)
        resp.raise_for_status()
        body = resp.json()
        all_tasks.extend(body.get("data", []))
        next_page = body.get("next_page")
        if not next_page or len(all_tasks) >= max_tasks:
            break
        offset = next_page["offset"]

    return all_tasks[:max_tasks]


def _build_task_summary(tasks: list, today: str) -> dict:
    total = len(tasks)
    completed = sum(1 for t in tasks if t.get("completed"))
    overdue = sum(
        1 for t in tasks
        if not t.get("completed") and t.get("due_date") and t["due_date"] < today
    )
    

    return {
        "total_tasks": total,
        "completed_tasks": completed,
        "incomplete_tasks": total - completed,
        "overdue_tasks": overdue,
        "completion_rate": round(completed / total * 100, 1) if total else 0.0,
    }


async def _fetch_user_scope(
    client: httpx.AsyncClient,
    headers: dict,
    workspace: dict,
    scope_gid: str,
    today: str,
) -> dict:
    """Fetch all tasks assigned to a specific user (or 'me')."""
    if scope_gid == "me":
        me_resp = await client.get(f"{ASANA_BASE}/users/me", headers=headers)
        me_resp.raise_for_status()
        me_data = me_resp.json()["data"]
        scope_gid = me_data["gid"]
        user_name = me_data.get("name", "")
        user_email = me_data.get("email", "")
    else:
        user_resp = await client.get(
            f"{ASANA_BASE}/users/{scope_gid}",
            headers=headers,
            params={"opt_fields": "name,email,gid"},
        )
        user_resp.raise_for_status()
        u = user_resp.json()["data"]
        user_name = u.get("name", "")
        user_email = u.get("email", "")

    tasks_raw = await _paginate_tasks(
        client, headers,
        {
            "assignee": scope_gid,
            "workspace": workspace["id"],
            "opt_fields": "name,due_on,completed,tags.name,memberships.project.name",
            "completed_since": "2000-01-01T00:00:00.000Z",
        },
    )

    tasks = []
    projects_set: set[str] = set()
    for t in tasks_raw:
        memberships = t.get("memberships") or []
        proj_name = (
            memberships[0]["project"]["name"]
            if memberships and memberships[0].get("project")
            else ""
        )
        if proj_name:
            projects_set.add(proj_name)
        tags = [tag.get("name", "") for tag in (t.get("tags") or [])]
        tasks.append({
            "id": t.get("gid", ""),
            "name": t.get("name", ""),
            "project": proj_name,
            "due_date": t.get("due_on") or "",
            "completed": t.get("completed", False),
            "tags": tags,
        })

    summary = _build_task_summary(tasks, today)
    return {
        "scope": {"type": "user", "gid": scope_gid, "name": user_name},
        "workspace": workspace,
        "user": {"gid": scope_gid, "name": user_name, "email": user_email},
        "projects_contributed": sorted(projects_set),
        "tasks": tasks,
        "summary": summary,
    }


async def _fetch_project_scope(
    client: httpx.AsyncClient,
    headers: dict,
    workspace: dict,
    project_gid: str,
    today: str,
) -> dict:
    """Fetch a single project and all its tasks."""
    proj_resp = await client.get(
        f"{ASANA_BASE}/projects/{project_gid}",
        headers=headers,
        params={"opt_fields": "name,current_status,due_date,members.name,completed,gid"},
    )
    proj_resp.raise_for_status()
    proj = proj_resp.json()["data"]

    status_obj = proj.get("current_status") or {}
    status = status_obj.get("text", "") if isinstance(status_obj, dict) else ""
    members = [m.get("name", "") for m in (proj.get("members") or [])]

    tasks_raw = await _paginate_tasks(
        client, headers,
        {
            "project": project_gid,
            "opt_fields": "name,assignee.name,due_on,completed,tags.name",
            "completed_since": "2000-01-01T00:00:00.000Z",
        },
    )

    tasks = []
    for t in tasks_raw:
        assignee = t.get("assignee") or {}
        tags = [tag.get("name", "") for tag in (t.get("tags") or [])]
        tasks.append({
            "id": t.get("gid", ""),
            "name": t.get("name", ""),
            "assignee": assignee.get("name", "") if isinstance(assignee, dict) else "",
            "due_date": t.get("due_on") or "",
            "completed": t.get("completed", False),
            "tags": tags,
        })

        

    summary = _build_task_summary(tasks, today)
    project_info = {
        "id": proj.get("gid", ""),
        "name": proj.get("name", ""),
        "status": status,
        "due_date": proj.get("due_date") or "",
        "team_members": members,
        **summary,
    }
# log the fetched project scope and summary for debugging
    print(f"Fetched project scope for project_gid={project_gid}: {len(tasks)} tasks, summary={summary}")
    return {
        "scope": {"type": "project", "gid": project_gid, "name": proj.get("name", "")},
        "workspace": workspace,
        "project": project_info,
        "tasks": tasks,
        "summary": summary,
    }
    
    

async def _fetch_all_scope(
    client: httpx.AsyncClient,
    headers: dict,
    workspace: dict,
    workspace_id: str,
    today: str,
) -> dict:
    """Fetch all projects and all tasks across the workspace."""
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

    for proj in projects_raw:
        proj_id = proj.get("gid", "")
        proj_name = proj.get("name", "")
        status_obj = proj.get("current_status") or {}
        status = status_obj.get("text", "") if isinstance(status_obj, dict) else ""
        due_date = proj.get("due_date") or ""
        members = [m.get("name", "") for m in (proj.get("members") or [])]

        tasks_raw = await _paginate_tasks(
            client, headers,
            {
                "project": proj_id,
                "opt_fields": "name,assignee.name,due_on,completed,tags.name",
                "completed_since": "2000-01-01T00:00:00.000Z",
            },
        )

        total_p = len(tasks_raw)
        completed_p = sum(1 for t in tasks_raw if t.get("completed"))
        overdue_p = sum(
            1 for t in tasks_raw
            if not t.get("completed") and t.get("due_on") and t["due_on"] < today
        )
        projects.append({
            "id": proj_id,
            "name": proj_name,
            "status": status,
            "due_date": due_date,
            "total_tasks": total_p,
            "completed_tasks": completed_p,
            "incomplete_tasks": total_p - completed_p,
            "overdue_tasks": overdue_p,
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

    print(f"Fetched all scope for workspace_id={workspace['id']}: {len(all_tasks)} tasks, {len(projects)} projects, summary={{'total_tasks': total_tasks, 'completed_tasks': completed_count, 'overdue_tasks': overdue_count}}")
    

    return {
        "workspace": workspace,
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
    

# ── Public API ────────────────────────────────────────────────────────────────

async def fetch_workspace_members(pat: str) -> list:
    """Return all members of the first workspace."""
    headers = {"Authorization": f"Bearer {pat}"}
    async with httpx.AsyncClient(timeout=30) as client:
        workspace = await _get_workspace(client, headers)
        resp = await client.get(
            f"{ASANA_BASE}/workspaces/{workspace['id']}/users",
            headers=headers,
            params={"opt_fields": "name,email,gid"},
        )
        resp.raise_for_status()
        return resp.json().get("data", [])


async def fetch_projects_list(pat: str) -> list:
    """Return all projects (gid + name only) for the first workspace."""
    headers = {"Authorization": f"Bearer {pat}"}
    async with httpx.AsyncClient(timeout=30) as client:
        workspace = await _get_workspace(client, headers)
        resp = await client.get(
            f"{ASANA_BASE}/projects",
            headers=headers,
            params={"workspace": workspace["id"], "opt_fields": "name,gid"},
        )
        resp.raise_for_status()
        return resp.json().get("data", [])


async def fetch_asana_data(
    pat: str,
    scope_type: str | None = None,
    scope_gid: str | None = None,
) -> dict:
    """
    Fetch Asana data scoped to a project, a user, or the whole workspace.

    scope_type: "project" | "user" | None (None = all workspace)
    scope_gid:  Asana GID of the project/user, or "me" for the current user
    """
    headers = {"Authorization": f"Bearer {pat}"}
    async with httpx.AsyncClient(timeout=30) as client:
        workspace = await _get_workspace(client, headers)
        today = date.today().isoformat()

        if scope_type == "user":
            return await _fetch_user_scope(client, headers, workspace, scope_gid or "me", today)
        elif scope_type == "project":
            if not scope_gid:
                raise ValueError("scope_gid is required for project scope")
            return await _fetch_project_scope(client, headers, workspace, scope_gid, today)
        else:
            return await _fetch_all_scope(client, headers, workspace, workspace["id"], today)
