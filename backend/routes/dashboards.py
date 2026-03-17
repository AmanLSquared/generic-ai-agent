import json
import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from database import get_db
from models import Dashboard
from services.injection_engine import inject_data

router = APIRouter()


class DashboardCreate(BaseModel):
    name: str
    html: str
    json_schema: dict
    asana_workspace_id: str | None = None


class DashboardUpdate(BaseModel):
    name: str | None = None
    html: str | None = None
    json_schema: dict | None = None


class InjectRequest(BaseModel):
    new_data: dict


def _make_embed_code(dashboard_id: str) -> str:
    return f'<iframe src="http://localhost:8000/dashboard/{dashboard_id}/view" width="100%" height="600" frameborder="0"></iframe>'


@router.post("/dashboards")
async def create_dashboard(req: DashboardCreate, db: AsyncSession = Depends(get_db)):
    dashboard_id = str(uuid.uuid4())
    embed_code = _make_embed_code(dashboard_id)
    dashboard = Dashboard(
        id=dashboard_id,
        name=req.name,
        html=req.html,
        json_schema=json.dumps(req.json_schema),
        embed_code=embed_code,
        asana_workspace_id=req.asana_workspace_id,
    )
    db.add(dashboard)
    await db.commit()
    await db.refresh(dashboard)
    return _serialize(dashboard)


@router.get("/dashboards")
async def list_dashboards(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Dashboard).order_by(Dashboard.updated_at.desc()))
    dashboards = result.scalars().all()
    return [_serialize(d) for d in dashboards]


@router.get("/dashboards/{dashboard_id}")
async def get_dashboard(dashboard_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Dashboard).where(Dashboard.id == dashboard_id))
    dashboard = result.scalar_one_or_none()
    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    return _serialize(dashboard)


@router.put("/dashboards/{dashboard_id}")
async def update_dashboard(dashboard_id: str, req: DashboardUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Dashboard).where(Dashboard.id == dashboard_id))
    dashboard = result.scalar_one_or_none()
    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    if req.name is not None:
        dashboard.name = req.name
    if req.html is not None:
        dashboard.html = req.html
    if req.json_schema is not None:
        dashboard.json_schema = json.dumps(req.json_schema)
    dashboard.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(dashboard)
    return _serialize(dashboard)


@router.delete("/dashboards/{dashboard_id}")
async def delete_dashboard(dashboard_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Dashboard).where(Dashboard.id == dashboard_id))
    dashboard = result.scalar_one_or_none()
    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    await db.execute(delete(Dashboard).where(Dashboard.id == dashboard_id))
    await db.commit()
    return {"ok": True}


@router.post("/dashboards/{dashboard_id}/inject")
async def inject_dashboard_data(dashboard_id: str, req: InjectRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Dashboard).where(Dashboard.id == dashboard_id))
    dashboard = result.scalar_one_or_none()
    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found")

    saved_schema = json.loads(dashboard.json_schema)
    new_data = req.new_data

    # Key mismatch validation
    saved_keys = set(saved_schema.keys())
    new_keys = set(new_data.keys())
    missing = saved_keys - new_keys
    extra = new_keys - saved_keys

    mismatch_count = len(missing)
    total_keys = len(saved_keys)
    if total_keys > 0 and mismatch_count / total_keys > 0.30:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Too many mismatched keys (>30%). Likely wrong file.",
                "missing_keys": list(missing),
                "extra_keys": list(extra),
            },
        )

    updated_html = inject_data(dashboard.html, new_data)
    dashboard.html = updated_html
    dashboard.json_schema = json.dumps(new_data)
    dashboard.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(dashboard)
    return _serialize(dashboard)


def _serialize(d: Dashboard) -> dict:
    return {
        "id": d.id,
        "name": d.name,
        "html": d.html,
        "json_schema": json.loads(d.json_schema),
        "embed_code": d.embed_code,
        "asana_workspace_id": d.asana_workspace_id,
        "created_at": d.created_at.isoformat() if d.created_at else None,
        "updated_at": d.updated_at.isoformat() if d.updated_at else None,
    }

