import json
import os
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import Setting
from services.openai_service import generate_dashboard_html, continue_dashboard_chat

router = APIRouter()

SYSTEM_PROMPT = """You are an expert frontend developer specializing in beautiful data dashboards.
Generate a single self-contained HTML file for a dashboard based on the user's data and instructions.
Rules:

1. The file must work standalone in any browser — include all CSS in a <style> tag.
2. Use Chart.js loaded from CDN (https://cdn.jsdelivr.net/npm/chart.js) for all charts.
3. Store ALL data in a single const DASHBOARD_DATA = { ... } object at the very top of the <script> block.
4. NEVER hardcode data values in chart configs or DOM — always reference DASHBOARD_DATA.fieldName.
5. The DASHBOARD_DATA structure must exactly match the user's input JSON structure.
6. Add this comment above DASHBOARD_DATA:
   // DASHBOARD_DATA — update this object to refresh all charts and values
   // Keys: [list the top-level keys here]
7. Design must be modern: use a clean card-based layout, subtle shadows, smooth colors, responsive grid.
8. Include KPI summary cards at the top if the data supports it.
9. Use appropriate chart types: bar/line for trends, pie/donut for proportions, radar for comparisons.
10. Return ONLY the complete HTML file content. No explanation, no markdown, no code fences."""


class GenerateRequest(BaseModel):
    prompt: str
    json_data: dict | None = None


class ContinueRequest(BaseModel):
    messages: list[dict]
    current_html: str
    json_data: dict | None = None


async def get_openai_key(db: AsyncSession) -> str:
    # Env var takes priority over database setting
    env_key = os.getenv("OPENAI_API_KEY", "").strip()
    if env_key:
        return env_key
    from sqlalchemy import select
    result = await db.execute(select(Setting).where(Setting.key == "openai_api_key"))
    setting = result.scalar_one_or_none()
    if not setting or not setting.value:
        raise HTTPException(status_code=400, detail="OpenAI API key not configured. Set OPENAI_API_KEY env var or add it in Settings.")
    return setting.value


@router.post("/generate")
async def generate(req: GenerateRequest, db: AsyncSession = Depends(get_db)):
    api_key = await get_openai_key(db)
    user_message = req.prompt
    if req.json_data:
        user_message += f"\n\nData:\n```json\n{json.dumps(req.json_data, indent=2)}\n```"
    html = await generate_dashboard_html(api_key, SYSTEM_PROMPT, user_message)
    return {"html": html}


@router.post("/generate/continue")
async def continue_generation(req: ContinueRequest, db: AsyncSession = Depends(get_db)):
    api_key = await get_openai_key(db)
    # Keep last 10 messages for context
    messages = req.messages[-10:]
    if req.json_data:
        messages[-1]["content"] += f"\n\nNew data:\n```json\n{json.dumps(req.json_data, indent=2)}\n```"
    html = await continue_dashboard_chat(api_key, SYSTEM_PROMPT, messages, req.current_html)
    return {"html": html}
