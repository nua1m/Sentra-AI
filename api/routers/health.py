from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.database import get_db
from api.models.schemas import HealthOut
from api.services.agent0_client import Agent0Client, get_agent0_client

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthOut)
async def health_check(
    db: AsyncSession = Depends(get_db),
    agent0: Agent0Client = Depends(get_agent0_client),
) -> HealthOut:
    # Check Agent0 connectivity
    agent0_ok = await agent0.check_health()

    # Check DB connectivity
    try:
        await db.execute(__import__("sqlalchemy").text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False

    return HealthOut(
        status="ok" if (agent0_ok and db_ok) else "degraded",
        agent0="reachable" if agent0_ok else "unreachable",
        database="connected" if db_ok else "disconnected",
    )
