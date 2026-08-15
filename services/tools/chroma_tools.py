from agents import function_tool
from typing import Any
from services.models.models import ChromaQueryRequestParameters
from services.tools.api_calling import api_post


@function_tool(strict_mode=False)
async def query_finance_chunks(request: ChromaQueryRequestParameters) -> dict[str, Any]:
    """Query finance chunks from the local Chroma DB."""
    return await api_post(
        "/chroma/query-finance",
        request.model_dump(),
    )

CHROMA_TOOLS = [
    query_finance_chunks]