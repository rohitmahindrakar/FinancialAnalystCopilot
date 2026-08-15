from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import sys

from pathlib import Path
from typing import Any
from dotenv import load_dotenv
from fastapi import APIRouter
from fastapi.responses import JSONResponse, StreamingResponse

from agents import OpenAIChatCompletionsModel
from services.models.models import OrchestratorRequest
from services.orchestration.openAIOrchestration.orchestration_common import event_stream_line
from services.orchestration.openAIOrchestration.orchestrator import Orchestrator
from services.rag.injest import Injestor
from services.routers.tool_registry import OrchestratorToolRegistry

load_dotenv()

router = APIRouter(prefix="/orchestrator", tags=["orchestrator"])
_openAI_Orchestrator: Orchestrator = Orchestrator()

ORCHESTRATOR_TOOL_REGISTRY = OrchestratorToolRegistry()

#logging configuration
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s"))
    logger.addHandler(handler)
logger.setLevel(logging.INFO)






WELCOME_MESSAGE = (
    "Welcome to Financial Analyst Copilot. "
    "I can help you explore company finance data, compare budgets, forecasts, and actuals, "
    "and surface context from finance documents and narrative reports. "
    "Ask me a question about your company’s financial performance or guidance, and I’ll select the right tools to provide an answer."
)

DATA_OVERVIEW = (
    "This orchestrator has access to structured finance records for budgets, forecasts, and actuals, "
    "including account, business unit, and period metadata, as well as semantically indexed finance document chunks "
    "for narrative and contextual explanations."
)



#write a method that calls openAI to rewrite a a user question, and gets a more retrieval friendly version of the question, along with key metadata facts from the question as a seperate collection of key facts. The method should return the rewritten question and the key facts as a list of strings.
@router.post("/rewrite-query")
def rewrite_query_with_key_facts(
        self,
        user_question: str,
        api_base_url: str,
) -> tuple[str, list[str]]:
    if not user_question.strip():
        raise ValueError("User question cannot be empty.")

    client = _get_openai_client(api_base_url=api_base_url)
    model = OpenAIChatCompletionsModel(model=OPENAI_MODEL, openai_client=client)

    prompt = (
        f"""Rewrite the following user question to be more retrieval-friendly and extract key metadata facts:\n\n
        User question: {user_question}\n\n
        Return the rewritten question and a list of key facts as separate items.
        Output format:

        Return only valid JSON.

        Do not return Markdown, code fences, comments, explanations, introductory text, or trailing text.

        Return a JSON object with exactly these properties:

        rewritten_question
        metadata_facts

        Use this exact structure:

        {{
        "rewritten_question": "string",
        "metadata_facts": {{
            "key": "value"
            }}
        }}"""
    )

    response = model.complete(prompt=prompt, temperature=0.0, max_tokens=256)
    output_text = response.get("choices", [{}])[0].get("message", {}).get("content", "").strip()

    # Assuming the output is in the format: "Rewritten Question: ...\nKey Facts: ..."
    rewritten_question = ""
    metadata_facts: list[str] = []

    if "Rewritten Question:" in output_text and "Key Facts:" in output_text:
        parts = output_text.split("Key Facts:")
        rewritten_question = parts[0].replace("Rewritten Question:", "").strip()
        key_facts_text = parts[1].strip()
        metadata_facts = [fact.strip() for fact in key_facts_text.split("\n") if fact.strip()]

    return rewritten_question, metadata_facts

@router.post("/rerank_query_results")
def rerank_context_evidence(
    question: str,
    rewritten_queries: list[str],
    expanded_terms: list[str],
    candidate_chunks: list[dict[str, Any]],
    client: Any | None = None,
    n_results: int = 5,
) -> list[dict[str, Any]]:
    if not candidate_chunks:
        return []

    evidence_items: list[dict[str, Any]] = []
    for index, chunk in enumerate(candidate_chunks):
        chunk_id = str(chunk.get("id") or chunk.get("chunk_id") or f"chunk-{index + 1}")
        text = str(chunk.get("document") or chunk.get("text") or chunk.get("content") or "")
        text = re.sub(r"\s+", " ", text).strip()
        preview = text[:1600] if len(text) > 1600 else text
        evidence_items.append(
            {
                "rank": index + 1,
                "id": chunk_id,
                "chunk_id": chunk_id,
                "document": preview,
                "metadata": chunk.get("metadata") or {},
            }
        )

    prompt = f"""
You are reranking finance evidence for a user question.
You are provided with a question and a list of relevant chunks of text from a query of a knowledge base.
The chunks are provided in the order they were retrieved; this should be approximately ordered by relevance, but you may be able to improve on that.
You must rank order the provided chunks by relevance to the question, with the most relevant chunk first.
Reply only with the list of ranked chunk ids, nothing else. Include all the chunk ids you are provided with, reranked.


User question:
{question}

Retrieved chunks:
{json.dumps(evidence_items, ensure_ascii=False)}

Return JSON with exactly this shape:
{{"ranked_ids": ["chunk-id-1", "chunk-id-2", ...], "reasons": ["why chunk-1 is useful", "why chunk-2 is useful", ...]}}

Rules:
- Order the list from most useful to least useful.
- Prefer evidence that directly answers the question.
- Keep the most relevant chunks near the top and filter weak or irrelevant ones to the bottom.
"""

    try:
        ranking_client = client or _get_openai_client()

        async def _generate_ranking() -> str:
            if hasattr(ranking_client, "responses"):
                try:
                    response = ranking_client.responses.create(
                        model=OPENAI_MODEL,
                        input=prompt,
                        temperature=0.0,
                        max_output_tokens=400,
                    )
                    if hasattr(response, "__await__"):
                        response = await response
                    return str(getattr(response, "output_text", "") or "")
                except Exception:
                    pass

            response = ranking_client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You rank finance evidence by usefulness for the user question."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.0,
                max_tokens=400,
            )
            if hasattr(response, "__await__"):
                response = await response
            return str(getattr(response.choices[0].message, "content", "") or "")

        content = asyncio.run(_generate_ranking())
        parsed = json.loads(content)
        ranked_ids = parsed.get("ranked_ids", [])
        reasons = parsed.get("reasons", [])

        ordered: list[dict[str, Any]] = []
        for index, chunk_id in enumerate(ranked_ids):
            matching = next((item for item in evidence_items if item["chunk_id"] == str(chunk_id)), None)
            if matching is None:
                continue
            ordered.append({**matching, "reason": reasons[index] if index < len(reasons) else ""})

        if ordered:
            return ordered[:n_results]
    except Exception:
        pass

    def _score(item: dict[str, Any]) -> tuple[int, int]:
        text = item.get("document", "").lower()
        tokens = set(re.findall(r"[a-z0-9]+", question.lower()))
        overlap = sum(1 for token in tokens if token in text)
        return (overlap, -item["rank"])

    ranked = sorted(evidence_items, key=_score, reverse=True)
    return [
        {
            **item,
            "reason": "Fallback heuristic ranking based on lexical overlap with the question.",
        }
        for item in ranked[:n_results]
    ]




# @router.post("/ask")
# def orchestrate_question(payload: OrchestratorRequest) -> StreamingResponse:
#     user_question = payload.user_question.strip()
#     if not user_question:
#         raise HTTPException(status_code=422, detail="user_question cannot be empty")

#     def event_stream() -> AsyncIterator[bytes]:
#         yield _event_stream_line(
#             "status",
#             {
#                 "stage": "received",
#                 "message": "Request received by orchestrator.",
#                 "user_question": user_question,
#             },
#         ).encode("utf-8")

#         try:
#             yield _event_stream_line(
#                 "status",
#                 {
#                     "stage": "routing",
#                     "message": "Routing your question to the best API tool.",
#                 },
#             ).encode("utf-8")

#             route = select_route_for_query(user_question)
#             primary_result: dict[str, Any] | None = None
#             secondary_result: dict[str, Any] | None = None

#             needs_context = _heuristic_router.needs_context(user_question)
#             needs_metric = _heuristic_router.needs_metric(user_question)

#             yield _event_stream_line(
#                 "status",
#                 {
#                     "stage": "tool_selected",
#                     "message": "Selected the most appropriate tool.",
#                     "tool_name": route.get("tool_name"),
#                     "tool_method": route.get("method"),
#                     "tool_path": route.get("path"),
#                     "arguments": route.get("arguments", {}),
#                     "intent": route.get("intent"),
#                 },
#             ).encode("utf-8")

#             if needs_context and needs_metric:
#                 yield _event_stream_line(
#                     "status",
#                     {
#                         "stage": "hybrid_execution",
#                         "message": "Your question needs both Chroma context and structured financial data, so the orchestrator is combining both sources.",
#                     },
#                 ).encode("utf-8")

#                 primary_route = route
#                 primary_result = invoke_tool_route(payload.api_base_url, primary_route)

#                 if "/chroma/" not in str(primary_route.get("path", "")):
#                     chroma_route = _heuristic_router.build_chroma_context_route(user_question)
#                     secondary_result = invoke_tool_route(payload.api_base_url, chroma_route)
#                 else:
#                     structured_route = _heuristic_router.build_structured_finance_route(user_question)
#                     secondary_result = invoke_tool_route(payload.api_base_url, structured_route)

#                 final_response = _heuristic_router.combine_final_response(primary_result, secondary_result)
#                 final_status_code = primary_result.get("status_code")
#             else:
#                 yield _event_stream_line(
#                     "status",
#                     {
#                         "stage": "executing",
#                         "message": "Executing the selected tool through the backend API.",
#                     },
#                 ).encode("utf-8")

#                 primary_result = invoke_tool_route(payload.api_base_url, route)
#                 final_response = format_tool_response(primary_result)
#                 final_status_code = primary_result.get("status_code")

#             yield _event_stream_line(
#                 "status",
#                 {
#                     "stage": "completed",
#                     "message": "Tool execution completed.",
#                     "status_code": final_status_code,
#                 },
#             ).encode("utf-8")

#             yield _event_stream_line(
#                 "final",
#                 {
#                     "final_response": final_response,
#                     "tool_name": route.get("tool_name"),
#                     "intent": route.get("intent"),
#                     "status_code": final_status_code,
#                 },
#             ).encode("utf-8")
#         except HTTPException as exc:
#             yield _event_stream_line(
#                 "error",
#                 {
#                     "message": exc.detail,
#                 },
#             ).encode("utf-8")
#         except Exception as exc:
#             yield _event_stream_line(
#                 "error",
#                 {
#                     "message": f"Unexpected orchestrator error: {exc}",
#                 },
#             ).encode("utf-8")

#     return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/welcome")
def orchestrator_welcome() -> JSONResponse:
    return JSONResponse(
        {
            "welcome_message": WELCOME_MESSAGE,
            "data_overview": DATA_OVERVIEW,
        }
    )


@router.post("/ask-openai")
async def orchestrate_with_openai_agents(payload: OrchestratorRequest):
    return StreamingResponse(_openAI_Orchestrator.orchestrate_new(payload), media_type="text/event-stream")

@router.get("/chunk-documents/{internal}")
async def chunk_documents(internal: bool): 
    return StreamingResponse(run_ingestion(internal=internal), media_type="text/event-stream")

async def run_ingestion(internal: bool = False) -> Any:

    repo_root = find_repo_root(Path.cwd())
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    financeDocs = repo_root / 'notebooks' / 'finance_docs'
    #print(os.getenv("OPENAI_API_KEY"))
    if internal:
        ingestor = Injestor(source_dir=financeDocs, model='gemma3:270m')
        print("Using local Ollama model")
    else:
        ingestor = Injestor(
            source_dir=financeDocs,
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            provider="openai",
            use_external_model=True,
            use_openai_embeddings=True
        )
        print("Using external OpenAI-compatible model via LiteLLM")

    yield event_stream_line(
        "status",
        {
            "stage": "document_chunking",
            "message": f"Request initiated to chunk available documents using model - {'gemma3:270m' if internal else os.getenv('OPENAI_MODEL', 'gpt-4o-mini')}.",
        },
    ).encode("utf-8")

    #print(f'Ingesting documents from: {financeDocs}')
    ingestion_result = await ingestor.ingest_documents()
    
    no_of_documents = len(ingestion_result)
    no_of_chunks = sum(result.chunk_count for result in ingestion_result)

    yield event_stream_line(
            "final",
            {
                "stage": "document_chunking",
                "message": f"Document ingestion complete. No of documents processed: {no_of_documents}, No of chunks created: {no_of_chunks}.",
            },
        ).encode("utf-8")

def find_repo_root(start: Path) -> Path:
    start = start.resolve()
    for candidate in [start, *start.parents]:
        if (candidate / 'services').exists() and (candidate / 'requirements.txt').exists():
            return candidate
    return start