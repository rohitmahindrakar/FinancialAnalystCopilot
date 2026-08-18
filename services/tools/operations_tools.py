from agents import function_tool
from typing import Any
from services.tools.api_calling import api_get

#operations
@function_tool
async def list_kpis() -> Any:
    """List all KPIs from the operations service."""
    return await api_get(
        "/kpis",
    )

@function_tool
async def get_kpi_by_id(kpi_id: str) -> Any:
    """Get KPI details by ID from the operations service."""
    return await api_get(
        f"/kpis/{kpi_id}"
    )


KPI_TOOLS = [
    list_kpis,
    get_kpi_by_id,
]