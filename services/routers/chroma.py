from __future__ import annotations

import os
from pathlib import Path
from typing import Any, ClassVar

from chromadb import PersistentClient, QueryResult, logger
from chromadb.config import Settings
from fastapi import APIRouter, HTTPException
from litellm import completion
from pydantic import BaseModel, Field
from services.models.models import ChromaQueryRequestParameters, RankOrder, Result
from services.rag.embeddings import OpenAIEmbeddingProvider

from agents import trace, generation_span

router = APIRouter(prefix="/chroma", tags=["chroma"])

DEFAULT_CHROMA_DB_PATH = Path(os.getenv("CHROMA_PERSIST_DIR", "")) if os.getenv("CHROMA_PERSIST_DIR") else Path(__file__).resolve().parents[2] / "database" / "chroma"

#openAI properties
external_model: str = os.getenv("OPENAI_MODEL") or "gpt-4o-mini"

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

    collection_name: str = "finance_docs_chunks"
    n_results: int = 5
    embedding_provider: ClassVar[OpenAIEmbeddingProvider] = OpenAIEmbeddingProvider(model="text-embedding-3-large")

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

#write a method that takes a query input, embeds it using text-embedding-3-large embedding model from OpenAI, searches the specified chroma collection, and returns the top N results for this query. The method should also handle optional query variants, expanded terms, and reranking of results based on relevance score.
def query_chroma_collection(
    self,
    query: str
) -> QueryResult:
    if not query.strip():
        raise ValueError("Query cannot be empty.")

    client = PersistentClient(path=str(DEFAULT_CHROMA_DB_PATH), settings=Settings(anonymized_telemetry=False))

    collection_names = [collection.name for collection in client.list_collections()]
    if self.collection_name not in collection_names:
        raise ValueError(f"Collection '{self.collection_name}' not found. Available collections: {collection_names}")

    collection = client.get_collection(name=self.collection_name)

    #write code to call embeddings.py to embed the query using text-embedding-3-large embedding model from OpenAI
    query_embedding = self.embedding_provider.embed_texts([query])[0]

    #variant_results: list[dict[str, Any]] = []
    raw_results = collection.query(
        query_embeddings=[query_embedding],
        n_results=max(self.n_results, 3),
        include=["documents", "metadatas", "distances"],
    )

    return raw_results
    # variant_results.append(raw_results)

    # merged_results = _merge_query_results(
    #     {
    #         "ids": [variant_result.get("ids", [[]])[0] for variant_result in variant_results],
    #         "documents": [variant_result.get("documents", [[]])[0] for variant_result in variant_results],
    #         "metadatas": [variant_result.get("metadatas", [[]])[0] for variant_result in variant_results],
    #         "distances": [variant_result.get("distances", [[]])[0] for variant_result in variant_results],
    #     },
    #     query_variants=query_variants,
    #     rerank=rerank,
    #     n_results=n_results,
    # )

    # matched_chunks = []
    # for result in merged_results:
    #     matched_chunks.append(
    #         {
    #             "id": result.get("id"),
    #             "document": result.get("document"),
    #             "metadata": result.get("metadata"),
    #             "distance": result.get("distance"),
    #             "query_variant": result.get("query_variant"),
    #             "relevance_score": result.get("relevance_score"),
    #         }
    #     )

    # return {
    #     "collection_name": collection_name,
    #     "query": query,
    #     "query_variants": query_variants,
    #     "n_results": n_results,
    #     "rerank
    # }


#write a method that takes a query input, embeds it using text-embedding-3-large embedding model from OpenAI, searches the specified chroma collection, and returns the top N results for this query.
#this methods fetches unranked chunks. Also searches based on metadata filters if provided.
@router.post("/query-finance")
def query_finance_chunks_and_return_reranked_results(payload: ChromaQueryRequestParameters) -> list[Result]:
    result = query_chroma_collection_new(payload)

    #call method to rerank the results based on relevance score
    reranked_result = rerank_query_results(result, payload.query)

    return reranked_result


def query_chroma_collection_new(
    arguments: ChromaQueryRequestParameters
) -> list[Result]:

    try:
        #TODO: keep this parameters here for now, but later consider making these configurable through an API
        collection_name: str = "finance_docs_chunks"
        n_results: int = 20

        query = arguments.query
        metadata_filters = arguments.metadata_filters
        if not query.strip():
            raise ValueError("Query cannot be empty.")

        client = PersistentClient(path=str(DEFAULT_CHROMA_DB_PATH), settings=Settings(anonymized_telemetry=False))

        collection_names = [collection.name for collection in client.list_collections()]
        if collection_name not in collection_names:
            raise ValueError(f"Collection '{collection_name}' not found. Available collections: {collection_names}")

        collection = client.get_collection(name=collection_name)

        # Embed the query using text-embedding-3-large embedding model from OpenAI
        # Use the module-level embedding provider defined on `ChromaQueryResult`
        query_embedding = ChromaQueryResult.embedding_provider.embed_texts([query])[0]

        # Search the specified Chroma collection
        if(metadata_filters is None or not metadata_filters):
            raw_results = collection.query(
                query_embeddings=[query_embedding],
                n_results=max(n_results, 3),
                include=["documents", "metadatas", "distances"],
            )
        else:
            raw_results = collection.query(
                query_embeddings=[query_embedding],
                n_results=max(n_results, 3),
                include=["documents", "metadatas", "distances"],
                where=metadata_filters
            )

        chunks: list[Result] = []
        for result in zip(raw_results["documents"][0], raw_results["metadatas"][0]):
            chunks.append(Result(page_content=result[0], metadata=result[1]))
        return chunks
    except Exception as exc:  # pragma: no cover - defensive path
        print(f"External model request failed: {exc}")
        return []


def rerank_query_results(
    chunks: list[Result],
    query: str
) -> list[Result]:

    system_prompt = """
        You are a document re-ranker.
        You are provided with a question and a list of relevant chunks of text from a query of a knowledge base.
        The chunks are provided in the order they were retrieved; this should be approximately ordered by relevance, but you may be able to improve on that.
        You must rank order the provided chunks by relevance to the question, with the most relevant chunk first.
        Reply only with the list of ranked chunk ids, nothing else. Include all the chunk ids you are provided with, reranked.
        """
    user_prompt = f"The user has asked the following question:\n\n{query}\n\nOrder all the chunks of text by relevance to the question, from most relevant to least relevant. Include all the chunk ids you are provided with, reranked.\n\n"
    user_prompt += "Here are the chunks:\n\n"

    for index, chunk in enumerate(chunks):
        user_prompt += f"# CHUNK ID: {index + 1}:\n\n{chunk.page_content}\n\n"
    user_prompt += "Reply only with the list of ranked chunk ids, nothing else."
    prompt = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


    #make a call to openAI asking it to rerank the results based on relevance score. The prompt should include the query and the raw results. The response should be a list of chunk IDs in the order of relevance. write the call using litellm
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        #self.logger.error("OPENAI_API_KEY is not configured. Add it to your .env file.")
        raise RuntimeError("OPENAI_API_KEY is not configured. Add it to your .env file.")

    model_name = external_model
    litellm_model = model_name if "/" in model_name else f"openai/{model_name}"

    print("calling openAI to rerank the results based on relevance score using litellm...")

    try:
        with trace("LiteLLM Reranking"):

            with generation_span(
                input=prompt,
                model=litellm_model
            ) as span:

                response = completion(
                            model=litellm_model,
                            api_key=api_key,
                            api_base=os.getenv("OPENAI_API_BASE"),
                            temperature=float(os.getenv("OPENAI_TEMPERATURE", 0.1)),
                            timeout=int(os.getenv("OPENAI_TIMEOUT", 90)),
                            messages=prompt,
                            response_format=RankOrder
                        )

                span.span_data.output = [
                    {
                        "role": "assistant",
                        "content": response.choices[0].message.content
                    }
                ]

        #return response
        

        #response = asyncio.run(asyncio.gather(*task))
        #content = response.choices[0].message.content if getattr(response, "choices", None) else None

        reply = response.choices[0].message.content
        print(f"response: {reply}")
        order = RankOrder.model_validate_json(reply).order

        #print a comparison of whether the order of the chunks has changed after reranking
        original_order = list(range(1, len(chunks) + 1))
        print(f"Original order: {original_order}")
        print(f"Reranked order: {order}")

        return [chunks[i - 1] for i in order]
    except Exception as exc:  # pragma: no cover - defensive path
        print(f"External model request failed: {exc}")
        return f"External model request failed: {exc}"

# @router.post("/query-finance")
def query_finance_chunks(payload: ChromaQueryRequest) -> dict[str, Any]:
    query_text = payload.query.strip()
    if not query_text:
        logger.warning("Received empty query")
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
