from agents import function_tool
from typing import Any
from services.tools.api_calling import api_get

#documents
@function_tool
async def list_documents() -> Any:
    """List all documents from the documents service."""
    return await api_get(
        "/source-documents",
    )

@function_tool
async def get_document_by_id(document_id: str) -> Any:
    """Get document details by ID from the documents service."""
    return await api_get(
        f"/source-documents/{document_id}"
    )

#answer-citations
@function_tool
async def list_answer_citations() -> Any:
    """List all answer citations from the documents service."""
    return await api_get(
        "/answer-citations",
    )

@function_tool
async def get_answer_citation_by_id(answer_citation_id: str) -> Any:
    """Get answer citation details by ID from the documents service."""
    return await api_get(
        f"/answer-citations/{answer_citation_id}"
    )


DOCUMENTS_TOOLS = [
    list_documents,
    get_document_by_id,
    list_answer_citations,
    get_answer_citation_by_id,
]