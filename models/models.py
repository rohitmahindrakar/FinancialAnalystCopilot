from typing import Any, Literal, Optional, TypedDict

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

class DocumentEvidence(BaseModel):
    evidence_id: str

    chunk_id: str

    document_name: str

    document_link: str | None = None

    page_number: int | None = None

    # Why this chunk was used by the analyst
    relevance: str

class DatabaseCell(BaseModel):
    column_name: str

    # Keep serialized representation predictable.
    value: str

    data_type: str | None = None


class DatabaseRow(BaseModel):
    cells: list[DatabaseCell] = Field(
        default_factory=list
    )

class DatabaseEvidence(BaseModel):
    evidence_id: str = Field(
        description="Unique identifier for this database evidence item."
    )

    query_name: str = Field(
        description="Short human-readable name describing what the query retrieved."
    )

    # query: str = Field(
    #     description="The database query executed to obtain this evidence."
    # )

    purpose: str = Field(
        description=(
            "Why this query was executed and how its results support the analysis."
        )
    )

    source_name: str = Field(
        description="Name of the database or logical financial data source."
    )

    rows: list[DatabaseRow] = Field(
        default_factory=list,
        description=(
            "Only the result rows materially used to support the analysis."
        ),
    )

    row_count: int = Field(
        description="Number of rows returned or represented by this evidence."
    )

class CalculationInput(BaseModel):
    name: str
    value: str
    unit: str | None = None


class CalculationEvidence(BaseModel):
    evidence_id: str

    calculation_name: str

    formula: str

    inputs: list[CalculationInput] = Field(
        default_factory=list
    )

    result: str

    unit: str | None = None

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
    claim_id: str = Field(
        description="Unique identifier for this material claim."
    )

    claim: str = Field(
        description=(
            "A material factual or analytical conclusion made in the draft answer."
        )
    )

    evidence_ids: list[str] = Field(
        default_factory=list,
        description=(
            "IDs of document, database, or calculation evidence "
            "that directly support this claim."
        ),
    )

class AnalystResult(BaseModel):

    draft_answer: str

    claims: list[AnalystClaim] = Field(
        default_factory=list
    )

    document_evidence: list[DocumentEvidence] = Field(
        default_factory=list
    )

    database_evidence: list[DatabaseEvidence] = Field(
        default_factory=list
    )

    calculation_evidence: list[CalculationEvidence] = Field(
        default_factory=list
    )

class ReviewRequest(BaseModel):

    user_question: str

    draft_answer: str

    claims: list[AnalystClaim] = Field(
        default_factory=list
    )

    document_evidence: list[DocumentEvidence] = Field(
        default_factory=list
    )

    database_evidence: list[DatabaseEvidence] = Field(
        default_factory=list
    )

    calculation_evidence: list[CalculationEvidence] = Field(
        default_factory=list
    )


#reviewer response
class ReviewIssue(BaseModel):

    issue_id: str

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
        "database_query",
    ]

    description: str

    affected_claim_ids: list[str] = Field(
        default_factory=list
    )

    evidence_ids: list[str] = Field(
        default_factory=list
    )

    suggested_correction: str | None = None


class ReviewResult(BaseModel):

    approved: bool = Field(
        description=(
            "True only when the draft answer is materially accurate, "
            "supported by the supplied evidence, and sufficiently complete."
        )
    )

    requires_additional_data: bool = Field(
        default=False,
        description=(
            "True when the identified issue cannot be resolved using the "
            "currently supplied evidence and targeted additional retrieval is required."
        ),
    )

    requires_recalculation: bool = Field(
        default=False,
        description=(
            "True when one or more calculations must be recomputed."
        ),
    )

    requires_revision: bool = Field(
        default=False,
        description=(
            "True when the analyst's draft answer should be modified before finalization."
        ),
    )

    requires_re_review: bool = Field(
        default=False,
        description=(
            "True when the revised analysis should be submitted to the reviewer again."
        ),
    )

class CitationInfo(BaseModel):

    citation_id: str

    citation_type: Literal[
        "document",
        "database",
        "calculation",
    ]

    label: str

    document_name: str | None = None

    document_link: str | None = None

    page_number: int | None = None

    chunk_id: str | None = None

    database_source: str | None = None

    query_name: str | None = None

    query_summary: str | None = None

    calculation_name: str | None = None

class FinalFinancialResponse(BaseModel):

    answer: str

    citations: list[CitationInfo] = Field(
        default_factory=list
    )

class FinanceRequestValidation(BaseModel):
    is_valid_request: bool
    category: str
    reason: str

class FinancialAnalysisState(TypedDict, total=False):

    user_question: str

    analysis_result: AnalystResult

    review_result: ReviewResult

    review_cycle: int

    final_answer: FinalFinancialResponse

    last_action: str