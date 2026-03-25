from fastapi import APIRouter

from app.api.routes.analytics import router as analytics_router
from app.api.routes.availability import router as availability_router
from app.api.routes.auth import router as auth_router
from app.api.routes.bookings import router as bookings_router
from app.api.routes.health import router as health_router
from app.api.routes.holds import router as holds_router
from app.api.routes.notifications import router as notifications_router
from app.api.routes.payments import router as payments_router
from app.api.routes.space import admin_router as admin_space_router
from app.api.routes.space import router as space_router

api_router = APIRouter()
api_router.include_router(analytics_router)
api_router.include_router(auth_router)
api_router.include_router(availability_router)
api_router.include_router(bookings_router)
api_router.include_router(health_router, tags=["Health"])
api_router.include_router(holds_router)
api_router.include_router(notifications_router)
api_router.include_router(payments_router)
api_router.include_router(space_router)
api_router.include_router(admin_space_router)
