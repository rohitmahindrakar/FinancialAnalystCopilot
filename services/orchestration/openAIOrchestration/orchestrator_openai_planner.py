from __future__ import annotations

import json
from typing import Any, Callable
from services.models.models import OpenAIPlanResult
from services.orchestration.openAIOrchestration.orchestration_common import get_openai_client, OPENAI_MODEL
from services.orchestration.openAIOrchestration.orchestrator_synthesizer import ResponseSynthesizer
from agents import Agent, AgentOutputSchema, ModelSettings, OpenAIChatCompletionsModel, Runner, RunResult

_response_synthesizer = ResponseSynthesizer()

class OpenAIAgentPlanner:
    """Builds the planning Agent and executes a single propose-tool-calls planning round."""

    INSTRUCTIONS = (
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
    )

    def __init__(self, tools: list[Callable[..., dict[str, Any]]]) -> None:
        self._tools = tools

    def build_agent(self, api_base_url: str) -> Agent:
        client = get_openai_client()
        model = OpenAIChatCompletionsModel(model=OPENAI_MODEL, openai_client=client)
        return Agent(
            name="finance-agent-orchestrator",
            model=model,
            instructions=self.INSTRUCTIONS,
            model_settings=ModelSettings(temperature=0.0, max_tokens=512),
            output_type=AgentOutputSchema(OpenAIPlanResult, strict_json_schema=False),
            tools=self._tools,
        )
        
    
    # @staticmethod
    # def _normalize_plan_output(final_output: Any) -> dict[str, Any]:
    #     if isinstance(final_output, dict):
    #         normalized = dict(final_output)
    #         if "complete" not in normalized:
    #             normalized["complete"] = bool(normalized.get("complete", False)) or not bool(normalized.get("tools"))
    #         if "reasoning" not in normalized:
    #             normalized["reasoning"] = ""
    #         return normalized

    #     if isinstance(final_output, str):
    #         stripped = final_output.strip()
    #         try:
    #             parsed = json.loads(stripped)
    #         except json.JSONDecodeError:
    #             return {"tools": [], "synthesis": stripped, "complete": False, "reasoning": ""}
    #         if isinstance(parsed, dict):
    #             if "complete" not in parsed:
    #                 parsed["complete"] = bool(parsed.get("complete", False)) or not bool(parsed.get("tools"))
    #             if "reasoning" not in parsed:
    #                 parsed["reasoning"] = ""
    #             return parsed

    #     return {"tools": [], "synthesis": str(final_output), "complete": False, "reasoning": ""}

    def plan(
        self,
        user_question: str,
        api_base_url: str,
        conversation_history: list[dict[str, str]] | None = None,
        prior_tool_results: list[dict[str, Any]] | None = None,
    ) -> OpenAIPlanResult:
        agent = self.build_agent(api_base_url=api_base_url)
        history_entries = list(conversation_history or [])
        history_entries.append({"role": "user", "content": user_question})
        history_text = _response_synthesizer.format_history(history_entries)

        prompt = (
            f"Current user question: {user_question}\n\n"
            "Conversation history:\n"
            f"{history_text}"
        )
        if prior_tool_results:
            prompt = (
                f"Current user question: {user_question}\n\n"
                "Conversation history:\n"
                f"{history_text}\n\n"
                "You have already gathered the following tool results from earlier rounds:\n"
                f"{json.dumps(prior_tool_results, indent=2)}\n\n"
                "Use those results to decide whether you can answer now or need more tool calls. "
                "If the evidence is sufficient, return complete=true with no further tools. "
                "If more evidence is needed, return complete=false and the next tool calls required."
            )

        result: RunResult = Runner.run_sync(
            agent,
            prompt,
            max_turns=8,
        )

        #write a method call to get the tools and reasoning from the result.final_output and return it as a dictionary with keys 'tools', 'reasoning', 'complete', and 'synthesis'
        return result.final_output
