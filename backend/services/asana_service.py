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

# SSL verification can be disabled via env var for dev environments with broken cert chains
_SSL_VERIFY = os.getenv("HTTPX_SSL_VERIFY", "true").lower() != "false"


def _client(**kwargs) -> httpx.AsyncClient:
    """Return a configured AsyncClient. Set HTTPX_SSL_VERIFY=false in .env to skip SSL verification."""
    return httpx.AsyncClient(verify=_SSL_VERIFY, **kwargs)


async def test_asana_token(pat: str) -> dict | None:
    try:
        async with _client() as client:
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
    max_tasks: int | None = 1000,
    url: str | None = None,
) -> list:
    """Fetch ALL tasks across multiple pages (Asana default is 20/page, max 100/page).

    url: override the default /tasks endpoint (e.g. /user_task_lists/{gid}/tasks).
    max_tasks=None: no cap, paginate until all tasks are fetched.
    """
    all_tasks: list = []
    fetch_params = {**params, "limit": 100}  # always request maximum page size
    offset: str | None = None
    endpoint = url if url else f"{ASANA_BASE}/tasks"

    while True:
        if offset:
            fetch_params["offset"] = offset
        resp = await client.get(endpoint, headers=headers, params=fetch_params)
        resp.raise_for_status()
        body = resp.json()
        all_tasks.extend(body.get("data", []))
        next_page = body.get("next_page")
        if not next_page or (max_tasks is not None and len(all_tasks) >= max_tasks):
            break
        offset = next_page["offset"]

    return all_tasks[:max_tasks] if max_tasks is not None else all_tasks


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
    """Fetch all tasks assigned to a specific user (or 'me'), including subtasks."""
    # Always resolve the token owner GID so we know if the target user is "self".
    me_resp = await client.get(f"{ASANA_BASE}/users/me", headers=headers)
    me_resp.raise_for_status()
    me_data = me_resp.json()["data"]
    me_gid = me_data["gid"]

    if scope_gid == "me":
        scope_gid = me_gid
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

    is_self = scope_gid == me_gid

    if is_self:
        # The user_task_list endpoint is the only API that returns the exact same
        # set of tasks shown in Asana's "My Tasks" dashboard (including subtasks
        # that are NOT cross-listed in any project). It is restricted to the
        # authenticated user (token owner) — fetching another user's task list
        # returns 403 Forbidden.
        task_list_resp = await client.get(
            f"{ASANA_BASE}/users/{scope_gid}/user_task_list",
            headers=headers,
            params={"workspace": workspace["id"], "opt_fields": "gid"},
        )
        task_list_resp.raise_for_status()
        task_list_gid = task_list_resp.json()["data"]["gid"]

        tasks_raw = await _paginate_tasks(
            client, headers,
            {
                "opt_fields": "name,due_on,completed,tags.name,memberships.project.name,num_subtasks",
                "completed_since": "2000-01-01T00:00:00.000Z",
            },
            max_tasks=None,  # no cap — fetch every page to match My Tasks count exactly
            url=f"{ASANA_BASE}/user_task_lists/{task_list_gid}/tasks",
        )
    else:
        # For other users the user_task_list API is forbidden. The assignee+workspace
        # filter is the best available option. The 1000-task cap is removed so all
        # pages are fetched.
        tasks_raw = await _paginate_tasks(
            client, headers,
            {
                "assignee": scope_gid,
                "workspace": workspace["id"],
                "opt_fields": "name,due_on,completed,tags.name,memberships.project.name,num_subtasks",
                "completed_since": "2000-01-01T00:00:00.000Z",
            },
            max_tasks=None,  # no cap — fetch all pages
        )

    parent_tasks = []
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
        parent_tasks.append({
            "id": t.get("gid", ""),
            "name": t.get("name", ""),
            "project": proj_name,
            "due_date": t.get("due_on") or "",
            "completed": t.get("completed", False),
            "tags": tags,
            "is_subtask": False,
            "parent_id": "",
            "parent_name": "",
            "num_subtasks": t.get("num_subtasks", 0) or 0,
            "subtasks": [],
        })

    # GET /tasks?assignee=USER already returns ALL tasks assigned to that user,
    # which includes subtasks assigned to them. No additional subtask fetching is
    # needed here — doing so would pull in subtasks assigned to OTHER people and
    # inflate the count beyond what Asana shows in the user task view.
    all_tasks_flat = parent_tasks
    summary = _build_task_summary(all_tasks_flat, today)

    # Per-project task breakdown for charts
    project_breakdown: dict[str, dict] = {}
    for t in all_tasks_flat:
        proj = t.get("project", "") or "Unassigned"
        if proj not in project_breakdown:
            project_breakdown[proj] = {"total": 0, "completed": 0, "overdue": 0}
        project_breakdown[proj]["total"] += 1
        if t.get("completed"):
            project_breakdown[proj]["completed"] += 1
        elif t.get("due_date") and t["due_date"] < today:
            project_breakdown[proj]["overdue"] += 1

    projects_breakdown_list = [
        {"name": k, **v} for k, v in project_breakdown.items()
    ]

    print(
        f"Fetched user scope for user_gid={scope_gid}: "
        f"{len(all_tasks_flat)} tasks (assigned to user), "
        f"summary={summary}"
    )
    return {
        "scope": {"type": "user", "gid": scope_gid, "name": user_name},
        "workspace": workspace,
        "user": {"gid": scope_gid, "name": user_name, "email": user_email},
        "projects_contributed": sorted(projects_set),
        "projects_breakdown": projects_breakdown_list,
        "tasks": parent_tasks,
        "subtasks": [],
        "all_tasks": all_tasks_flat,
        "summary": summary,
    }


async def _fetch_subtasks(
    client: httpx.AsyncClient,
    headers: dict,
    parent_task: dict,
    seen_gids: set,
) -> list:
    """Recursively fetch ALL subtasks at all depths for a given task.

    seen_gids is a shared set (pre-seeded with parent task GIDs) used to skip
    tasks already counted as direct project/user members and to avoid cycles.
    """
    import asyncio

    try:
        subtasks_raw: list = []
        fetch_params: dict = {
            "opt_fields": "name,assignee.name,due_on,completed,tags.name,num_subtasks",
            "limit": 100,
        }
        offset: str | None = None
        while True:
            if offset:
                fetch_params["offset"] = offset
            resp = await client.get(
                f"{ASANA_BASE}/tasks/{parent_task['id']}/subtasks",
                headers=headers,
                params=fetch_params,
            )
            resp.raise_for_status()
            body = resp.json()
            subtasks_raw.extend(body.get("data", []))
            next_page = body.get("next_page")
            if not next_page:
                break
            offset = next_page["offset"]
    except Exception as e:
        print(f"Warning: could not fetch subtasks for {parent_task['id']}: {e}")
        return []

    collected = []
    tasks_needing_recursion = []

    for s in subtasks_raw:
        gid = s.get("gid", "")
        if not gid or gid in seen_gids:
            # already a direct project/user member or already visited — skip
            continue
        seen_gids.add(gid)

        assignee = s.get("assignee") or {}
        tags = [tag.get("name", "") for tag in (s.get("tags") or [])]
        num_sub = s.get("num_subtasks", 0) or 0
        subtask_dict = {
            "id": gid,
            "name": s.get("name", ""),
            "assignee": assignee.get("name", "") if isinstance(assignee, dict) else "",
            "due_date": s.get("due_on") or "",
            "completed": s.get("completed", False),
            "tags": tags,
            "is_subtask": True,
            "parent_id": parent_task["id"],
            "parent_name": parent_task["name"],
            "num_subtasks": num_sub,
            "subtasks": [],  # populated below after recursive fetch
        }
        collected.append(subtask_dict)
        if num_sub > 0:
            tasks_needing_recursion.append(subtask_dict)

    # Recurse into subtasks-of-subtasks in parallel
    if tasks_needing_recursion:
        nested_results = await asyncio.gather(
            *[_fetch_subtasks(client, headers, t, seen_gids) for t in tasks_needing_recursion],
            return_exceptions=True,
        )
        nested_by_parent: dict = {}
        for result in nested_results:
            if isinstance(result, list):
                collected.extend(result)
                for nt in result:
                    nested_by_parent.setdefault(nt["parent_id"], []).append(nt)
        # Attach direct children to their immediate parent subtask
        for t in tasks_needing_recursion:
            t["subtasks"] = nested_by_parent.get(t["id"], [])

    return collected


async def _fetch_project_scope(
    client: httpx.AsyncClient,
    headers: dict,
    workspace: dict,
    project_gid: str,
    today: str,
) -> dict:
    """Fetch a single project, all its tasks, and all subtasks."""
    import asyncio

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
            "opt_fields": "name,assignee.name,due_on,completed,tags.name,num_subtasks",
            "completed_since": "2000-01-01T00:00:00.000Z",
        },
    )

    # Build parent task list
    parent_tasks = []
    for t in tasks_raw:
        assignee = t.get("assignee") or {}
        tags = [tag.get("name", "") for tag in (t.get("tags") or [])]
        parent_tasks.append({
            "id": t.get("gid", ""),
            "name": t.get("name", ""),
            "assignee": assignee.get("name", "") if isinstance(assignee, dict) else "",
            "due_date": t.get("due_on") or "",
            "completed": t.get("completed", False),
            "tags": tags,
            "is_subtask": False,
            "parent_id": "",
            "parent_name": "",
            "num_subtasks": t.get("num_subtasks", 0) or 0,
        })

    # Fetch all subtasks recursively (including subtasks-of-subtasks at all depths).
    # Pre-seed seen_gids with parent task GIDs so that subtasks which are also direct
    # project members are not double-counted.
    seen_gids: set = {t["id"] for t in parent_tasks}
    tasks_with_subtasks = [t for t in parent_tasks if t["num_subtasks"] > 0]
    subtask_results = await asyncio.gather(
        *[_fetch_subtasks(client, headers, t, seen_gids) for t in tasks_with_subtasks],
        return_exceptions=True,
    )

    all_subtasks = []
    for result in subtask_results:
        if isinstance(result, list):
            all_subtasks.extend(result)

    # Attach direct subtasks to each parent task for template use
    subtasks_by_parent: dict = {}
    for st in all_subtasks:
        subtasks_by_parent.setdefault(st["parent_id"], []).append(st)

    for t in parent_tasks:
        t["subtasks"] = subtasks_by_parent.get(t["id"], [])

    # All tasks flat (parents + subtasks) for accurate summary
    all_tasks_flat = parent_tasks + all_subtasks

    summary = _build_task_summary(all_tasks_flat, today)
    project_info = {
        "id": proj.get("gid", ""),
        "name": proj.get("name", ""),
        "status": status,
        "due_date": proj.get("due_date") or "",
        "team_members": members,
        **summary,
    }

    print(
        f"Fetched project scope for project_gid={project_gid}: "
        f"{len(parent_tasks)} tasks + {len(all_subtasks)} subtasks = {len(all_tasks_flat)} total, "
        f"summary={summary}"
    )
    return {
        "scope": {"type": "project", "gid": project_gid, "name": proj.get("name", "")},
        "workspace": workspace,
        "project": project_info,
        "tasks": parent_tasks,        # parent tasks (each has .subtasks list)
        "subtasks": all_subtasks,     # flat subtask list
        "all_tasks": all_tasks_flat,  # parents + subtasks combined (for charts/summary)
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
    async with _client(timeout=30) as client:
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
    async with _client(timeout=30) as client:
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
    async with _client(timeout=30) as client:
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
