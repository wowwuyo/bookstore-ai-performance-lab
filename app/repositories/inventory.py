"""Inventory queries and updates."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Inventory


async def get_inventory(session: AsyncSession, book_id: int) -> Inventory | None:
    return await session.get(Inventory, book_id)


async def get_inventory_for_update(
    session: AsyncSession, book_id: int
) -> Inventory | None:
    return await session.scalar(select(Inventory).where(Inventory.book_id == book_id))
