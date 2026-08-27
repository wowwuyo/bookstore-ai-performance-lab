"""Order API schemas."""

from enum import StrEnum

from pydantic import BaseModel, Field


class OrderStatusResponse(StrEnum):
    PENDING = "PENDING"
    RESERVED = "RESERVED"


class CreateOrderItem(BaseModel):
    book_id: int = Field(gt=0)
    quantity: int = Field(gt=0)


class CreateOrderRequest(BaseModel):
    items: list[CreateOrderItem] = Field(min_length=1)


class OrderItemResponse(BaseModel):
    book_id: int
    quantity: int


class OrderResponse(BaseModel):
    order_id: str
    status: OrderStatusResponse
    items: list[OrderItemResponse]
