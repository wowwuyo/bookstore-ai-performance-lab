"""Order endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.schemas.orders import CreateOrderRequest, OrderResponse
from app.services.order_service import create_order, read_order, reserve_order

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("", response_model=OrderResponse, status_code=201)
async def create_order_endpoint(
    request: CreateOrderRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> OrderResponse:
    return await create_order(session, request)


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: Annotated[str, Path(min_length=1)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> OrderResponse:
    return await read_order(session, order_id)


@router.post("/{order_id}/reserve", response_model=OrderResponse)
async def reserve_inventory(
    order_id: Annotated[str, Path(min_length=1)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> OrderResponse:
    return await reserve_order(session, order_id)
