#generate a class orchestrator.py, that behaves as a langraph orchestrator. It should use the nodes - analyst_node, reviewer_node, revision_node and final_node as part of its orchestration flow.
import traceback
from typing import Literal
import uuid
import logging

from fastapi import HTTPException, logger

from database.repository.conversationhistory import ConversationHistorySession
from models.models import AnalystClaim, CitationInfo, FinalFinancialResponse, OrchestratorRequest, ReviewRequest, ReviewResult, FinancialAnalysisState, AnalystResult, UserContext
from agents import InputGuardrailTripwireTriggered, MaxTurnsExceeded, ModelBehaviorError, Runner, ToolInputGuardrailTripwireTriggered
from langgraph.graph import StateGraph, START, END
import json

from services.orchestration.agents.agents import Agents
from services.orchestration.openAIOrchestration.orchestration_common import event_stream_line

#logging configuration
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s"))
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

class Orchestrator:

    MAX_ANALYST_TURNS = 5
    MAX_REVIEW_CYCLES = 4

    #def __init__(self):#, analyst_node, reviewer_node, revision_node, final_node):
        # self.analyst_node = analyst_node
        # self.reviewer_node = reviewer_node
        # self.revision_node = revision_node
        # self.finalize_node = final_node

    async def orchestrate(self, payload: OrchestratorRequest):# -> ReviewResult:

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
            builder = self.build_state_graph()

            financial_graph = builder.compile()

            state = await financial_graph.ainvoke(
                {
                    "user_id": payload.user_id,
                    "role_code": payload.role_code,
                    "conversation_id": payload.conversation_id,
                    "user_question": user_question,
                    "review_cycle": 0,
                }
            )

            #capture final_response from state which is already an object of FinalFinancialResponse, and add it to the event stream below
            finalResponse: FinalFinancialResponse = state["final_answer"]

            yield event_stream_line(
                                    "final",
                                    {
                                        "stage": "request_processed",
                                        "final_response": finalResponse.model_dump(),
                                        "conversation_id": payload.conversation_id,
                                    }).encode("utf-8")
        except ToolInputGuardrailTripwireTriggered as exc:
            logger.error("Input guardrail tripwire triggered for question: %s", user_question)
            yield event_stream_line(
                                            "error",
                                            {
                                                "stage": "request_processed",
                                                "message": (
                                                    "You dont have access to the resource requested."
                                                ),
                                                "conversation_id": payload.conversation_id,
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
                                    "conversation_id": payload.conversation_id,
                                }
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
                                    "conversation_id": payload.conversation_id,
                                }
                            ).encode("utf-8")

        # # Step 1: Analyst Node
        # review_request = self.analyst_node.process(user_question)

        # # Step 2: Reviewer Node
        # review_result = self.reviewer_node.process(review_request)

        # # Step 3: Revision Node (if needed)
        # if review_result.requires_revision:
        #     revised_request = self.revision_node.process(review_request, review_result)
        #     review_result = self.reviewer_node.process(revised_request)

        # # Step 4: Final Node
        # final_result = self.final_node.process(review_result)

        # return final_result

    def build_state_graph(self):

        builder = StateGraph(FinancialAnalysisState)

        # ---------------------------------------------------------
        # Register nodes
        # ---------------------------------------------------------

        builder.add_node(
            "analyst",
            self.analyst_node,
        )

        builder.add_node(
            "reviewer",
            self.reviewer_node,
        )

        builder.add_node(
            "revise",
            self.revision_node,
        )

        builder.add_node(
            "finalize",
            self.finalize_node,
        )

        builder.add_node(
            "review_failed",
            self.review_failed_node,
        )

        # ---------------------------------------------------------
        # Initial workflow
        # ---------------------------------------------------------

        builder.add_edge(
            START,
            "analyst",
        )

        # Review is mandatory.
        # Analyst cannot go directly to finalize.
        builder.add_edge(
            "analyst",
            "reviewer",
        )

        # ---------------------------------------------------------
        # Reviewer routing
        # ---------------------------------------------------------

        builder.add_conditional_edges(
            "reviewer",
            self.route_after_review,
            {
                "revise": "revise",
                "finalize": "finalize",
                "review_failed": "review_failed",
            },
        )

        # ---------------------------------------------------------
        # Revision workflow
        # ---------------------------------------------------------

        # Every revised analysis must go through review again.
        builder.add_edge(
            "revise",
            "reviewer",
        )

        # ---------------------------------------------------------
        # Terminal states
        # ---------------------------------------------------------

        builder.add_edge(
            "finalize",
            END,
        )

        builder.add_edge(
            "review_failed",
            END,
        )

        return builder#.compile()
    
    
    async def analyst_node(
        self,
        state: FinancialAnalysisState,
    ) -> dict:

        try:
            agent_instance = Agents()
            analyst_agent = agent_instance.build_analyst_agent()

            session = ConversationHistorySession(user_id=state["user_id"], conversation_id=state["conversation_id"], title=state["user_question"][:100])

            user_context = UserContext(
                role_code=state["role_code"],
            )

            result = await Runner.run(
                analyst_agent,
                state["user_question"],
                max_turns=8,
                context=user_context,
                session=session,
            )

            analysis: AnalystResult = (
                result.final_output
            )

            return {
                "analysis_result": analysis,
                "last_action": "analysis_completed",
            }
        except Exception as exc:
            raise exc


    async def reviewer_node(
        self,
        state: FinancialAnalysisState,
    ) -> dict:

        try:
            agent_instance = Agents()
            reviewer_agent = agent_instance.build_reviewer_agent()
            #session = ConversationHistorySession(user_id=state["user_id"], conversation_id=state["conversation_id"])

            analysis = state["analysis_result"]
            
            review_request = ReviewRequest(
                user_question=state["user_question"],

                draft_answer=analysis.draft_answer,

                claims=analysis.claims,

                document_evidence=analysis.document_evidence,

                database_evidence=analysis.database_evidence,

                calculation_evidence=analysis.calculation_evidence,
            )

            result = await Runner.run(
                reviewer_agent,
                review_request.model_dump_json(),
                max_turns=4,
                #session=session,
            )

            review: ReviewResult = result.final_output

            return {
                "review_result": review,
                "review_cycle": state.get(
                    "review_cycle",
                    0,
                ) + 1,
                "last_action": "review",
            }
        except Exception as exc:
            raise exc


    async def revision_node(
        self,
        state: FinancialAnalysisState,
    ) -> dict:

        try:
            analysis: AnalystResult = state["analysis_result"]
            review: ReviewResult = state["review_result"]

            revision_input = f"""
                This is a REVISION of an existing financial analysis.

                Original user question:
                {state["user_question"]}

                Current analysis:
                {analysis.model_dump_json(indent=2)}

                Reviewer findings:
                {review.model_dump_json(indent=2)}

                Address the specific reviewer findings.

                Preserve existing conclusions and evidence that remain valid.

                If requires_additional_data=true, retrieve only the additional
                information necessary to resolve the identified issues.

                If requires_recalculation=true, recompute only the affected
                calculations.

                Do not restart the entire analysis unless the reviewer findings
                make the existing analysis fundamentally unusable.
            """


            agent_instance = Agents()
            analyst_agent = agent_instance.build_analyst_agent()
            #session = ConversationHistorySession(user_id=state["user_id"], conversation_id=state["conversation_id"])

            result = await Runner.run(
                analyst_agent,
                revision_input,
                max_turns=self.MAX_ANALYST_TURNS,
                #session=session,
            )

            revised_analysis: AnalystResult = result.final_output

            return {
                "analysis_result": revised_analysis,
                "last_action": "analysis_revised",
            }
        except Exception as exc:
            raise exc

    async def finalize_node(
            self,
            state: FinancialAnalysisState,
    ) -> dict:

        analysis: AnalystResult = state[
            "analysis_result"
        ]

        final_response = FinalFinancialResponse(
            answer=analysis.draft_answer,
            citations=self.build_citations(analysis),
        )

        return {
            "final_answer": final_response,
            "last_action": "finalized",
        }



    async def route_after_review(
    self,
    state: FinancialAnalysisState,
    ) -> Literal[
        "revise",
        "finalize",
    ]:
        review: ReviewResult | None = state.get(
            "review_result"
        )

        review_cycle = state.get(
            "review_cycle",
            0,
        )

        # Reviewer did not return a usable result.
        if review is None:
            return "review_failed"

        # Successful independent review.
        if review.approved:
            return "finalize"

        # Prevent infinite analyst/reviewer loops.
        if review_cycle >= self.MAX_REVIEW_CYCLES:
            return "review_failed"

        # Reviewer identified something that must be corrected.
        return "revise"

        # Any reviewer finding requiring action
        # goes back to the analyst.
        # if (
        #     review.requires_additional_data
        #     or review.requires_recalculation
        #     or review.requires_revision
        #     or review.requires_re_review
        #     or len(review.issues) > 0
        # ):
        #     return "revise"

        # Conservative fallback:
        # approved=False should not normally reach finalize.
        #return "revise"

    async def review_failed_node(
        self,
        state: FinancialAnalysisState,
    ) -> dict:

        analysis = state.get(
            "analysis_result"
        )

        review = state.get(
            "review_result"
        )

        citations = []

        if analysis:
            citations = self.build_citations(
                analysis
            )

        return {
            "final_answer": FinalFinancialResponse(
                answer=(
                    "The financial analysis could not be independently "
                    "validated within the allowed review cycles. "
                    "The available results should therefore not be treated "
                    "as fully validated."
                ),
                citations=citations,
            ),
            "last_action": "review_failed",
        }

    def build_citations(
        self,
        analysis: AnalystResult,
    ) -> list[CitationInfo]:

        citations: list[CitationInfo] = []

        for ev in analysis.document_evidence:

            citations.append(
                CitationInfo(
                    citation_id=ev.evidence_id,
                    citation_type="document",
                    label=ev.document_name,

                    document_name=ev.document_name,
                    document_link=ev.document_link,
                    page_number=ev.page_number,
                    chunk_id=ev.chunk_id,

                    database_source=None,
                    query_name=None,
                    query_summary=None,
                    calculation_name=None,
                )
            )

        for ev in analysis.database_evidence:

            citations.append(
                CitationInfo(
                    citation_id=ev.evidence_id,
                    citation_type="database",
                    label=ev.query_name,

                    document_name=None,
                    document_link=None,
                    page_number=None,
                    chunk_id=None,

                    database_source=ev.source_name,
                    query_name=ev.query_name,
                    query_summary=ev.purpose,

                    calculation_name=None,
                )
            )

        for ev in analysis.calculation_evidence:

            citations.append(
                CitationInfo(
                    citation_id=ev.evidence_id,
                    citation_type="calculation",
                    label=ev.calculation_name,

                    document_name=None,
                    document_link=None,
                    page_number=None,
                    chunk_id=None,

                    database_source=None,
                    query_name=None,
                    query_summary=None,

                    calculation_name=ev.calculation_name,
                )
            )

        return citations