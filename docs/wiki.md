# AI Dashboard Builder — Wiki

Build beautiful Asana dashboards from a chat prompt. No code required.

---

## Table of Contents

1. [What It Does](#1-what-it-does)
2. [Setup](#2-setup)
3. [Core User Flows](#3-core-user-flows)
   - [Build a dashboard from Asana data](#31-build-a-dashboard-from-asana-data)
   - [Refine a dashboard with follow-up prompts](#32-refine-a-dashboard-with-follow-up-prompts)
   - [Save and embed a dashboard](#33-save-and-embed-a-dashboard)
   - [View a saved dashboard with live data](#34-view-a-saved-dashboard-with-live-data)
   - [Update a dashboard with fresh data](#35-update-a-dashboard-with-fresh-data)
4. [Asana Connection](#4-asana-connection)
5. [Chart Types & What Drives Them](#5-chart-types--what-drives-them)
6. [API Quick Reference](#6-api-quick-reference)
7. [Environment Variables](#7-environment-variables)
8. [Known Gotchas](#8-known-gotchas)

---

## 1. What It Does

| Feature | How it works |
|---|---|
| **Chat → Dashboard** | Describe what you want; GPT-4.1 generates a complete self-contained HTML file |
| **Live Asana data** | Pick a project or team member; real task/section/assignee data is fetched from Asana and injected |
| **Iterative refinement** | Send follow-up messages ("dark theme", "add completion over time chart") — the layout and data bindings are preserved |
| **Live embed** | Saved dashboards re-render from the Asana API on every view; embed via `<iframe>` |
| **No-AI data refresh** | Swap the data in a saved dashboard without touching design |

---

## 2. Setup

### Requirements
- Python 3.11+ and Node.js 18+
- An OpenAI API key (`sk-…`)
- *(Optional)* An Asana Personal Access Token

### Backend
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**

### First-time config
1. Click the **Settings** icon (bottom of the sidebar)
2. Paste your OpenAI API key → **Save** → **Test**
3. *(Optional)* Paste your Asana PAT → **Save**

Both keys are encrypted before being stored in the local SQLite database.

---

## 3. Core User Flows

### 3.1 Build a dashboard from Asana data

```
1. Click the Asana button in the chat input bar
2. Choose a scope:
     • Project  — pick a project from the dropdown
     • Member   — pick a team member
3. Data is fetched automatically (you'll see a loading toast)
4. Type your prompt, e.g.:
     "Create a project status dashboard with KPI cards,
      a tasks-by-section bar chart, and a task table"
5. Click Send (or press Enter)
6. The generated dashboard appears in the preview panel on the right
```

> The AI receives a **schema skeleton** (no real names or numbers) to prevent any actual Asana data from being sent to OpenAI. Real values are injected server-side after the template is returned.

---

### 3.2 Refine a dashboard with follow-up prompts

Once a dashboard is visible in the preview panel, continue chatting:

| Example prompt | Effect |
|---|---|
| `"Switch to a dark theme"` | Regenerates with dark background/card styles |
| `"Add a task completion over time line chart"` | Adds a new chart section using `completed_at` dates |
| `"Show only incomplete tasks in the task table"` | Adds a Jinja2 `{% if not t.completed %}` filter |
| `"Move the KPI cards to a 2-column grid"` | Adjusts the CSS grid layout |

All follow-up messages edit the **Jinja2 template**, not the rendered HTML, so data bindings are never broken.

---

### 3.3 Save and embed a dashboard

1. Click **Save Dashboard** (top-right of the preview panel)
2. The dashboard is saved with:
   - The Jinja2 template (not rendered HTML — no hardcoded values)
   - The Asana scope (`project` / `user`, GID, name)
3. An embed code is generated automatically:
   ```html
   <iframe src="http://localhost:8000/render/{id}?project_id={gid}"
           width="100%" height="600" frameborder="0"></iframe>
   ```
4. In **History**, click **Embed** on any card to copy this code

---

### 3.4 View a saved dashboard with live data

1. Click **History** in the sidebar
2. Click **Open** on any dashboard card
3. If the dashboard has an Asana scope attached:
   - Fresh data is fetched from Asana automatically
   - A green **● Live Data** badge appears in the header
4. If Asana is unreachable, the last saved static HTML is shown as a fallback

The `/render/{id}?project_id=GID` endpoint also works directly in a browser or embedded `<iframe>` — it hits the Asana API on every request.

---

### 3.5 Update a dashboard with fresh data

**Option A — Automatic (Asana-linked dashboards):**
Just open the dashboard. Live data is always fetched on open.

**Option B — Manual inject (any dashboard):**
1. Go to **History**
2. Click **Update Data** on a dashboard card
3. In the modal:
   - Upload a new JSON file, **or**
   - Pick a new Asana scope to re-fetch
4. Click **Update** — only the data payload changes; layout and charts are untouched

> The inject endpoint validates that the new data doesn't deviate more than 30% from the saved schema. If it does, you'll see a list of missing/extra keys.

---

## 4. Asana Connection

### Getting a PAT
1. Go to **https://app.asana.com/0/my-apps**
2. Click **New access token**
3. Paste the token into **Settings → Asana PAT → Save**

### What data is fetched per scope

**Project scope** includes:
- Project metadata (name, status, due date, team members)
- All tasks + subtasks (recursive, all depths)
- Per-section breakdown (total / completed / incomplete / overdue)
- Per-assignee breakdown
- `completed_at` timestamps for completion-over-time charts

**User/member scope** includes:
- All tasks assigned to that person (across all projects)
- Per-project breakdown
- `completed_at` timestamps

### Scope limitations

| Situation | Behaviour |
|---|---|
| Viewing your own tasks | Uses the `/user_task_lists` API — exact match for "My Tasks" in Asana |
| Viewing another member's tasks | Uses `assignee` filter — may differ slightly from their personal "My Tasks" view |
| Large projects (1000+ tasks) | All pages are fetched automatically; may take a few seconds |

---

## 5. Chart Types & What Drives Them

| Chart | Data source in template |
|---|---|
| Task status donut/pie | `summary.completed_tasks`, `summary.incomplete_tasks` |
| Tasks by section (bar) | `sections_breakdown` — `s.name`, `s.total`, `s.completed`, `s.incomplete`, `s.overdue` |
| Tasks by assignee (bar) | `assignee_breakdown` — `a.assignee`, `a.total`, `a.completed`, `a.overdue` |
| Per-project breakdown (user) | `projects_breakdown` — `p.name`, `p.total`, `p.completed`, `p.overdue` |
| **Completion over time** | `t.completed_at[:10]` — grouped by date in JavaScript |
| KPI cards | `summary.*` or `project.*` fields |

**Completion over time — template pattern:**
```javascript
const byDate = {};
{% for t in all_tasks %}{% if t.completed and t.completed_at %}
byDate["{{ t.completed_at[:10] }}"] = (byDate["{{ t.completed_at[:10] }}"] || 0) + 1;
{% endif %}{% endfor %}
const labels = Object.keys(byDate).sort();
const data   = labels.map(d => byDate[d]);
// pass to Chart.js
```

---

## 6. API Quick Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/generate` | Generate dashboard from prompt + data |
| `POST` | `/api/generate/continue` | Refine existing dashboard via chat |
| `GET` | `/api/dashboards` | List saved dashboards |
| `POST` | `/api/dashboards` | Save a dashboard |
| `DELETE` | `/api/dashboards/{id}` | Delete a dashboard |
| `POST` | `/api/dashboards/{id}/inject` | Inject new data (no AI) |
| `GET` | `/dashboard/{id}/view` | Serve static HTML |
| `GET` | `/render/{id}?project_id=GID` | Live render (hits Asana API) |
| `GET` | `/render/{id}?user_id=GID` | Live render for user scope |
| `POST` | `/api/asana/connect` | Validate + save Asana PAT |
| `GET` | `/api/asana/data` | Fetch Asana data for a scope |
| `GET` | `/api/asana/projects` | List all workspace projects |
| `GET` | `/api/asana/members` | List all workspace members |
| `PUT` | `/api/settings/{key}` | Save `openai_api_key` or `asana_pat` |
| `DELETE` | `/api/settings/history` | Delete all saved dashboards |

---

## 7. Environment Variables

Create a `.env` file in `backend/`. All are optional — they override UI settings.

| Variable | Default | Notes |
|---|---|---|
| `OPENAI_API_KEY` | *(from DB)* | |
| `ASANA_PAT` | *(from DB)* | |
| `DATABASE_URL` | `sqlite+aiosqlite:///./dashboard_builder.db` | Change for PostgreSQL in production |
| `FERNET_KEY` | Fixed dev seed | **Must be set in production.** Generate: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |
| `HTTPX_SSL_VERIFY` | `true` | Set `false` only in dev environments with broken cert chains |

---

## 8. Known Gotchas

| Gotcha | Detail |
|---|---|
| **`completed_at` is empty for incomplete tasks** | Only tasks marked complete have a `completed_at` value. Always wrap with `{% if t.completed and t.completed_at %}`. |
| **Template vs. rendered HTML** | The preview shows rendered HTML; the saved dashboard stores the Jinja2 template. Don't paste the preview HTML back as a prompt input. |
| **Jinja2 doesn't support `tasks[:10]`** | Python slice notation inside `{% %}` blocks is auto-stripped. Use `{% if loop.index <= 10 %}` inside the loop instead. |
| **30% key mismatch on inject** | If you inject data with a very different structure than the original, the API rejects it. Use a dataset with the same top-level keys. |
| **Re-opening vs. re-fetching** | Opening a dashboard in History always fetches live data. To point it at a *different* project, use **Update Data** instead. |
| **Fernet key rotation** | Changing `FERNET_KEY` invalidates all stored encrypted values. Re-enter keys in Settings after rotation. |
