from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from database import get_db
from models import Setting, Dashboard

router = APIRouter()


class SettingUpdate(BaseModel):
    value: str


@router.get("/settings")
async def get_settings(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Setting))
    settings = result.scalars().all()
    # Return masked values for secrets
    out = {}
    for s in settings:
        if s.key in ("openai_api_key", "asana_pat"):
            out[s.key] = "***" if s.value else ""
        else:
            out[s.key] = s.value
    return out


@router.put("/settings/{key}")
async def upsert_setting(key: str, req: SettingUpdate, db: AsyncSession = Depends(get_db)):
    allowed_keys = {"openai_api_key", "asana_pat"}
    if key not in allowed_keys:
        raise HTTPException(status_code=400, detail=f"Unknown setting key: {key}")
    result = await db.execute(select(Setting).where(Setting.key == key))
    setting = result.scalar_one_or_none()
    if setting:
        setting.value = req.value
        setting.updated_at = datetime.utcnow()
    else:
        db.add(Setting(key=key, value=req.value))
    await db.commit()
    return {"ok": True}


@router.post("/settings/test-openai")
async def test_openai(db: AsyncSession = Depends(get_db)):
    import os
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        result = await db.execute(select(Setting).where(Setting.key == "openai_api_key"))
        setting = result.scalar_one_or_none()
        if not setting or not setting.value:
            raise HTTPException(status_code=400, detail="OpenAI API key not configured.")
        api_key = setting.value
    from services.openai_service import test_openai_key
    ok = await test_openai_key(api_key)
    if not ok:
        raise HTTPException(status_code=400, detail="Invalid OpenAI API key.")
    return {"ok": True}


@router.delete("/settings/history")
async def clear_history(db: AsyncSession = Depends(get_db)):
    await db.execute(delete(Dashboard))
    await db.commit()
    return {"ok": True}
