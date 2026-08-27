"""Book and inventory queries."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Book


async def get_book_with_inventory(session: AsyncSession, book_id: int) -> Book | None:
    statement = (
        select(Book).options(selectinload(Book.inventory)).where(Book.id == book_id)
    )
    return await session.scalar(statement)
