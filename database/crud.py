from __future__ import annotations

import sqlite3
from dataclasses import asdict, is_dataclass
from typing import Any, Dict, Iterable, List, Optional, Union

from .connection import DatabaseConnection


def _row_to_dict(row: Optional[sqlite3.Row]) -> Optional[Dict[str, Any]]:
    if row is None:
        return None
    return dict(row)


def _normalize_values(values: Union[Dict[str, Any], object]) -> Dict[str, Any]:
    if is_dataclass(values):
        values = asdict(values)
    elif not isinstance(values, dict):
        raise TypeError("Values must be a dict or dataclass instance.")
    return values


class BaseDAO:
    def __init__(self, db: DatabaseConnection, table_name: str, primary_key: str, columns: List[str]) -> None:
        self.db = db
        self.table_name = table_name
        self.primary_key = primary_key
        self.columns = columns

    def _filter_values(self, values: Dict[str, Any]) -> Dict[str, Any]:
        return {key: value for key, value in values.items() if key in self.columns and value is not None}

    def create(self, values: Union[Dict[str, Any], object]) -> int:
        normalized = _normalize_values(values)
        filtered = self._filter_values(normalized)
        if not filtered:
            raise ValueError("At least one valid column value must be provided for insert.")

        column_names = ", ".join(filtered.keys())
        placeholders = ", ".join("?" for _ in filtered)
        sql = f"INSERT INTO {self.table_name} ({column_names}) VALUES ({placeholders})"

        with self.db.session() as connection:
            cursor = connection.execute(sql, tuple(filtered.values()))
            return cursor.lastrowid

    def get_by_id(self, record_id: int) -> Optional[Dict[str, Any]]:
        sql = f"SELECT * FROM {self.table_name} WHERE {self.primary_key} = ?"
        with self.db.session() as connection:
            row = connection.execute(sql, (record_id,)).fetchone()
            return _row_to_dict(row)

    def list_all(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        sql = f"SELECT * FROM {self.table_name} ORDER BY {self.primary_key} LIMIT ? OFFSET ?"
        with self.db.session() as connection:
            rows = connection.execute(sql, (limit, offset)).fetchall()
            return [dict(row) for row in rows]

    def update(self, record_id: int, values: Union[Dict[str, Any], object]) -> bool:
        normalized = _normalize_values(values)
        filtered = self._filter_values(normalized)
        if not filtered:
            raise ValueError("At least one valid column value must be provided for update.")

        assignments = ", ".join(f"{column} = ?" for column in filtered)
        sql = f"UPDATE {self.table_name} SET {assignments} WHERE {self.primary_key} = ?"

        with self.db.session() as connection:
            cursor = connection.execute(sql, tuple(filtered.values()) + (record_id,))
            return cursor.rowcount > 0

    def create_from_model(self, model: object) -> int:
        return self.create(model)

    def update_from_model(self, record_id: int, model: object) -> bool:
        return self.update(record_id, model)

    def delete_by_id(self, record_id: int) -> bool:
        sql = f"DELETE FROM {self.table_name} WHERE {self.primary_key} = ?"
        with self.db.session() as connection:
            cursor = connection.execute(sql, (record_id,))
            return cursor.rowcount > 0

    def search(self, filters: Dict[str, Any], limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        filtered = {key: value for key, value in filters.items() if key in self.columns and value is not None}
        if not filtered:
            return self.list_all(limit=limit, offset=offset)

        conditions = " AND ".join(f"{key} = ?" for key in filtered)
        parameters = tuple(filtered.values()) + (limit, offset)
        sql = f"SELECT * FROM {self.table_name} WHERE {conditions} ORDER BY {self.primary_key} LIMIT ? OFFSET ?"

        with self.db.session() as connection:
            rows = connection.execute(sql, parameters).fetchall()
            return [dict(row) for row in rows]


class AnswerCitationDAO(BaseDAO):
    def __init__(self, db: DatabaseConnection) -> None:
        super().__init__(
            db,
            table_name="answer_citation",
            primary_key="citation_id",
            columns=[
                "query_id",
                "source_document_id",
                "chunk_id",
                "source_table",
                "source_column",
                "citation_type",
                "citation_text",
                "created_timestamp",
            ],
        )


class CalculationResultDAO(BaseDAO):
    def __init__(self, db: DatabaseConnection) -> None:
        super().__init__(
            db,
            table_name="calculation_result",
            primary_key="calculation_id",
            columns=[
                "query_id",
                "kpi_id",
                "period_id",
                "business_unit_id",
                "formula_used",
                "result_value",
                "comparison_value",
                "variance_amount",
                "variance_percent",
                "calculation_sql",
                "created_timestamp",
            ],
        )


class DimAccountDAO(BaseDAO):
    def __init__(self, db: DatabaseConnection) -> None:
        super().__init__(
            db,
            table_name="dim_account",
            primary_key="account_id",
            columns=[
                "account_code",
                "account_name",
                "account_type",
                "parent_account_id",
                "financial_statement_section",
                "normal_balance",
                "active_flag",
            ],
        )


class DimBusinessUnitDAO(BaseDAO):
    def __init__(self, db: DatabaseConnection) -> None:
        super().__init__(
            db,
            table_name="dim_business_unit",
            primary_key="business_unit_id",
            columns=[
                "business_unit_name",
                "parent_business_unit_id",
                "region",
                "segment",
                "active_flag",
            ],
        )


class DimPeriodDAO(BaseDAO):
    def __init__(self, db: DatabaseConnection) -> None:
        super().__init__(
            db,
            table_name="dim_period",
            primary_key="period_id",
            columns=[
                "period_name",
                "month",
                "month_name",
                "quarter",
                "year",
                "period_start_date",
                "period_end_date",
                "fiscal_year",
                "fiscal_quarter",
                "is_closed",
            ],
        )


class DocumentChunkDAO(BaseDAO):
    def __init__(self, db: DatabaseConnection) -> None:
        super().__init__(
            db,
            table_name="document_chunk",
            primary_key="chunk_id",
            columns=[
                "source_document_id",
                "chunk_text",
                "chunk_type",
                "page_number",
                "section_title",
                "embedding_id",
                "created_timestamp",
            ],
        )


class EvaluationResultDAO(BaseDAO):
    def __init__(self, db: DatabaseConnection) -> None:
        super().__init__(
            db,
            table_name="evaluation_result",
            primary_key="evaluation_result_id",
            columns=[
                "test_case_id",
                "actual_intent",
                "actual_response",
                "citation_present_flag",
                "numeric_answer_correct_flag",
                "fallback_correct_flag",
                "score",
                "notes",
                "run_timestamp",
            ],
        )


class EvaluationTestCaseDAO(BaseDAO):
    def __init__(self, db: DatabaseConnection) -> None:
        super().__init__(
            db,
            table_name="evaluation_test_case",
            primary_key="test_case_id",
            columns=[
                "question",
                "expected_intent",
                "expected_metric",
                "expected_behavior",
                "expected_source",
                "category",
                "active_flag",
            ],
        )


class FinanceActualsDAO(BaseDAO):
    def __init__(self, db: DatabaseConnection) -> None:
        super().__init__(
            db,
            table_name="finance_actuals",
            primary_key="actual_id",
            columns=[
                "period_id",
                "business_unit_id",
                "account_id",
                "scenario",
                "amount",
                "currency_code",
                "source_file_id",
                "load_timestamp",
            ],
        )


class FinanceBudgetDAO(BaseDAO):
    def __init__(self, db: DatabaseConnection) -> None:
        super().__init__(
            db,
            table_name="finance_budget",
            primary_key="budget_id",
            columns=[
                "period_id",
                "business_unit_id",
                "account_id",
                "amount",
                "currency_code",
                "version",
                "source_file_id",
                "load_timestamp",
            ],
        )


class FinanceForecastDAO(BaseDAO):
    def __init__(self, db: DatabaseConnection) -> None:
        super().__init__(
            db,
            table_name="finance_forecast",
            primary_key="forecast_id",
            columns=[
                "period_id",
                "business_unit_id",
                "account_id",
                "amount",
                "forecast_version",
                "currency_code",
                "source_file_id",
                "load_timestamp",
            ],
        )


class KPIRegistryDAO(BaseDAO):
    def __init__(self, db: DatabaseConnection) -> None:
        super().__init__(
            db,
            table_name="kpi_registry",
            primary_key="kpi_id",
            columns=[
                "kpi_name",
                "business_definition",
                "formula",
                "source_table",
                "required_columns",
                "default_grain",
                "owner",
                "citation_source_id",
                "active_flag",
                "notes",
            ],
        )


class QueryLogDAO(BaseDAO):
    def __init__(self, db: DatabaseConnection) -> None:
        super().__init__(
            db,
            table_name="query_log",
            primary_key="query_id",
            columns=[
                "user_question",
                "classified_intent",
                "resolved_metric",
                "resolved_period",
                "requires_clarification",
                "response_status",
                "response_text",
                "created_timestamp",
            ],
        )


class SourceDocumentDAO(BaseDAO):
    def __init__(self, db: DatabaseConnection) -> None:
        super().__init__(
            db,
            table_name="source_document",
            primary_key="source_document_id",
            columns=[
                "document_name",
                "document_type",
                "document_path",
                "source_category",
                "created_date",
                "loaded_timestamp",
                "checksum",
                "description",
            ],
        )


class UserFeedbackDAO(BaseDAO):
    def __init__(self, db: DatabaseConnection) -> None:
        super().__init__(
            db,
            table_name="user_feedback",
            primary_key="feedback_id",
            columns=[
                "query_id",
                "rating",
                "confidence_score",
                "comment",
                "created_timestamp",
            ],
        )
