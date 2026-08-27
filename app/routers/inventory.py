"""Inventory endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.schemas.inventory import InventoryResponse
from app.services.inventory_service import read_inventory

router = APIRouter(prefix="/inventory", tags=["inventory"])


@router.get("/{book_id}", response_model=InventoryResponse)
async def get_inventory(
    book_id: Annotated[int, Path(gt=0)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> InventoryResponse:
    return await read_inventory(session, book_id)
