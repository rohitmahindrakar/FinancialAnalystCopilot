from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class ChromaQueryRequestParameters(BaseModel):
    query: str = Field(..., min_length=1, description="The question or phrase to search in the Chroma collection.")
    metadata_filters: dict[str, str | int | float | bool] = Field(
        default_factory=dict,
        description="Optional metadata filters to narrow down the search results.",
    )


class RankOrder(BaseModel):
    order: list[int] = Field(
        description="The order of relevance of chunks, from most relevant to least relevant, by chunk id number"
    )


class Result(BaseModel):
    page_content: str
    metadata: dict[str, Any]


class FinancialRequest(BaseModel):
    operation: Optional[
        Literal[
            "get_metric",
            "rank_business_units",
            "compare_business_units",
            "trend",
        ]
    ]

    metric: Optional[
        Literal[
            "revenue",
            "cogs",
            "expense",
            "other_income",
            "other_expense",
        ]
    ]

    scenario: Optional[Literal["actual", "budget", "forecast"]]

    fiscal_year: Optional[int]
    fiscal_quarter: Optional[Literal["Q1", "Q2", "Q3", "Q4"]]

    period_name: Optional[str] = ""

    business_unit_names: Optional[list[str]] = []

    top_n: Optional[int] = 10

    rank_direction: Optional[Literal["highest", "lowest"]]

    currency_code: Optional[str] = "USD"


class OrchestratorRequest(BaseModel):
    user_question: str = Field(..., min_length=1)
    api_base_url: str = Field(default="http://127.0.0.1:8000")
    conversation_id: str | None = Field(default=None, description="Optional conversation ID to maintain context across multiple requests.")


class OpenAIPlanResult(BaseModel):
    tools: list[dict[str, Any]] = Field(default_factory=list)
    synthesis: str = Field(default="")
    complete: bool = Field(default=False)
    reasoning: str = Field(default="")


class ChartSeries(BaseModel):
    name: str
    values: list[float]


class ChartSpec(BaseModel):
    chart_type: Literal["line", "bar", "scatter"]
    title: str
    x_label: str
    y_label: str

    categories: list[str]
    series: list[ChartSeries]


class FinancialCopilotAPIResponse(BaseModel):
    answer: str
    chart: ChartSpec | None = None


# ============================================================
# Structured evidence passed from Analyst -> Reviewer
# ============================================================

class Evidence(BaseModel):
    source_id: str
    chunk_id: str | None = None
    source_name: str
    page_number: int | None = None

    #text: str

    retrieval_score: float | None = None

class CalculationInput(BaseModel):
    name: str
    value: float
    unit: str | None = None

class Calculation(BaseModel):
    name: str

    inputs: list[CalculationInput]

    result: float

    unit: str | None = None


class AnalystClaim(BaseModel):
    claim: str

    # References IDs from the evidence list
    evidence_ids: list[str] = Field(default_factory=list)


class ReviewRequest(BaseModel):
    user_question: str

    draft_answer: str

    claims: list[AnalystClaim] = Field(default_factory=list)

    evidence: list[Evidence] = Field(default_factory=list)
    #evidenceIds: list[str] = Field(default_factory=list)

    calculations: list[Calculation] = Field(default_factory=list)


#reviewer response
class ReviewIssue(BaseModel):

    severity: Literal[
        "low",
        "medium",
        "high",
    ]

    category: Literal[
        "factual",
        "calculation",
        "unsupported_claim",
        "missing_information",
        "logical_consistency",
        "source_mismatch",
    ]

    description: str

    suggested_correction: str | None = None


class ReviewResult(BaseModel):

    approved: bool

    confidence: float = Field(
        ge=0.0,
        le=1.0,
    )

    issues: list[ReviewIssue] = Field(
        default_factory=list
    )

    requires_additional_data: bool = False
    requires_recalculation: bool = False
    requires_revision: bool = False
    requires_re_review: bool = False

    summary: str

class FinanceRequestValidation(BaseModel):
    is_valid_request: bool
    category: str
    reason: str