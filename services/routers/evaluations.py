from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from typing import Any

from ..dependencies import get_database_connection, paginate
from ..api_schemas import (
    CalculationResultCreate,
    CalculationResultUpdate,
    EvaluationResultCreate,
    EvaluationResultUpdate,
    EvaluationTestCaseCreate,
    EvaluationTestCaseUpdate,
)
from database.connection import DatabaseConnection
from database.crud import (
    CalculationResultDAO,
    EvaluationResultDAO,
    EvaluationTestCaseDAO,
)

router = APIRouter()


@router.get("/calculation-results")
def list_calculation_results(
    limit: int = Query(25, ge=1, le=200),
    offset: int = Query(0, ge=0),
    query_id: int | None = None,
    kpi_id: int | None = None,
    period_id: int | None = None,
    business_unit_id: int | None = None,
    db: DatabaseConnection = Depends(get_database_connection),
) -> Any:
    dao = CalculationResultDAO(db)
    results = dao.search(
        {
            "query_id": query_id,
            "kpi_id": kpi_id,
            "period_id": period_id,
            "business_unit_id": business_unit_id,
        },
        limit=limit,
        offset=offset,
    )
    return paginate(results, limit, offset)


@router.get("/calculation-results/{calculation_id}")
def get_calculation_result(calculation_id: int, db: DatabaseConnection = Depends(get_database_connection)) -> Any:
    dao = CalculationResultDAO(db)
    record = dao.get_by_id(calculation_id)
    if not record:
        raise HTTPException(status_code=404, detail="Calculation result not found")
    return record


@router.post("/calculation-results", status_code=201)
def create_calculation_result(payload: CalculationResultCreate, db: DatabaseConnection = Depends(get_database_connection)) -> Any:
    dao = CalculationResultDAO(db)
    calculation_id = dao.create_from_model(payload)
    return {"calculation_id": calculation_id}


@router.put("/calculation-results/{calculation_id}")
def update_calculation_result(
    calculation_id: int,
    payload: CalculationResultUpdate,
    db: DatabaseConnection = Depends(get_database_connection),
) -> Any:
    dao = CalculationResultDAO(db)
    if not dao.update(calculation_id, payload):
        raise HTTPException(status_code=404, detail="Calculation result not found")
    return {"calculation_id": calculation_id}


@router.delete("/calculation-results/{calculation_id}", status_code=204)
def delete_calculation_result(calculation_id: int, db: DatabaseConnection = Depends(get_database_connection)) -> Response:
    dao = CalculationResultDAO(db)
    if not dao.delete_by_id(calculation_id):
        raise HTTPException(status_code=404, detail="Calculation result not found")
    return Response(status_code=204)


@router.get("/evaluation-results")
def list_evaluation_results(
    limit: int = Query(25, ge=1, le=200),
    offset: int = Query(0, ge=0),
    test_case_id: int | None = None,
    db: DatabaseConnection = Depends(get_database_connection),
) -> Any:
    dao = EvaluationResultDAO(db)
    results = dao.search(
        {"test_case_id": test_case_id},
        limit=limit,
        offset=offset,
    )
    return paginate(results, limit, offset)


@router.get("/evaluation-results/{evaluation_result_id}")
def get_evaluation_result(evaluation_result_id: int, db: DatabaseConnection = Depends(get_database_connection)) -> Any:
    dao = EvaluationResultDAO(db)
    record = dao.get_by_id(evaluation_result_id)
    if not record:
        raise HTTPException(status_code=404, detail="Evaluation result not found")
    return record


@router.post("/evaluation-results", status_code=201)
def create_evaluation_result(payload: EvaluationResultCreate, db: DatabaseConnection = Depends(get_database_connection)) -> Any:
    dao = EvaluationResultDAO(db)
    evaluation_result_id = dao.create_from_model(payload)
    return {"evaluation_result_id": evaluation_result_id}


@router.put("/evaluation-results/{evaluation_result_id}")
def update_evaluation_result(
    evaluation_result_id: int,
    payload: EvaluationResultUpdate,
    db: DatabaseConnection = Depends(get_database_connection),
) -> Any:
    dao = EvaluationResultDAO(db)
    if not dao.update(evaluation_result_id, payload):
        raise HTTPException(status_code=404, detail="Evaluation result not found")
    return {"evaluation_result_id": evaluation_result_id}


@router.delete("/evaluation-results/{evaluation_result_id}", status_code=204)
def delete_evaluation_result(evaluation_result_id: int, db: DatabaseConnection = Depends(get_database_connection)) -> Response:
    dao = EvaluationResultDAO(db)
    if not dao.delete_by_id(evaluation_result_id):
        raise HTTPException(status_code=404, detail="Evaluation result not found")
    return Response(status_code=204)


@router.get("/evaluation-test-cases")
def list_evaluation_test_cases(
    limit: int = Query(25, ge=1, le=200),
    offset: int = Query(0, ge=0),
    active_flag: int | None = Query(None, ge=0, le=1),
    db: DatabaseConnection = Depends(get_database_connection),
) -> Any:
    dao = EvaluationTestCaseDAO(db)
    results = dao.search(
        {"active_flag": active_flag},
        limit=limit,
        offset=offset,
    )
    return paginate(results, limit, offset)


@router.get("/evaluation-test-cases/{test_case_id}")
def get_evaluation_test_case(test_case_id: int, db: DatabaseConnection = Depends(get_database_connection)) -> Any:
    dao = EvaluationTestCaseDAO(db)
    record = dao.get_by_id(test_case_id)
    if not record:
        raise HTTPException(status_code=404, detail="Evaluation test case not found")
    return record


@router.post("/evaluation-test-cases", status_code=201)
def create_evaluation_test_case(payload: EvaluationTestCaseCreate, db: DatabaseConnection = Depends(get_database_connection)) -> Any:
    dao = EvaluationTestCaseDAO(db)
    test_case_id = dao.create_from_model(payload)
    return {"test_case_id": test_case_id}


@router.put("/evaluation-test-cases/{test_case_id}")
def update_evaluation_test_case(
    test_case_id: int,
    payload: EvaluationTestCaseUpdate,
    db: DatabaseConnection = Depends(get_database_connection),
) -> Any:
    dao = EvaluationTestCaseDAO(db)
    if not dao.update(test_case_id, payload):
        raise HTTPException(status_code=404, detail="Evaluation test case not found")
    return {"test_case_id": test_case_id}


@router.delete("/evaluation-test-cases/{test_case_id}", status_code=204)
def delete_evaluation_test_case(test_case_id: int, db: DatabaseConnection = Depends(get_database_connection)) -> Response:
    dao = EvaluationTestCaseDAO(db)
    if not dao.delete_by_id(test_case_id):
        raise HTTPException(status_code=404, detail="Evaluation test case not found")
    return Response(status_code=204)
