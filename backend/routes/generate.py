import json
import os
from fastapi import APIRouter, HTTPException, Depends
from jinja2 import Environment, ChainableUndefined
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import Setting
from services.openai_service import generate_dashboard_html, continue_dashboard_chat

router = APIRouter()

SYSTEM_PROMPT = """You are an expert frontend developer specializing in beautiful data dashboards.
Generate a single self-contained Jinja2 HTML template for an Asana project dashboard.

The template will be rendered server-side using Jinja2. You will receive the data SCHEMA (structure only).
You MUST use Jinja2 variables for every value — NEVER put any actual data value in the HTML.

Available Jinja2 variables:

  project.name           — project name (string)
  project.status         — current status text (string)
  project.due_date       — project due date (string, may be empty)
  project.team_members   — list of member name strings
  project.total_tasks    — total task count (int)
  project.completed_tasks   — completed count (int)
  project.incomplete_tasks  — incomplete count (int)
  project.overdue_tasks  — overdue count (int)
  project.completion_rate   — completion % (float)

  tasks                  — list of parent task objects:
    t.name, t.assignee, t.due_date, t.completed (bool), t.tags (list),
    t.is_subtask (False), t.num_subtasks (int), t.subtasks (list of subtask objects)

  subtasks               — flat list of all subtask objects:
    st.name, st.assignee, st.due_date, st.completed (bool), st.tags (list),
    st.is_subtask (True), st.parent_id, st.parent_name

  all_tasks              — parents + subtasks combined (use for charts/summary accuracy)

  summary.total_tasks, summary.completed_tasks, summary.incomplete_tasks,
  summary.overdue_tasks, summary.completion_rate
  (summary counts include subtasks)

  workspace.name         — workspace name (string)

RULES — read carefully, violating any rule is wrong:
1. EVERY dynamic value MUST use {{ }} syntax. ZERO hardcoded data values allowed.
2. String values → {{ project.name }}, numbers → {{ summary.total_tasks }}, etc.
3. Lists → {% for t in tasks %} ... {% endfor %}
4. Conditions → {% if t.completed %}Completed{% else %}Incomplete{% endif %}
5. Chart.js data arrays MUST use Jinja2 inline:
     data: [{{ summary.completed_tasks }}, {{ summary.incomplete_tasks }}]
     labels: [{% for t in tasks %}"{{ t.name }}"{% if not loop.last %},{% endif %}{% endfor %}]
6. Member workload bar chart labels and data:
     labels: [{% for m in project.team_members %}"{{ m }}"{% if not loop.last %},{% endif %}{% endfor %}]
7. Include all CSS in a <style> tag — the file must be self-contained.
8. Load Chart.js from CDN: https://cdn.jsdelivr.net/npm/chart.js
9. Design: modern card-based layout, subtle shadows, smooth colors, responsive grid.
10. KPI cards for: total tasks, completed, overdue, completion rate — all using Jinja2 variables.
11. Return ONLY the complete HTML template. No explanation, no markdown, no code fences.

EXAMPLE of correct vs wrong:

  WRONG:  <div class="kpi-value">13</div>
  RIGHT:  <div class="kpi-value">{{ summary.total_tasks }}</div>

  WRONG:  <h1>Intel - Projects</h1>
  RIGHT:  <h1>{{ project.name }}</h1>

  WRONG:  data: [10, 3]
  RIGHT:  data: [{{ summary.completed_tasks }}, {{ summary.incomplete_tasks }}]

  WRONG:  <td>Traffic Widget</td>
  RIGHT:  <td>{{ t.name }}</td>

  WRONG:  <span>Jasindan Rasalingam</span>
  RIGHT:  {% for m in project.team_members %}<span>{{ m }}</span>{% endfor %}"""

USER_SYSTEM_PROMPT = """You are an expert frontend developer specializing in beautiful data dashboards.
Generate a single self-contained Jinja2 HTML template for an Asana member/user dashboard.

The template will be rendered server-side using Jinja2. You will receive the data SCHEMA (structure only).
You MUST use Jinja2 variables for every value — NEVER put any actual data value in the HTML.

Available Jinja2 variables:

  user.name              — member name (string)
  user.email             — member email (string)
  user.gid               — member GID (string)

  workspace.name         — workspace name (string)

  projects_contributed   — list of project name strings this user has tasks in

  projects_breakdown     — list of per-project stats:
    p.name, p.total (int), p.completed (int), p.overdue (int)

  tasks                  — list of parent task objects assigned to this user:
    t.name, t.project (project name), t.due_date, t.completed (bool), t.tags (list),
    t.is_subtask (False), t.num_subtasks (int), t.subtasks (list of subtask objects)

  subtasks               — flat list of all subtask objects:
    st.name, st.project, st.due_date, st.completed (bool), st.tags (list),
    st.is_subtask (True), st.parent_id, st.parent_name

  all_tasks              — parents + subtasks combined (use for charts/summary accuracy)

  summary.total_tasks, summary.completed_tasks, summary.incomplete_tasks,
  summary.overdue_tasks, summary.completion_rate
  (summary counts include subtasks)

RULES — read carefully, violating any rule is wrong:
1. EVERY dynamic value MUST use {{ }} syntax. ZERO hardcoded data values allowed.
2. String values → {{ user.name }}, numbers → {{ summary.total_tasks }}, etc.
3. Lists → {% for t in tasks %} ... {% endfor %}
4. Conditions → {% if t.completed %}Completed{% else %}Incomplete{% endif %}
5. Chart.js data arrays MUST use Jinja2 inline:
     data: [{{ summary.completed_tasks }}, {{ summary.incomplete_tasks }}]
     labels: [{% for p in projects_breakdown %}"{{ p.name }}"{% if not loop.last %},{% endif %}{% endfor %}]
6. Per-project bar chart:
     labels: [{% for p in projects_breakdown %}"{{ p.name }}"{% if not loop.last %},{% endif %}{% endfor %}]
     data:   [{% for p in projects_breakdown %}{{ p.total }}{% if not loop.last %},{% endif %}{% endfor %}]
7. Include all CSS in a <style> tag — the file must be self-contained.
8. Load Chart.js from CDN: https://cdn.jsdelivr.net/npm/chart.js
9. Design: modern card-based layout, subtle shadows, smooth colors, responsive grid.
10. KPI cards: total tasks, completed, overdue, completion rate — all using Jinja2 variables.
11. Show task table with columns: Task, Project, Due Date, Status, Tags.
12. Return ONLY the complete HTML template. No explanation, no markdown, no code fences.

EXAMPLE of correct vs wrong:

  WRONG:  <h1>Jasindan Rasalingam</h1>
  RIGHT:  <h1>{{ user.name }}</h1>

  WRONG:  <div class="kpi-value">42</div>
  RIGHT:  <div class="kpi-value">{{ summary.total_tasks }}</div>

  WRONG:  data: [10, 3]
  RIGHT:  data: [{{ summary.completed_tasks }}, {{ summary.incomplete_tasks }}]

  WRONG:  <td>Traffic Widget</td>
  RIGHT:  <td>{{ t.name }}</td>"""


CONTINUATION_SYSTEM_PROMPT = """You are an expert frontend developer specializing in beautiful data dashboards.
You are refining an existing Jinja2 HTML template dashboard based on the user's follow-up instructions.

Rules:
1. Return the COMPLETE updated Jinja2 HTML template — every line, from <!DOCTYPE html> to </html>.
2. CRITICAL: This is a Jinja2 template. It contains {{ variable }} expressions and {% %} blocks.
   - PRESERVE all Jinja2 expressions exactly — do NOT replace them with hardcoded values.
   - Do NOT remove any {{ }} or {% %} blocks unless the user explicitly asks.
3. Only change what the user asks for (theme, layout, colors, chart type, new section, etc.).
4. Keep all Chart.js CDN references and the self-contained CSS structure intact.
5. If user asks to add a new data field, use the appropriate Jinja2 variable from the schema.
6. Return ONLY the complete HTML template. No explanation, no markdown, no code fences."""


class GenerateRequest(BaseModel):
    prompt: str
    json_data: dict | None = None


class ContinueRequest(BaseModel):
    messages: list[dict]
    current_html: str
    json_data: dict | None = None


async def get_openai_key(db: AsyncSession) -> str:
    env_key = os.getenv("OPENAI_API_KEY", "").strip()
    if env_key:
        return env_key
    from sqlalchemy import select
    result = await db.execute(select(Setting).where(Setting.key == "openai_api_key"))
    setting = result.scalar_one_or_none()
    if not setting or not setting.value:
        raise HTTPException(status_code=400, detail="OpenAI API key not configured. Set OPENAI_API_KEY env var or add it in Settings.")
    return setting.value


def _schema_only(data: dict) -> dict:
    """
    Strip all actual values from Asana data — return only the schema skeleton.
    This prevents the AI from hardcoding any real values into the Jinja2 template.
    Preview rendering uses the original full data separately.
    """
    return {
        "scope": {"type": "project", "gid": "<gid>", "name": "<project_name>"},
        "workspace": {"id": "<workspace_id>", "name": "<workspace_name>"},
        "project": {
            "id": "<id>",
            "name": "<project_name>",
            "status": "<status_text>",
            "due_date": "<YYYY-MM-DD or empty>",
            "team_members": ["<member_name_1>", "<member_name_2>"],
            "total_tasks": "<int>",
            "completed_tasks": "<int>",
            "incomplete_tasks": "<int>",
            "overdue_tasks": "<int>",
            "completion_rate": "<float>",
        },
        "tasks": [
            {
                "id": "<id>",
                "name": "<task_name>",
                "assignee": "<assignee_name or empty>",
                "due_date": "<YYYY-MM-DD or empty>",
                "completed": "<true or false>",
                "tags": ["<tag_name>"],
                "is_subtask": False,
                "num_subtasks": "<int>",
                "subtasks": [
                    {
                        "id": "<id>",
                        "name": "<subtask_name>",
                        "assignee": "<assignee_name or empty>",
                        "due_date": "<YYYY-MM-DD or empty>",
                        "completed": "<true or false>",
                        "tags": ["<tag_name>"],
                        "is_subtask": True,
                        "parent_name": "<parent_task_name>",
                    }
                ],
            }
        ],
        "subtasks": [
            {
                "id": "<id>",
                "name": "<subtask_name>",
                "assignee": "<assignee_name or empty>",
                "due_date": "<YYYY-MM-DD or empty>",
                "completed": "<true or false>",
                "tags": ["<tag_name>"],
                "is_subtask": True,
                "parent_id": "<parent_task_id>",
                "parent_name": "<parent_task_name>",
            }
        ],
        "all_tasks": "<flat list of all tasks + subtasks combined — use for summary charts>",
        "summary": {
            "total_tasks": "<int — includes subtasks>",
            "completed_tasks": "<int>",
            "incomplete_tasks": "<int>",
            "overdue_tasks": "<int>",
            "completion_rate": "<float>",
        },
    }


def _schema_only_user() -> dict:
    """Schema skeleton for user/member scope."""
    return {
        "scope": {"type": "user", "gid": "<gid>", "name": "<user_name>"},
        "workspace": {"id": "<workspace_id>", "name": "<workspace_name>"},
        "user": {"gid": "<gid>", "name": "<user_name>", "email": "<email>"},
        "projects_contributed": ["<project_name_1>", "<project_name_2>"],
        "projects_breakdown": [
            {"name": "<project_name>", "total": "<int>", "completed": "<int>", "overdue": "<int>"}
        ],
        "tasks": [
            {
                "id": "<id>",
                "name": "<task_name>",
                "project": "<project_name>",
                "due_date": "<YYYY-MM-DD or empty>",
                "completed": "<true or false>",
                "tags": ["<tag_name>"],
                "is_subtask": False,
                "num_subtasks": "<int>",
                "subtasks": [
                    {
                        "id": "<id>",
                        "name": "<subtask_name>",
                        "project": "<project_name>",
                        "due_date": "<YYYY-MM-DD or empty>",
                        "completed": "<true or false>",
                        "tags": ["<tag_name>"],
                        "is_subtask": True,
                        "parent_name": "<parent_task_name>",
                    }
                ],
            }
        ],
        "subtasks": [
            {
                "id": "<id>",
                "name": "<subtask_name>",
                "project": "<project_name>",
                "due_date": "<YYYY-MM-DD or empty>",
                "completed": "<true or false>",
                "tags": ["<tag_name>"],
                "is_subtask": True,
                "parent_id": "<parent_task_id>",
                "parent_name": "<parent_task_name>",
            }
        ],
        "all_tasks": "<flat list of all tasks + subtasks combined>",
        "summary": {
            "total_tasks": "<int — includes subtasks>",
            "completed_tasks": "<int>",
            "incomplete_tasks": "<int>",
            "overdue_tasks": "<int>",
            "completion_rate": "<float>",
        },
    }


    import copy
    trimmed = copy.deepcopy(data)
    tasks = trimmed.get("tasks", [])
    total = len(tasks)
    if total > max_tasks:
        trimmed["tasks"] = tasks[:max_tasks]
        trimmed["_tasks_note"] = (
            f"Tasks list capped at {max_tasks} of {total} for display. "
            "Use the 'summary' fields for accurate totals in KPI cards."
        )
    return trimmed


def _render_jinja_preview(template_str: str, json_data: dict) -> str:
    """Render Jinja2 template with actual JSON data for frontend preview.
    Uses SafeDict so missing/hallucinated variables return '' instead of crashing."""
    from datetime import date, datetime
    from main import _make_safe, SafeDict, _DateAwareEnvironment

    today_str = date.today().isoformat()

    class _CallableStr(str):
        def __call__(self, *args, **kwargs):
            return today_str

    def _strftime_filter(value, fmt="%Y-%m-%d"):
        if not value:
            return ''
        if isinstance(value, (date, datetime)):
            return value.strftime(fmt)
        for parser_fmt in ("%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z",
                           "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(str(value)[:26], parser_fmt).strftime(fmt)
            except ValueError:
                continue
        return str(value)

    env = _DateAwareEnvironment(autoescape=False, undefined=ChainableUndefined)
    env.filters["strftime"] = _strftime_filter
    try:
        tmpl = env.from_string(template_str)
        safe = _make_safe(json_data)
        return tmpl.render(
            project=safe.get("project", SafeDict()),
            user=safe.get("user", SafeDict()),
            tasks=safe.get("tasks", []),
            subtasks=safe.get("subtasks", []),
            all_tasks=safe.get("all_tasks", safe.get("tasks", [])),
            summary=safe.get("summary", SafeDict()),
            workspace=safe.get("workspace", SafeDict()),
            scope=safe.get("scope", SafeDict()),
            projects_contributed=safe.get("projects_contributed", []),
            projects_breakdown=safe.get("projects_breakdown", []),
            now=_CallableStr(today_str),
            today=_CallableStr(today_str),
        )
    except Exception as e:
        print(f"Jinja2 preview render error: {e}")
        return template_str  # fallback: return template as-is


@router.post("/generate")
async def generate(req: GenerateRequest, db: AsyncSession = Depends(get_db)):
    api_key = await get_openai_key(db)
    if req.json_data:
        scope_type = req.json_data.get("scope", {}).get("type", "project")
        is_user_scope = scope_type == "user"
        schema = _schema_only_user() if is_user_scope else _schema_only(req.json_data)
        system_prompt = USER_SYSTEM_PROMPT if is_user_scope else SYSTEM_PROMPT
        user_message = req.prompt + f"\n\nAsana {scope_type} data SCHEMA (use these Jinja2 variable names ONLY — do NOT hardcode any real values):\n```json\n{json.dumps(schema, indent=2)}\n```"
        template = await generate_dashboard_html(api_key, system_prompt, user_message)
        rendered_html = _render_jinja_preview(template, req.json_data)
        return {"html": rendered_html, "template": template}

    # Pure text prompt — no scope data
    template = await generate_dashboard_html(api_key, SYSTEM_PROMPT, req.prompt)
    return {"html": template, "template": template}


@router.post("/generate/continue")
async def continue_generation(req: ContinueRequest, db: AsyncSession = Depends(get_db)):
    api_key = await get_openai_key(db)
    messages = [dict(m) for m in req.messages[-10:]]
    if req.json_data:
        scope_type = req.json_data.get("scope", {}).get("type", "project")
        is_user_scope = scope_type == "user"
        schema = _schema_only_user() if is_user_scope else _schema_only(req.json_data)
        messages[-1]["content"] += f"\n\nReminder — this is a Jinja2 template. Use ONLY these variable names, do NOT hardcode any real values:\n```json\n{json.dumps(schema, indent=2)}\n```"
    # current_html is the Jinja2 template (not rendered HTML)
    template = await continue_dashboard_chat(api_key, CONTINUATION_SYSTEM_PROMPT, messages, req.current_html)
    if req.json_data:
        rendered_html = _render_jinja_preview(template, req.json_data)
    else:
        # No new json_data — return template itself as preview
        rendered_html = template
    return {"html": rendered_html, "template": template}
