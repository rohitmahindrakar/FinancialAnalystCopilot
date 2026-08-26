#write a class that will guard access to tools based on the user role. The class should have a method that takes in a tool name and a user role and returns True if the user has access to the tool and False otherwise. The class should also have a method that takes in a user role and returns a list of all the tools that the user has access to.
from agents import ToolGuardrailFunctionOutput, tool_input_guardrail
from agents.tool_guardrails import ToolInputGuardrailData

from models.models import UserContext

TOOL_ROLE_MAP = {
            "list_employees": ["Human Resources", "Finance Manager", "Chief Financial Officer"],
            "get_employee_by_id": ["Human Resources", "Finance Manager", "Chief Financial Officer"],
            "get_employee_compensation_by_id": ["Human Resources", "Finance Manager", "Chief Financial Officer"]
        }

#class ToolAccessGuard:    

def has_access(self, tool_name: str, user_role: str) -> bool:
    return user_role in TOOL_ROLE_MAP.get(tool_name, [])

def accessible_tools(self, user_role: str) -> list:
    return [tool for tool, roles in TOOL_ROLE_MAP.items() if user_role in roles]

@tool_input_guardrail
async def role_guardrail(
    data: ToolInputGuardrailData,
) -> ToolGuardrailFunctionOutput:

    tool_name = data.context.tool_name

    allowed_roles = TOOL_ROLE_MAP.get(
        tool_name,
        set(),
    )

    user_role = getattr(data.context.context, "role_code", None)

    allowed = bool(user_role) and user_role in allowed_roles

    output_info = {
        "allowed": allowed,
        "tool": tool_name,
        "user_role": user_role,
        "allowed_roles": list(allowed_roles),
    }

    if allowed:
        return ToolGuardrailFunctionOutput.allow(output_info=output_info)

    return ToolGuardrailFunctionOutput.raise_exception(output_info=output_info)