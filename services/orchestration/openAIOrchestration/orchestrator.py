import logging
import traceback
import uuid

from typing import Any
from agents import Agent, GuardrailFunctionOutput, InputGuardrailTripwireTriggered, MaxTurnsExceeded, ModelBehaviorError, ModelSettings, OpenAIResponsesModel, RunContextWrapper, Runner, TResponseInputItem, input_guardrail
from fastapi import HTTPException

from models.models import ChartSeries, ChartSpec, FinanceRequestValidation, ReviewRequest, ReviewResult
from services.models.models import OrchestratorRequest
from services.orchestration.agents.agents import Agents
from services.orchestration.openAIOrchestration.orchestration_common import OPENAI_MODEL, event_stream_line, get_openai_client
from services.orchestration.openAIOrchestration.orchestrator_loop import OrchestrationLoopRunner

#import the tools
from services.routers.conversationhistory import ConversationHistorySession
from services.tools.chroma_tools import CHROMA_TOOLS, query_finance_chunks_by_id
from services.tools.dimension_tools import DIMENSION_TOOLS
from services.tools.financial_query_tool import query_financial_data
from services.tools.health_tools import HEALTH_TOOLS
from services.tools.operations_tools import KPI_TOOLS

#logging configuration
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s"))
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

#_openai_agent_planner = OpenAIAgentPlanner(tools=[CHROMA_TOOLS, DIMENSION_TOOLS, OPERATIONS_TOOLS, FINANCE_TOOLS, HEALTH_TOOLS])
_orchestration_loop_runner = OrchestrationLoopRunner()


# INSTRUCTIONS = (
#         "You are a secure Financial Analyst. "
#         "Users will ask questions about financial data, budgets, forecasts, actuals, and related information. "
#         "The metric information supporting this data is available in the database, and narrative context is available in semantically indexed document chunks. "
#         "The metric information available to you is for the fiscal year 2026, and the fiscal quarters Q1, Q2, Q3, and Q4. Forecast is available for forecast version - Q4 forecast only. Information on all this is available in the tools you can call. "
#         "All this data is available to you via tools that you can call. "
#         "The tools provide structured finance records for budgets, forecasts, actuals, account metadata, business unit information, and period definitions, "
#         "Use only the supplied tools to answer the user's questions. "
#         "First decide whether the current evidence is sufficient to answer the user's question. "
#         "You also have access to a financial reviewer agent that can review your output and provide feedback on any issues, missing information, errors, or inconsistencies. "
#         "Use this agent to review your output and provide a summary of findings. Pass the agent the relevant data and your output for review. "

#         "Workflow: "
#         "1. Determine what information is needed. "
#         "2. Call the appropriate financial data and calculation tools. "
#         "3. Synthesize a proposed answer. "
#         "4. BEFORE returning the final answer, call "
#         "   review_financial_analysis agent tool with the proposed analysis and "
#         "   relevant supporting facts. "
#         "5. Incorporate valid reviewer corrections. "
#         "6. Return the corrected final answer. "

#         "Do not skip the review step for analytical or recommendation-style "
#         "financial questions."
#    )
INSTRUCTIONS = ("""
            You are a Financial Analyst Copilot.

            Understand the user's request and determine what information
            and analysis are required.

            Use the available financial database, document retrieval,
            calculation, and analysis tools as needed.

            The metric information supporting this data is available in the database, and narrative context is available in semantically indexed document chunks. 
            The tools provide structured finance records for budgets, forecasts, actuals, account metadata, business unit information, and period definitions.
            Use only the supplied tools to answer the user's questions.
            You also have access to a financial reviewer agent that can review your output and provide feedback on any issues, missing information, errors, or inconsistencies.
            Use this agent to review your output and provide a summary of findings. Pass the agent the relevant structured data including your output for review.

            For substantial financial analysis:

            1. Gather the required evidence.
            2. Perform the necessary calculations.
            3. Develop a draft answer.
            4. Identify the material claims made in the draft.
            5. Call review_financial_analysis before returning the answer.
            6. Pass the reviewer:
            - original user question
            - draft answer
            - claims
            - evidence supporting the claims
            - relevant calculations
            7. Inspect the ReviewResult.

            If approved=true:
                return the final response.

            If approved=false:
                If requires_additional_data=true:
                    retrieve only the additional data needed to resolve
                    the identified reviewer issues.

                If requires_recalculation=true:
                    rerun the relevant calculation tools.

                If requires_revision=true:
                    revise the draft using the validated evidence.

                If requires_re_review=true:
                    call financial_reviewer again after making the
                    required corrections.

            Do not restart the entire analysis.

            Only perform actions required to resolve the specific
            reviewer issues.

            Do not repeat a tool call with identical arguments unless
            the reviewer identified a reason that requires it.

            Do not blindly accept reviewer feedback if it contradicts
            authoritative data from tools.

            Do not call the reviewer repeatedly unless a material correction
            was required.

            Simple factual retrieval questions do not require review.

            Examples that SHOULD normally be reviewed:
            - trend analysis
            - company comparisons
            - profitability analysis
            - financial health analysis
            - valuation conclusions
            - risk assessments
            - multi-step calculations

            Examples that generally DO NOT require review:
            - "What was revenue in Q2?"
            - "What is the current debt balance?"
            - "What is EBITDA?"
            """
        )

#write instructions for a financial reviewer agent. These instructions will be sent over to an LLM with corresponding data, to help review the data, find out any issues, missing information, errors, etc., and provide a summary of findings to be shared to the main orchestrator agent to work on if needed.
INSTRUCTIONS_REVIEWER = (
        """
    You are an independent Financial Analysis Review Agent.

    You review analysis produced by another financial analyst agent.

    Your job is NOT to independently redo the entire analysis.

    You will receive:
    - the user's original question
    - the analyst's proposed answer
    - specific claims made by the analyst
    - supporting evidence
    - calculations performed by the analyst

    You have access to the tool - query_finance_chunks_by_id, that can retrieve chunks from the local Chroma DB by chunk ID. Use this tool to retrieve any supporting evidence you need to validate the claims.

    Validate the proposed answer across the following areas.

    1. FACTUAL SUPPORT

    Check whether material claims are actually supported by the
    supplied evidence.

    Do not assume a claim is true simply because it sounds reasonable.

    Flag conclusions that are stronger than the supplied evidence.


    2. NUMERICAL ACCURACY

    Verify:
    - percentages
    - growth rates
    - ratios
    - margins
    - period comparisons
    - units
    - signs
    - currencies

    Flag calculations that do not follow from the supplied inputs.


    3. SOURCE CONSISTENCY

    Check whether evidence associated with a claim actually supports
    that claim.

    Flag:
    - incorrect source attribution
    - wrong periods
    - contradictory evidence
    - evidence that does not support the associated claim


    4. LOGICAL CONSISTENCY

    Look for:
    - contradictions
    - reasoning gaps
    - unjustified causal claims
    - overstatements
    - conclusions that do not follow from the evidence


    5. COMPLETENESS

    Compare the draft answer to the user's original question.

    Determine whether all material parts of the question were answered.


    IMPORTANT LIMITATIONS

    Do NOT:
    - independently repeat broad document searches
    - independently repeat database research
    - create an entirely new financial analysis
    - rewrite the final answer
    - invent missing financial information

    Your responsibility is validation.

    If the answer is adequately supported and materially correct,
    return approved=true.

    If issues exist, return approved=false and identify the issues
    precisely.

    Use high severity only for issues that could materially change
    the interpretation or answer.
    """
    )

INSTRUCTIONS_INPUT_GUARDRAIL = (
    """
        You validate requests sent to an internal company finance copilot.

        The copilot is designed to answer questions using internal financial data
        for ONE company.

        VALID requests include questions about:
        - revenue
        - expenses
        - operating expenses
        - gross margin
        - operating margin
        - EBITDA
        - profit and loss
        - budget
        - forecast
        - actual performance
        - actual vs budget
        - actual vs forecast
        - prior-period comparisons
        - financial variances
        - department or business-unit financial performance
        - cost trends
        - financial KPIs
        - financial summaries
        - explanations of changes in financial performance

        Examples of VALID requests:
        - "What was revenue last quarter?"
        - "How did Q2 actual revenue compare to budget?"
        - "Why was operating expense above forecast in July?"
        - "Show me marketing spend for the current quarter."
        - "What drove the decline in gross margin?"
        - "Summarize our year-to-date financial performance."

        INVALID requests include:
        - researching or analyzing another company
        - stock recommendations
        - investment advice
        - personal finance questions
        - legal advice
        - medical advice
        - general questions unrelated to internal company finance
        - requests to bypass security or access restricted information
        - requests unrelated to the purpose of the finance copilot

        Examples of INVALID requests:
        - "Should I buy Apple stock?"
        - "What was Microsoft's revenue last quarter?"
        - "Help me choose a mortgage."
        - "Write a poem."
        - "Show me data I am not authorized to access."

        IMPORTANT:
        Do not reject a request merely because it is ambiguous.

        For example:
        - "How did we do last quarter?"
        - "Why are costs higher?"
        - "How are we performing?"

        are still valid internal finance requests.

        Ambiguity such as missing period, department, or scenario should be handled
        later by the finance agent or data retrieval layer.

        Return:
        - is_valid_request
        - category
        - reason
    """)

class Orchestrator:
    def __init__(self):
        # self.tools = tools
        # self.planner = planner
        # self.synthesizer = synthesizer
        self.INSTRUCTIONS = INSTRUCTIONS
        self.INSTRUCTIONS_REVIEWER = INSTRUCTIONS_REVIEWER
        self.INSTRUCTIONS_INPUT_GUARDRAIL = INSTRUCTIONS_INPUT_GUARDRAIL
        pass


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
            #create an instance of the class agent, and create an agent using the build_orchestrator_agent method, and then run the agent with the user_question, and yield the final output as an event stream line
            agent_instance = Agents()
            agent = agent_instance.build_orchestrator_agent()
            
            # agent = self.build_orchestrator_agent()

            session = ConversationHistorySession(conversation_id=payload.conversation_id)

            result = await Runner.run(
                agent,
                user_question,
                max_turns=10,
                session=session,
                hooks=DebugHooks(),
            )

            final = result.final_output
            print(f"Final output from orchestrate_new: {final}")

            yield event_stream_line(
                            "final",
                            {
                                "stage": "request_processed",
                                "final_response": result.final_output,
                                "conversation_id": payload.conversation_id,
                                # "chart": ChartSpec(
                                #             chart_type="line",
                                #             title="Sample Chart",
                                #             x_label="Fiscal Year",
                                #             y_label="Revenue ($B)",
                                #             categories=[
                                #                 "2023",
                                #                 "2024",
                                #                 "2025",
                                #                 "2026",
                                #             ],
                                #             series=[
                                #                 ChartSeries(
                                #                     name="Revenue",
                                #                     values=[
                                #                         211.9,
                                #                         245.1,
                                #                         281.7,
                                #                         315.4,
                                #                     ],
                                #                 )
                                #             ],
                                #         ),
                            },
                        ).encode("utf-8")
        except InputGuardrailTripwireTriggered as exc:
            logger.error("Input guardrail tripwire triggered for question: %s", user_question)
            yield event_stream_line(
                                            "error",
                                            {
                                                "stage": "request_processed",
                                                "message": (
                                                    exc.guardrail_result.output.output_info.reason
                                                    if exc.guardrail_result.output.output_info.reason
                                                    else "This request is outside the scope of the internal finance copilot. "
                                                         "I can help with internal financial performance, actuals, budgets, "
                                                         "forecasts, expenses, revenue, margins, and variance analysis."
                                                ),
                                                "conversation_id": payload.conversation_id,
                                            },
                                        ).encode("utf-8")
        except ModelBehaviorError as exc:
            print("ERROR:", exc)

            if exc.run_data:
                print("Number of raw responses:",
                    len(exc.run_data.raw_responses))

                for i, response in enumerate(
                    exc.run_data.raw_responses
                ):
                    print(f"\n=== RESPONSE {i} ===")
                    print(response)

                    response = exc.run_data.raw_responses[-1]

                    for item in response.output:

                        if getattr(item, "name", None) == "financial_reviewer":

                            raw = getattr(item, "arguments", None)

                            print("RAW REVIEWER ARGS:")
                            print(raw)

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
            print("TYPE:", type(e).__name__)
            print("ERROR:", repr(e))
            traceback.print_exc()
            #raise
            yield event_stream_line(
                                "error",
                                {
                                    "stage": "request_processed",
                                    "error_message": "Error occurred during orchestration: ",
                                },
                                conversation_id=payload.conversation_id,
                            ).encode("utf-8")

from agents import RunHooks

class DebugHooks(RunHooks):

    async def on_tool_start(
        self,
        context,
        agent,
        tool,
    ):
        print("\n=== TOOL START ===")
        print("Agent:", agent.name)
        print("Tool:", tool.name)

        # For function tools, context is typically ToolContext
        if hasattr(context, "tool_arguments"):
            print("RAW TOOL ARGUMENTS:")
            print(context.tool_arguments)

        if hasattr(context, "tool_call_id"):
            print("Tool call ID:", context.tool_call_id)

    async def on_llm_end(
        self,
        context,
        agent,
        response,
    ):
        for item in response.output:

            name = getattr(item, "name", None)

            if name == "financial_reviewer":

                print("\n=== FINANCIAL REVIEWER CALL ===")

                arguments = getattr(
                    item,
                    "arguments",
                    None,
                )

                print("RAW ARGUMENT STRING:")
                print(arguments)

                raw = item.arguments

                print("Argument characters:", len(raw))
                print("Last 1000 chars:")
                print(raw[-1000:])

                import json

                try:
                    json.loads(raw)
                except json.JSONDecodeError as exc:
                    print("Error:", exc)
                    print("Position:", exc.pos)
                    print("Length:", len(raw))
                    print("Last characters:", repr(raw[-500:]))

                print("==============================")


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