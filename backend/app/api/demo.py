from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.security import require_permission
from app.database.seed_demo_data import seed_demo_dataset

router = APIRouter(
    prefix="/demo",
    tags=["demo"],
    dependencies=[Depends(require_permission("admin"))],
)


@router.post("/seed")
def seed_demo() -> dict:
    return seed_demo_dataset()
