from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from typing import Any

from ..dependencies import get_database_connection, paginate
from ..api_schemas import (
    DimAccountCreate,
    DimAccountUpdate,
    DimBusinessUnitCreate,
    DimBusinessUnitUpdate,
    DimPeriodCreate,
    DimPeriodUpdate,
)
from database.connection import DatabaseConnection
from database.crud import DimAccountDAO, DimBusinessUnitDAO, DimPeriodDAO

router = APIRouter()


@router.get("/accounts")
async def list_accounts(
    limit: int = Query(25, ge=1, le=200),
    offset: int = Query(0, ge=0),
    account_code: str | None = None,
    account_type: str | None = None,
    active_flag: int | None = Query(None, ge=0, le=1),
    parent_account_id: int | None = None,
    db: DatabaseConnection = Depends(get_database_connection),
) -> Any:
    dao = DimAccountDAO(db)
    results = await dao.search(
        {
            "account_code": account_code,
            "account_type": account_type,
            "active_flag": active_flag,
            "parent_account_id": parent_account_id,
        },
        limit=limit,
        offset=offset,
    )
    return paginate(results, limit, offset)


@router.get("/accounts/{account_id}")
async def get_account(account_id: int, db: DatabaseConnection = Depends(get_database_connection)) -> Any:
    dao = DimAccountDAO(db)
    record = await dao.get_by_id(account_id)
    if not record:
        raise HTTPException(status_code=404, detail="Account not found")
    return record


@router.post("/accounts", status_code=201)
async def create_account(payload: DimAccountCreate, db: DatabaseConnection = Depends(get_database_connection)) -> Any:
    dao = DimAccountDAO(db)
    account_id = await dao.create_from_model(payload)
    return {"account_id": account_id}


@router.put("/accounts/{account_id}")
async def update_account(
    account_id: int,
    payload: DimAccountUpdate,
    db: DatabaseConnection = Depends(get_database_connection),
) -> Any:
    dao = DimAccountDAO(db)
    if not await dao.update(account_id, payload):
        raise HTTPException(status_code=404, detail="Account not found")
    return {"account_id": account_id}


@router.delete("/accounts/{account_id}", status_code=204)
async def delete_account(account_id: int, db: DatabaseConnection = Depends(get_database_connection)) -> Response:
    dao = DimAccountDAO(db)
    if not await dao.delete_by_id(account_id):
        raise HTTPException(status_code=404, detail="Account not found")
    return Response(status_code=204)


@router.get("/business-units")
async def list_business_units(
    limit: int = Query(25, ge=1, le=200),
    offset: int = Query(0, ge=0),
    region: str | None = None,
    segment: str | None = None,
    active_flag: int | None = Query(None, ge=0, le=1),
    db: DatabaseConnection = Depends(get_database_connection),
) -> Any:
    dao = DimBusinessUnitDAO(db)
    results = await dao.search(
        {
            "region": region,
            "segment": segment,
            "active_flag": active_flag,
        },
        limit=limit,
        offset=offset,
    )
    return paginate(results, limit, offset)


@router.get("/business-units/{business_unit_id}")
async def get_business_unit(business_unit_id: int, db: DatabaseConnection = Depends(get_database_connection)) -> Any:
    dao = DimBusinessUnitDAO(db)
    record = await dao.get_by_id(business_unit_id)
    if not record:
        raise HTTPException(status_code=404, detail="Business unit not found")
    return record


@router.post("/business-units", status_code=201)
async def create_business_unit(payload: DimBusinessUnitCreate, db: DatabaseConnection = Depends(get_database_connection)) -> Any:
    dao = DimBusinessUnitDAO(db)
    business_unit_id = await dao.create_from_model(payload)
    return {"business_unit_id": business_unit_id}


@router.put("/business-units/{business_unit_id}")
async def update_business_unit(
    business_unit_id: int,
    payload: DimBusinessUnitUpdate,
    db: DatabaseConnection = Depends(get_database_connection),
) -> Any:
    dao = DimBusinessUnitDAO(db)
    if not await dao.update(business_unit_id, payload):
        raise HTTPException(status_code=404, detail="Business unit not found")
    return {"business_unit_id": business_unit_id}


@router.delete("/business-units/{business_unit_id}", status_code=204)
async def delete_business_unit(business_unit_id: int, db: DatabaseConnection = Depends(get_database_connection)) -> Response:
    dao = DimBusinessUnitDAO(db)
    if not await dao.delete_by_id(business_unit_id):
        raise HTTPException(status_code=404, detail="Business unit not found")
    return Response(status_code=204)


@router.get("/periods")
async def list_periods(
    limit: int = Query(25, ge=1, le=200),
    offset: int = Query(0, ge=0),
    year: int | None = None,
    quarter: int | None = Query(None, ge=1, le=4),
    month: int | None = Query(None, ge=1, le=12),
    fiscal_year: int | None = None,
    is_closed: int | None = Query(None, ge=0, le=1),
    db: DatabaseConnection = Depends(get_database_connection),
) -> Any:
    dao = DimPeriodDAO(db)
    results = await dao.search(
        {
            "year": year,
            "quarter": quarter,
            "month": month,
            "fiscal_year": fiscal_year,
            "is_closed": is_closed,
        },
        limit=limit,
        offset=offset,
    )
    return paginate(results, limit, offset)


@router.get("/periods/{period_id}")
async def get_period(period_id: int, db: DatabaseConnection = Depends(get_database_connection)) -> Any:
    dao = DimPeriodDAO(db)
    record = await dao.get_by_id(period_id)
    if not record:
        raise HTTPException(status_code=404, detail="Period not found")
    return record


@router.post("/periods", status_code=201)
async def create_period(payload: DimPeriodCreate, db: DatabaseConnection = Depends(get_database_connection)) -> Any:
    dao = DimPeriodDAO(db)
    period_id = await dao.create_from_model(payload)
    return {"period_id": period_id}


@router.put("/periods/{period_id}")
async def update_period(
    period_id: int,
    payload: DimPeriodUpdate,
    db: DatabaseConnection = Depends(get_database_connection),
) -> Any:
    dao = DimPeriodDAO(db)
    if not await dao.update(period_id, payload):
        raise HTTPException(status_code=404, detail="Period not found")
    return {"period_id": period_id}


@router.delete("/periods/{period_id}", status_code=204)
async def delete_period(period_id: int, db: DatabaseConnection = Depends(get_database_connection)) -> Response:
    dao = DimPeriodDAO(db)
    if not await dao.delete_by_id(period_id):
        raise HTTPException(status_code=404, detail="Period not found")
    return Response(status_code=204)
