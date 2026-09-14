from __future__ import annotations
from fastapi import APIRouter, Depends
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.auth import get_current_admin
from src.database.models.auth import UserSession
from src.database.models.user import User
from src.database.session import get_db
router=APIRouter(prefix="/api/auth",tags=["auth"])
@router.post("/sessions/revoke-all")
async def revoke_all_sessions(admin:User=Depends(get_current_admin),db:AsyncSession=Depends(get_db))->dict[str,int]:
    del admin
    result=await db.execute(delete(UserSession))
    await db.commit()
    return {"sessions_revoked":result.rowcount or 0}
