import os
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from models import Setting
from services.asana_service import fetch_asana_data

router = APIRouter()


class AsanaConnect(BaseModel):
    pat: str


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
async def get_asana_data(db: AsyncSession = Depends(get_db)):
    from services.asana_service import decrypt_value
    # Env var takes priority over encrypted DB value
    pat = os.getenv("ASANA_PAT", "").strip()
    if not pat:
        result = await db.execute(select(Setting).where(Setting.key == "asana_pat"))
        setting = result.scalar_one_or_none()
        if not setting or not setting.value:
            raise HTTPException(status_code=400, detail="Asana not connected. Please add your PAT in Settings.")
        pat = decrypt_value(setting.value)
    data = await fetch_asana_data(pat)

    print("Fetched Asana data:", data)
    
    return data
