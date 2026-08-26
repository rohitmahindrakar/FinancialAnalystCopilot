
from typing import Any

from fastapi import APIRouter, Depends, Query


from database.connection import DatabaseConnection
from database.crud import EmployeeDAO
from services.dependencies import get_database_connection, paginate


router = APIRouter()

@router.get("/employees")
async def get_all_employees(
    limit: int = Query(25, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: DatabaseConnection = Depends(get_database_connection),
) -> Any:

    dao = EmployeeDAO(db)
    results = await dao.search(
        {},
        limit=limit,
        offset=offset,
    )
    return paginate(results, limit, offset)

@router.get("/employee/{employee_id}")
async def get_employee_by_id(
    employee_id: int,
    db: DatabaseConnection = Depends(get_database_connection),
) -> Any:

    dao = EmployeeDAO(db)
    result = await dao.get_by_id(employee_id)
    return result

@router.get("/employee_compensation_by_id/{employee_id}")
async def get_employee_compensation_by_id(
    employee_id: int,
    db: DatabaseConnection = Depends(get_database_connection),
) -> Any:

    from database.crud import EmployeeCompensationDAO
    dao = EmployeeCompensationDAO(db)
    result = await dao.get_by_employee_id(employee_id)
    return result