from agents import function_tool
from typing import Any
from services.tools.api_calling import api_get

#accounts
@function_tool
async def list_accounts() -> Any:
    """List all accounts from the dimensions service."""
    return await api_get(
        "/accounts",
    )

@function_tool
async def get_account_by_id(account_id: str) -> Any:
    """Get account details by ID from the dimensions service."""
    return await api_get(
        f"/accounts/{account_id}"
    )

#business units
@function_tool
async def list_business_units() -> Any:
    """List all business units from the dimensions service."""
    return await api_get(
        "/business-units",
    )

@function_tool
async def get_business_unit_by_id(business_unit_id: str) -> Any:
    """Get business unit details by ID from the dimensions service."""
    return await api_get(
        f"/business-units/{business_unit_id}"
    )

#periods
@function_tool
async def list_periods() -> Any:
    """List all periods from the dimensions service."""
    return await api_get(
        "/periods",
    )

@function_tool
async def get_period_by_id(period_id: str) -> Any:
    """Get period details by ID from the dimensions service."""
    return await api_get(
        f"/periods/{period_id}"
    )


DIMENSION_TOOLS = [
    list_accounts,
    get_account_by_id,
    list_business_units,
    get_business_unit_by_id,
    list_periods,
    get_period_by_id,
]