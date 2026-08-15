from __future__ import annotations

import os
from typing import Any, Callable

from agents import function_tool
from fastapi import HTTPException

from services.orchestration_old import invoke_tool_route


APP_ALLOWED_TOOL_PATHS = {
    "/health",
    "/metadata/tables",
    "/chroma/query-finance",
    "/accounts",
    "/accounts/{account_id}",
    "/business-units",
    "/business-units/{business_unit_id}",
    "/periods",
    "/periods/{period_id}",
    "/source-documents",
    "/source-documents/{source_document_id}",
    "/answer-citations",
    "/answer-citations/{citation_id}",
    "/document-chunks",
    "/document-chunks/{chunk_id}",
    "/finance/actuals",
    "/finance/actuals/{actual_id}",
    "/finance/budgets",
    "/finance/budgets/{budget_id}",
    "/finance/forecasts",
    "/finance/forecasts/{forecast_id}",
    "/kpis",
    "/kpis/{kpi_id}",
    "/queries",
    "/queries/{query_id}",
    "/feedback",
    "/feedback/{feedback_id}",
    "/calculation-results",
    "/calculation-results/{calculation_id}",
    "/evaluation-results",
    "/evaluation-results/{evaluation_result_id}",
    "/evaluation-test-cases",
    "/evaluation-test-cases/{test_case_id}",
}

OPENAI_TOOL_NAME_TO_ROUTE: dict[str, dict[str, str]] = {}


class OrchestratorToolRegistry:
    """Central registry of backend tools available to the orchestrator."""

    def __init__(self) -> None:
        self._tools_by_name: dict[str, Callable[..., dict[str, Any]]] = {}
        self.tools: list[Callable[..., dict[str, Any]]] = []
        self._register_default_tools()

    def _register_default_tools(self) -> None:
        for definition in ROUTER_TOOL_DEFINITIONS:
            self._register_tool(definition)

    def _register_tool(self, definition: dict[str, Any]) -> None:
        tool_name = str(definition["tool_name"])
        method = str(definition["method"]).upper()
        path = str(definition["path"])
        description = str(definition.get("description", ""))

        def tool(**kwargs: Any) -> dict[str, Any]:
            return guarded_execute_backend_tool(
                api_base_url=os.getenv("API_BASE_URL", "http://127.0.0.1:8000"),
                method=method,
                path=path,
                arguments=kwargs,
                tool_name=tool_name,
            )

        tool = function_tool(name_override=tool_name, strict_mode=False)(tool)
        tool.__name__ = tool_name
        tool.__doc__ = description
        self._tools_by_name[tool_name] = tool
        self.tools.append(tool)

    def get_tool(self, tool_name: str) -> Callable[..., dict[str, Any]] | None:
        return self._tools_by_name.get(tool_name)

    def get_tool_names(self) -> list[str]:
        return list(self._tools_by_name)


def _normalize_openai_tool_target(method: str, path: str, tool_name: str | None = None) -> tuple[str, str]:
    candidate = (tool_name or path or "").strip()
    mapping = OPENAI_TOOL_NAME_TO_ROUTE.get(candidate)
    if mapping:
        return mapping["method"], mapping["path"]

    normalized_path = path.strip()
    if normalized_path in APP_ALLOWED_TOOL_PATHS:
        return method.upper(), normalized_path

    if normalized_path.startswith("functions."):
        mapped = OPENAI_TOOL_NAME_TO_ROUTE.get(normalized_path)
        if mapped:
            return mapped["method"], mapped["path"]

    raise HTTPException(
        status_code=400,
        detail=f"Tool path '{normalized_path}' is not approved for agent execution.",
    )


def guarded_execute_backend_tool(api_base_url: str, method: str, path: str, arguments: dict[str, Any], tool_name: str | None = None) -> dict[str, Any]:
    normalized_method, normalized_path = _normalize_openai_tool_target(method, path, tool_name=tool_name)

    route = {
        "tool_name": tool_name or "agent_tool",
        "method": normalized_method,
        "path": normalized_path,
        "arguments": arguments,
        "description": "Securely executed internal tool selected by the OpenAI Agents SDK.",
        "intent": "agent_tool_call",
    }
    return invoke_tool_route(api_base_url, route)


ROUTER_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "tool_name": "health_check",
        "method": "GET",
        "path": "/health",
        "description": "Check API health and database connectivity.",
    },
    {
        "tool_name": "list_tables",
        "method": "GET",
        "path": "/metadata/tables",
        "description": "List available API metadata tables.",
    },
    {
        "tool_name": "query_finance_chunks",
        "method": "POST",
        "path": "/chroma/query-finance",
        "description": "Query the Chroma finance document index for contextual passages. After this tool is called, the tool - rerank_query_results, has to be called.",
        "arguments": {
            "query": "The search query for finance documents.",
            "metadata_filters": "Additional meta data filters, to search the knowledge base  on specific key value pairs.",
        },
    },
    {
        "tool_name": "rewrite_query",
        "method": "POST",
        "path": "/orchestrator/rewrite-query",
        "description": "Call this tool, if no data was returned when Chroma was queried to get finance data. This tool will rewrite a user question into clearer, more retrieval-friendly query, also will return metadata around facts in the question to be used when searching the knowledge base again. Once this tool is called to rewrite the question, the tool - query_finance_chunks, should be called again, to get the results from the knowledge base again.",
    },
    # {
    #     "tool_name": "expand_query",
    #     "method": "POST",
    #     "path": "/chroma/query-finance",
    #     "description": "Expand a user query with synonyms and related finance terms to improve recall and reduce vocabulary mismatch.",
    # },
    {
        "tool_name": "rerank_query_results",
        "method": "POST",
        "path": "/orchestrator/rerank-chunks",
        "description": "This tool must be called after a call to the tool - query_finance_chunks. This tool Re-ranks retrieved chunks from the tool - query_finance_chunks, so that the most contextually relevant finance passages appear first.",
    },
    {
        "tool_name": "list_accounts",
        "method": "GET",
        "path": "/accounts",
        "description": "List account records with optional filters.",
    },
    {
        "tool_name": "get_account",
        "method": "GET",
        "path": "/accounts/{account_id}",
        "description": "Retrieve a single account by account_id.",
    },
    {
        "tool_name": "create_account",
        "method": "POST",
        "path": "/accounts",
        "description": "Create a new account record.",
    },
    {
        "tool_name": "update_account",
        "method": "PUT",
        "path": "/accounts/{account_id}",
        "description": "Update an existing account record.",
    },
    {
        "tool_name": "delete_account",
        "method": "DELETE",
        "path": "/accounts/{account_id}",
        "description": "Delete an account by account_id.",
    },
    {
        "tool_name": "list_business_units",
        "method": "GET",
        "path": "/business-units",
        "description": "List business unit records with optional filters.",
    },
    {
        "tool_name": "get_business_unit",
        "method": "GET",
        "path": "/business-units/{business_unit_id}",
        "description": "Retrieve a business unit by business_unit_id.",
    },
    {
        "tool_name": "create_business_unit",
        "method": "POST",
        "path": "/business-units",
        "description": "Create a new business unit record.",
    },
    {
        "tool_name": "update_business_unit",
        "method": "PUT",
        "path": "/business-units/{business_unit_id}",
        "description": "Update a business unit record.",
    },
    {
        "tool_name": "delete_business_unit",
        "method": "DELETE",
        "path": "/business-units/{business_unit_id}",
        "description": "Delete a business unit by business_unit_id.",
    },
    {
        "tool_name": "list_periods",
        "method": "GET",
        "path": "/periods",
        "description": "List period records with optional filters.",
    },
    {
        "tool_name": "get_period",
        "method": "GET",
        "path": "/periods/{period_id}",
        "description": "Retrieve a period by period_id.",
    },
    {
        "tool_name": "create_period",
        "method": "POST",
        "path": "/periods",
        "description": "Create a new period record.",
    },
    {
        "tool_name": "update_period",
        "method": "PUT",
        "path": "/periods/{period_id}",
        "description": "Update a period record.",
    },
    {
        "tool_name": "delete_period",
        "method": "DELETE",
        "path": "/periods/{period_id}",
        "description": "Delete a period by period_id.",
    },
    {
        "tool_name": "list_source_documents",
        "method": "GET",
        "path": "/source-documents",
        "description": "List source documents with optional filters.",
    },
    {
        "tool_name": "get_source_document",
        "method": "GET",
        "path": "/source-documents/{source_document_id}",
        "description": "Retrieve a source document by source_document_id.",
    },
    {
        "tool_name": "create_source_document",
        "method": "POST",
        "path": "/source-documents",
        "description": "Create a new source document record.",
    },
    {
        "tool_name": "update_source_document",
        "method": "PUT",
        "path": "/source-documents/{source_document_id}",
        "description": "Update a source document record.",
    },
    {
        "tool_name": "delete_source_document",
        "method": "DELETE",
        "path": "/source-documents/{source_document_id}",
        "description": "Delete a source document by source_document_id.",
    },
    {
        "tool_name": "list_answer_citations",
        "method": "GET",
        "path": "/answer-citations",
        "description": "List answer citations with optional filters.",
    },
    {
        "tool_name": "get_answer_citation",
        "method": "GET",
        "path": "/answer-citations/{citation_id}",
        "description": "Retrieve an answer citation by citation_id.",
    },
    {
        "tool_name": "create_answer_citation",
        "method": "POST",
        "path": "/answer-citations",
        "description": "Create a new answer citation.",
    },
    {
        "tool_name": "update_answer_citation",
        "method": "PUT",
        "path": "/answer-citations/{citation_id}",
        "description": "Update an answer citation.",
    },
    {
        "tool_name": "delete_answer_citation",
        "method": "DELETE",
        "path": "/answer-citations/{citation_id}",
        "description": "Delete an answer citation by citation_id.",
    },
    {
        "tool_name": "list_document_chunks",
        "method": "GET",
        "path": "/document-chunks",
        "description": "List document chunks with optional filters.",
    },
    {
        "tool_name": "get_document_chunk",
        "method": "GET",
        "path": "/document-chunks/{chunk_id}",
        "description": "Retrieve a document chunk by chunk_id.",
    },
    {
        "tool_name": "create_document_chunk",
        "method": "POST",
        "path": "/document-chunks",
        "description": "Create a new document chunk.",
    },
    {
        "tool_name": "update_document_chunk",
        "method": "PUT",
        "path": "/document-chunks/{chunk_id}",
        "description": "Update a document chunk.",
    },
    {
        "tool_name": "delete_document_chunk",
        "method": "DELETE",
        "path": "/document-chunks/{chunk_id}",
        "description": "Delete a document chunk by chunk_id.",
    },
    {
        "tool_name": "list_finance_actuals",
        "method": "GET",
        "path": "/finance/actuals",
        "description": "List finance actual values with optional filters.",
    },
    {
        "tool_name": "get_finance_actual",
        "method": "GET",
        "path": "/finance/actuals/{actual_id}",
        "description": "Retrieve a finance actual record by actual_id.",
    },
    {
        "tool_name": "create_finance_actual",
        "method": "POST",
        "path": "/finance/actuals",
        "description": "Create a finance actual entry.",
    },
    {
        "tool_name": "update_finance_actual",
        "method": "PUT",
        "path": "/finance/actuals/{actual_id}",
        "description": "Update a finance actual entry.",
    },
    {
        "tool_name": "delete_finance_actual",
        "method": "DELETE",
        "path": "/finance/actuals/{actual_id}",
        "description": "Delete a finance actual entry by actual_id.",
    },
    {
        "tool_name": "list_finance_budgets",
        "method": "GET",
        "path": "/finance/budgets",
        "description": "List finance budget values with optional filters.",
    },
    {
        "tool_name": "get_finance_budget",
        "method": "GET",
        "path": "/finance/budgets/{budget_id}",
        "description": "Retrieve a finance budget record by budget_id.",
    },
    {
        "tool_name": "create_finance_budget",
        "method": "POST",
        "path": "/finance/budgets",
        "description": "Create a finance budget entry.",
    },
    {
        "tool_name": "update_finance_budget",
        "method": "PUT",
        "path": "/finance/budgets/{budget_id}",
        "description": "Update a finance budget entry.",
    },
    {
        "tool_name": "delete_finance_budget",
        "method": "DELETE",
        "path": "/finance/budgets/{budget_id}",
        "description": "Delete a finance budget entry by budget_id.",
    },
    {
        "tool_name": "list_finance_forecasts",
        "method": "GET",
        "path": "/finance/forecasts",
        "description": "List finance forecast values with optional filters.",
    },
    {
        "tool_name": "get_finance_forecast",
        "method": "GET",
        "path": "/finance/forecasts/{forecast_id}",
        "description": "Retrieve a finance forecast record by forecast_id.",
    },
    {
        "tool_name": "create_finance_forecast",
        "method": "POST",
        "path": "/finance/forecasts",
        "description": "Create a finance forecast entry.",
    },
    {
        "tool_name": "update_finance_forecast",
        "method": "PUT",
        "path": "/finance/forecasts/{forecast_id}",
        "description": "Update a finance forecast entry.",
    },
    {
        "tool_name": "delete_finance_forecast",
        "method": "DELETE",
        "path": "/finance/forecasts/{forecast_id}",
        "description": "Delete a finance forecast entry by forecast_id.",
    },
    {
        "tool_name": "list_kpis",
        "method": "GET",
        "path": "/kpis",
        "description": "List KPI definitions with optional filters.",
    },
    {
        "tool_name": "get_kpi",
        "method": "GET",
        "path": "/kpis/{kpi_id}",
        "description": "Retrieve a KPI by kpi_id.",
    },
    {
        "tool_name": "create_kpi",
        "method": "POST",
        "path": "/kpis",
        "description": "Create a new KPI record.",
    },
    {
        "tool_name": "update_kpi",
        "method": "PUT",
        "path": "/kpis/{kpi_id}",
        "description": "Update an existing KPI record.",
    },
    {
        "tool_name": "delete_kpi",
        "method": "DELETE",
        "path": "/kpis/{kpi_id}",
        "description": "Delete a KPI by kpi_id.",
    },
    {
        "tool_name": "list_queries",
        "method": "GET",
        "path": "/queries",
        "description": "List query logs with optional filters.",
    },
    {
        "tool_name": "get_query",
        "method": "GET",
        "path": "/queries/{query_id}",
        "description": "Retrieve a query log by query_id.",
    },
    {
        "tool_name": "create_query",
        "method": "POST",
        "path": "/queries",
        "description": "Create a new query log.",
    },
    {
        "tool_name": "update_query",
        "method": "PUT",
        "path": "/queries/{query_id}",
        "description": "Update a query log.",
    },
    {
        "tool_name": "delete_query",
        "method": "DELETE",
        "path": "/queries/{query_id}",
        "description": "Delete a query log by query_id.",
    },
    {
        "tool_name": "list_feedback",
        "method": "GET",
        "path": "/feedback",
        "description": "List user feedback with optional filters.",
    },
    {
        "tool_name": "get_feedback",
        "method": "GET",
        "path": "/feedback/{feedback_id}",
        "description": "Retrieve feedback by feedback_id.",
    },
    {
        "tool_name": "create_feedback",
        "method": "POST",
        "path": "/feedback",
        "description": "Create a new feedback entry.",
    },
    {
        "tool_name": "update_feedback",
        "method": "PUT",
        "path": "/feedback/{feedback_id}",
        "description": "Update feedback.",
    },
    {
        "tool_name": "delete_feedback",
        "method": "DELETE",
        "path": "/feedback/{feedback_id}",
        "description": "Delete feedback by feedback_id.",
    },
    {
        "tool_name": "list_calculation_results",
        "method": "GET",
        "path": "/calculation-results",
        "description": "List calculation results with optional filters.",
    },
    {
        "tool_name": "get_calculation_result",
        "method": "GET",
        "path": "/calculation-results/{calculation_id}",
        "description": "Retrieve a calculation result by calculation_id.",
    },
    {
        "tool_name": "create_calculation_result",
        "method": "POST",
        "path": "/calculation-results",
        "description": "Create a new calculation result.",
    },
    {
        "tool_name": "update_calculation_result",
        "method": "PUT",
        "path": "/calculation-results/{calculation_id}",
        "description": "Update a calculation result.",
    },
    {
        "tool_name": "delete_calculation_result",
        "method": "DELETE",
        "path": "/calculation-results/{calculation_id}",
        "description": "Delete a calculation result by calculation_id.",
    },
    {
        "tool_name": "list_evaluation_results",
        "method": "GET",
        "path": "/evaluation-results",
        "description": "List evaluation results with optional filters.",
    },
    {
        "tool_name": "get_evaluation_result",
        "method": "GET",
        "path": "/evaluation-results/{evaluation_result_id}",
        "description": "Retrieve an evaluation result by evaluation_result_id.",
    },
    {
        "tool_name": "create_evaluation_result",
        "method": "POST",
        "path": "/evaluation-results",
        "description": "Create a new evaluation result.",
    },
    {
        "tool_name": "update_evaluation_result",
        "method": "PUT",
        "path": "/evaluation-results/{evaluation_result_id}",
        "description": "Update an evaluation result.",
    },
    {
        "tool_name": "delete_evaluation_result",
        "method": "DELETE",
        "path": "/evaluation-results/{evaluation_result_id}",
        "description": "Delete an evaluation result by evaluation_result_id.",
    },
    {
        "tool_name": "list_evaluation_test_cases",
        "method": "GET",
        "path": "/evaluation-test-cases",
        "description": "List evaluation test cases with optional filters.",
    },
    {
        "tool_name": "get_evaluation_test_case",
        "method": "GET",
        "path": "/evaluation-test-cases/{test_case_id}",
        "description": "Retrieve an evaluation test case by test_case_id.",
    },
    {
        "tool_name": "create_evaluation_test_case",
        "method": "POST",
        "path": "/evaluation-test-cases",
        "description": "Create a new evaluation test case.",
    },
    {
        "tool_name": "update_evaluation_test_case",
        "method": "PUT",
        "path": "/evaluation-test-cases/{test_case_id}",
        "description": "Update an evaluation test case.",
    },
    {
        "tool_name": "delete_evaluation_test_case",
        "method": "DELETE",
        "path": "/evaluation-test-cases/{test_case_id}",
        "description": "Delete an evaluation test case by test_case_id.",
    },
]


def _build_openai_tool_name_to_route() -> dict[str, dict[str, str]]:
    mapping: dict[str, dict[str, str]] = {}
    for definition in ROUTER_TOOL_DEFINITIONS:
        tool_name = str(definition["tool_name"])
        route = {
            "path": str(definition["path"]),
            "method": str(definition["method"]).upper(),
        }
        mapping[tool_name] = route
        mapping[f"functions.{tool_name}"] = route
    return mapping


OPENAI_TOOL_NAME_TO_ROUTE = _build_openai_tool_name_to_route()
