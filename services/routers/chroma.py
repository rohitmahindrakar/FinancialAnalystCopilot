from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from chromadb import PersistentClient
from chromadb.config import Settings
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/chroma", tags=["chroma"])

DEFAULT_CHROMA_DB_PATH = Path(os.getenv("CHROMA_PERSIST_DIR", "")) if os.getenv("CHROMA_PERSIST_DIR") else Path(__file__).resolve().parents[2] / "database" / "chroma"


class ChromaQueryRequest(BaseModel):
    query: str = Field(..., min_length=1, description="The question or phrase to search in the Chroma collection.")
    collection_name: str = Field(default="finance_docs_chunks", description="Collection to search in the local Chroma DB.")
    n_results: int = Field(default=5, ge=1, le=20)
    rewritten_queries: list[str] | None = Field(default=None, description="Optional rewritten versions of the query for retrieval.")
    expanded_terms: list[str] | None = Field(default=None, description="Optional query-expansion terms for better recall.")
    rerank: bool = Field(default=False, description="Whether to re-rank retrieved chunks by relevance heuristics.")
    query_variants: list[str] | None = Field(default=None, description="Optional precomputed query variants to use directly.")


class ChromaQueryResult(BaseModel):
    id: str
    document: str | None = None
    metadata: dict[str, Any] | None = None
    distance: float | None = None


def _normalize_query_text(text: str) -> str:
    return " ".join(text.split())


def _build_query_variants(
    query: str,
    rewritten_queries: list[str] | None = None,
    expanded_terms: list[str] | None = None,
) -> list[str]:
    base_query = _normalize_query_text(query)
    variants: list[str] = []
    seen: set[str] = set()

    def _add_variant(value: str) -> None:
        variant = _normalize_query_text(value)
        if variant and variant not in seen:
            seen.add(variant)
            variants.append(variant)

    _add_variant(base_query)

    for rewritten_query in rewritten_queries or []:
        _add_variant(rewritten_query)

    if expanded_terms:
        cleaned_terms = [term for term in expanded_terms if term and term.strip()]
        if cleaned_terms:
            _add_variant(f"{base_query} {' '.join(cleaned_terms)}")
            for term in cleaned_terms:
                _add_variant(f"{base_query} {term}")

    return variants


def _score_candidate(document: str | None, query_variant: str | None, distance: float | None) -> float:
    score = 0.0
    if distance is not None:
        score += max(0.0, 1.0 - float(distance))

    if document and query_variant:
        document_tokens = set(_normalize_query_text(document).lower().split())
        query_tokens = set(_normalize_query_text(query_variant).lower().split())
        overlap = len(document_tokens & query_tokens)
        score += overlap * 0.15

    return score


def _merge_query_results(
    raw_results: dict[str, Any],
    query_variants: list[str] | None = None,
    rerank: bool = False,
    n_results: int = 5,
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    variant_results = raw_results.get("ids", [])
    if not variant_results:
        return []

    if not isinstance(variant_results, list):
        return []

    documents_by_variant = raw_results.get("documents", [])
    metadatas_by_variant = raw_results.get("metadatas", [])
    distances_by_variant = raw_results.get("distances", [])

    for index, ids in enumerate(variant_results):
        query_variant = query_variants[index] if query_variants and index < len(query_variants) else None
        documents = documents_by_variant[index] if index < len(documents_by_variant) else []
        metadatas = metadatas_by_variant[index] if index < len(metadatas_by_variant) else []
        distances = distances_by_variant[index] if index < len(distances_by_variant) else []

        for offset, chunk_id in enumerate(ids):
            if str(chunk_id) in seen_ids:
                continue

            document = documents[offset] if offset < len(documents) else None
            metadata = metadatas[offset] if offset < len(metadatas) else None
            distance = distances[offset] if offset < len(distances) else None
            score = _score_candidate(document, query_variant, distance)

            candidates.append(
                {
                    "id": chunk_id,
                    "document": document,
                    "metadata": metadata,
                    "distance": distance,
                    "query_variant": query_variant,
                    "relevance_score": round(score, 4),
                }
            )
            seen_ids.add(str(chunk_id))

    if rerank:
        candidates.sort(key=lambda item: item.get("relevance_score", 0.0), reverse=True)

    return candidates[:n_results]


@router.post("/query-finance")
def query_finance_chunks(payload: ChromaQueryRequest) -> dict[str, Any]:
    query_text = payload.query.strip()
    if not query_text:
        raise HTTPException(status_code=422, detail="query cannot be empty")

    client = PersistentClient(path=str(DEFAULT_CHROMA_DB_PATH), settings=Settings(anonymized_telemetry=False))

    collection_names = [collection.name for collection in client.list_collections()]
    if payload.collection_name not in collection_names:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Collection '{payload.collection_name}' was not found in Chroma at "
                f"{DEFAULT_CHROMA_DB_PATH}. Available collections: {collection_names}"
            ),
        )

    collection = client.get_collection(name=payload.collection_name)
    query_variants = payload.query_variants or _build_query_variants(
        query_text,
        rewritten_queries=payload.rewritten_queries,
        expanded_terms=payload.expanded_terms,
    )

    variant_results: list[dict[str, Any]] = []
    for variant in query_variants:
        raw_results = collection.query(
            query_texts=[variant],
            n_results=max(payload.n_results, 3),
            include=["documents", "metadatas", "distances"],
        )
        variant_results.append(raw_results)

    merged_results = _merge_query_results(
        {
            "ids": [variant_result.get("ids", [[]])[0] for variant_result in variant_results],
            "documents": [variant_result.get("documents", [[]])[0] for variant_result in variant_results],
            "metadatas": [variant_result.get("metadatas", [[]])[0] for variant_result in variant_results],
            "distances": [variant_result.get("distances", [[]])[0] for variant_result in variant_results],
        },
        query_variants=query_variants,
        rerank=payload.rerank,
        n_results=payload.n_results,
    )

    matched_chunks = []
    for result in merged_results:
        matched_chunks.append(
            {
                "id": result.get("id"),
                "document": result.get("document"),
                "metadata": result.get("metadata"),
                "distance": result.get("distance"),
                "query_variant": result.get("query_variant"),
                "relevance_score": result.get("relevance_score"),
            }
        )

    return {
        "collection_name": payload.collection_name,
        "query": query_text,
        "query_variants": query_variants,
        "n_results": payload.n_results,
        "rerank": payload.rerank,
        "results": matched_chunks,
    }
