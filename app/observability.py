"""Metrics, structured logging, request correlation, and baseline tracing."""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from contextvars import ContextVar
from uuid import uuid4

import structlog
from fastapi import FastAPI, Request, Response
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from prometheus_client import Counter, Gauge, Histogram

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.TimeStamper(fmt="iso", utc=True, key="timestamp"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer(),
    ],
)
logger = structlog.get_logger("bookstore")

http_server_requests = Counter(
    "http_server_requests_total",
    "HTTP requests completed.",
    ("method", "route", "status_code"),
)
http_server_request_duration = Histogram(
    "http_server_request_duration_seconds",
    "HTTP request duration.",
    ("method", "route"),
)
inventory_reservation_attempts = Counter(
    "inventory_reservation_attempts_total",
    "Inventory reservation attempts.",
    ("result", "error_type"),
)
inventory_reservation_duration = Histogram(
    "inventory_reservation_duration_seconds",
    "Inventory reservation duration.",
    ("result",),
)
inventory_reservation_in_progress = Gauge(
    "inventory_reservation_in_progress",
    "Inventory reservations currently executing.",
)
inventory_reservation_anomalies = Counter(
    "inventory_reservation_anomalies_total",
    "Detected reservation anomalies.",
    ("type",),
)
order_state_transitions = Counter(
    "order_state_transitions_total",
    "Order state transitions.",
    ("from_state", "to_state"),
)
sqlite_busy_errors = Counter(
    "sqlite_busy_errors_total",
    "SQLite busy or locked failures.",
    ("operation",),
)

tracer = trace.get_tracer("bookstore.application")
_request_id_context: ContextVar[str | None] = ContextVar("request_id", default=None)
_trace_id_context: ContextVar[str | None] = ContextVar("trace_id", default=None)
_tracing_configured = False

_KNOWN_OPERATIONS = {
    ("GET", "/health"): "health",
    ("POST", "/orders"): "create_order",
    ("GET", "/orders/{order_id}"): "get_order",
    ("POST", "/orders/{order_id}/reserve"): "reserve_inventory",
    ("POST", "/orders/{order_id}/cancel"): "cancel_order",
    ("POST", "/orders/{order_id}/fulfill"): "fulfill_order",
    ("GET", "/inventory/{book_id}"): "get_inventory",
    ("GET", "/metrics"): "metrics",
}


def configure_tracing(app: FastAPI) -> None:
    """Install an in-process OTel provider and FastAPI server instrumentation."""
    global _tracing_configured
    if not _tracing_configured:
        trace.set_tracer_provider(
            TracerProvider(
                resource=Resource.create({"service.name": "bookstore-ai-performance-lab"})
            )
        )
        _tracing_configured = True
    FastAPIInstrumentor.instrument_app(app)


def get_request_id(request: Request | None = None) -> str:
    """Return the current request ID, with a safe fallback for early failures."""
    if request is not None:
        request_id = getattr(request.state, "request_id", None)
        if request_id:
            return str(request_id)
    return _request_id_context.get() or f"req-{uuid4()}"


def current_trace_id() -> str:
    """Return a correlation-friendly trace ID."""
    span_context = trace.get_current_span().get_span_context()
    if span_context.is_valid:
        return f"{span_context.trace_id:032x}"
    return _trace_id_context.get() or f"trace-{uuid4()}"


def route_template(request: Request) -> str:
    """Return the matched route template without introducing path cardinality."""
    route = request.scope.get("route")
    path = getattr(route, "path", None)
    return str(path) if path else "unmatched"


def operation_for_request(request: Request) -> str:
    """Map the current request to a bounded operation label."""
    return _KNOWN_OPERATIONS.get(
        (request.method, route_template(request)),
        "unknown",
    )


def _valid_request_id(candidate: str | None) -> str:
    if candidate and 1 <= len(candidate) <= 128:
        return candidate
    return f"req-{uuid4()}"


def install_http_observability(app: FastAPI) -> None:
    """Install request IDs, JSON access logs, and HTTP metrics."""

    @app.middleware("http")
    async def observe_http(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        started = time.perf_counter()
        request_id = _valid_request_id(request.headers.get("X-Request-ID"))
        request.state.request_id = request_id
        request_token = _request_id_context.set(request_id)
        provisional_trace_id = current_trace_id()
        trace_token = _trace_id_context.set(provisional_trace_id)
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            trace_id=provisional_trace_id,
        )
        status_code = 500
        response: Response | None = None
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            duration = time.perf_counter() - started
            route = route_template(request)
            http_server_requests.labels(
                method=request.method,
                route=route,
                status_code=str(status_code),
            ).inc()
            http_server_request_duration.labels(
                method=request.method,
                route=route,
            ).observe(duration)
            logger.info(
                "http_request",
                operation=operation_for_request(request),
                method=request.method,
                route=route,
                status_code=status_code,
                result="success" if status_code < 400 else "error",
                duration_ms=round(duration * 1000, 3),
            )
            if response is not None:
                response.headers["X-Request-ID"] = request_id
                response.headers["X-Trace-ID"] = current_trace_id()
            structlog.contextvars.clear_contextvars()
            _request_id_context.reset(request_token)
            _trace_id_context.reset(trace_token)
