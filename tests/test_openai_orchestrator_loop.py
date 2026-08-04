from services.routers.orchestrator import _execute_openai_orchestration_loop


def test_execute_openai_orchestration_loop_stops_when_complete() -> None:
    planner_calls = []

    def planner(question: str, prior_results: list[dict]) -> dict:
        planner_calls.append((question, len(prior_results)))
        if len(prior_results) == 0:
            return {"tools": [{"tool_name": "list_finance_actuals"}], "synthesis": "", "complete": False}
        return {"tools": [], "synthesis": "I have enough information now.", "complete": True}

    def executor(call: dict) -> dict:
        return {"status_code": 200, "data": [{"tool_name": call["tool_name"]}]}

    result = _execute_openai_orchestration_loop(
        user_question="What were the actuals?",
        planner=planner,
        executor=executor,
        max_rounds=3,
    )

    assert result["completed"] is True
    assert len(result["tool_results"]) == 1
    assert result["last_plan"]["complete"] is True
    assert len(planner_calls) == 2
