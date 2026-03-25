from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.db.models import User
from app.db.session import get_db_session
from app.schemas.notification import MessageResponse, NotificationPrefsUpdate
from app.services.notification import update_notification_preferences

router = APIRouter(tags=["Notifications"])


@router.put("/notifications/preferences", response_model=MessageResponse)
async def update_notification_preferences_endpoint(
    payload: NotificationPrefsUpdate,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> MessageResponse:
    await update_notification_preferences(session, current_user=current_user, payload=payload)
    return MessageResponse(message="Настройки уведомлений обновлены")
