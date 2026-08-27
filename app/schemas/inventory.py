"""Inventory API schemas."""

from pydantic import BaseModel


class InventoryResponse(BaseModel):
    book_id: int
    available_quantity: int
