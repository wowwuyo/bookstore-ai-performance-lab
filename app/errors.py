"""Application errors and FastAPI error-envelope handlers."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.observability import (
    get_request_id,
    logger,
    operation_for_request,
    sqlite_busy_errors,
)


class ApplicationError(Exception):
    """A domain/application failure with a stable HTTP representation."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int,
        details: Any | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = {} if details is None else details


def book_not_found(book_id: int) -> ApplicationError:
    """Return the stable missing-book error."""
    return ApplicationError(
        "BOOK_NOT_FOUND",
        "Book was not found.",
        404,
        {"book_id": book_id},
    )


def book_inactive(book_id: int) -> ApplicationError:
    """Return the stable inactive-book error."""
    return ApplicationError(
        "BOOK_INACTIVE",
        "Book is inactive.",
        409,
        {"book_id": book_id},
    )


def order_not_found(order_id: str) -> ApplicationError:
    """Return the stable missing-order error."""
    return ApplicationError(
        "ORDER_NOT_FOUND",
        "Order was not found.",
        404,
        {"order_id": order_id},
    )


def invalid_order_state(
    order_id: str,
    current_state: str,
    operation: str,
) -> ApplicationError:
    """Return the stable invalid-state error."""
    return ApplicationError(
        "INVALID_ORDER_STATE",
        "The order is not in a valid state for this operation.",
        409,
        {
            "order_id": order_id,
            "current_state": current_state,
            "operation": operation,
        },
    )


def insufficient_inventory(details: list[dict[str, int]]) -> ApplicationError:
    """Return the stable all-or-nothing inventory error."""
    return ApplicationError(
        "INSUFFICIENT_INVENTORY",
        "One or more items do not have enough inventory.",
        409,
        details,
    )


def idempotency_conflict() -> ApplicationError:
    """Return the stable idempotency-key/body mismatch error."""
    return ApplicationError(
        "IDEMPOTENCY_CONFLICT",
        "The idempotency key was already used with a different request.",
        409,
    )


def _error_response(
    request: Request,
    *,
    code: str,
    message: str,
    details: Any,
    status_code: int,
) -> JSONResponse:
    request_id = get_request_id(request)
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "details": details,
                "request_id": request_id,
            }
        },
        headers={"X-Request-ID": request_id},
    )


def _is_sqlite_busy(exc: OperationalError) -> bool:
    message = str(exc.orig).lower()
    return "locked" in message or "busy" in message


def register_error_handlers(app: FastAPI) -> None:
    """Register the common error envelope for every application failure."""

    @app.exception_handler(ApplicationError)
    async def application_error_handler(
        request: Request,
        exc: ApplicationError,
    ) -> JSONResponse:
        return _error_response(
            request,
            code=exc.code,
            message=exc.message,
            details=exc.details,
            status_code=exc.status_code,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        return _error_response(
            request,
            code="VALIDATION_ERROR",
            message="Request validation failed.",
            details=jsonable_encoder(exc.errors()),
            status_code=422,
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(
        request: Request,
        exc: StarletteHTTPException,
    ) -> JSONResponse:
        return _error_response(
            request,
            code="HTTP_ERROR",
            message=str(exc.detail),
            details={},
            status_code=exc.status_code,
        )

    @app.exception_handler(OperationalError)
    async def operational_error_handler(
        request: Request,
        exc: OperationalError,
    ) -> JSONResponse:
        if _is_sqlite_busy(exc):
            operation = operation_for_request(request)
            sqlite_busy_errors.labels(operation=operation).inc()
            logger.warning(
                "sqlite_busy",
                operation=operation,
                error_type="SQLITE_BUSY",
                retry_count=0,
            )
            return _error_response(
                request,
                code="SQLITE_BUSY",
                message="The database is temporarily busy.",
                details={},
                status_code=503,
            )
        logger.exception("database_operation_failed", error_type=type(exc).__name__)
        return _error_response(
            request,
            code="INTERNAL_ERROR",
            message="An internal server error occurred.",
            details={},
            status_code=500,
        )

    @app.exception_handler(Exception)
    async def unexpected_error_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        logger.exception("unexpected_error", error_type=type(exc).__name__)
        return _error_response(
            request,
            code="INTERNAL_ERROR",
            message="An internal server error occurred.",
            details={},
            status_code=500,
        )
