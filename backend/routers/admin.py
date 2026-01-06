from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.db.models import User
from backend.db.settings_crud import get_admin_settings, update_admin_settings, to_public_dict
from backend.routers.conversations import get_current_user
from backend.schemas.settings import AdminSettingsOut, AdminSettingsUpdateIn

router = APIRouter(tags=["admin"])


def require_admin(user=Depends(get_current_user)):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    return user


@router.get("/admin/users")
def list_users(status: str = "pending", db: Session = Depends(get_db), admin=Depends(require_admin)):
    q = db.query(User)
    if status:
        q = q.filter(User.status == status)
    users = q.order_by(User.created_at.asc()).all()
    return {
        "ok": True,
        "users": [
            {
                "id": u.id,
                "email": u.email,
                "role": u.role,
                "status": u.status,
                "created_at": u.created_at.isoformat(),
            }
            for u in users
        ],
    }


@router.post("/admin/users/{user_id}/approve")
def approve_user(user_id: int, db: Session = Depends(get_db), admin=Depends(require_admin)):
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        return JSONResponse(status_code=404, content={"detail": "User not found"})
    u.status = "approved"
    db.commit()
    return {"ok": True}


@router.post("/admin/users/{user_id}/deny")
def deny_user(user_id: int, db: Session = Depends(get_db), admin=Depends(require_admin)):
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        return JSONResponse(status_code=404, content={"detail": "User not found"})
    u.status = "denied"
    db.commit()
    return {"ok": True}


@router.get("/admin/settings", response_model=AdminSettingsOut)
def get_settings(db: Session = Depends(get_db), admin=Depends(require_admin)):
    row = get_admin_settings(db)
    return AdminSettingsOut(**to_public_dict(row))


@router.put("/admin/settings", response_model=AdminSettingsOut)
def put_settings(payload: AdminSettingsUpdateIn, db: Session = Depends(get_db), admin=Depends(require_admin)):
    row = update_admin_settings(db, payload.model_dump(exclude_none=True))
    return AdminSettingsOut(**to_public_dict(row))