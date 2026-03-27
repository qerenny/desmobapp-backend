from __future__ import annotations

from contextlib import asynccontextmanager
from logging import getLogger

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.errors import register_exception_handlers
from app.api.router import api_router
from app.core.config import settings
from app.core.logging import configure_logging

configure_logging(settings.log_level)

logger = getLogger(__name__)

OPENAPI_TAGS = [
    {"name": "Auth", "description": "Authentication and registration endpoints."},
    {"name": "Availability", "description": "Availability lookup for venues, rooms and seats."},
    {"name": "Bookings", "description": "Booking lifecycle, including check-in."},
    {"name": "Favorites", "description": "User favorite venues management."},
    {"name": "Holds", "description": "Temporary slot reservation before booking confirmation."},
    {"name": "Payments", "description": "Mock payment flow for MVP integration."},
    {"name": "Notifications", "description": "User notification preference management."},
    {"name": "Profile", "description": "Current user profile endpoints."},
    {"name": "Venues", "description": "Venue, room and seat browsing endpoints."},
    {"name": "Admin", "description": "Administrative venue and layout management."},
    {"name": "Analytics", "description": "Administrative occupancy analytics endpoints."},
    {"name": "Health", "description": "Service liveness and readiness probes."},
]


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("Starting application", extra={"env": settings.app_env})
    yield
    logger.info("Stopping application")


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    debug=settings.debug,
    lifespan=lifespan,
    description="Coworking booking backend API implementing the agreed frontend contract.",
    contact={"name": "ITMO Project Team"},
    openapi_tags=OPENAPI_TAGS,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
register_exception_handlers(app)
app.include_router(api_router)
