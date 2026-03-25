from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class AnalyticsPeriod(BaseModel):
    startDate: date
    endDate: date


class OccupancyAnalyticsResponse(BaseModel):
    period: AnalyticsPeriod
    occupancyRate: float
    totalBookings: int
    revenue: float
