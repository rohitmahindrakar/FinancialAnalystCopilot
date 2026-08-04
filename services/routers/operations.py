from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from typing import Any

from ..dependencies import get_database_connection, paginate
from ..api_schemas import (
    KPIRegistryCreate,
    KPIRegistryUpdate,
    QueryLogCreate,
    QueryLogUpdate,
    UserFeedbackCreate,
    UserFeedbackUpdate,
)
from database.connection import DatabaseConnection
from database.crud import KPIRegistryDAO, QueryLogDAO, UserFeedbackDAO

router = APIRouter()


@router.get("/kpis")
def list_kpis(
    limit: int = Query(25, ge=1, le=200),
    offset: int = Query(0, ge=0),
    active_flag: int | None = Query(None, ge=0, le=1),
    source_table: str | None = None,
    owner: str | None = None,
    db: DatabaseConnection = Depends(get_database_connection),
) -> Any:
    dao = KPIRegistryDAO(db)
    results = dao.search(
        {
            "active_flag": active_flag,
            "source_table": source_table,
            "owner": owner,
        },
        limit=limit,
        offset=offset,
    )
    return paginate(results, limit, offset)


@router.get("/kpis/{kpi_id}")
def get_kpi(kpi_id: int, db: DatabaseConnection = Depends(get_database_connection)) -> Any:
    dao = KPIRegistryDAO(db)
    record = dao.get_by_id(kpi_id)
    if not record:
        raise HTTPException(status_code=404, detail="KPI not found")
    return record


@router.post("/kpis", status_code=201)
def create_kpi(payload: KPIRegistryCreate, db: DatabaseConnection = Depends(get_database_connection)) -> Any:
    dao = KPIRegistryDAO(db)
    kpi_id = dao.create_from_model(payload)
    return {"kpi_id": kpi_id}


@router.put("/kpis/{kpi_id}")
def update_kpi(
    kpi_id: int,
    payload: KPIRegistryUpdate,
    db: DatabaseConnection = Depends(get_database_connection),
) -> Any:
    dao = KPIRegistryDAO(db)
    if not dao.update(kpi_id, payload):
        raise HTTPException(status_code=404, detail="KPI not found")
    return {"kpi_id": kpi_id}


@router.delete("/kpis/{kpi_id}", status_code=204)
def delete_kpi(kpi_id: int, db: DatabaseConnection = Depends(get_database_connection)) -> Response:
    dao = KPIRegistryDAO(db)
    if not dao.delete_by_id(kpi_id):
        raise HTTPException(status_code=404, detail="KPI not found")
    return Response(status_code=204)


@router.get("/queries")
def list_queries(
    limit: int = Query(25, ge=1, le=200),
    offset: int = Query(0, ge=0),
    classified_intent: str | None = None,
    response_status: str | None = None,
    requires_clarification: int | None = Query(None, ge=0, le=1),
    db: DatabaseConnection = Depends(get_database_connection),
) -> Any:
    dao = QueryLogDAO(db)
    results = dao.search(
        {
            "classified_intent": classified_intent,
            "response_status": response_status,
            "requires_clarification": requires_clarification,
        },
        limit=limit,
        offset=offset,
    )
    return paginate(results, limit, offset)


@router.get("/queries/{query_id}")
def get_query(query_id: int, db: DatabaseConnection = Depends(get_database_connection)) -> Any:
    dao = QueryLogDAO(db)
    record = dao.get_by_id(query_id)
    if not record:
        raise HTTPException(status_code=404, detail="Query not found")
    return record


@router.post("/queries", status_code=201)
def create_query(payload: QueryLogCreate, db: DatabaseConnection = Depends(get_database_connection)) -> Any:
    dao = QueryLogDAO(db)
    query_id = dao.create_from_model(payload)
    return {"query_id": query_id}


@router.put("/queries/{query_id}")
def update_query(
    query_id: int,
    payload: QueryLogUpdate,
    db: DatabaseConnection = Depends(get_database_connection),
) -> Any:
    dao = QueryLogDAO(db)
    if not dao.update(query_id, payload):
        raise HTTPException(status_code=404, detail="Query not found")
    return {"query_id": query_id}


@router.delete("/queries/{query_id}", status_code=204)
def delete_query(query_id: int, db: DatabaseConnection = Depends(get_database_connection)) -> Response:
    dao = QueryLogDAO(db)
    if not dao.delete_by_id(query_id):
        raise HTTPException(status_code=404, detail="Query not found")
    return Response(status_code=204)


@router.get("/feedback")
def list_feedback(
    limit: int = Query(25, ge=1, le=200),
    offset: int = Query(0, ge=0),
    query_id: int | None = None,
    rating: str | None = None,
    db: DatabaseConnection = Depends(get_database_connection),
) -> Any:
    dao = UserFeedbackDAO(db)
    results = dao.search(
        {
            "query_id": query_id,
            "rating": rating,
        },
        limit=limit,
        offset=offset,
    )
    return paginate(results, limit, offset)


@router.get("/feedback/{feedback_id}")
def get_feedback(feedback_id: int, db: DatabaseConnection = Depends(get_database_connection)) -> Any:
    dao = UserFeedbackDAO(db)
    record = dao.get_by_id(feedback_id)
    if not record:
        raise HTTPException(status_code=404, detail="Feedback not found")
    return record


@router.post("/feedback", status_code=201)
def create_feedback(payload: UserFeedbackCreate, db: DatabaseConnection = Depends(get_database_connection)) -> Any:
    dao = UserFeedbackDAO(db)
    feedback_id = dao.create_from_model(payload)
    return {"feedback_id": feedback_id}


@router.put("/feedback/{feedback_id}")
def update_feedback(
    feedback_id: int,
    payload: UserFeedbackUpdate,
    db: DatabaseConnection = Depends(get_database_connection),
) -> Any:
    dao = UserFeedbackDAO(db)
    if not dao.update(feedback_id, payload):
        raise HTTPException(status_code=404, detail="Feedback not found")
    return {"feedback_id": feedback_id}


@router.delete("/feedback/{feedback_id}", status_code=204)
def delete_feedback(feedback_id: int, db: DatabaseConnection = Depends(get_database_connection)) -> Response:
    dao = UserFeedbackDAO(db)
    if not dao.delete_by_id(feedback_id):
        raise HTTPException(status_code=404, detail="Feedback not found")
    return Response(status_code=204)
