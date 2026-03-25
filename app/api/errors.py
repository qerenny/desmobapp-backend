from __future__ import annotations

from logging import getLogger

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.schemas.common import ErrorResponse

logger = getLogger(__name__)


async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
    payload = ErrorResponse(detail=exc.detail).model_dump()
    return JSONResponse(status_code=exc.status_code, content=payload, headers=exc.headers)


async def request_validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    payload = ErrorResponse(detail=exc.errors()).model_dump()
    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, content=payload)


async def unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled application error", exc_info=exc)
    detail = str(exc) if settings.debug else "Internal server error."
    payload = ErrorResponse(detail=detail).model_dump()
    return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=payload)


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, request_validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
