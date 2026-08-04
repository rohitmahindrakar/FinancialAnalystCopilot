from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class AnswerCitation:
    query_id: int
    citation_type: str
    citation_text: str
    source_document_id: Optional[int] = None
    chunk_id: Optional[int] = None
    source_table: Optional[str] = None
    source_column: Optional[str] = None
    created_timestamp: Optional[str] = None


@dataclass
class CalculationResult:
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
    created_timestamp: Optional[str] = None


@dataclass
class DimAccount:
    account_code: str
    account_name: str
    account_type: str
    financial_statement_section: str
    normal_balance: str
    parent_account_id: Optional[int] = None
    active_flag: Optional[int] = 1


@dataclass
class DimBusinessUnit:
    business_unit_name: str
    parent_business_unit_id: Optional[int] = None
    region: Optional[str] = None
    segment: Optional[str] = None
    active_flag: Optional[int] = 1


@dataclass
class DimPeriod:
    period_name: str
    month: int
    month_name: str
    quarter: int
    year: int
    period_start_date: str
    period_end_date: str
    fiscal_year: int
    fiscal_quarter: str
    is_closed: Optional[int] = 1


@dataclass
class DocumentChunk:
    source_document_id: int
    chunk_text: str
    chunk_type: str
    page_number: Optional[int] = None
    section_title: Optional[str] = None
    embedding_id: Optional[str] = None
    created_timestamp: Optional[str] = None


@dataclass
class EvaluationResult:
    test_case_id: int
    actual_intent: Optional[str] = None
    actual_response: Optional[str] = None
    citation_present_flag: Optional[int] = None
    numeric_answer_correct_flag: Optional[int] = None
    fallback_correct_flag: Optional[int] = None
    score: Optional[float] = None
    notes: Optional[str] = None
    run_timestamp: Optional[str] = None


@dataclass
class EvaluationTestCase:
    question: str
    expected_intent: str
    expected_behavior: str
    category: str
    expected_metric: Optional[str] = None
    expected_source: Optional[str] = None
    active_flag: Optional[int] = 1


@dataclass
class FinanceActuals:
    period_id: int
    business_unit_id: int
    account_id: int
    amount: float
    scenario: Optional[str] = "Actual"
    currency_code: Optional[str] = "USD"
    source_file_id: Optional[int] = None
    load_timestamp: Optional[str] = None


@dataclass
class FinanceBudget:
    period_id: int
    business_unit_id: int
    account_id: int
    amount: float
    version: Optional[str] = "Original Budget"
    currency_code: Optional[str] = "USD"
    source_file_id: Optional[int] = None
    load_timestamp: Optional[str] = None


@dataclass
class FinanceForecast:
    period_id: int
    business_unit_id: int
    account_id: int
    amount: float
    forecast_version: Optional[str] = "Q2 Forecast"
    currency_code: Optional[str] = "USD"
    source_file_id: Optional[int] = None
    load_timestamp: Optional[str] = None


@dataclass
class KPIRegistry:
    kpi_name: str
    business_definition: str
    formula: str
    source_table: str
    required_columns: str
    default_grain: str
    owner: str
    citation_source_id: Optional[int] = None
    active_flag: Optional[int] = 1
    notes: Optional[str] = None


@dataclass
class QueryLog:
    user_question: str
    classified_intent: str
    response_status: str
    resolved_metric: Optional[str] = None
    resolved_period: Optional[str] = None
    requires_clarification: Optional[int] = 0
    response_text: Optional[str] = None
    created_timestamp: Optional[str] = None


@dataclass
class SourceDocument:
    document_name: str
    document_type: str
    document_path: str
    source_category: str
    created_date: Optional[str] = None
    checksum: Optional[str] = None
    description: Optional[str] = None
    loaded_timestamp: Optional[str] = None


@dataclass
class UserFeedback:
    query_id: int
    rating: Optional[str] = None
    confidence_score: Optional[int] = None
    comment: Optional[str] = None
    created_timestamp: Optional[str] = None
