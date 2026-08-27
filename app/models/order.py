"""Order database models."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base


class OrderStatus(StrEnum):
    PENDING = "PENDING"
    RESERVED = "RESERVED"


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    status: Mapped[OrderStatus] = mapped_column(
        String(20), nullable=False, default=OrderStatus.PENDING
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    items: Mapped[list[OrderItem]] = relationship(
        back_populates="order", cascade="all, delete-orphan", order_by="OrderItem.id"
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id"), nullable=False)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    order: Mapped[Order] = relationship(back_populates="items")
