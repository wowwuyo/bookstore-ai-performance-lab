"""Initial bookstore data."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Book, Inventory

DEFAULT_BOOKS = (
    {"id": 1, "title": "FastAPI 入門", "quantity": 10},
    {"id": 2, "title": "SQLite 實戰", "quantity": 0},
)


async def seed_initial_data(session: AsyncSession) -> None:
    """Insert the stable demo catalogue once."""
    existing_book = await session.scalar(select(Book.id).limit(1))
    if existing_book is not None:
        return
    for book_data in DEFAULT_BOOKS:
        session.add(
            Book(
                id=book_data["id"],
                title=book_data["title"],
                inventory=Inventory(quantity=book_data["quantity"]),
            )
        )
    await session.commit()
