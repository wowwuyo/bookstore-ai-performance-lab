"""Order queries and persistence."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Order


async def get_order(session: AsyncSession, order_id: str) -> Order | None:
    statement = (
        select(Order).options(selectinload(Order.items)).where(Order.id == order_id)
    )
    return await session.scalar(statement)
