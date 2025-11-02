from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter()


class HealthStatus(BaseModel):
    status: Literal["ok"] = Field(default="ok")
    service: str = Field(default="repo-aware-reviewer-backend")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


@router.get("/health", response_model=HealthStatus, summary="Health check")
async def get_health() -> HealthStatus:
    """Lightweight health endpoint used for readiness and liveness checks."""
    return HealthStatus()

