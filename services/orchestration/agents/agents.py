
#write a class agents, that has methods build_orchestrator_agent, build_reviewer_agent, build_input_guardrail_agent, and get_latest_user_input
from agents import Agent, GuardrailFunctionOutput, OpenAIResponsesModel, RunContextWrapper, TResponseInputItem, input_guardrail, Runner, ModelSettings

from models.models import AnalystResult, FinanceRequestValidation, ReviewRequest, ReviewResult
from services.orchestration.openAIOrchestration.orchestration_common import OPENAI_MODEL, get_openai_client
from services.tools.chroma_tools import CHROMA_TOOLS, query_finance_chunks_by_id
from services.tools.dimension_tools import DIMENSION_TOOLS
from services.tools.employee_tools import EMPLOYEE_TOOLS
from services.tools.financial_query_tool import query_financial_data
from services.tools.health_tools import HEALTH_TOOLS
from services.tools.operations_tools import KPI_TOOLS


class Agents:

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

    INSTRUCTIONS_ANALYST = ("""
                You are a Financial Analyst Copilot.
    
                Understand the user's request and determine what information
                and analysis are required.
    
                Use the available financial database, document retrieval,
                calculation, and analysis tools as needed.
    
                The metric information supporting this data is available in the database, and narrative context is available in semantically indexed document chunks. 
                The tools provide structured finance records for budgets, forecasts, actuals, account metadata, business unit information, and period definitions.
                Use only the supplied tools to answer the user's questions.

                You may perform the following using the available tools:
                - query financial databases
                - retrieve financial documents
                - perform calculations
                - compare periods or companies
                - other financial analysis based on users request

                Evidence may come from:

                1. DOCUMENTS
                If document chunks were used, populate document_evidence.
                Include the chunk ID and available document provenance.

                2. DATABASE
                If database queries were used, populate database_evidence.
                Include:
                - purpose
                - returned rows used in the analysis
                - source name

                Do not fabricate document evidence when the answer came
                exclusively from the database.

                3. CALCULATIONS
                If calculations materially support a conclusion, populate
                calculation_evidence with the formula, inputs and result.

                Every material claim must reference one or more evidence_ids.

                It is valid for:
                document_evidence = []
                when no documents were searched.

                It is valid for:
                database_evidence = []
                when no database queries were required.

                Do not perform the independent review yourself.
                """
            )
    

    INSTRUCTIONS_REVIEWER = (
        """
    You are an independent Financial Analysis Review Agent.

    You review analysis produced by another financial analyst agent.

    Your job is NOT to independently redo the entire analysis.

    You will receive:
    - the user's original question
    - the analyst's proposed answer
    - specific claims made by the analyst
    - supporting evidence as chunk Ids, if available, else the collection will be empty
    - calculations performed by the analyst

    You have access to the tool - query_finance_chunks_by_id, that can retrieve chunks from the local Chroma DB by chunk ID.
    Use this tool to retrieve any supporting evidence you need to validate the claims, only if chunk Ids are provided. If chunk Ids are not provided, you may assume the analyst did not use any document chunks for the analysis.

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
        - employee info
        - salary
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
        - quarterly summary
        - summary for a specific quarter

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
        Allow requests that are continuation on a conversation, even if they are ambiguous on their own. Examples questions that could be continued conversations include,
        - "sure"
        - "go ahead"
        - yes/no responses
        - clarifying questions

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


    def build_analyst_agent(self):
        client = get_openai_client()
        model = OpenAIResponsesModel(
                    model=OPENAI_MODEL,
                    openai_client=client,
                )

        @input_guardrail
        async def validate_finance_request(
            ctx: RunContextWrapper[None],
            agent: Agent,
            input: str | list[TResponseInputItem],
        ) -> GuardrailFunctionOutput:

            latest_user_input = self.get_latest_user_input(input)

            result = await Runner.run(
                self.build_input_guardrail_agent(),
                latest_user_input,
                context=ctx.context,
            )
    
            validation = result.final_output
    
            return GuardrailFunctionOutput(
                output_info=validation,
                tripwire_triggered=not validation.is_valid_request,
            )
        
        return Agent(
            name="finance-analyst-agent",
            model=model,
            instructions=self.INSTRUCTIONS_ANALYST,
            model_settings=ModelSettings(temperature=0.0, max_tokens=None),
            output_type=AnalystResult,
            input_guardrails=[validate_finance_request],
            tools=[
                *CHROMA_TOOLS,
                *DIMENSION_TOOLS,
                *KPI_TOOLS,
                query_financial_data,
                *HEALTH_TOOLS,
                *EMPLOYEE_TOOLS,
            ]
        )

    def build_orchestrator_agent(self):
        client = get_openai_client()
        model = OpenAIResponsesModel(
                    model=OPENAI_MODEL,
                    openai_client=client,
                )

        @input_guardrail
        async def validate_finance_request(
            ctx: RunContextWrapper[None],
            agent: Agent,
            input: str | list[TResponseInputItem],
        ) -> GuardrailFunctionOutput:

            latest_user_input = self.get_latest_user_input(input)

            result = await Runner.run(
                self.build_input_guardrail_agent(),
                latest_user_input,
                context=ctx.context,
            )
    
            validation = result.final_output
    
            return GuardrailFunctionOutput(
                output_info=validation,
                tripwire_triggered=not validation.is_valid_request,
            )
        
        return Agent(
            name="finance-analyst-agent",
            model=model,
            instructions=self.INSTRUCTIONS,
            model_settings=ModelSettings(temperature=0.0, max_tokens=None),
            input_guardrails=[validate_finance_request],
            #output_type=AgentOutputSchema(OpenAIPlanResult, strict_json_schema=False),
            tools=[
                *CHROMA_TOOLS,
                *DIMENSION_TOOLS,
                *EMPLOYEE_TOOLS,
                *KPI_TOOLS,
                query_financial_data,
                *HEALTH_TOOLS,
                self.build_reviewer_agent().as_tool(
                    tool_name="financial_reviewer",
                    tool_description="""
                        Review a proposed financial analysis before returning it to the user.

                        Pass the original user question, draft answer, and claims,
                        supporting evidence, and calculations.

                        Pass only the chunk IDs actually used in the evidence, not the full text or all the chunkIds you received, to avoid overwhelming the reviewer.
                        Pass only the relevant claims, not all claims.
                        Also, only pass the relevant calculations, not all calculations.

                        Use this tool after completing substantial financial analysis
                        and before returning the final response.

                        The reviewer validates factual support, calculations,
                        evidence consistency, logic, and completeness.
                        """,
                    parameters=ReviewRequest,
                    # DEBUGGING:
                    failure_error_function=None,
                ),  # Add the reviewer agent as a tool
            ]
        )

    def build_reviewer_agent(self) -> Agent:
        client = get_openai_client()
        model = OpenAIResponsesModel(
                    model=OPENAI_MODEL,
                    openai_client=client,
                )
        return Agent(
            name="review_financial_analysis",
            model=model,
            instructions=self.INSTRUCTIONS_REVIEWER,
            model_settings=ModelSettings(temperature=0.0, max_tokens=None),
            output_type=ReviewResult,
            tools=[
                query_finance_chunks_by_id,
            ]
        )

    def build_input_guardrail_agent(self) -> Agent:
        client = get_openai_client()
        model = OpenAIResponsesModel(
                    model=OPENAI_MODEL,
                    openai_client=client,
                )
        return Agent(
            name="input_guardrail",
            model=model,
            instructions=self.INSTRUCTIONS_INPUT_GUARDRAIL,
            model_settings=ModelSettings(temperature=0.0, max_tokens=512),
            output_type=FinanceRequestValidation
        )

    def get_latest_user_input(
            self,
            input: str | list[TResponseInputItem],
        ) -> str:
    
            # Single-turn input
            if isinstance(input, str):
                return input
    
            # Multi-turn input: walk backwards and find the newest user message
            #if the input contains "try again", skip it and continue looking for the latest user input
            for item in reversed(input):
    
                if isinstance(item, dict):
                    if item.get("role") == "user":
                        content = item.get("content", "")
                        if isinstance(content, str) and "try again" in content.lower():
                            continue
    
                        if isinstance(content, str):
                            return content
    
                        # Handle structured content
                        if isinstance(content, list):
                            texts = []
    
                            for part in content:
                                if isinstance(part, dict):
                                    text = part.get("text")
                                    if text:
                                        texts.append(text)
    
                            return "\n".join(texts)
    
            # Safe fallback
            return ""
    