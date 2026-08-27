"""SQLAlchemy ORM models."""

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    metadata = MetaData()


from app.models.book import Book, Inventory
from app.models.order import Order, OrderItem, OrderStatus

__all__ = ["Base", "Book", "Inventory", "Order", "OrderItem", "OrderStatus"]
