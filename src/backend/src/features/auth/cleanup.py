from __future__ import annotations

import logging
import time

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models.auth import UserSession
from src.database.models.password_reset import PasswordResetToken
from src.database.models.user_invitation import UserInvitation

logger = logging.getLogger(__name__)


async def cleanup_expired_authentication_records(
    db: AsyncSession, now: int | None = None
) -> tuple[int, int, int]:
    """Remove authentication records that can no longer be used.

    Active sessions and invitations are retained. Accepted invitations and
    used/expired reset tokens are safe to remove because their one-time
    credentials can no longer authenticate a request.
    """
    current_time = int(time.time()) if now is None else now

    invitation_result = await db.execute(
        delete(UserInvitation).where(
            (UserInvitation.expires_at <= current_time)
            | UserInvitation.accepted_at.is_not(None)
        )
    )
    reset_result = await db.execute(
        delete(PasswordResetToken).where(
            (PasswordResetToken.expires_at <= current_time)
            | PasswordResetToken.used_at.is_not(None)
        )
    )
    session_result = await db.execute(
        delete(UserSession).where(UserSession.expires_at <= current_time)
    )
    await db.commit()

    counts = (
        invitation_result.rowcount or 0,
        reset_result.rowcount or 0,
        session_result.rowcount or 0,
    )
    logger.info(
        "Authentication cleanup removed %d invitations, %d password reset tokens, and %d sessions",
        *counts,
    )
    return counts
