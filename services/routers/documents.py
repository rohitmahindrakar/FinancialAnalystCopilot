from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from typing import Any

from ..dependencies import get_database_connection, paginate
from ..api_schemas import (
    AnswerCitationCreate,
    AnswerCitationUpdate,
    DocumentChunkCreate,
    DocumentChunkUpdate,
    SourceDocumentCreate,
    SourceDocumentUpdate,
)
from database.connection import DatabaseConnection
from database.crud import AnswerCitationDAO, DocumentChunkDAO, SourceDocumentDAO

router = APIRouter()


@router.get("/source-documents")
def list_source_documents(
    limit: int = Query(25, ge=1, le=200),
    offset: int = Query(0, ge=0),
    document_type: str | None = None,
    source_category: str | None = None,
    db: DatabaseConnection = Depends(get_database_connection),
) -> Any:
    dao = SourceDocumentDAO(db)
    results = dao.search(
        {
            "document_type": document_type,
            "source_category": source_category,
        },
        limit=limit,
        offset=offset,
    )
    return paginate(results, limit, offset)


@router.get("/source-documents/{source_document_id}")
def get_source_document(source_document_id: int, db: DatabaseConnection = Depends(get_database_connection)) -> Any:
    dao = SourceDocumentDAO(db)
    record = dao.get_by_id(source_document_id)
    if not record:
        raise HTTPException(status_code=404, detail="Source document not found")
    return record


@router.post("/source-documents", status_code=201)
def create_source_document(payload: SourceDocumentCreate, db: DatabaseConnection = Depends(get_database_connection)) -> Any:
    dao = SourceDocumentDAO(db)
    source_document_id = dao.create_from_model(payload)
    return {"source_document_id": source_document_id}


@router.put("/source-documents/{source_document_id}")
def update_source_document(
    source_document_id: int,
    payload: SourceDocumentUpdate,
    db: DatabaseConnection = Depends(get_database_connection),
) -> Any:
    dao = SourceDocumentDAO(db)
    if not dao.update(source_document_id, payload):
        raise HTTPException(status_code=404, detail="Source document not found")
    return {"source_document_id": source_document_id}


@router.delete("/source-documents/{source_document_id}", status_code=204)
def delete_source_document(source_document_id: int, db: DatabaseConnection = Depends(get_database_connection)) -> Response:
    dao = SourceDocumentDAO(db)
    if not dao.delete_by_id(source_document_id):
        raise HTTPException(status_code=404, detail="Source document not found")
    return Response(status_code=204)


@router.get("/answer-citations")
def list_answer_citations(
    limit: int = Query(25, ge=1, le=200),
    offset: int = Query(0, ge=0),
    query_id: int | None = None,
    source_document_id: int | None = None,
    chunk_id: int | None = None,
    citation_type: str | None = None,
    db: DatabaseConnection = Depends(get_database_connection),
) -> Any:
    dao = AnswerCitationDAO(db)
    results = dao.search(
        {
            "query_id": query_id,
            "source_document_id": source_document_id,
            "chunk_id": chunk_id,
            "citation_type": citation_type,
        },
        limit=limit,
        offset=offset,
    )
    return paginate(results, limit, offset)


@router.get("/answer-citations/{citation_id}")
def get_answer_citation(citation_id: int, db: DatabaseConnection = Depends(get_database_connection)) -> Any:
    dao = AnswerCitationDAO(db)
    record = dao.get_by_id(citation_id)
    if not record:
        raise HTTPException(status_code=404, detail="Answer citation not found")
    return record


@router.post("/answer-citations", status_code=201)
def create_answer_citation(payload: AnswerCitationCreate, db: DatabaseConnection = Depends(get_database_connection)) -> Any:
    dao = AnswerCitationDAO(db)
    citation_id = dao.create_from_model(payload)
    return {"citation_id": citation_id}


@router.put("/answer-citations/{citation_id}")
def update_answer_citation(
    citation_id: int,
    payload: AnswerCitationUpdate,
    db: DatabaseConnection = Depends(get_database_connection),
) -> Any:
    dao = AnswerCitationDAO(db)
    if not dao.update(citation_id, payload):
        raise HTTPException(status_code=404, detail="Answer citation not found")
    return {"citation_id": citation_id}


@router.delete("/answer-citations/{citation_id}", status_code=204)
def delete_answer_citation(citation_id: int, db: DatabaseConnection = Depends(get_database_connection)) -> Response:
    dao = AnswerCitationDAO(db)
    if not dao.delete_by_id(citation_id):
        raise HTTPException(status_code=404, detail="Answer citation not found")
    return Response(status_code=204)


@router.get("/document-chunks")
def list_document_chunks(
    limit: int = Query(25, ge=1, le=200),
    offset: int = Query(0, ge=0),
    source_document_id: int | None = None,
    chunk_type: str | None = None,
    db: DatabaseConnection = Depends(get_database_connection),
) -> Any:
    dao = DocumentChunkDAO(db)
    results = dao.search(
        {
            "source_document_id": source_document_id,
            "chunk_type": chunk_type,
        },
        limit=limit,
        offset=offset,
    )
    return paginate(results, limit, offset)


@router.get("/document-chunks/{chunk_id}")
def get_document_chunk(chunk_id: int, db: DatabaseConnection = Depends(get_database_connection)) -> Any:
    dao = DocumentChunkDAO(db)
    record = dao.get_by_id(chunk_id)
    if not record:
        raise HTTPException(status_code=404, detail="Document chunk not found")
    return record


@router.post("/document-chunks", status_code=201)
def create_document_chunk(payload: DocumentChunkCreate, db: DatabaseConnection = Depends(get_database_connection)) -> Any:
    dao = DocumentChunkDAO(db)
    chunk_id = dao.create_from_model(payload)
    return {"chunk_id": chunk_id}


@router.put("/document-chunks/{chunk_id}")
def update_document_chunk(
    chunk_id: int,
    payload: DocumentChunkUpdate,
    db: DatabaseConnection = Depends(get_database_connection),
) -> Any:
    dao = DocumentChunkDAO(db)
    if not dao.update(chunk_id, payload):
        raise HTTPException(status_code=404, detail="Document chunk not found")
    return {"chunk_id": chunk_id}


@router.delete("/document-chunks/{chunk_id}", status_code=204)
def delete_document_chunk(chunk_id: int, db: DatabaseConnection = Depends(get_database_connection)) -> Response:
    dao = DocumentChunkDAO(db)
    if not dao.delete_by_id(chunk_id):
        raise HTTPException(status_code=404, detail="Document chunk not found")
    return Response(status_code=204)
