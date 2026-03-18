import os
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from models import Setting
from services.asana_service import (
    fetch_asana_data,
    fetch_workspace_members,
    fetch_projects_list,
)

router = APIRouter()


class AsanaConnect(BaseModel):
    pat: str


async def _get_pat(db: AsyncSession) -> str:
    """Resolve the Asana PAT from env or encrypted DB setting."""
    from services.asana_service import decrypt_value
    pat = os.getenv("ASANA_PAT", "").strip()
    if pat:
        return pat
    result = await db.execute(select(Setting).where(Setting.key == "asana_pat"))
    setting = result.scalar_one_or_none()
    if not setting or not setting.value:
        raise HTTPException(
            status_code=400,
            detail="Asana not connected. Please add your PAT in Settings.",
        )
    return decrypt_value(setting.value)


@router.post("/asana/connect")
async def connect_asana(req: AsanaConnect, db: AsyncSession = Depends(get_db)):
    from services.asana_service import test_asana_token, encrypt_value
    user_info = await test_asana_token(req.pat)
    if not user_info:
        raise HTTPException(status_code=400, detail="Invalid Asana PAT or connection failed.")

    encrypted = encrypt_value(req.pat)
    result = await db.execute(select(Setting).where(Setting.key == "asana_pat"))
    setting = result.scalar_one_or_none()
    if setting:
        setting.value = encrypted
    else:
        db.add(Setting(key="asana_pat", value=encrypted))
    await db.commit()
    return {"ok": True, "user": user_info}


@router.get("/asana/data")
async def get_asana_data(
    scope_type: str | None = Query(default=None, description="'project' or 'user'"),
    scope_gid: str | None = Query(default=None, description="Asana GID, or 'me' for current user"),
    db: AsyncSession = Depends(get_db),
):
    """
    Fetch Asana data scoped to a project, a user, or the entire workspace.
    - scope_type=project & scope_gid=<project_gid>  → single project dashboard
    - scope_type=user   & scope_gid=<user_gid|me>   → user task dashboard
    - (no params)                                    → full workspace overview
    """
    pat = await _get_pat(db)
    return await fetch_asana_data(pat, scope_type=scope_type, scope_gid=scope_gid)


@router.get("/asana/members")
async def get_asana_members(db: AsyncSession = Depends(get_db)):
    """Return all members of the connected workspace."""
    pat = await _get_pat(db)
    members = await fetch_workspace_members(pat)
    return {"members": members}


@router.get("/asana/projects")
async def get_asana_projects(db: AsyncSession = Depends(get_db)):
    """Return all projects (gid + name) in the connected workspace."""
    pat = await _get_pat(db)
    projects = await fetch_projects_list(pat)
    return {"projects": projects}

