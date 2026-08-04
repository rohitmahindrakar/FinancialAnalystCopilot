from services.routers.tool_registry import OrchestratorToolRegistry


def test_orchestrator_tool_registry_exposes_router_tools() -> None:
    registry = OrchestratorToolRegistry()

    tool_names = {tool.__name__ for tool in registry.tools}

    assert "list_finance_actuals" in tool_names
    assert "list_finance_budgets" in tool_names
    assert "list_finance_forecasts" in tool_names
    assert "query_finance_chunks" in tool_names
    assert "list_accounts" in tool_names
    assert "list_business_units" in tool_names
    assert "list_periods" in tool_names
    assert "list_source_documents" in tool_names
    assert "list_evaluation_test_cases" in tool_names
    assert "rewrite_query" in tool_names
    assert "expand_query" in tool_names
    assert "rerank_query_results" in tool_names
