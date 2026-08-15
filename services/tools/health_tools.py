from agents import function_tool
from typing import Any
from services.tools.api_calling import api_get

#health
@function_tool
async def health_check() -> Any:
    """Perform a health check on the health service."""
    return await api_get(
        "/health-check",
    )

@function_tool
async def list_tables() -> Any:
    """List all tables from the health service."""
    return await api_get(
        f"/metadata/tables"
    )


HEALTH_TOOLS = [
    health_check,
    list_tables,
]