
from pydantic import BaseModel, Field
from typing import Any, Literal, Optional


class ChromaQueryRequestParameters(BaseModel):
    query: str = Field(..., min_length=1, description="The question or phrase to search in the Chroma collection.")
    metadata_filters: dict[str, str | int | float | bool] = Field(default_factory=dict, description="Optional metadata filters to narrow down the search results.")

class RankOrder(BaseModel):
    order: list[int] = Field(
        description="The order of relevance of chunks, from most relevant to least relevant, by chunk id number"
    )

class Result(BaseModel):
    page_content: str
    metadata: dict[str, Any]

class FinancialRequest(BaseModel):
    # model_config = ConfigDict(extra="forbid")

    # needs_clarification: bool
    # clarification_question: Optional[str]

    operation: Optional[
        Literal[
            "get_metric",
            "rank_business_units",
            "compare_business_units",
            "trend"
        ]
    ]

    metric: Optional[
        Literal[
            "revenue",
            "cogs",
            "expense",
            "other_income",
            "other_expense"
        ]
    ]

    scenario: Optional[
        Literal["actual", "budget", "forecast"]
    ]

    fiscal_year: Optional[int]
    fiscal_quarter: Optional[
        Literal["Q1", "Q2", "Q3", "Q4"]
    ]

    period_name: Optional[str] = ""

    business_unit_names: Optional[list[str]] = []

    top_n: Optional[int] = 10

    rank_direction: Optional[
        Literal["highest", "lowest"]
    ]

    currency_code: Optional[str] = "USD"

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