"""Book and inventory database models."""

from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base


class Book(Base):
    __tablename__ = "books"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    inventory: Mapped[Inventory | None] = relationship(
        back_populates="book", uselist=False, cascade="all, delete-orphan"
    )


class Inventory(Base):
    __tablename__ = "inventory"

    book_id: Mapped[int] = mapped_column(ForeignKey("books.id"), primary_key=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    book: Mapped[Book] = relationship(back_populates="inventory")
