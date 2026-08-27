"""Order creation, lookup, and inventory reservation services."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import (
    book_inactive,
    book_not_found,
    insufficient_inventory,
    invalid_order_state,
    order_not_found,
)
from app.models import Order, OrderItem, OrderStatus
from app.repositories.books import get_book_with_inventory
from app.repositories.inventory import get_inventory_for_update
from app.repositories.orders import get_order
from app.schemas.orders import CreateOrderRequest, OrderItemResponse, OrderResponse


def _to_response(order: Order) -> OrderResponse:
    return OrderResponse(
        order_id=order.id,
        status=order.status,
        items=[
            OrderItemResponse(book_id=item.book_id, quantity=item.quantity)
            for item in order.items
        ],
    )


async def create_order(
    session: AsyncSession, request: CreateOrderRequest
) -> OrderResponse:
    for item in request.items:
        book = await get_book_with_inventory(session, item.book_id)
        if book is None:
            raise book_not_found(item.book_id)
        if not book.is_active:
            raise book_inactive(item.book_id)
    order = Order(status=OrderStatus.PENDING)
    order.items = [
        OrderItem(book_id=item.book_id, quantity=item.quantity)
        for item in request.items
    ]
    session.add(order)
    await session.commit()
    await session.refresh(order, attribute_names=["items"])
    return _to_response(order)


async def read_order(session: AsyncSession, order_id: str) -> OrderResponse:
    order = await get_order(session, order_id)
    if order is None:
        raise order_not_found(order_id)
    return _to_response(order)


async def reserve_order(session: AsyncSession, order_id: str) -> OrderResponse:
    order = await get_order(session, order_id)
    if order is None:
        raise order_not_found(order_id)
    if order.status != OrderStatus.PENDING:
        raise invalid_order_state(order.id, order.status, "reserve")

    requested_by_book: dict[int, int] = {}
    for item in order.items:
        requested_by_book[item.book_id] = (
            requested_by_book.get(item.book_id, 0) + item.quantity
        )

    shortages: list[dict[str, int]] = []
    inventories = []
    for book_id, requested_quantity in requested_by_book.items():
        inventory = await get_inventory_for_update(session, book_id)
        available = inventory.quantity if inventory is not None else 0
        if inventory is None or available < requested_quantity:
            shortages.append(
                {
                    "book_id": book_id,
                    "requested": requested_quantity,
                    "available": available,
                }
            )
        else:
            inventories.append((inventory, requested_quantity))
    if shortages:
        await session.rollback()
        raise insufficient_inventory(shortages)

    for inventory, quantity in inventories:
        inventory.quantity -= quantity
    order.status = OrderStatus.RESERVED
    await session.commit()
    await session.refresh(order, attribute_names=["items"])
    return _to_response(order)
