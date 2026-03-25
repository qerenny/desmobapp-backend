from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user, require_permissions
from app.db.models import User
from app.db.session import get_db_session
from app.schemas.analytics import OccupancyAnalyticsResponse
from app.services.analytics import get_occupancy_analytics

router = APIRouter(prefix="/admin", tags=["Analytics"])


@router.get("/analytics/occupancy", response_model=OccupancyAnalyticsResponse)
async def occupancy_analytics(
    startDate: date = Query(),
    endDate: date = Query(),
    session: AsyncSession = Depends(get_db_session),
    _: User = Depends(get_current_user),
    __=Depends(require_permissions("analytics.read")),
) -> OccupancyAnalyticsResponse:
    if endDate < startDate:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="endDate must be on or after startDate.")
    return await get_occupancy_analytics(session, start_date=startDate, end_date=endDate)
