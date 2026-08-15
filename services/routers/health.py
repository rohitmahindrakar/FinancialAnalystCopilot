from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from typing import Any

from ..dependencies import get_database_connection
from database.connection import DatabaseConnection

router = APIRouter()


@router.get("/health-check")
async def health_check(db: DatabaseConnection = Depends(get_database_connection)) -> Any:
    try:
        async with db.session() as connection:
            connection.execute("SELECT 1")
        return {"status": "ok", "database_connected": True}
    except Exception:
        raise HTTPException(status_code=500, detail="Database health check failed")


@router.get("/metadata/tables")
def list_tables() -> Any:
    return {
        "tables": [
            "answer_citation",
            "calculation_result",
            "dim_account",
            "dim_business_unit",
            "dim_period",
            "document_chunk",
            "evaluation_result",
            "evaluation_test_case",
            "finance_actuals",
            "finance_budget",
            "finance_forecast",
            "kpi_registry",
            "query_log",
            "source_document",
            "user_feedback",
        ]
    }
