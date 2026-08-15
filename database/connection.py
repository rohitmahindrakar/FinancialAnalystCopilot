from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any

DEFAULT_DATABASE_NAME = os.getenv("DATABASE_PATH", "financial_analyst_copilot.db")


class DatabaseConnection:
    """Manage SQLite database connections and transactions."""

    def __init__(self, database_path: str | Path = DEFAULT_DATABASE_NAME) -> None:
        self.database_path = Path(database_path)
        self._connection: sqlite3.Connection | None = None

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON;")
        return connection

    def session(self) -> "DatabaseConnection":
        return self

    def __enter__(self) -> sqlite3.Connection:
        self._connection = self.connect()
        return self._connection

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self._connection is None:
            return
        try:
            if exc_type is None:
                self._connection.commit()
        except Exception:
            self._connection.rollback()
            raise
        finally:
            self._connection.close()
            self._connection = None

    async def __aenter__(self) -> sqlite3.Connection:
        self._connection = self.connect()
        return self._connection

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self._connection is None:
            return
        try:
            if exc_type is None:
                self._connection.commit()
        except Exception:
            self._connection.rollback()
            raise
        finally:
            self._connection.close()
            self._connection = None
