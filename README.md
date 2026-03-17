# AI Dashboard Builder

A full-stack web application that lets you describe data, have GPT-4o generate a beautiful self-contained HTML dashboard, iteratively refine it through chat, save dashboards to history, and re-inject new data with **zero layout or design changes**.

---

## Features

- **Chat-to-Dashboard** — describe your data or paste JSON; GPT-4o generates a complete, responsive HTML dashboard
- **Iterative Refinement** — follow-up messages like "change to dark theme" regenerate the full dashboard preserving the data structure
- **Data Injection Engine** — replace only `DASHBOARD_DATA` in a saved dashboard with new JSON; everything else stays pixel-identical (no AI involved)
- **Asana Integration** — connect via Personal Access Token; fetch project/task data and build dashboards from it; re-fetch with one click to update
- **Dashboard History** — grid of saved dashboards with mini-previews, embed code, and data update flow
- **Settings** — manage OpenAI API key and Asana PAT (stored encrypted in SQLite)

---

## Quick Start

### Backend

```bash
cd project/backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd project/frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173)

---

## First-time Setup

1. Go to **Settings** (gear icon in sidebar)
2. Enter your OpenAI API key (`sk-…`) and click **Save**
3. (Optional) Enter your Asana Personal Access Token and click **Save**

---

## Project Structure

```
project/
├── backend/
│   ├── main.py                    # FastAPI app + /dashboard/{id}/view endpoint
│   ├── database.py                # SQLite async engine
│   ├── models.py                  # SQLAlchemy ORM models
│   ├── routes/
│   │   ├── generate.py            # POST /api/generate, /api/generate/continue
│   │   ├── dashboards.py          # CRUD + POST /api/dashboards/{id}/inject
│   │   ├── asana.py               # POST /api/asana/connect, GET /api/asana/data
│   │   └── settings.py            # GET/PUT /api/settings/{key}
│   ├── services/
│   │   ├── openai_service.py      # GPT-4o calls
│   │   ├── injection_engine.py    # Regex-based DASHBOARD_DATA replacement
│   │   └── asana_service.py       # Asana REST API + Fernet encryption
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/index.js           # All Axios API calls
│   │   ├── components/
│   │   │   ├── ChatPanel.jsx      # Left panel: chat bubbles + input
│   │   │   ├── PreviewPanel.jsx   # Right panel: iframe preview + code view
│   │   │   ├── HistoryPanel.jsx   # Dashboard grid + inject modal
│   │   │   └── Settings.jsx       # API key + PAT management
│   │   ├── pages/
│   │   │   ├── Home.jsx           # Main chat + preview page
│   │   │   ├── History.jsx        # History grid page
│   │   │   └── SettingsPage.jsx
│   │   └── App.jsx                # Router + sidebar
│   ├── package.json
│   ├── tailwind.config.js
│   └── vite.config.js
└── README.md
```

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/generate` | Generate dashboard from prompt + JSON |
| POST | `/api/generate/continue` | Refine existing dashboard via chat |
| POST | `/api/dashboards` | Save a dashboard |
| GET | `/api/dashboards` | List all dashboards |
| GET | `/api/dashboards/{id}` | Get single dashboard |
| PUT | `/api/dashboards/{id}` | Update dashboard |
| DELETE | `/api/dashboards/{id}` | Delete dashboard |
| POST | `/api/dashboards/{id}/inject` | Inject new JSON data (no AI) |
| GET | `/dashboard/{id}/view` | Serve raw HTML (for iframe embed) |
| POST | `/api/asana/connect` | Test + save Asana PAT |
| GET | `/api/asana/data` | Fetch + normalize Asana data |
| GET | `/api/settings` | Get settings (masked) |
| PUT | `/api/settings/{key}` | Upsert a setting |
| POST | `/api/settings/test-openai` | Test OpenAI key |
| DELETE | `/api/settings/history` | Clear all dashboards |

---

## Data Injection — How It Works

Every AI-generated dashboard stores all data in:

```javascript
// DASHBOARD_DATA — update this object to refresh all charts and values
// Keys: [sales, revenue, categories, ...]
const DASHBOARD_DATA = { ... };
```

When you click **Update Data**, the backend:
1. Validates new JSON keys against the saved schema (blocks if >30% mismatch)
2. Uses regex to find and replace **only** the `DASHBOARD_DATA` block
3. Saves the updated HTML — no AI, no layout changes, pixel-identical output

---

## Environment Variables (Backend)

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite+aiosqlite:///./dashboard_builder.db` | SQLite path |
| `FERNET_KEY` | Derived from fixed seed | Encryption key for Asana PAT. **Set this in production!** |

Generate a secure Fernet key:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```
