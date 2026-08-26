from __future__ import annotations
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response

from ..dependencies import get_database_connection, paginate
from database.connection import DatabaseConnection
from database.crud import AppUserDAO


router = APIRouter()

@router.get("/users")
async def list_all_users(
    limit: int = Query(25, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: DatabaseConnection = Depends(get_database_connection),
) -> Any:

    dao = AppUserDAO(db)
    results = await dao.list_with_role_name(limit=limit, offset=offset)
    return paginate(results, limit, offset)

@router.get("/users/{user_id}")
async def get_user(user_id: int, db: DatabaseConnection = Depends(get_database_connection)) -> Any:
    dao = AppUserDAO(db)
    record = await dao.get_by_id(user_id)
    if not record:
        raise HTTPException(status_code=404, detail="User not found")
    return record
