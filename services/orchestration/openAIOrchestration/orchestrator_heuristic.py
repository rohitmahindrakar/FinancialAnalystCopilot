from __future__ import annotations

import re
from typing import Any

from services.orchestration_old import format_tool_response


class HeuristicRouteSelector:
    """Keyword-based routing used by the deterministic (non-agentic) /ask endpoint."""

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

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        return [token.lower() for token in re.findall(r"[a-zA-Z]+", text)]

    def needs_context(self, question: str) -> bool:
        tokens = set(self._tokenize(question))
        return bool(tokens & self.CONTEXT_HINTS)

    def needs_metric(self, question: str) -> bool:
        tokens = set(self._tokenize(question))
        return bool(tokens & self.METRIC_HINTS)

    @staticmethod
    def build_chroma_context_route(question: str) -> dict[str, Any]:
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

    @staticmethod
    def build_structured_finance_route(question: str) -> dict[str, Any]:
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

    @staticmethod
    def combine_final_response(primary_result: dict[str, Any], secondary_result: dict[str, Any] | None = None) -> str:
        parts: list[str] = []
        parts.append("Structured finance response:\n" + format_tool_response(primary_result))

        if secondary_result is not None:
            parts.append("Chroma context response:\n" + format_tool_response(secondary_result))

        return "\n\n".join(parts)


_heuristic_router = HeuristicRouteSelector()
