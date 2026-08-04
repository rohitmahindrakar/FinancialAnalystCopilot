from typing import Any

from database.connection import DatabaseConnection

DEFAULT_DATABASE_NAME = "financial_analyst_copilot.db"


def get_database_connection() -> DatabaseConnection:
    return DatabaseConnection(DEFAULT_DATABASE_NAME)


def paginate(items: list[dict], limit: int, offset: int) -> dict[str, Any]:
    return {"total": len(items), "limit": limit, "offset": offset, "items": items}
