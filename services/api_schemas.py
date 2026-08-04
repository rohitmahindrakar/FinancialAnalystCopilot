from __future__ import annotations

from datetime import date
from typing import Any, Optional

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(..., example="ok")
    database_connected: bool = Field(...)


class PaginatedResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[dict]


class AnswerCitationCreate(BaseModel):
    query_id: int
    source_document_id: Optional[int] = None
    chunk_id: Optional[int] = None
    source_table: Optional[str] = None
    source_column: Optional[str] = None
    citation_type: str
    citation_text: str


class AnswerCitationUpdate(BaseModel):
    source_document_id: Optional[int] = None
    chunk_id: Optional[int] = None
    source_table: Optional[str] = None
    source_column: Optional[str] = None
    citation_type: Optional[str] = None
    citation_text: Optional[str] = None


class CalculationResultCreate(BaseModel):
    query_id: int
    formula_used: str
    result_value: Optional[float] = None
    comparison_value: Optional[float] = None
    variance_amount: Optional[float] = None
    variance_percent: Optional[float] = None
    calculation_sql: Optional[str] = None
    kpi_id: Optional[int] = None
    period_id: Optional[int] = None
    business_unit_id: Optional[int] = None


class CalculationResultUpdate(BaseModel):
    formula_used: Optional[str] = None
    result_value: Optional[float] = None
    comparison_value: Optional[float] = None
    variance_amount: Optional[float] = None
    variance_percent: Optional[float] = None
    calculation_sql: Optional[str] = None
    kpi_id: Optional[int] = None
    period_id: Optional[int] = None
    business_unit_id: Optional[int] = None


class DimAccountCreate(BaseModel):
    account_code: str
    account_name: str
    account_type: str
    financial_statement_section: str
    normal_balance: str
    parent_account_id: Optional[int] = None
    active_flag: Optional[int] = Field(default=1, ge=0, le=1)


class DimAccountUpdate(BaseModel):
    account_code: Optional[str] = None
    account_name: Optional[str] = None
    account_type: Optional[str] = None
    financial_statement_section: Optional[str] = None
    normal_balance: Optional[str] = None
    parent_account_id: Optional[int] = None
    active_flag: Optional[int] = Field(default=None, ge=0, le=1)


class DimBusinessUnitCreate(BaseModel):
    business_unit_name: str
    parent_business_unit_id: Optional[int] = None
    region: Optional[str] = None
    segment: Optional[str] = None
    active_flag: Optional[int] = Field(default=1, ge=0, le=1)


class DimBusinessUnitUpdate(BaseModel):
    business_unit_name: Optional[str] = None
    parent_business_unit_id: Optional[int] = None
    region: Optional[str] = None
    segment: Optional[str] = None
    active_flag: Optional[int] = Field(default=None, ge=0, le=1)


class DimPeriodCreate(BaseModel):
    period_name: str
    month: int = Field(ge=1, le=12)
    month_name: str
    quarter: int = Field(ge=1, le=4)
    year: int
    period_start_date: str
    period_end_date: str
    fiscal_year: int
    fiscal_quarter: str
    is_closed: Optional[int] = Field(default=1, ge=0, le=1)


class DimPeriodUpdate(BaseModel):
    period_name: Optional[str] = None
    month: Optional[int] = Field(default=None, ge=1, le=12)
    month_name: Optional[str] = None
    quarter: Optional[int] = Field(default=None, ge=1, le=4)
    year: Optional[int] = None
    period_start_date: Optional[str] = None
    period_end_date: Optional[str] = None
    fiscal_year: Optional[int] = None
    fiscal_quarter: Optional[str] = None
    is_closed: Optional[int] = Field(default=None, ge=0, le=1)


class DocumentChunkCreate(BaseModel):
    source_document_id: int
    chunk_text: str
    chunk_type: str
    page_number: Optional[int] = None
    section_title: Optional[str] = None
    embedding_id: Optional[str] = None


class DocumentChunkUpdate(BaseModel):
    source_document_id: Optional[int] = None
    chunk_text: Optional[str] = None
    chunk_type: Optional[str] = None
    page_number: Optional[int] = None
    section_title: Optional[str] = None
    embedding_id: Optional[str] = None


class EvaluationResultCreate(BaseModel):
    test_case_id: int
    actual_intent: Optional[str] = None
    actual_response: Optional[str] = None
    citation_present_flag: Optional[int] = Field(default=None, ge=0, le=1)
    numeric_answer_correct_flag: Optional[int] = Field(default=None, ge=0, le=1)
    fallback_correct_flag: Optional[int] = Field(default=None, ge=0, le=1)
    score: Optional[float] = Field(default=None, ge=0, le=100)
    notes: Optional[str] = None


class EvaluationResultUpdate(BaseModel):
    actual_intent: Optional[str] = None
    actual_response: Optional[str] = None
    citation_present_flag: Optional[int] = Field(default=None, ge=0, le=1)
    numeric_answer_correct_flag: Optional[int] = Field(default=None, ge=0, le=1)
    fallback_correct_flag: Optional[int] = Field(default=None, ge=0, le=1)
    score: Optional[float] = Field(default=None, ge=0, le=100)
    notes: Optional[str] = None


class EvaluationTestCaseCreate(BaseModel):
    question: str
    expected_intent: str
    expected_behavior: str
    category: str
    expected_metric: Optional[str] = None
    expected_source: Optional[str] = None
    active_flag: Optional[int] = Field(default=1, ge=0, le=1)


class EvaluationTestCaseUpdate(BaseModel):
    question: Optional[str] = None
    expected_intent: Optional[str] = None
    expected_behavior: Optional[str] = None
    category: Optional[str] = None
    expected_metric: Optional[str] = None
    expected_source: Optional[str] = None
    active_flag: Optional[int] = Field(default=None, ge=0, le=1)


class FinanceActualsCreate(BaseModel):
    period_id: int
    business_unit_id: int
    account_id: int
    amount: float
    scenario: Optional[str] = Field(default="Actual")
    currency_code: Optional[str] = Field(default="USD")
    source_file_id: Optional[int] = None


class FinanceActualsUpdate(BaseModel):
    amount: Optional[float] = None
    scenario: Optional[str] = None
    currency_code: Optional[str] = None
    source_file_id: Optional[int] = None


class FinanceBudgetCreate(BaseModel):
    period_id: int
    business_unit_id: int
    account_id: int
    amount: float
    version: Optional[str] = Field(default="Original Budget")
    currency_code: Optional[str] = Field(default="USD")
    source_file_id: Optional[int] = None


class FinanceBudgetUpdate(BaseModel):
    amount: Optional[float] = None
    version: Optional[str] = None
    currency_code: Optional[str] = None
    source_file_id: Optional[int] = None


class FinanceForecastCreate(BaseModel):
    period_id: int
    business_unit_id: int
    account_id: int
    amount: float
    forecast_version: Optional[str] = Field(default="Q2 Forecast")
    currency_code: Optional[str] = Field(default="USD")
    source_file_id: Optional[int] = None


class FinanceForecastUpdate(BaseModel):
    amount: Optional[float] = None
    forecast_version: Optional[str] = None
    currency_code: Optional[str] = None
    source_file_id: Optional[int] = None


class KPIRegistryCreate(BaseModel):
    kpi_name: str
    business_definition: str
    formula: str
    source_table: str
    required_columns: str
    default_grain: str
    owner: str
    citation_source_id: Optional[int] = None
    active_flag: Optional[int] = Field(default=1, ge=0, le=1)
    notes: Optional[str] = None


class KPIRegistryUpdate(BaseModel):
    kpi_name: Optional[str] = None
    business_definition: Optional[str] = None
    formula: Optional[str] = None
    source_table: Optional[str] = None
    required_columns: Optional[str] = None
    default_grain: Optional[str] = None
    owner: Optional[str] = None
    citation_source_id: Optional[int] = None
    active_flag: Optional[int] = Field(default=None, ge=0, le=1)
    notes: Optional[str] = None


class QueryLogCreate(BaseModel):
    user_question: str
    classified_intent: str
    response_status: str
    resolved_metric: Optional[str] = None
    resolved_period: Optional[str] = None
    requires_clarification: Optional[int] = Field(default=0, ge=0, le=1)
    response_text: Optional[str] = None


class QueryLogUpdate(BaseModel):
    user_question: Optional[str] = None
    classified_intent: Optional[str] = None
    response_status: Optional[str] = None
    resolved_metric: Optional[str] = None
    resolved_period: Optional[str] = None
    requires_clarification: Optional[int] = Field(default=None, ge=0, le=1)
    response_text: Optional[str] = None


class IntentRouteRequest(BaseModel):
    user_question: str


class IntentRouteResponse(BaseModel):
    tool_name: str
    tool_path: str
    tool_method: str
    description: str
    intent: str
    arguments: dict[str, Any]


class SourceDocumentCreate(BaseModel):
    document_name: str
    document_type: str
    document_path: str
    source_category: str
    created_date: Optional[str] = None
    checksum: Optional[str] = None
    description: Optional[str] = None


class SourceDocumentUpdate(BaseModel):
    document_name: Optional[str] = None
    document_type: Optional[str] = None
    document_path: Optional[str] = None
    source_category: Optional[str] = None
    created_date: Optional[str] = None
    checksum: Optional[str] = None
    description: Optional[str] = None


class UserFeedbackCreate(BaseModel):
    query_id: int
    rating: Optional[str] = None
    confidence_score: Optional[int] = Field(default=None, ge=1, le=5)
    comment: Optional[str] = None


class UserFeedbackUpdate(BaseModel):
    rating: Optional[str] = None
    confidence_score: Optional[int] = Field(default=None, ge=1, le=5)
    comment: Optional[str] = None
