from __future__ import annotations

import logging
from typing import Any, Callable

logger = logging.getLogger(__name__)


class OrchestrationLoopRunner:
    """Executes an iterative propose-then-execute loop until the planner reports completion."""

    def run(
        self,
        user_question: str,
        planner: Callable[[str, list[dict[str, Any]]], dict[str, Any]],
        executor: Callable[[dict[str, Any]], dict[str, Any]],
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

