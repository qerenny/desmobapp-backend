from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.db.models import User
from app.db.session import get_db_session
from app.schemas.auth import ProfileUpdateRequest, UserProfile
from app.services.auth import get_current_user_profile, update_current_user_profile

router = APIRouter(tags=["Profile"])


@router.get("/me", response_model=UserProfile, summary="Get current user profile")
@router.get("/auth/me", response_model=UserProfile, include_in_schema=False)
async def me(
    current_user: User = Depends(get_current_user),
) -> UserProfile:
    return await get_current_user_profile(current_user=current_user)


@router.patch("/me", response_model=UserProfile, summary="Update current user profile")
@router.patch("/users/me", response_model=UserProfile, include_in_schema=False)
async def update_me(
    payload: ProfileUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> UserProfile:
    return await update_current_user_profile(session, current_user=current_user, payload=payload)
