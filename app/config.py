"""Application configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass

from sqlalchemy.engine import URL, make_url

DEFAULT_DATABASE_URL = "sqlite+aiosqlite:///./data/bookstore.db"
DATABASE_URL_ENVIRONMENT_VARIABLE = "BOOKSTORE_DATABASE_URL"


@dataclass(frozen=True, slots=True)
class Settings:
    """Runtime settings loaded from environment variables."""

    database_url: str

    @classmethod
    def from_environment(cls) -> Settings:
        """Build settings from the current process environment."""
        database_url = os.getenv(
            DATABASE_URL_ENVIRONMENT_VARIABLE,
            DEFAULT_DATABASE_URL,
        )
        parsed_url = make_url(database_url)
        if parsed_url.drivername != "sqlite+aiosqlite":
            message = f"{DATABASE_URL_ENVIRONMENT_VARIABLE} must use the 'sqlite+aiosqlite' driver"
            raise ValueError(message)
        if not parsed_url.database:
            message = (
                f"{DATABASE_URL_ENVIRONMENT_VARIABLE} must reference a SQLite database"
            )
            raise ValueError(message)
        return cls(database_url=database_url)

    @property
    def parsed_database_url(self) -> URL:
        """Return the validated SQLAlchemy database URL."""
        return make_url(self.database_url)


settings = Settings.from_environment()
