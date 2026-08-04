from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from typing import Any

from ..dependencies import get_database_connection, paginate
from ..api_schemas import (
    FinanceActualsCreate,
    FinanceActualsUpdate,
    FinanceBudgetCreate,
    FinanceBudgetUpdate,
    FinanceForecastCreate,
    FinanceForecastUpdate,
)
from database.connection import DatabaseConnection
from database.crud import FinanceActualsDAO, FinanceBudgetDAO, FinanceForecastDAO

router = APIRouter()


@router.get("/finance/actuals")
def list_finance_actuals(
    limit: int = Query(25, ge=1, le=200),
    offset: int = Query(0, ge=0),
    period_id: int | None = None,
    business_unit_id: int | None = None,
    account_id: int | None = None,
    scenario: str | None = None,
    db: DatabaseConnection = Depends(get_database_connection),
) -> Any:
    dao = FinanceActualsDAO(db)
    results = dao.search(
        {
            "period_id": period_id,
            "business_unit_id": business_unit_id,
            "account_id": account_id,
            "scenario": scenario,
        },
        limit=limit,
        offset=offset,
    )
    return paginate(results, limit, offset)


@router.get("/finance/actuals/{actual_id}")
def get_finance_actual(actual_id: int, db: DatabaseConnection = Depends(get_database_connection)) -> Any:
    dao = FinanceActualsDAO(db)
    record = dao.get_by_id(actual_id)
    if not record:
        raise HTTPException(status_code=404, detail="Finance actual not found")
    return record


@router.post("/finance/actuals", status_code=201)
def create_finance_actual(payload: FinanceActualsCreate, db: DatabaseConnection = Depends(get_database_connection)) -> Any:
    dao = FinanceActualsDAO(db)
    actual_id = dao.create_from_model(payload)
    return {"actual_id": actual_id}


@router.put("/finance/actuals/{actual_id}")
def update_finance_actual(
    actual_id: int,
    payload: FinanceActualsUpdate,
    db: DatabaseConnection = Depends(get_database_connection),
) -> Any:
    dao = FinanceActualsDAO(db)
    if not dao.update(actual_id, payload):
        raise HTTPException(status_code=404, detail="Finance actual not found")
    return {"actual_id": actual_id}


@router.delete("/finance/actuals/{actual_id}", status_code=204)
def delete_finance_actual(actual_id: int, db: DatabaseConnection = Depends(get_database_connection)) -> Response:
    dao = FinanceActualsDAO(db)
    if not dao.delete_by_id(actual_id):
        raise HTTPException(status_code=404, detail="Finance actual not found")
    return Response(status_code=204)


@router.get("/finance/budgets")
def list_finance_budgets(
    limit: int = Query(25, ge=1, le=200),
    offset: int = Query(0, ge=0),
    period_id: int | None = None,
    business_unit_id: int | None = None,
    account_id: int | None = None,
    version: str | None = None,
    db: DatabaseConnection = Depends(get_database_connection),
) -> Any:
    dao = FinanceBudgetDAO(db)
    results = dao.search(
        {
            "period_id": period_id,
            "business_unit_id": business_unit_id,
            "account_id": account_id,
            "version": version,
        },
        limit=limit,
        offset=offset,
    )
    return paginate(results, limit, offset)


@router.get("/finance/budgets/{budget_id}")
def get_finance_budget(budget_id: int, db: DatabaseConnection = Depends(get_database_connection)) -> Any:
    dao = FinanceBudgetDAO(db)
    record = dao.get_by_id(budget_id)
    if not record:
        raise HTTPException(status_code=404, detail="Finance budget not found")
    return record


@router.post("/finance/budgets", status_code=201)
def create_finance_budget(payload: FinanceBudgetCreate, db: DatabaseConnection = Depends(get_database_connection)) -> Any:
    dao = FinanceBudgetDAO(db)
    budget_id = dao.create_from_model(payload)
    return {"budget_id": budget_id}


@router.put("/finance/budgets/{budget_id}")
def update_finance_budget(
    budget_id: int,
    payload: FinanceBudgetUpdate,
    db: DatabaseConnection = Depends(get_database_connection),
) -> Any:
    dao = FinanceBudgetDAO(db)
    if not dao.update(budget_id, payload):
        raise HTTPException(status_code=404, detail="Finance budget not found")
    return {"budget_id": budget_id}


@router.delete("/finance/budgets/{budget_id}", status_code=204)
def delete_finance_budget(budget_id: int, db: DatabaseConnection = Depends(get_database_connection)) -> Response:
    dao = FinanceBudgetDAO(db)
    if not dao.delete_by_id(budget_id):
        raise HTTPException(status_code=404, detail="Finance budget not found")
    return Response(status_code=204)


@router.get("/finance/forecasts")
def list_finance_forecasts(
    limit: int = Query(25, ge=1, le=200),
    offset: int = Query(0, ge=0),
    period_id: int | None = None,
    business_unit_id: int | None = None,
    account_id: int | None = None,
    forecast_version: str | None = None,
    db: DatabaseConnection = Depends(get_database_connection),
) -> Any:
    dao = FinanceForecastDAO(db)
    results = dao.search(
        {
            "period_id": period_id,
            "business_unit_id": business_unit_id,
            "account_id": account_id,
            "forecast_version": forecast_version,
        },
        limit=limit,
        offset=offset,
    )
    return paginate(results, limit, offset)


@router.get("/finance/forecasts/{forecast_id}")
def get_finance_forecast(forecast_id: int, db: DatabaseConnection = Depends(get_database_connection)) -> Any:
    dao = FinanceForecastDAO(db)
    record = dao.get_by_id(forecast_id)
    if not record:
        raise HTTPException(status_code=404, detail="Finance forecast not found")
    return record


@router.post("/finance/forecasts", status_code=201)
def create_finance_forecast(payload: FinanceForecastCreate, db: DatabaseConnection = Depends(get_database_connection)) -> Any:
    dao = FinanceForecastDAO(db)
    forecast_id = dao.create_from_model(payload)
    return {"forecast_id": forecast_id}


@router.put("/finance/forecasts/{forecast_id}")
def update_finance_forecast(
    forecast_id: int,
    payload: FinanceForecastUpdate,
    db: DatabaseConnection = Depends(get_database_connection),
) -> Any:
    dao = FinanceForecastDAO(db)
    if not dao.update(forecast_id, payload):
        raise HTTPException(status_code=404, detail="Finance forecast not found")
    return {"forecast_id": forecast_id}


@router.delete("/finance/forecasts/{forecast_id}", status_code=204)
def delete_finance_forecast(forecast_id: int, db: DatabaseConnection = Depends(get_database_connection)) -> Response:
    dao = FinanceForecastDAO(db)
    if not dao.delete_by_id(forecast_id):
        raise HTTPException(status_code=404, detail="Finance forecast not found")
    return Response(status_code=204)
