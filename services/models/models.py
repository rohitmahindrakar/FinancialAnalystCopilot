
from pydantic import BaseModel, Field
from typing import Any


class ChromaQueryRequestParameters(BaseModel):
    query: str = Field(..., min_length=1, description="The question or phrase to search in the Chroma collection.")
    metadata_filters: dict[str, str | int | float | bool] = Field(default_factory=dict, description="Optional metadata filters to narrow down the search results.")

class OrchestratorRequest(BaseModel):
    user_question: str = Field(..., min_length=1)
    api_base_url: str = Field(default="http://127.0.0.1:8000")
    #conversation_history: list[dict[str, str]] = Field(default_factory=list)
    conversation_id: str | None = Field(default=None, description="Optional conversation ID to maintain context across multiple requests.")


class OpenAIPlanResult(BaseModel):
    tools: list[dict[str, Any]] = Field(default_factory=list)
    synthesis: str = Field(default="")
    complete: bool = Field(default=False)
    reasoning: str = Field(default="")