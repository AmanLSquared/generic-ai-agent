from contextlib import asynccontextmanager
import json
import os
from dotenv import load_dotenv
load_dotenv()  # Load .env before anything else reads os.getenv()

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from jinja2 import Environment, ChainableUndefined
from sqlalchemy import select

from database import init_db, migrate_db, AsyncSessionLocal
from models import Dashboard, Setting
from routes import dashboards, generate, asana, settings as settings_router


import re as _re
from datetime import datetime as _datetime

_ISO_DATE_RE = _re.compile(r"^\d{4}-\d{2}-\d{2}")


def _parse_date_str(s: str, fmt: str = "%Y-%m-%d") -> str:
    """Parse an ISO date/datetime string and format it. Returns the original string on failure."""
    for parser_fmt in ("%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z",
                       "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return _datetime.strptime(s[:26], parser_fmt).strftime(fmt)
        except ValueError:
            continue
    return s


class SmartDateStr(str):
    """String subclass that also exposes .strftime() so templates can call
    {{ task.due_date.strftime('%b %d') }} even when the value is an ISO string."""
    def strftime(self, fmt="%Y-%m-%d"):
        return _parse_date_str(str(self), fmt)


class _DateAwareEnvironment(Environment):
    """Jinja2 Environment that intercepts .strftime attribute access on plain strings.
    This means {{ some_date_string.strftime('%b %d') }} always works, even if the
    string was not wrapped in SmartDateStr by _make_safe."""
    def getattr(self, obj, attribute):
        if attribute == "strftime" and isinstance(obj, str):
            return SmartDateStr(obj).strftime
        return super().getattr(obj, attribute)


class SafeDict(dict):
    """Dict that returns empty string for missing keys — prevents Jinja2 UndefinedError."""
    def __missing__(self, key):
        return ''
    def __getattr__(self, key):
        return self.get(key, '')


def _make_safe(obj):
    """Recursively wrap dicts in SafeDict; wrap ISO date strings in SmartDateStr."""
    if isinstance(obj, dict):
        return SafeDict({k: _make_safe(v) for k, v in obj.items()})
    if isinstance(obj, list):
        return [_make_safe(i) for i in obj]
    if isinstance(obj, str) and _ISO_DATE_RE.match(obj):
        return SmartDateStr(obj)
    return obj


def _preprocess_template(template_str: str) -> str:
    """
    Fix common AI-generated Jinja2 syntax errors before the template is compiled.

    Known issue: the AI sometimes emits Python slice notation inside {% %} blocks,
    e.g. `{% for t in tasks[:10] %}` or `{% for t in all_tasks[0:5] %}`.
    Jinja2 does NOT support Python slice syntax and raises:
        TemplateSyntaxError: expected token 'end of statement block', got '['
    Fix: strip the slice from every {% ... %} block so `tasks[:10]` becomes `tasks`.
    """
    import re as _re2

    def _fix_block(m):
        # Remove Python-style slice notation [start:end] / [:end] / [start:] from
        # inside {% %} statement blocks only (not from {{ }} expressions).
        fixed = _re2.sub(r'\[\d*:\d*\]', '', m.group(1))
        return '{%' + fixed + '%}'

    return _re2.sub(r'\{%(.*?)%\}', _fix_block, template_str, flags=_re2.DOTALL)


def _jinja_render(template_str: str, asana_data: dict) -> str:
    from datetime import date, datetime

    today_str = date.today().isoformat()

    class _CallableStr(str):
        """A string that is also callable — handles both {{ now }} and {{ now() }}."""
        def __call__(self, *args, **kwargs):
            return today_str

    def _strftime_filter(value, fmt="%Y-%m-%d"):
        """Jinja2 filter: format a date string or date/datetime object. Returns '' on failure."""
        if not value:
            return ''
        if isinstance(value, (date, datetime)):
            return value.strftime(fmt)
        # Try parsing ISO date strings like "2026-03-19" or "2026-03-19T..."
        for parser_fmt in ("%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z",
                           "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(str(value)[:26], parser_fmt).strftime(fmt)
            except ValueError:
                continue
        return str(value)

    env = _DateAwareEnvironment(autoescape=False, undefined=ChainableUndefined)
    env.filters["strftime"] = _strftime_filter
    env.filters["now"] = lambda _value=None, fmt="%Y-%m-%d": today_str
    env.filters["date"] = _strftime_filter
    tmpl = env.from_string(_preprocess_template(template_str))
    safe = _make_safe(asana_data)
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
        sections=safe.get("sections", []),
        sections_breakdown=safe.get("sections_breakdown", []),
        assignee_breakdown=safe.get("assignee_breakdown", []),
        now=_CallableStr(today_str),
        today=_CallableStr(today_str),
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await migrate_db()
    yield


app = FastAPI(title="AI Dashboard Builder", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(generate.router, prefix="/api")
app.include_router(dashboards.router, prefix="/api")
app.include_router(asana.router, prefix="/api")
app.include_router(settings_router.router, prefix="/api")


@app.get("/dashboard/{dashboard_id}/view", response_class=HTMLResponse)
async def view_dashboard(dashboard_id: str):
    from services.asana_service import fetch_asana_data, decrypt_value
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Dashboard).where(Dashboard.id == dashboard_id))
        dashboard = result.scalar_one_or_none()
        if not dashboard:
            return HTMLResponse("<h1>Dashboard not found</h1>", status_code=404)

        # If template + stored scope exists, render dynamically
        if dashboard.html_template and dashboard.asana_scope_type and dashboard.asana_scope_gid:
            pat = os.getenv("ASANA_PAT", "").strip()
            if not pat:
                pat_result = await db.execute(select(Setting).where(Setting.key == "asana_pat"))
                setting = pat_result.scalar_one_or_none()
                if setting and setting.value:
                    pat = decrypt_value(setting.value)
            if pat:
                try:
                    asana_data = await fetch_asana_data(
                        pat,
                        scope_type=dashboard.asana_scope_type,
                        scope_gid=dashboard.asana_scope_gid,
                    )
                    rendered = _jinja_render(dashboard.html_template, asana_data)
                    return HTMLResponse(content=rendered)
                except Exception as e:
                    print(f"Dynamic render failed, falling back to static: {e}")

        return HTMLResponse(content=dashboard.html)


@app.get("/render/{dashboard_id}", response_class=HTMLResponse)
async def render_dashboard(
    dashboard_id: str,
    project_id: str | None = Query(default=None, description="Asana project GID"),
    user_id: str | None = Query(default=None, description="Asana user GID (or 'me')"),
):
    """
    Dynamic render endpoint — pass project_id OR user_id.
    Fetches real-time Asana data and injects into the saved Jinja2 template.
    Each request hits Asana's API fresh (no caching).
    """
    if not project_id and not user_id:
        return HTMLResponse("<h1>Pass ?project_id=GID or ?user_id=GID</h1>", status_code=400)

    from services.asana_service import fetch_asana_data, decrypt_value

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Dashboard).where(Dashboard.id == dashboard_id))
        dashboard = result.scalar_one_or_none()
        if not dashboard:
            return HTMLResponse("<h1>Dashboard not found</h1>", status_code=404)
        if not dashboard.html_template:
            return HTMLResponse(
                "<h1>No Jinja2 template found. Re-save the dashboard to generate a template.</h1>",
                status_code=400,
            )

        pat = os.getenv("ASANA_PAT", "").strip()
        if not pat:
            pat_result = await db.execute(select(Setting).where(Setting.key == "asana_pat"))
            setting = pat_result.scalar_one_or_none()
            if not setting or not setting.value:
                return HTMLResponse("<h1>Asana not connected</h1>", status_code=400)
            pat = decrypt_value(setting.value)

        html_template = dashboard.html_template

    import httpx

    try:
        if project_id:
            asana_data = await fetch_asana_data(pat, scope_type="project", scope_gid=project_id)
        else:
            asana_data = await fetch_asana_data(pat, scope_type="user", scope_gid=user_id)
    except httpx.HTTPStatusError as e:
        status = e.response.status_code
        if status == 400:
            return HTMLResponse(
                f"<h1>Invalid Asana GID</h1><p>The provided ID is not a valid Asana GID. "
                f"Asana GIDs are numeric strings (e.g. 1234567890123456), not UUIDs.</p>",
                status_code=400,
            )
        elif status == 401:
            return HTMLResponse("<h1>Asana authentication failed</h1><p>Check your PAT.</p>", status_code=401)
        elif status == 404:
            return HTMLResponse("<h1>Asana resource not found</h1>", status_code=404)
        else:
            return HTMLResponse(
                f"<h1>Asana API error ({status})</h1><p>{e.response.text}</p>",
                status_code=502,
            )

    try:
        rendered = _jinja_render(html_template, asana_data)
    except Exception as tmpl_err:
        return HTMLResponse(
            f"<h1>Template render error</h1><pre>{tmpl_err}</pre>",
            status_code=500,
        )
    return HTMLResponse(content=rendered)
