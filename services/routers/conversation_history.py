from __future__ import annotations
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response

from ..dependencies import get_database_connection, paginate
from database.connection import DatabaseConnection
from database.crud import AppUserDAO, ConversationHistoryDAO


router = APIRouter()

#generate a route to return conversatio_n history for a given user_id
@router.get("/users/{user_id}/conversation_history")
async def get_conversation_history(
    user_id: int,
    limit: int = Query(25, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: DatabaseConnection = Depends(get_database_connection),
) -> Any:
    dao = ConversationHistoryDAO(db)
    records = await dao.get_conversation_history_by_user_id(user_id)
    if not records:
        raise HTTPException(status_code=404, detail="Conversation history not found")
    return paginate(records, limit, offset)

#generate a route to return conversation history for a given conversation_id
@router.get("/conversation_history/{conversation_id}")
async def get_conversation_history_by_conversation_id(
    conversation_id: str,
    limit: int = Query(25, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: DatabaseConnection = Depends(get_database_connection),
) -> Any:
    dao = ConversationHistoryDAO(db)
    records = await dao.get_by_conversation_id(conversation_id)
    if not records:
        raise HTTPException(status_code=404, detail="Conversation history not found")
    return paginate(records, limit, offset)