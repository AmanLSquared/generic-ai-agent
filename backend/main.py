from contextlib import asynccontextmanager
from dotenv import load_dotenv
load_dotenv()  # Load .env before anything else reads os.getenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from sqlalchemy import select

from database import init_db, AsyncSessionLocal
from models import Dashboard
from routes import dashboards, generate, asana, settings as settings_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
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
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Dashboard).where(Dashboard.id == dashboard_id))
        dashboard = result.scalar_one_or_none()
        if not dashboard:
            return HTMLResponse("<h1>Dashboard not found</h1>", status_code=404)
        return HTMLResponse(content=dashboard.html)
