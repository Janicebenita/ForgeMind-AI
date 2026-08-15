from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.security import require_permission
from app.schemas.api import SearchRequest
from app.services.retrieval_service import retrieve

router = APIRouter(prefix="/search", tags=["search"])


@router.post("")
def semantic_search(
    payload: SearchRequest,
    user: Annotated[dict[str, str], Depends(require_permission("read"))],
) -> dict:
    return {
        "query": payload.query,
        "results": retrieve(payload.query, payload.limit, user_role=user["role"]),
    }
