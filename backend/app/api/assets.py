from fastapi import APIRouter, Depends
from app.database import query
from app.core.security import require_permission

router = APIRouter(
    prefix="/assets",
    tags=["assets"],
    dependencies=[Depends(require_permission("read"))],
)

@router.get("/{tag}/usage", response_model=list[dict])
def get_asset_usage(tag: str):
    """Return rail usage records for the given asset tag."""
    return query("SELECT * FROM asset_usage WHERE asset_tag = ?", (tag,))
