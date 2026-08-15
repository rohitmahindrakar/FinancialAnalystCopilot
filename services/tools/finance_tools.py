from agents import function_tool
from typing import Any
from services.tools.api_calling import api_get

#finance
@function_tool
async def list_actuals() -> Any:
    """List all actuals from the finance service."""
    return await api_get(
        "/finance/actuals",
    )

@function_tool
async def get_actual_by_id(actual_id: str) -> Any:
    """Get actual details by ID from the finance service."""
    return await api_get(
        f"/finance/actuals/{actual_id}"
    )

#budgets
@function_tool
async def list_budgets() -> Any:
    """List all budgets from the finance service."""
    return await api_get(
        "/finance/budgets",
    )

@function_tool
async def get_budget_by_id(budget_id: str) -> Any:
    """Get budget details by ID from the finance service."""
    return await api_get(
        f"/finance/budgets/{budget_id}"
    )

#forecasts
@function_tool
async def list_forecasts() -> Any:
    """List all forecasts from the finance service."""
    return await api_get(
        "/finance/forecasts",
    )

@function_tool
async def get_forecast_by_id(forecast_id: str) -> Any:
    """Get forecast details by ID from the finance service."""
    return await api_get(
        f"/finance/forecasts/{forecast_id}"
    )


FINANCE_TOOLS = [
    list_actuals,
    get_actual_by_id,
    list_budgets,
    get_budget_by_id,
    list_forecasts,
    get_forecast_by_id,
]