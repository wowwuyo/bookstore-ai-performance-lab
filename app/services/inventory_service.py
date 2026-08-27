"""Inventory application service."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import book_not_found
from app.repositories.books import get_book_with_inventory
from app.schemas.inventory import InventoryResponse


async def read_inventory(session: AsyncSession, book_id: int) -> InventoryResponse:
    book = await get_book_with_inventory(session, book_id)
    if book is None or not book.is_active or book.inventory is None:
        raise book_not_found(book_id)
    return InventoryResponse(
        book_id=book.id, available_quantity=book.inventory.quantity
    )
