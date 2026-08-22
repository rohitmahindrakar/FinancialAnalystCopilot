from agents import function_tool
from typing import Any
from services.models.models import ChromaQueryRequestParameters
from services.tools.api_calling import api_get, api_post


@function_tool(strict_mode=False)
async def query_finance_chunks(request: ChromaQueryRequestParameters) -> dict[str, Any]:
    """Query finance chunks from the local Chroma DB. The chunks include company information, financial data, quarterly reports, conversations, and other relevant information. Query is performed using the provided parameters, and relevant chunks of data are returned."""
    return await api_post(
        "/chroma/query-finance",
        request.model_dump(),
    )

@function_tool(strict_mode=False)
async def query_finance_chunks_by_id(chunk_id: str) -> dict[str, Any]:
    """Query finance chunks from the local Chroma DB by chunk ID. The chunks include company information, financial data, quarterly reports, conversations, and other relevant information. Query is performed using the provided chunk ID, and relevant chunks of data are returned."""
    return await api_get(
        f"/chroma/get-chunk-by-id/{chunk_id}",
    )

CHROMA_TOOLS = [
    query_finance_chunks]