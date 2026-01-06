from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.db.settings_crud import get_admin_settings, to_public_dict
from backend.routers.conversations import get_current_user
from backend.schemas.settings import PublicSettingsOut

router = APIRouter(tags=["settings"])


@router.get("/settings", response_model=PublicSettingsOut)
def get_public_settings(db: Session = Depends(get_db), user=Depends(get_current_user)):
    row = get_admin_settings(db)
    return PublicSettingsOut(**to_public_dict(row))