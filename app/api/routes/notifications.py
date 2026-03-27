from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.db.enums import NotificationStatus
from app.db.models import User
from app.db.session import get_db_session
from app.schemas.common import MessageResponse
from app.schemas.notification import (
    NotificationListResponse,
    NotificationPreferencesResponse,
    NotificationPrefsUpdate,
    PushTokenCreateRequest,
    PushTokenResponse,
)
from app.services.notification import (
    delete_push_token,
    get_notification_preferences,
    list_notifications,
    register_push_token,
    update_notification_preferences,
)

router = APIRouter(tags=["Notifications"])


@router.get("/notifications/preferences", response_model=NotificationPreferencesResponse)
async def get_notification_preferences_endpoint(
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> NotificationPreferencesResponse:
    return await get_notification_preferences(session, current_user=current_user)


@router.put("/notifications/preferences", response_model=MessageResponse)
async def update_notification_preferences_endpoint(
    payload: NotificationPrefsUpdate,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> MessageResponse:
    await update_notification_preferences(session, current_user=current_user, payload=payload)
    return MessageResponse(message="Настройки уведомлений обновлены")


@router.get("/notifications", response_model=NotificationListResponse)
async def list_notifications_endpoint(
    status_filter: NotificationStatus | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> NotificationListResponse:
    return await list_notifications(
        session,
        current_user=current_user,
        status=status_filter,
        page=page,
        limit=limit,
    )


@router.post("/devices/push-tokens", response_model=PushTokenResponse, status_code=status.HTTP_201_CREATED)
async def register_push_token_endpoint(
    payload: PushTokenCreateRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> PushTokenResponse:
    return await register_push_token(session, current_user=current_user, payload=payload)


@router.delete("/devices/push-tokens/{deviceId}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_push_token_endpoint(
    deviceId: UUID,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> Response:
    await delete_push_token(session, current_user=current_user, device_id=deviceId)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
