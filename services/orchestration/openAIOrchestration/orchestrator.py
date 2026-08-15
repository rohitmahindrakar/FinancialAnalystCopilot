from datetime import datetime
import logging
import uuid

from typing import Any
from agents import Agent, MaxTurnsExceeded, ModelSettings, OpenAIResponsesModel, Runner
from fastapi import HTTPException
from streamlit import json

from services.api_schemas import ConversationHistoryCreate
from services.models.models import OrchestratorRequest
from services.orchestration.openAIOrchestration.orchestration_common import OPENAI_MODEL, event_stream_line, get_openai_client
from services.orchestration.openAIOrchestration.orchestrator_loop import OrchestrationLoopRunner

#import the tools
from services.routers.conversationhistory import ConversationHistorySession, create_conversation_history, update_conversation_history
from services.tools.chroma_tools import CHROMA_TOOLS
from services.tools.dimension_tools import DIMENSION_TOOLS
from services.tools.health_tools import HEALTH_TOOLS
from services.tools.operations_tools import OPERATIONS_TOOLS
from services.tools.finance_tools import FINANCE_TOOLS

#logging configuration
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s"))
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

#_openai_agent_planner = OpenAIAgentPlanner(tools=[CHROMA_TOOLS, DIMENSION_TOOLS, OPERATIONS_TOOLS, FINANCE_TOOLS, HEALTH_TOOLS])
_orchestration_loop_runner = OrchestrationLoopRunner()


INSTRUCTIONS = (
        "You are a secure Financial Analyst. "
        "Users will ask questions about financial data, budgets, forecasts, actuals, and related information. "
        "The metric information supporting this data is available in the database, and narrative context is available in semantically indexed document chunks. "
        "All this data is available to you via tools that you can call. "
        "The tools provide structured finance records for budgets, forecasts, actuals, account metadata, business unit information, and period definitions, "
        "Use only the supplied tools to answer the user's questions. "
        "First decide whether the current evidence is sufficient to answer the user's question. "
        "You also have access to a financial reviewer agent that can review your output and provide feedback on any issues, missing information, errors, or inconsistencies. "
        "Use this agent to review your output and provide a summary of findings. Pass the agent the relevant data and your output for review. "

        "Workflow: "
        "1. Determine what information is needed. "
        "2. Call the appropriate financial data and calculation tools. "
        "3. Synthesize a proposed answer. "
        "4. BEFORE returning the final answer, call "
        "   review_financial_analysis agent tool with the proposed analysis and "
        "   relevant supporting facts. "
        "5. Incorporate valid reviewer corrections. "
        "6. Return the corrected final answer. "

        "Do not skip the review step for analytical or recommendation-style "
        "financial questions."
    )

#write instructions for a financial reviewer agent. These instructions will be sent over to an LLM with corresponding data, to help review the data, find out any issues, missing information, errors, etc., and provide a summary of findings to be shared to the main orchestrator agent to work on if needed.
INSTRUCTIONS_REVIEWER = (
        "You are a secure Financial Reviewer. "
        "You have been provided data from a financial analyst agent, which includes financial data, budgets, forecasts, actuals, and related information. "
        "Your task is to review this data, identify any issues, missing information, errors, or inconsistencies, and provide a summary of your findings. "
        "Use your expertise to analyze the data critically and provide actionable insights. "
        "Your summary should be clear, concise, and focused on the key points that need attention. "
    )

class Orchestrator:
    def __init__(self):
        # self.tools = tools
        # self.planner = planner
        # self.synthesizer = synthesizer
        self.INSTRUCTIONS = INSTRUCTIONS
        self.INSTRUCTIONS_REVIEWER = INSTRUCTIONS_REVIEWER
        pass

    def _execute_openai_orchestration_loop(
        user_question: str,
        planner: Any,
        executor: Any,
        max_rounds: int = 4,
    ) -> dict[str, Any]:
        """Retained as a module-level function for backward compatibility with existing callers/tests."""
        return _orchestration_loop_runner.run(user_question, planner, executor, max_rounds=max_rounds)

    def build_orchestrator_agent(self) -> Agent:
            client = get_openai_client()
            model = OpenAIResponsesModel(
                        model=OPENAI_MODEL,
                        openai_client=client,
                    )
            #OpenAIChatCompletionsModel(model=OPENAI_MODEL, openai_client=client)
            return Agent(
                name="finance-analyst-agent",
                model=model,
                instructions=self.INSTRUCTIONS,
                model_settings=ModelSettings(temperature=0.0, max_tokens=512),
                #output_type=AgentOutputSchema(OpenAIPlanResult, strict_json_schema=False),
                tools=[
                    *CHROMA_TOOLS,
                    *DIMENSION_TOOLS,
                    *OPERATIONS_TOOLS,
                    *FINANCE_TOOLS,
                    *HEALTH_TOOLS,
                    self.build_reviewer_agent().as_tool(
                         tool_name="financial_reviewer",
                         tool_description="Reviews and analysis generated output to identify any issues, missing information, errors, or inconsistencies, and provides a summary of findings.",
                    ),  # Add the reviewer agent as a tool
                ]
            )

    def build_reviewer_agent(self) -> Agent:
            client = get_openai_client()
            model = OpenAIResponsesModel(
                        model=OPENAI_MODEL,
                        openai_client=client,
                    )
            #OpenAIChatCompletionsModel(model=OPENAI_MODEL, openai_client=client)
            return Agent(
                name="finance-reviewer-agent",
                model=model,
                instructions=self.INSTRUCTIONS_REVIEWER,
                model_settings=ModelSettings(temperature=0.0, max_tokens=512),
                #output_type=AgentOutputSchema(OpenAIPlanResult, strict_json_schema=False),
                # tools=[
                #     *CHROMA_TOOLS,
                #     *DIMENSION_TOOLS,
                #     *OPERATIONS_TOOLS,
                #     *FINANCE_TOOLS,
                #     *HEALTH_TOOLS,
                # ]
            )

    async def orchestrate_new(self, payload: OrchestratorRequest):
        user_question = payload.user_question.strip()
        if not user_question:
            logger.warning("Received an empty user question for OpenAI orchestrator.")
            raise HTTPException(status_code=422, detail="user_question cannot be empty")

        #check if conversation_id is provided, if not create a new random guid conversation id
        if not payload.conversation_id:
            payload.conversation_id = str(uuid.uuid4())
            logger.info("No conversation_id provided. Generated new conversation_id: %s", payload.conversation_id)

        yield event_stream_line(
                "status",
                {
                    "stage": "request_received",
                    "message": "Processing request based on available information.",
                    "conversation_id": payload.conversation_id,
                },                
            ).encode("utf-8")
        
        try:
            agent = self.build_orchestrator_agent()

            session = ConversationHistorySession(conversation_id=payload.conversation_id)

            result = await Runner.run(
                agent,
                user_question,
                max_turns=10,
                session=session,
            )

            final = result.final_output
            print(f"Final output from orchestrate_new: {final}")

            yield event_stream_line(
                            "final",
                            {
                                "stage": "request_processed",
                                "final_response": result.final_output,
                                "conversation_id": payload.conversation_id,
                            },
                        ).encode("utf-8")
        except MaxTurnsExceeded as e:
            logger.error("Max turns exceeded during orchestration: %s", str(e))
            yield event_stream_line(
                                "error",
                                {
                                    "stage": "request_processed",
                                    "error_message": "Max turns exceeded during orchestration.",
                                },
                                conversation_id=payload.conversation_id,
                            ).encode("utf-8")
        except Exception as e:
            logger.error("Error during orchestration: %s", str(e))
            yield event_stream_line(
                                "error",
                                {
                                    "stage": "request_processed",
                                    "error_message": "Error occurred during orchestration: ",
                                },
                                conversation_id=payload.conversation_id,
                            ).encode("utf-8")


    # def orchestrate(self, payload: OrchestratorRequest) -> str:
    #     user_question = payload.user_question.strip()
    #     if not user_question:
    #         logger.warning("Received an empty user question for OpenAI orchestrator.")
    #         raise HTTPException(status_code=422, detail="user_question cannot be empty")
    
    #     logger.info("OpenAI orchestrator request received for question: %s", user_question)
    
    #     def event_stream() -> AsyncIterator[bytes]:
    #         yield event_stream_line(
    #             "status",
    #             {
    #                 "stage": "received",
    #                 "message": "Request received....",
    #                 "user_question": user_question,
    #             },
    #         ).encode("utf-8")
    
    #         try:
    #             yield event_stream_line(
    #                 "status",
    #                 {
    #                     "stage": "planning",
    #                     "message": "going through available information and planning next steps....",
    #                 },
    #             ).encode("utf-8")
    
    #             logger.info("Starting iterative OpenAI planning loop for question: %s", user_question)
    
    #             def planner(question: str, prior_results: list[dict[str, Any]]) -> OpenAIPlanResult:
    #                 plan = _openai_agent_planner.plan(
    #                     question,
    #                     payload.api_base_url,
    #                     conversation_history=payload.conversation_history,
    #                     prior_tool_results=prior_results,
    #                 )
    #                 #plan["prior_tool_results"] = prior_results
    #                 return plan
    
    #             def executor(call: dict[str, Any]) -> dict[str, Any]:
    #                 method = str(call.get("method", "GET")).upper()
    #                 path = str(call.get("path", ""))
    #                 tool_name = str(call.get("tool_name") or "")
    #                 arguments = dict(call.get("arguments") or {})
    #                 logger.info("Executing tool call: tool_name=%s method=%s path=%s arguments=%s", tool_name, method, path, arguments)
    #                 result = guarded_execute_backend_tool(payload.api_base_url, method, path, arguments, tool_name=tool_name)
    #                 logger.info("Tool execution completed: tool_name=%s status_code=%s", tool_name, result.get("status_code"))
    #                 return result
    
    #             tool_results: list[dict[str, Any]] = []
    #             history: list[dict[str, Any]] = []
    #             last_plan: OpenAIPlanResult | None = None
    #             tool_calls: list[dict[str, Any]] = []
    
    #             for round_index in range(4):
    #                 logger.info("OpenAI orchestration round %s/%s", round_index + 1, 4)
    #                 plan = planner(user_question, tool_results)
    #                 last_plan = plan
    #                 history.append({"round": round_index + 1, "plan": plan})
    
    #                 reasoning = str(plan.reasoning or "")
    #                 if reasoning:
    #                     logger.info("Planner reasoning for round %s: %s", round_index + 1, reasoning)
    #                     yield _event_stream_line(
    #                         "status",
    #                         {
    #                             "stage": "planning_update",
    #                             "message": reasoning,
    #                             "round": round_index + 1,
    #                             "reasoning": reasoning,
    #                             "complete": bool(plan.complete),
    #                         },
    #                     ).encode("utf-8")
    
    #                 round_tool_calls = list(plan.tools or [])
    #                 if not round_tool_calls:
    #                     logger.info("No further tool calls proposed; stopping orchestration loop.")
    #                     break
    
    #                 tool_calls.extend(round_tool_calls)
    #                 logger.info("Planner proposed %d tool call(s) in round %s.", len(round_tool_calls), round_index + 1)
    #                 for call in round_tool_calls:
    #                     method = str(call.get("method", "GET")).upper()
    #                     path = str(call.get("path", ""))
    #                     tool_name = str(call.get("tool_name") or "")
    #                     arguments = dict(call.get("arguments") or {})
    #                     logger.info("Executing tool call: tool_name=%s method=%s path=%s arguments=%s", tool_name, method, path, arguments)
    #                     result = executor(call)
    #                     logger.info("Tool execution completed: tool_name=%s status_code=%s", tool_name, result.get("status_code"))
    #                     tool_results.append(result)
    
    #                 if plan.complete:
    #                     logger.info("Planner marked the response as complete; stopping orchestration loop.")
    #                     break
    
    #             synthesis = str(last_plan.synthesis or "") if last_plan else ""
    #             logger.info("Iterative OpenAI planning completed. Total tool result(s): %d", len(tool_results))
    #             for round_entry in history:
    #                 round_plan = round_entry.get("plan", None)
    #                 logger.info("Round %s proposed %d tool call(s).", round_entry.get("round"), len(round_plan.tools or []) if round_plan else 0)
    
    #             yield event_stream_line(
    #                 "status",
    #                 {
    #                     "stage": "tool_selected",
    #                     "message": "OpenAI Agents selected the tool list to execute.",
    #                     "tools": tool_calls,
    #                     "reasoning": last_plan.reasoning if last_plan else None,
    #                 },
    #             ).encode("utf-8")
    
    #             logger.info("Synthesizing final response from %d tool result(s).", len(tool_results))
    #             final_response = _response_synthesizer.synthesize(
    #                 user_question=user_question,
    #                 conversation_history=payload.conversation_history,
    #                 tool_results=tool_results,
    #                 plan=last_plan,
    #             )
    #             if not final_response.strip():
    #                 logger.warning("Final synthesis returned no content; falling back to planner synthesis.")
    #                 final_response = synthesis or "No result found for user's question"
    
    #             yield event_stream_line(
    #                 "status",
    #                 {
    #                     "stage": "completed",
    #                     "message": "Agents orchestration completed.",
    #                 },
    #             ).encode("utf-8")
    
    #             logger.info("Final response - %s", final_response)
    
    #             yield _event_stream_line(
    #                 "final",
    #                 {
    #                     "final_response": final_response,
    #                     "tools": tool_calls,
    #                     "status_code": 200,
    #                 },
    #             ).encode("utf-8")
    #         except HTTPException as exc:
    #             logger.exception("OpenAI orchestrator raised an HTTP error for question: %s", user_question)
    #             yield event_stream_line(
    #                 "error",
    #                 {
    #                     "message": exc.detail,
    #                 },
    #             ).encode("utf-8")
    #         except Exception as exc:
    #             logger.exception("Unexpected OpenAI orchestrator error for question: %s", user_question)
    #             yield event_stream_line(
    #                 "error",
    #                 {
    #                     "message": f"Unexpected OpenAI Agents orchestrator error: {exc}",
    #                 },
    #             ).encode("utf-8")

    #     StreamingResponse(event_stream(), media_type="text/event-stream")