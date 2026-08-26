from agents import function_tool
from typing import Any
from services.tools.tool_access_guard import role_guardrail
from services.tools.api_calling import api_get

#accounts
@function_tool(
    tool_input_guardrails=[role_guardrail]
)
async def list_employees() -> Any:
    """List all accounts from the dimensions service."""
    return await api_get(
        "/employees",
    )

@function_tool(
    tool_input_guardrails=[role_guardrail]
)
async def get_employee_by_id(employee_id: str) -> Any:
    """Get employee details by ID from the dimensions service."""
    return await api_get(
        f"/employee/{employee_id}"
    )

@function_tool(
    tool_input_guardrails=[role_guardrail]
)
async def get_employee_compensation_by_id(employee_id: str) -> Any:
    """Get employee compensation details by ID from the dimensions service."""
    return await api_get(
        f"/employee_compensation_by_id/{employee_id}"
    )

EMPLOYEE_TOOLS = [
    list_employees,
    get_employee_by_id,
    get_employee_compensation_by_id,
]