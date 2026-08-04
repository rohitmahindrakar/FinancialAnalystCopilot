from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from typing import Any, AsyncIterator

from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from agents import Agent, AgentOutputSchema, ModelSettings, OpenAIChatCompletionsModel, Runner, function_tool
from openai import AsyncOpenAI

from services.orchestration import format_tool_response, invoke_tool_route, select_route_for_query
from services.routers.tool_registry import OrchestratorToolRegistry, guarded_execute_backend_tool

load_dotenv()

logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s"))
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

router = APIRouter(prefix="/orchestrator", tags=["orchestrator"])
ORCHESTRATOR_TOOL_REGISTRY = OrchestratorToolRegistry()

CONTEXT_HINTS = {
    "context",
    "summary",
    "summarize",
    "document",
    "passage",
    "chunk",
    "background",
    "explain",
    "narrative",
    "why",
    "management commentary",
    "meeting",
    "discussion",
    "transcript",
}

METRIC_HINTS = {
    "metric",
    "metrics",
    "actual",
    "actuals",
    "budget",
    "budgets",
    "forecast",
    "forecasts",
    "kpi",
    "kpis",
    "variance",
    "revenue",
    "margin",
    "growth",
    "amount",
    "total",
    "compare",
    "performance",
    "ratio",
    "period",
}

class OrchestratorRequest(BaseModel):
    user_question: str = Field(..., min_length=1)
    api_base_url: str = Field(default="http://127.0.0.1:8000")
    conversation_history: list[dict[str, str]] = Field(default_factory=list)


class OpenAIPlanResult(BaseModel):
    tools: list[dict[str, Any]] = Field(default_factory=list)
    synthesis: str = Field(default="")
    complete: bool = Field(default=False)
    reasoning: str = Field(default="")


OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

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


def _event_stream_line(event: str, payload: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(payload)}\n\n"


def _tokenize(text: str) -> list[str]:
    return [token.lower() for token in re.findall(r"[a-zA-Z]+", text)]


def _needs_context(question: str) -> bool:
    tokens = set(_tokenize(question))
    return bool(tokens & CONTEXT_HINTS)


def _needs_metric(question: str) -> bool:
    tokens = set(_tokenize(question))
    return bool(tokens & METRIC_HINTS)


def _build_chroma_context_route(question: str) -> dict[str, Any]:
    return {
        "tool_name": "query_finance_chunks",
        "method": "POST",
        "path": "/chroma/query-finance",
        "description": "Query Chroma chunk collection for contextual passages.",
        "intent": "semantic_context_lookup",
        "arguments": {
            "query": question,
            "collection_name": "finance_docs_chunks",
            "n_results": 3,
        },
    }


def _build_structured_finance_route(question: str) -> dict[str, Any]:
    lower_question = question.lower()
    if "budget" in lower_question:
        path = "/finance/budgets"
        tool_name = "list_finance_budgets"
    elif "forecast" in lower_question:
        path = "/finance/forecasts"
        tool_name = "list_finance_forecasts"
    else:
        path = "/finance/actuals"
        tool_name = "list_finance_actuals"

    return {
        "tool_name": tool_name,
        "method": "GET",
        "path": path,
        "description": "Query the structured finance database for numeric facts and metrics.",
        "intent": "structured_financial_lookup",
        "arguments": {
            "limit": 5,
            "offset": 0,
        },
    }


def _combine_final_response(primary_result: dict[str, Any], secondary_result: dict[str, Any] | None = None) -> str:
    parts: list[str] = []
    parts.append("Structured finance response:\n" + format_tool_response(primary_result))

    if secondary_result is not None:
        parts.append("Chroma context response:\n" + format_tool_response(secondary_result))

    return "\n\n".join(parts)


def _guarded_execute_backend_tool(api_base_url: str, method: str, path: str, arguments: dict[str, Any], tool_name: str | None = None) -> dict[str, Any]:
    return guarded_execute_backend_tool(api_base_url, method, path, arguments, tool_name=tool_name)


_RETRIEVAL_CONTEXT: dict[str, dict[str, Any]] = {}


def _normalize_retrieval_key(query: str) -> str:
    return re.sub(r"\s+", " ", query.strip()).lower()


def _get_retrieval_context(query: str) -> dict[str, Any]:
    key = _normalize_retrieval_key(query)
    context = _RETRIEVAL_CONTEXT.get(key)
    if context is None:
        context = {
            "query": query.strip(),
            "rewritten_queries": [],
            "expanded_terms": [],
            "candidate_chunks": [],
            "ranked_chunks": [],
        }
        _RETRIEVAL_CONTEXT[key] = context
    return context


def _update_retrieval_context(query: str, **updates: Any) -> dict[str, Any]:
    context = _get_retrieval_context(query)
    for key, value in updates.items():
        if value is not None:
            context[key] = value
    return context


def _dedupe_candidate_chunks(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen_ids: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for chunk in chunks:
        chunk_id = str(chunk.get("id") or chunk.get("chunk_id") or "")
        if not chunk_id:
            chunk_id = json.dumps(
                {
                    "document": str(chunk.get("document") or chunk.get("text") or chunk.get("content") or ""),
                    "metadata": chunk.get("metadata") or {},
                },
                sort_keys=True,
            )
        if chunk_id in seen_ids:
            continue
        seen_ids.add(chunk_id)
        deduped.append(chunk)
    return deduped


def _collect_context_chunks(context: dict[str, Any], candidate_chunks: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    if candidate_chunks:
        chunks.extend(candidate_chunks)
    for chunk in context.get("candidate_chunks", []) or []:
        chunks.append(chunk)
    for chunk in context.get("ranked_chunks", []) or []:
        chunks.append(chunk)
    return _dedupe_candidate_chunks(chunks)


def _rank_context_evidence(
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

User question:
{question}

Rewritten queries:
{json.dumps(rewritten_queries, ensure_ascii=False)}

Expanded terms:
{json.dumps(expanded_terms, ensure_ascii=False)}

Candidate evidence:
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


@function_tool(name_override="list_finance_actuals", strict_mode=False)
def list_finance_actuals(limit: int = 5, offset: int = 0) -> dict[str, Any]:
    """Fetch structured finance actuals from the local finance API."""
    return _guarded_execute_backend_tool(
        api_base_url=os.getenv("API_BASE_URL", "http://127.0.0.1:8000"),
        method="GET",
        path="/finance/actuals",
        arguments={"limit": limit, "offset": offset},
    )


@function_tool(name_override="list_finance_budgets", strict_mode=False)
def list_finance_budgets(limit: int = 5, offset: int = 0) -> dict[str, Any]:
    """Fetch structured finance budget records from the local finance API."""
    return _guarded_execute_backend_tool(
        api_base_url=os.getenv("API_BASE_URL", "http://127.0.0.1:8000"),
        method="GET",
        path="/finance/budgets",
        arguments={"limit": limit, "offset": offset},
    )


@function_tool(name_override="list_finance_forecasts", strict_mode=False)
def list_finance_forecasts(limit: int = 5, offset: int = 0) -> dict[str, Any]:
    """Fetch structured finance forecast records from the local finance API."""
    return _guarded_execute_backend_tool(
        api_base_url=os.getenv("API_BASE_URL", "http://127.0.0.1:8000"),
        method="GET",
        path="/finance/forecasts",
        arguments={"limit": limit, "offset": offset},
    )


@function_tool(name_override="query_finance_chunks", strict_mode=False)
def query_finance_chunks(query: str, collection_name: str = "finance_docs_chunks", n_results: int = 3) -> dict[str, Any]:
    """Fetch semantically relevant finance document chunks from the Chroma collection."""
    return _guarded_execute_backend_tool(
        api_base_url=os.getenv("API_BASE_URL", "http://127.0.0.1:8000"),
        method="POST",
        path="/chroma/query-finance",
        arguments={
            "query": query,
            "collection_name": collection_name,
            "n_results": n_results,
        },
    )


@function_tool(name_override="rewrite_query", strict_mode=False)
def rewrite_query(query: str, collection_name: str = "finance_docs_chunks", n_results: int = 5) -> dict[str, Any]:
    """Rewrite the user question into clearer retrieval queries and gather candidate chunks for each rewrite."""
    normalized_query = query.strip()
    rewritten_queries = [
        normalized_query,
        f"{normalized_query} financial context",
        f"{normalized_query} company performance",
    ]

    try:
        if OPENAI_API_KEY:
            client = AsyncOpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_API_BASE)

            async def _generate_rewrites() -> list[str]:
                response = await client.chat.completions.create(
                    model=OPENAI_MODEL,
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You rewrite finance questions into concise, retrieval-friendly search queries. "
                                "Return exactly 3 short queries, one per line, without bullets or extra commentary."
                            ),
                        },
                        {
                            "role": "user",
                            "content": normalized_query,
                        },
                    ],
                    temperature=0.0,
                    max_tokens=200,
                )
                content = str(response.choices[0].message.content or "").strip()
                lines = [line.strip() for line in content.splitlines() if line.strip()]
                return lines[:3] if lines else rewritten_queries[:3]

            generated_queries = asyncio.run(_generate_rewrites())
            if generated_queries:
                rewritten_queries = [
                    normalized_query,
                    *[query_value for query_value in generated_queries if query_value and query_value != normalized_query],
                ]
    except Exception:
        rewritten_queries = [
            normalized_query,
            f"{normalized_query} financial context",
            f"{normalized_query} company performance",
        ]

    candidate_chunks: list[dict[str, Any]] = []
    query_variants: list[str] = []
    for variant in rewritten_queries[:3]:
        if not variant.strip():
            continue
        response = _guarded_execute_backend_tool(
            api_base_url=os.getenv("API_BASE_URL", "http://127.0.0.1:8000"),
            method="POST",
            path="/chroma/query-finance",
            arguments={
                "query": variant,
                "collection_name": collection_name,
                "n_results": max(n_results, 3),
            },
        )
        query_variants.append(variant)
        candidate_chunks.extend(response.get("results", []) or [])

    ordered_chunks = _dedupe_candidate_chunks(candidate_chunks)[:n_results]
    repeated_queries = [variant for variant in rewritten_queries if variant.strip()]
    _update_retrieval_context(
        query,
        rewritten_queries=repeated_queries,
        candidate_chunks=ordered_chunks,
    )

    return {
        "collection_name": collection_name,
        "query": normalized_query,
        "query_variants": query_variants,
        "n_results": n_results,
        "rewritten_queries": repeated_queries,
        "results": ordered_chunks,
        "rerank": False,
    }


@function_tool(name_override="expand_query", strict_mode=False)
def expand_query(query: str, collection_name: str = "finance_docs_chunks", n_results: int = 5) -> dict[str, Any]:
    """Expand the original query with finance-domain synonyms and related concepts to improve recall."""
    expanded_terms = [
        query.strip(),
        "financials",
        "performance",
        "forecast",
        "budget",
        "actual",
        "variance",
        "revenue",
        "margin",
        "guidance",
    ]
    expanded_query = " ".join(dict.fromkeys([query.strip(), *expanded_terms]))
    context = _get_retrieval_context(query)
    response = _guarded_execute_backend_tool(
        api_base_url=os.getenv("API_BASE_URL", "http://127.0.0.1:8000"),
        method="POST",
        path="/chroma/query-finance",
        arguments={
            "query": expanded_query,
            "collection_name": collection_name,
            "n_results": max(n_results, 3),
            "expanded_terms": expanded_terms,
            "rewritten_queries": context.get("rewritten_queries", []),
        },
    )
    expanded_chunks = _dedupe_candidate_chunks(list(response.get("results", []) or []))[:n_results]
    combined_chunks = _dedupe_candidate_chunks([*(context.get("candidate_chunks", []) or []), *expanded_chunks])
    _update_retrieval_context(
        query,
        expanded_terms=[term for term in expanded_terms if term and term.strip()],
        candidate_chunks=combined_chunks,
    )

    return {
        "collection_name": collection_name,
        "query": query,
        "query_variants": [expanded_query],
        "n_results": n_results,
        "expanded_terms": [term for term in expanded_terms if term and term.strip()],
        "rewritten_queries": context.get("rewritten_queries", []),
        "results": combined_chunks[:n_results],
        "rerank": False,
    }


@function_tool(name_override="rerank_query_results", strict_mode=False)
def rerank_query_results(query: str, collection_name: str = "finance_docs_chunks", n_results: int = 5) -> dict[str, Any]:
    """Re-rank the candidate chunks gathered from rewritten and expanded retrieval steps so the most relevant passages come first."""
    context = _get_retrieval_context(query)
    candidate_chunks = _collect_context_chunks(context)
    if not candidate_chunks:
        response = _guarded_execute_backend_tool(
            api_base_url=os.getenv("API_BASE_URL", "http://127.0.0.1:8000"),
            method="POST",
            path="/chroma/query-finance",
            arguments={
                "query": query,
                "collection_name": collection_name,
                "n_results": max(n_results, 3),
                "rerank": True,
            },
        )
        candidate_chunks = list(response.get("results", []) or [])

    ranked_chunks = _rank_context_evidence(
        question=query,
        rewritten_queries=context.get("rewritten_queries", []),
        expanded_terms=context.get("expanded_terms", []),
        candidate_chunks=candidate_chunks,
        n_results=n_results,
    )
    _update_retrieval_context(query, ranked_chunks=ranked_chunks)

    return {
        "collection_name": collection_name,
        "query": query,
        "n_results": n_results,
        "rewritten_queries": context.get("rewritten_queries", []),
        "expanded_terms": context.get("expanded_terms", []),
        "results": ranked_chunks,
        "rerank": True,
    }


def _get_openai_client() -> AsyncOpenAI:
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY is not configured in the .env file.")

    return AsyncOpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_API_BASE)


def _build_openai_agent(api_base_url: str) -> Agent:
    client = _get_openai_client()
    model = OpenAIChatCompletionsModel(model=OPENAI_MODEL, openai_client=client)
    return Agent(
        name="finance-agent-orchestrator",
        model=model,
        instructions=(
            "You are a secure finance orchestration planner. "
            "Use only the supplied tools to answer the user's question. "
            "First decide whether the current evidence is sufficient to answer the user's question. "
            "If the answer is already supported by the earlier tool results, set 'complete' to true and return no more tools. "
            "If more evidence is needed, set 'complete' to false and propose the next tool calls required to answer the question. "
            "Then return a JSON object with exactly four keys: 'tools', 'synthesis', 'complete', and 'reasoning'. "
            "The 'tools' value must be an ordered list of tool calls. "
            "Each tool entry must contain 'tool_name', 'path', 'method', and 'arguments'. "
            "This assistant has access to structured finance records for budgets, forecasts, actuals, account metadata, business unit information, and period definitions, "
            "as well as semantically indexed finance document chunks for narrative and contextual explanations. "
            "Use query_finance_chunks for document context, summaries, narrative background, and passage-like explanations. "
            "For context-heavy questions, use rewrite_query first to obtain rewritten search variants and candidate chunks, then expand_query to broaden coverage, and finally rerank_query_results to order the evidence before synthesis. "
            "Use list_finance_actuals, list_finance_budgets, or list_finance_forecasts for structured numerical data, metrics, and financial records. "
            "Do not invent tool paths or call any tool outside the approved finance and Chroma routes. "
            "The 'synthesis' field should be a short natural-language description of how the answer should be assembled from the selected tool results."
        ),
        model_settings=ModelSettings(temperature=0.0, max_tokens=512),
        output_type=AgentOutputSchema(OpenAIPlanResult, strict_json_schema=False),
        tools=ORCHESTRATOR_TOOL_REGISTRY.tools,
    )


def _run_openai_agent_orchestration(
    user_question: str,
    api_base_url: str,
    prior_tool_results: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    agent = _build_openai_agent(api_base_url=api_base_url)
    prompt = user_question
    if prior_tool_results:
        prompt = (
            f"User question: {user_question}\n\n"
            "You have already gathered the following tool results from earlier rounds:\n"
            f"{json.dumps(prior_tool_results, indent=2)}\n\n"
            "Use those results to decide whether you can answer now or need more tool calls. "
            "If the evidence is sufficient, return complete=true with no further tools. "
            "If more evidence is needed, return complete=false and the next tool calls required."
        )

    result = Runner.run_sync(
        agent,
        prompt,
        max_turns=8,
    )
    final_output = result.final_output

    if isinstance(final_output, OpenAIPlanResult):
        return final_output.model_dump()

    if isinstance(final_output, dict):
        normalized = dict(final_output)
        if "complete" not in normalized:
            normalized["complete"] = bool(normalized.get("complete", False)) or not bool(normalized.get("tools"))
        if "reasoning" not in normalized:
            normalized["reasoning"] = ""
        return normalized

    if isinstance(final_output, str):
        stripped = final_output.strip()
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            return {"tools": [], "synthesis": stripped, "complete": False, "reasoning": ""}
        if isinstance(parsed, dict):
            if "complete" not in parsed:
                parsed["complete"] = bool(parsed.get("complete", False)) or not bool(parsed.get("tools"))
            if "reasoning" not in parsed:
                parsed["reasoning"] = ""
            return parsed

    return {"tools": [], "synthesis": str(final_output), "complete": False}


def _execute_openai_orchestration_loop(
    user_question: str,
    planner: Any,
    executor: Any,
    max_rounds: int = 4,
) -> dict[str, Any]:
    tool_results: list[dict[str, Any]] = []
    history: list[dict[str, Any]] = []
    last_plan: dict[str, Any] | None = None

    for round_index in range(max_rounds):
        logger.info("OpenAI orchestration round %s/%s", round_index + 1, max_rounds)
        plan = planner(user_question, tool_results)
        last_plan = plan
        history.append({"round": round_index + 1, "plan": plan})

        reasoning = str(plan.get("reasoning", "") or "")
        if reasoning:
            logger.info("Planner reasoning for round %s: %s", round_index + 1, reasoning)

        tool_calls = list(plan.get("tools", []) or [])
        if not tool_calls:
            logger.info("No further tool calls proposed; stopping orchestration loop.")
            break

        logger.info("Planner proposed %d tool call(s) in round %s.", len(tool_calls), round_index + 1)
        for call in tool_calls:
            logger.info(
                "Executing proposed tool call: tool_name=%s method=%s path=%s arguments=%s",
                call.get("tool_name"),
                call.get("method"),
                call.get("path"),
                call.get("arguments"),
            )
            result = executor(call)
            tool_results.append(result)

        if plan.get("complete"):
            logger.info("Planner marked the response as complete; stopping orchestration loop.")
            break

    return {
        "completed": bool(last_plan and last_plan.get("complete")),
        "tool_results": tool_results,
        "history": history,
        "last_plan": last_plan or {},
    }


def _format_conversation_history(history: list[dict[str, str]]) -> str:
    if not history:
        return "No prior conversation history provided."

    lines: list[str] = []
    for entry in history:
        role = str(entry.get("role", "user")).strip() or "user"
        content = str(entry.get("content", "")).strip()
        if content:
            lines.append(f"{role.title()}: {content}")

    return "\n".join(lines)


def _extract_ranked_evidence(tool_results: list[dict[str, Any]]) -> str:
    evidence_sections: list[str] = []
    ranked_results = [result for result in tool_results if isinstance(result, dict) and result.get("rerank") is True and result.get("results")]

    if ranked_results:
        for result in ranked_results:
            chunks = result.get("results", []) or []
            if not chunks:
                continue
            lines = []
            for index, chunk in enumerate(chunks, start=1):
                document = str(chunk.get("document") or chunk.get("text") or chunk.get("content") or "")
                document = re.sub(r"\s+", " ", document).strip()
                if not document:
                    continue
                reason = str(chunk.get("reason") or "")
                if reason:
                    lines.append(f"{index}. {document} [reason: {reason}]")
                else:
                    lines.append(f"{index}. {document}")
            if lines:
                evidence_sections.append("Ranked evidence (most relevant first):\n" + "\n".join(lines))

    if evidence_sections:
        return "\n\n".join(evidence_sections)

    fallback_results = [result for result in tool_results if isinstance(result, dict) and result.get("results")]
    if fallback_results:
        lines: list[str] = []
        for result in fallback_results[:1]:
            for index, chunk in enumerate(result.get("results", []) or [], start=1):
                document = str(chunk.get("document") or chunk.get("text") or chunk.get("content") or "")
                document = re.sub(r"\s+", " ", document).strip()
                if document:
                    lines.append(f"{index}. {document}")
        if lines:
            return "Retrieved evidence:\n" + "\n".join(lines)

    return ""


def _build_final_synthesis_prompt(
    user_question: str,
    conversation_history: list[dict[str, str]],
    tool_results: list[dict[str, Any]],
    plan: dict[str, Any],
) -> str:
    history_text = _format_conversation_history(conversation_history)
    results_text = "\n\n".join(json.dumps(result, indent=2) for result in tool_results)
    tool_plan = json.dumps(plan.get("tools", []), indent=2)
    ranked_evidence_text = _extract_ranked_evidence(tool_results)

    return (
        "You are a finance assistant. Use the tool execution results as the source of truth for the answer. "
        "Prioritize the ranked evidence section when it is present, and use the top-ranked chunks as the primary support for your answer. "
        "Summarize the current user question only using the returned tool data and the prior conversation context. "
        "If there is no supporting data in the tool outputs, say so clearly and avoid inventing numbers.\n\n"
        f"Current user question: {user_question}\n\n"
        f"Conversation history:\n{history_text}\n\n"
        f"Planner tool plan:\n{tool_plan}\n\n"
        f"Tool execution results:\n{results_text}\n\n"
        f"Ranked evidence:\n{ranked_evidence_text}\n\n"
        "Return only a concise, well-structured final answer suitable for the UI."
    )


def _synthesize_openai_final_response(
    user_question: str,
    conversation_history: list[dict[str, str]],
    tool_results: list[dict[str, Any]],
    plan: dict[str, Any],
) -> str:
    client = _get_openai_client()
    prompt = _build_final_synthesis_prompt(user_question, conversation_history, tool_results, plan)

    async def _generate() -> str:
        response = await client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a careful finance assistant. Base the answer only on the tool results and previous chat context. "
                        "Avoid fabricating numbers or facts."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            temperature=0.0,
            max_tokens=512,
        )
        return str(response.choices[0].message.content or "")

    return asyncio.run(_generate())


@router.post("/ask")
def orchestrate_question(payload: OrchestratorRequest) -> StreamingResponse:
    user_question = payload.user_question.strip()
    if not user_question:
        raise HTTPException(status_code=422, detail="user_question cannot be empty")

    def event_stream() -> AsyncIterator[bytes]:
        yield _event_stream_line(
            "status",
            {
                "stage": "received",
                "message": "Request received by orchestrator.",
                "user_question": user_question,
            },
        ).encode("utf-8")

        try:
            yield _event_stream_line(
                "status",
                {
                    "stage": "routing",
                    "message": "Routing your question to the best API tool.",
                },
            ).encode("utf-8")

            route = select_route_for_query(user_question)
            primary_result: dict[str, Any] | None = None
            secondary_result: dict[str, Any] | None = None

            needs_context = _needs_context(user_question)
            needs_metric = _needs_metric(user_question)

            yield _event_stream_line(
                "status",
                {
                    "stage": "tool_selected",
                    "message": "Selected the most appropriate tool.",
                    "tool_name": route.get("tool_name"),
                    "tool_method": route.get("method"),
                    "tool_path": route.get("path"),
                    "arguments": route.get("arguments", {}),
                    "intent": route.get("intent"),
                },
            ).encode("utf-8")

            if needs_context and needs_metric:
                yield _event_stream_line(
                    "status",
                    {
                        "stage": "hybrid_execution",
                        "message": "Your question needs both Chroma context and structured financial data, so the orchestrator is combining both sources.",
                    },
                ).encode("utf-8")

                primary_route = route
                primary_result = invoke_tool_route(payload.api_base_url, primary_route)

                if "/chroma/" not in str(primary_route.get("path", "")):
                    chroma_route = _build_chroma_context_route(user_question)
                    secondary_result = invoke_tool_route(payload.api_base_url, chroma_route)
                else:
                    structured_route = _build_structured_finance_route(user_question)
                    secondary_result = invoke_tool_route(payload.api_base_url, structured_route)

                final_response = _combine_final_response(primary_result, secondary_result)
                final_status_code = primary_result.get("status_code")
            else:
                yield _event_stream_line(
                    "status",
                    {
                        "stage": "executing",
                        "message": "Executing the selected tool through the backend API.",
                    },
                ).encode("utf-8")

                primary_result = invoke_tool_route(payload.api_base_url, route)
                final_response = format_tool_response(primary_result)
                final_status_code = primary_result.get("status_code")

            yield _event_stream_line(
                "status",
                {
                    "stage": "completed",
                    "message": "Tool execution completed.",
                    "status_code": final_status_code,
                },
            ).encode("utf-8")

            yield _event_stream_line(
                "final",
                {
                    "final_response": final_response,
                    "tool_name": route.get("tool_name"),
                    "intent": route.get("intent"),
                    "status_code": final_status_code,
                },
            ).encode("utf-8")
        except HTTPException as exc:
            yield _event_stream_line(
                "error",
                {
                    "message": exc.detail,
                },
            ).encode("utf-8")
        except Exception as exc:
            yield _event_stream_line(
                "error",
                {
                    "message": f"Unexpected orchestrator error: {exc}",
                },
            ).encode("utf-8")

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/welcome")
def orchestrator_welcome() -> JSONResponse:
    return JSONResponse(
        {
            "welcome_message": WELCOME_MESSAGE,
            "data_overview": DATA_OVERVIEW,
        }
    )


@router.post("/ask-openai")
def orchestrate_with_openai_agents(payload: OrchestratorRequest) -> StreamingResponse:
    user_question = payload.user_question.strip()
    if not user_question:
        logger.warning("Received an empty user question for OpenAI orchestrator.")
        raise HTTPException(status_code=422, detail="user_question cannot be empty")

    logger.info("OpenAI orchestrator request received for question: %s", user_question)

    def event_stream() -> AsyncIterator[bytes]:
        yield _event_stream_line(
            "status",
            {
                "stage": "received",
                "message": "Request received by OpenAI Agents orchestrator.",
                "user_question": user_question,
            },
        ).encode("utf-8")

        try:
            yield _event_stream_line(
                "status",
                {
                    "stage": "planning",
                    "message": "Calling the OpenAI Agents SDK to select the correct tool list for the question.",
                },
            ).encode("utf-8")

            logger.info("Starting iterative OpenAI planning loop for question: %s", user_question)

            def planner(question: str, prior_results: list[dict[str, Any]]) -> dict[str, Any]:
                plan = _run_openai_agent_orchestration(
                    question,
                    payload.api_base_url,
                    prior_tool_results=prior_results,
                )
                plan["prior_tool_results"] = prior_results
                return plan

            def executor(call: dict[str, Any]) -> dict[str, Any]:
                method = str(call.get("method", "GET")).upper()
                path = str(call.get("path", ""))
                tool_name = str(call.get("tool_name") or "")
                arguments = dict(call.get("arguments") or {})
                logger.info("Executing tool call: tool_name=%s method=%s path=%s arguments=%s", tool_name, method, path, arguments)
                result = _guarded_execute_backend_tool(payload.api_base_url, method, path, arguments, tool_name=tool_name)
                logger.info("Tool execution completed: tool_name=%s status_code=%s", tool_name, result.get("status_code"))
                return result

            tool_results: list[dict[str, Any]] = []
            history: list[dict[str, Any]] = []
            last_plan: dict[str, Any] | None = None
            tool_calls: list[dict[str, Any]] = []

            for round_index in range(4):
                logger.info("OpenAI orchestration round %s/%s", round_index + 1, 4)
                plan = planner(user_question, tool_results)
                last_plan = plan
                history.append({"round": round_index + 1, "plan": plan})

                reasoning = str(plan.get("reasoning", "") or "")
                if reasoning:
                    logger.info("Planner reasoning for round %s: %s", round_index + 1, reasoning)
                    yield _event_stream_line(
                        "status",
                        {
                            "stage": "planning_update",
                            "message": "Planner updated its reasoning for the next step.",
                            "round": round_index + 1,
                            "reasoning": reasoning,
                            "complete": bool(plan.get("complete", False)),
                        },
                    ).encode("utf-8")

                round_tool_calls = list(plan.get("tools", []) or [])
                if not round_tool_calls:
                    logger.info("No further tool calls proposed; stopping orchestration loop.")
                    break

                tool_calls.extend(round_tool_calls)
                logger.info("Planner proposed %d tool call(s) in round %s.", len(round_tool_calls), round_index + 1)
                for call in round_tool_calls:
                    method = str(call.get("method", "GET")).upper()
                    path = str(call.get("path", ""))
                    tool_name = str(call.get("tool_name") or "")
                    arguments = dict(call.get("arguments") or {})
                    logger.info("Executing tool call: tool_name=%s method=%s path=%s arguments=%s", tool_name, method, path, arguments)
                    result = executor(call)
                    logger.info("Tool execution completed: tool_name=%s status_code=%s", tool_name, result.get("status_code"))
                    tool_results.append(result)

                if plan.get("complete"):
                    logger.info("Planner marked the response as complete; stopping orchestration loop.")
                    break

            synthesis = str(last_plan.get("synthesis", "")) if last_plan else ""
            logger.info("Iterative OpenAI planning completed. Total tool result(s): %d", len(tool_results))
            for round_entry in history:
                round_plan = round_entry.get("plan", {})
                logger.info("Round %s proposed %d tool call(s).", round_entry.get("round"), len(round_plan.get("tools", []) or []))

            yield _event_stream_line(
                "status",
                {
                    "stage": "tool_selected",
                    "message": "OpenAI Agents selected the tool list to execute.",
                    "tools": tool_calls,
                    "reasoning": last_plan.get("reasoning", "") if isinstance(last_plan, dict) else None,
                },
            ).encode("utf-8")

            logger.info("Synthesizing final response from %d tool result(s).", len(tool_results))
            final_response = _synthesize_openai_final_response(
                user_question=user_question,
                conversation_history=payload.conversation_history,
                tool_results=tool_results,
                plan=last_plan or {},
            )
            if not final_response.strip():
                logger.warning("Final synthesis returned no content; falling back to planner synthesis.")
                final_response = synthesis or "No tool results were returned by the OpenAI Agents orchestration path."

            yield _event_stream_line(
                "status",
                {
                    "stage": "completed",
                    "message": "OpenAI Agents orchestration completed.",
                },
            ).encode("utf-8")

            yield _event_stream_line(
                "final",
                {
                    "final_response": final_response,
                    "tools": tool_calls,
                    "status_code": 200,
                },
            ).encode("utf-8")
        except HTTPException as exc:
            logger.exception("OpenAI orchestrator raised an HTTP error for question: %s", user_question)
            yield _event_stream_line(
                "error",
                {
                    "message": exc.detail,
                },
            ).encode("utf-8")
        except Exception as exc:
            logger.exception("Unexpected OpenAI orchestrator error for question: %s", user_question)
            yield _event_stream_line(
                "error",
                {
                    "message": f"Unexpected OpenAI Agents orchestrator error: {exc}",
                },
            ).encode("utf-8")

    return StreamingResponse(event_stream(), media_type="text/event-stream")
