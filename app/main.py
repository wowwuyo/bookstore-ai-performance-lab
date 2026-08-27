"""FastAPI application assembly and database lifecycle."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import dispose_database, init_database
from app.errors import register_error_handlers
from app.observability import configure_tracing, install_http_observability
from app.routers import inventory, orders, system


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    """Create missing tables at startup and dispose connections at shutdown."""
    del application
    await init_database()
    try:
        yield
    finally:
        await dispose_database()


def create_app() -> FastAPI:
    """Build the bookstore API."""
    application = FastAPI(
        title="Bookstore AI Performance Lab",
        version="0.1.0",
        lifespan=lifespan,
    )
    register_error_handlers(application)
    install_http_observability(application)
    application.include_router(system.router)
    application.include_router(orders.router)
    application.include_router(inventory.router)
    configure_tracing(application)
    return application


app = create_app()
