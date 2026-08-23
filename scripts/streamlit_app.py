
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import requests
import streamlit as st
import pandas as pd

from models.models import ChartSpec, CitationInfo, FinalFinancialResponse

DEFAULT_API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
LOGO_PATH = Path(__file__).resolve().parent / "assets" / "company_logo.svg"
USER_AVATAR = "🧑\u200d💼"
ASSISTANT_AVATAR = "📈"
SAMPLE_QUESTIONS = [
    "Summarize the latest budget context for Q3.",
    "What are the key forecast trends across the business units?",
    "Compare actuals and budgets for the latest reporting period.",
    "Explain the main document context around the company's guidance.",
]

st.set_page_config(page_title="FinPulseAI", page_icon="📊", layout="wide")

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Sora:wght@400;500;600;700;800&family=IBM+Plex+Sans:wght@400;500;600&display=swap');

    :root {
        --fp-navy: #0d1b2a;
        --fp-cyan: #44d1c2;
        --fp-ink: #10273e;
        --fp-slate: #4f6782;
        --fp-pearl: #f5f9ff;
        --fp-line: #d8e4f5;
    }

    .stApp {
        font-family: 'IBM Plex Sans', sans-serif;
        background:
            radial-gradient(1200px 500px at -10% -10%, rgba(68, 209, 194, 0.28) 0%, rgba(68, 209, 194, 0) 60%),
            radial-gradient(1000px 500px at 115% 0%, rgba(57, 121, 194, 0.18) 0%, rgba(57, 121, 194, 0) 62%),
            linear-gradient(180deg, #f5f9ff 0%, #eef4fd 100%);
    }

    h1, h2, h3, h4 {
        font-family: 'Sora', sans-serif;
        letter-spacing: -0.02em;
        color: var(--fp-ink);
    }

    .block-container {
        padding-top: 1rem;
        padding-bottom: 6rem;
        max-width: 980px;
    }

    .brand-header {
        display: flex;
        align-items: center;
        gap: 1rem;
        margin-bottom: 1.2rem;
        padding: 1rem 1.2rem;
        background: rgba(255, 255, 255, 0.82);
        border: 1px solid rgba(9, 33, 61, 0.11);
        border-radius: 20px;
        box-shadow: 0 18px 34px rgba(9, 33, 61, 0.12);
        backdrop-filter: blur(7px);
        animation: rise-in 520ms ease-out;
    }

    .brand-header img {
        width: 68px;
        height: 68px;
        border-radius: 18px;
        box-shadow: 0 12px 24px rgba(19, 76, 133, 0.22);
    }

    .brand-title {
        font-family: 'Sora', sans-serif;
        font-size: 1.7rem;
        font-weight: 800;
        color: #0f2845;
    }

    .brand-subtitle {
        font-size: 0.9rem;
        color: var(--fp-slate);
        max-width: 38rem;
    }

    .status-pill {
        display: inline-block;
        padding: 0.26rem 0.78rem;
        border-radius: 999px;
        background: #e7fff8;
        color: #0b6f4b;
        border: 1px solid rgba(11, 111, 75, 0.2);
        font-size: 0.75rem;
        font-weight: 600;
        margin-left: auto;
        box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.35);
        animation: pulse-dot 1.6s ease-in-out infinite;
    }

    .signal-row {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 0.65rem;
        margin-bottom: 1.2rem;
    }

    .signal-card {
        background: rgba(255, 255, 255, 0.84);
        border: 1px solid var(--fp-line);
        border-radius: 14px;
        padding: 0.65rem 0.8rem;
        box-shadow: 0 10px 22px rgba(10, 42, 77, 0.08);
        animation: rise-in 600ms ease-out;
    }

    .signal-card b {
        display: block;
        color: var(--fp-ink);
        font-size: 0.88rem;
        margin-bottom: 0.08rem;
    }

    .signal-card span {
        color: var(--fp-slate);
        font-size: 0.76rem;
    }

    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0c213a 0%, #123a5f 58%, #1a4f74 100%);
        border-right: 1px solid rgba(255, 255, 255, 0.14);
    }

    section[data-testid="stSidebar"] * {
        color: #edf4ff !important;
    }

    section[data-testid="stSidebar"] div[data-testid="stTextInput"] input {
        color: #0f2845 !important;
        background: #ffffff;
        border-radius: 11px;
        border: 1px solid #b9d0ec;
    }

    section[data-testid="stSidebar"] .stButton button {
        background: rgba(255, 255, 255, 0.12);
        border: 1px solid rgba(255, 255, 255, 0.3);
        color: #f3f8ff;
        border-radius: 12px;
        text-align: left;
        transition: all 220ms ease;
    }

    section[data-testid="stSidebar"] .stButton button:hover {
        border-color: #9fd8ff;
        background: rgba(255, 255, 255, 0.22);
        transform: translateY(-1px);
    }

    div[data-testid="stChatMessage"] {
        background: rgba(255, 255, 255, 0.93);
        border: 1px solid #d9e4f2;
        border-radius: 18px;
        box-shadow: 0 12px 28px rgba(9, 33, 61, 0.08);
        margin-bottom: 0.6rem;
    }

    div[data-testid="stChatInput"] textarea {
        border-radius: 14px !important;
        border: 1px solid #bdd3ed !important;
        box-shadow: 0 6px 16px rgba(10, 42, 77, 0.09);
    }

    @media (max-width: 900px) {
        .signal-row {
            grid-template-columns: 1fr;
        }
        .brand-title {
            font-size: 1.35rem;
        }
        .brand-subtitle {
            font-size: 0.84rem;
        }
    }

    @keyframes rise-in {
        from {
            opacity: 0;
            transform: translateY(10px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    @keyframes pulse-dot {
        0%, 100% {
            transform: scale(1);
            opacity: 0.95;
        }
        50% {
            transform: scale(1.03);
            opacity: 1;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

if "history" not in st.session_state:
    st.session_state.history = []
if "welcome_loaded" not in st.session_state:
    st.session_state.welcome_loaded = False
if "pending_question" not in st.session_state:
    st.session_state.pending_question = None

with st.sidebar:
    if LOGO_PATH.exists():
        st.image(str(LOGO_PATH), width=64)
    st.markdown("### FinPulseAI")
    st.caption("Real-time financial pulse checks powered by a grounded orchestration engine.")
    st.divider()

    api_base_url = st.text_input("API base URL", value=DEFAULT_API_BASE_URL)

    st.divider()
    st.markdown("**Try a sample question**")
    for idx, sample in enumerate(SAMPLE_QUESTIONS):
        if st.button(sample, key=f"sample_{idx}", use_container_width=True):
            st.session_state.pending_question = sample

    #add a button to call a backend API \chunk-documents\{internal}, and shows the streaming response below the button
    st.markdown("**Chunk documents**")
    if st.button("📄 Chunk documents", use_container_width=True):
        internal = st.checkbox("Use internal model", value=False)
        response = requests.get(f"{api_base_url.rstrip('/')}/orchestrator/chunk-documents/{internal}", stream=True)
        for line in response.iter_lines():
            if line:
                #write a method to capture the streaming response json, that has the format {"event": "status", "data": {"message": "chunking in progress"}}, and displays it in a block below the button, and if the event is "final", display the final message in a success message box
                try:
                    decoded_line = line.decode("utf-8")
                    parsed_line = json.loads(decoded_line)
                    event = parsed_line.get("event")
                    data = parsed_line.get("data", {})
                    message = data.get("message", "")
                    if event == "status":
                        st.info(message)
                    elif event == "final":
                        st.success(message)
                except json.JSONDecodeError:
                    st.error(f"Failed to decode JSON from line: {line}")
                except Exception as e:
                    st.error(f"An error occurred while processing the line: {e}")
                #st.text(line.decode("utf-8"))
                
    st.divider()
    if st.button("🗑️ Clear conversation", use_container_width=True):
        st.session_state.history = []
        st.session_state.welcome_loaded = False
        st.rerun()

st.markdown('<div class="brand-header">', unsafe_allow_html=True)
col_logo, col_brand, col_status = st.columns([1, 5, 2])
with col_logo:
    if LOGO_PATH.exists():
        st.image(str(LOGO_PATH), width=64)
with col_brand:
    st.markdown(
        "<div class='brand-title'>FinPulseAI</div>"
        "<div class='brand-subtitle'>Track the health and movement of company financial performance with grounded, source-backed intelligence.</div>",
        unsafe_allow_html=True,
    )
with col_status:
    st.markdown("<span class='status-pill'>● Connected</span>", unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

st.markdown(
    """
    <div class="signal-row">
        <div class="signal-card"><b>Performance Pulse</b><span>Monitor shifts in budget, forecast, and actuals.</span></div>
        <div class="signal-card"><b>Risk Drift</b><span>Spot early variance patterns before they widen.</span></div>
        <div class="signal-card"><b>Narrative Context</b><span>Link every answer to grounded document evidence.</span></div>
    </div>
    """,
    unsafe_allow_html=True,
)


def fetch_welcome_message() -> str:
    try:
        welcome_response = requests.get(f"{api_base_url.rstrip('/')}/orchestrator/welcome", timeout=20)
        welcome_response.raise_for_status()
        welcome_data = welcome_response.json()
        welcome_text = welcome_data.get("welcome_message", "")
        overview_text = welcome_data.get("data_overview", "")
        combined_text = "\n\n".join(filter(None, [welcome_text, overview_text]))
        return combined_text or "Welcome to FinPulseAI. Ask a question to get started."
    except requests.HTTPError as exc:
        error_details = exc.response.text if exc.response is not None else str(exc)
        return f"Unable to load welcome message from backend: {error_details}"
    except requests.RequestException as exc:
        return f"Unable to connect to backend welcome API: {exc}"


def _coerce_final_financial_response(final_response: Any) -> FinalFinancialResponse | None:
    if isinstance(final_response, FinalFinancialResponse):
        return final_response

    if isinstance(final_response, str):
        stripped = final_response.strip()
        if not stripped:
            return FinalFinancialResponse(answer="", citations=[])
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            return FinalFinancialResponse(answer=stripped, citations=[])
        final_response = parsed

    if not isinstance(final_response, dict):
        return None

    if isinstance(final_response.get("final_answer"), dict):
        nested = _coerce_final_financial_response(final_response.get("final_answer"))
        if nested is not None:
            return nested

    answer = final_response.get("answer")
    if answer is None:
        answer = final_response.get("final_answer")
    if answer is None:
        answer = ""

    raw_citations = final_response.get("citations")
    if raw_citations is None:
        raw_citations = final_response.get("citationInformation")
    if raw_citations is None:
        raw_citations = []

    citations: list[CitationInfo] = []
    if isinstance(raw_citations, list):
        for citation in raw_citations:
            try:
                citations.append(CitationInfo.model_validate(citation))
            except Exception:
                continue

    return FinalFinancialResponse(answer=str(answer), citations=citations)


def _coerce_chart_spec(chart_payload: Any) -> ChartSpec | None:
    if chart_payload is None:
        return None

    if isinstance(chart_payload, ChartSpec):
        return chart_payload

    if isinstance(chart_payload, str):
        try:
            parsed = json.loads(chart_payload)
        except json.JSONDecodeError:
            return None
        chart_payload = parsed

    if isinstance(chart_payload, dict):
        try:
            return ChartSpec.model_validate(chart_payload)
        except Exception:
            return None

    return None


def _extract_chart_payload(final_response: Any, payload: dict[str, Any]) -> Any:
    top_level = payload.get("chartSpec") or payload.get("chart")
    if top_level is not None:
        return top_level

    if isinstance(final_response, dict):
        nested = (
            final_response.get("chartSpec")
            or final_response.get("chart")
            or final_response.get("chart_spec")
        )
        if nested is not None:
            return nested

        nested_final = final_response.get("final_answer")
        if isinstance(nested_final, dict):
            return (
                nested_final.get("chartSpec")
                or nested_final.get("chart")
                or nested_final.get("chart_spec")
            )

    return None


def stream_orchestrator_response(response: requests.Response, status: Any) -> tuple[FinalFinancialResponse | None, ChartSpec | None]:
    """Consume the backend SSE stream, updating the status widget, and return the final answer."""
    event_name: str | None = None
    data_lines: list[str] = []
    final_response: FinalFinancialResponse | None = None
    final_chart_spec: ChartSpec | None = None

    def handle_event(name: str, payload: dict[str, Any]) -> None:
        nonlocal final_response
        nonlocal final_chart_spec

        try:
            if name == "status":
                message = payload.get("message", "")
                stage = payload.get("stage", "")
                reasoning = payload.get("reasoning")

                if st.session_state.conversation_id is None and payload.get("conversation_id") is not None:
                    st.session_state.conversation_id = payload.get("conversation_id")

                if stage == "planning_update" and reasoning:
                    text = f"Planning: {reasoning}"
                elif stage and message:
                    text = f"{stage.replace('_', ' ').title()}: {message}"
                else:
                    text = message
                if text:
                    status.update(label=text)
                    status.write(text)
            elif name == "final":
                raw_final_response = payload.get("final_response", "")
                if (
                    isinstance(raw_final_response, dict)
                    and "citations" not in raw_final_response
                    and "citationInformation" not in raw_final_response
                    and payload.get("citationInformation") is not None
                ):
                    raw_final_response = {
                        **raw_final_response,
                        "citationInformation": payload.get("citationInformation"),
                    }
                coerced = _coerce_final_financial_response(raw_final_response)
                if coerced is None:
                    final_response = FinalFinancialResponse(answer=str(raw_final_response), citations=[])
                else:
                    final_response = coerced

                final_chart_spec = _coerce_chart_spec(
                    _extract_chart_payload(raw_final_response, payload)
                )
            elif name == "error":
                error_text = payload.get("message") or payload.get("error_message") or "Unexpected orchestrator error"
                final_response = FinalFinancialResponse(answer=error_text, citations=[])
                final_chart_spec = None
        except Exception as exc:
            final_response = FinalFinancialResponse(answer=f"Unexpected error: {exc}", citations=[])
            final_chart_spec = None

    for raw_line in response.iter_lines():
        if raw_line is None:
            continue
        line = raw_line.decode("utf-8") if isinstance(raw_line, bytes) else raw_line
        if line.startswith("event:"):
            event_name = line.split(":", 1)[1].strip()
        elif line.startswith("data:"):
            data_lines.append(line.split(":", 1)[1].strip())
        elif not line.strip() and event_name is not None and data_lines:
            json_str = ''.join(data_lines)
            handle_event(event_name, json.loads(json_str))
            event_name = None
            data_lines = []

    if event_name is not None and data_lines:
        json_str = ''.join(data_lines)
        handle_event(event_name, json.loads(json_str))

    return final_response, final_chart_spec


def ask_orchestrator(user_question: str, status: Any) -> tuple[FinalFinancialResponse, ChartSpec | None] | str:
    try:
        # conversation_history = [
        #     {"role": item["role"], "content": item["text"]} for item in st.session_state.history[:-1]
        # ]
        response = requests.post(
            f"{api_base_url.rstrip('/')}/orchestrator/ask-openai",
            json={
                "user_question": user_question,
                "api_base_url": api_base_url,
                #"conversation_history": conversation_history,
                "conversation_id": st.session_state.conversation_id
            },
            stream=True,
            timeout=120,
        )
        response.raise_for_status()
        final_answer, chart_spec = stream_orchestrator_response(response, status)
        if final_answer is None:
            return "The orchestrator returned no final response."
        return final_answer, chart_spec
    except requests.HTTPError as exc:
        error_text = exc.response.text if exc.response is not None else str(exc)
        return f"Error calling API: {error_text}"
    except requests.RequestException as exc:
        return f"Connection error: {exc}"
    except Exception as exc:  # noqa: BLE001 - surface unexpected errors to the chat
        return f"Unexpected error: {exc}"


def render_response(response: FinalFinancialResponse, chart_spec: ChartSpec | None = None) -> None:
    st.markdown(response.answer)

    if chart_spec:
        data = {"category": chart_spec.categories}
        for series in chart_spec.series:
            data[series.name] = series.values

        df = pd.DataFrame(data)
        st.subheader(chart_spec.title)

        if chart_spec.chart_type == "line":
            st.line_chart(df, x="category")
        elif chart_spec.chart_type == "bar":
            st.bar_chart(df, x="category")
        elif chart_spec.chart_type == "scatter":
            st.scatter_chart(df, x="category")

    if not response.citations:
        return

    with st.expander("Citation Information", expanded=True):
        for citation in response.citations:
            label = citation.label or citation.citation_id
            st.markdown(f"**[{citation.citation_type.title()}] {label}**")

            if citation.citation_type == "document":
                details: list[str] = []
                if citation.document_name:
                    details.append(f"Document: {citation.document_name}")
                if citation.page_number is not None:
                    details.append(f"Page: {citation.page_number}")
                if citation.chunk_id:
                    details.append(f"Chunk ID: {citation.chunk_id}")
                if citation.document_link:
                    details.append(f"Link: {citation.document_link}")
                if details:
                    st.caption(" | ".join(details))

            elif citation.citation_type == "database":
                details = []
                if citation.database_source:
                    details.append(f"Source: {citation.database_source}")
                if citation.query_name:
                    details.append(f"Query: {citation.query_name}")
                if citation.query_summary:
                    details.append(f"Summary: {citation.query_summary}")
                if details:
                    st.caption(" | ".join(details))

            elif citation.citation_type == "calculation":
                if citation.calculation_name:
                    st.caption(f"Calculation: {citation.calculation_name}")

if not st.session_state.welcome_loaded:
    st.session_state.history.append({"role": "assistant", "text": fetch_welcome_message()})
    st.session_state.welcome_loaded = True
    st.session_state.conversation_id = None

for item in st.session_state.history:
    avatar = USER_AVATAR if item["role"] == "user" else ASSISTANT_AVATAR
    with st.chat_message(item["role"], avatar=avatar):
        structured_response = item.get("response")
        history_chart_spec = _coerce_chart_spec(item.get("chart_spec"))
        if item["role"] == "assistant" and structured_response:
            coerced = _coerce_final_financial_response(structured_response)
            if coerced:
                render_response(coerced, history_chart_spec)
            else:
                st.markdown(item["text"])
        else:
            st.markdown(item["text"])

prompt = st.chat_input("Ask a business finance question...")
if not prompt and st.session_state.pending_question:
    prompt = st.session_state.pending_question
st.session_state.pending_question = None

if prompt:
    st.session_state.history.append({"role": "user", "text": prompt})
    with st.chat_message("user", avatar=USER_AVATAR):
        st.markdown(prompt)

    with st.chat_message("assistant", avatar=ASSISTANT_AVATAR):
        with st.status("Contacting FinPulseAI agent...", expanded=True) as status:
            final_answer = ask_orchestrator(prompt, status)
            status.update(label="Response ready", state="complete", expanded=False)
    
        if isinstance(final_answer, tuple):
            final_response, chart_spec = final_answer
            render_response(final_response, chart_spec)
            st.session_state.history.append(
                {
                    "role": "assistant",
                    "text": final_response.answer,
                    "response": final_response.model_dump(mode="json"),
                    "chart_spec": chart_spec.model_dump(mode="json") if chart_spec else None,
                }
            )
        else:
            st.markdown(final_answer)
            st.session_state.history.append({"role": "assistant", "text": final_answer})
