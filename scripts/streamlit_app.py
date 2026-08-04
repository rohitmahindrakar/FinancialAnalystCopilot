from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import requests
import streamlit as st

import os

DEFAULT_API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
LOGO_PATH = Path(__file__).resolve().parent / "assets" / "company_logo.svg"
SAMPLE_QUESTIONS = [
    "Summarize the latest budget context for Q3.",
    "What are the key forecast trends across the business units?",
    "Compare actuals and budgets for the latest reporting period.",
    "Explain the main document context around the company's guidance.",
]

st.set_page_config(page_title="Financial Analyst Copilot", page_icon="💬", layout="wide")

st.markdown(
    """
    <style>
    .main {
        background: linear-gradient(180deg, #f4f8fb 0%, #eef4fa 100%);
    }
    .block-container {
        padding-top: 0.25rem;
        padding-bottom: 2rem;
        max-width: 100%;
    }
    .brand-header {
        display: flex;
        align-items: center;
        gap: 1rem;
        margin-bottom: 1rem;
        padding: 0.75rem 1rem;
        background: rgba(255, 255, 255, 0.82);
        border: 1px solid rgba(13, 46, 92, 0.12);
        border-radius: 16px;
        box-shadow: 0 10px 28px rgba(13, 46, 92, 0.08);
    }
    .brand-header img {
        width: 72px;
        height: 72px;
        border-radius: 18px;
    }
    .brand-title {
        font-size: 1.8rem;
        font-weight: 700;
        color: #0d2e5c;
    }
    .brand-subtitle {
        font-size: 0.95rem;
        color: #456587;
    }
    .sample-card {
        background: linear-gradient(135deg, #ffffff, #f1f6fb);
        border: 1px solid #d7e4f2;
        border-radius: 14px;
        padding: 0.8rem 1rem;
        margin: 0.35rem 0.35rem 0.35rem 0;
        cursor: pointer;
        box-shadow: 0 6px 16px rgba(13, 46, 92, 0.05);
    }
    .sample-card:hover {
        border-color: #0f5da8;
        transform: translateY(-1px);
    }
    .chat-bubble-user {
        background: #0d2e5c;
        color: white;
        padding: 0.9rem 1rem;
        border-radius: 16px 16px 4px 16px;
        margin: 0.5rem 0;
    }
    .chat-bubble-assistant {
        background: #ffffff;
        color: #0f2443;
        padding: 0.95rem 1rem;
        border-radius: 16px 16px 16px 4px;
        border: 1px solid #dbe7f3;
        margin: 0.5rem 0;
        box-shadow: 0 8px 20px rgba(13, 46, 92, 0.05);
    }
    div[data-testid="stForm"] {
        background: rgba(255, 255, 255, 0.84);
        padding: 1rem;
        border-radius: 18px;
        border: 1px solid #dbe7f3;
        box-shadow: 0 10px 22px rgba(13, 46, 92, 0.06);
    }
    </style>
    """,
    unsafe_allow_html=True,
)


if "history" not in st.session_state:
    st.session_state.history = []

with st.container():
    st.markdown('<div class="brand-header">', unsafe_allow_html=True)
    col_logo, col_brand = st.columns([1, 5])
    with col_logo:
        if LOGO_PATH.exists():
            st.image(str(LOGO_PATH), width=84)
    with col_brand:
        st.markdown(
            "<div class='brand-title'>Financial Analyst Copilot</div><div class='brand-subtitle'>Corporate finance question answering with secure orchestration and grounded insights.</div>",
            unsafe_allow_html=True,
        )
    st.markdown('</div>', unsafe_allow_html=True)

st.subheader("Try one of these sample questions")
question_cols = st.columns(2)
for idx, sample in enumerate(SAMPLE_QUESTIONS):
    with question_cols[idx % 2]:
        if st.button(sample, key=f"sample_{idx}", use_container_width=True):
            st.session_state.user_question = sample
            st.rerun()

st.write("Ask a business finance question and the app will send the request through a single backend orchestrator API call.")


def parse_sse_stream(response: requests.Response) -> list[tuple[str, dict[str, Any]]]:
    events: list[tuple[str, dict[str, Any]]] = []
    event_name: str | None = None
    data_lines: list[str] = []

    for raw_line in response.iter_lines():
        if raw_line is None:
            continue

        line = raw_line.decode("utf-8") if isinstance(raw_line, bytes) else raw_line
        if line.startswith("event:"):
            event_name = line.split(":", 1)[1].strip()
        elif line.startswith("data:"):
            data_lines.append(line.split(":", 1)[1].strip())
        elif not line.strip() and event_name is not None and data_lines:
            payload = json.loads("".join(data_lines))
            events.append((event_name, payload))
            event_name = None
            data_lines = []

    if event_name is not None and data_lines:
        payload = json.loads("".join(data_lines))
        events.append((event_name, payload))

    return events


def render_live_stream(response: requests.Response, placeholder: Any) -> tuple[str | None, list[str]]:
    event_name: str | None = None
    data_lines: list[str] = []
    progress_messages: list[str] = []
    final_answer: str | None = None

    for raw_line in response.iter_lines():
        if raw_line is None:
            continue

        line = raw_line.decode("utf-8") if isinstance(raw_line, bytes) else raw_line
        if line.startswith("event:"):
            event_name = line.split(":", 1)[1].strip()
        elif line.startswith("data:"):
            data_lines.append(line.split(":", 1)[1].strip())
        elif not line.strip() and event_name is not None and data_lines:
            payload = json.loads("".join(data_lines))
            if event_name == "status":
                message = payload.get("message", "")
                stage = payload.get("stage", "")
                reasoning = payload.get("reasoning")
                if stage == "planning_update" and reasoning:
                    progress_messages.append(f"[planning_update] {reasoning}")
                elif stage and message:
                    progress_messages.append(f"[{stage}] {message}")
                elif message:
                    progress_messages.append(message)
                placeholder.markdown("### Backend agent status\n" + "\n".join(progress_messages))
            elif event_name == "final":
                final_answer = payload.get("final_response", "")
                placeholder.markdown(final_answer)
            elif event_name == "error":
                final_answer = payload.get("message", "Unexpected orchestrator error")
                placeholder.markdown(final_answer)
                break

            event_name = None
            data_lines = []

    if event_name is not None and data_lines:
        payload = json.loads("".join(data_lines))
        if event_name == "status":
            message = payload.get("message", "")
            stage = payload.get("stage", "")
            reasoning = payload.get("reasoning")
            if stage == "planning_update" and reasoning:
                progress_messages.append(f"[planning_update] {reasoning}")
            elif stage and message:
                progress_messages.append(f"[{stage}] {message}")
            elif message:
                progress_messages.append(message)
            placeholder.markdown("### Backend agent status\n" + "\n".join(progress_messages))
        elif event_name == "final":
            final_answer = payload.get("final_response", "")
            placeholder.markdown(final_answer)
        elif event_name == "error":
            final_answer = payload.get("message", "Unexpected orchestrator error")
            placeholder.markdown(final_answer)

    return final_answer, progress_messages


def format_history_item(item: dict[str, Any]) -> str:
    if item["role"] == "user":
        return f'<div class="chat-bubble-user">{item["text"]}</div>'
    if item["role"] == "assistant":
        return f'<div class="chat-bubble-assistant">{item["text"]}</div>'
    return str(item["text"])


if "history" not in st.session_state:
    st.session_state.history = []

if "user_question" not in st.session_state:
    st.session_state.user_question = ""

if "welcome_loaded" not in st.session_state:
    st.session_state.welcome_loaded = False

api_base_url = st.text_input("API base URL", value=DEFAULT_API_BASE_URL)

if not st.session_state.welcome_loaded:
    try:
        welcome_response = requests.get(f"{api_base_url.rstrip('/')}/orchestrator/welcome", timeout=20)
        welcome_response.raise_for_status()
        welcome_data = welcome_response.json()
        welcome_text = welcome_data.get("welcome_message", "")
        overview_text = welcome_data.get("data_overview", "")
        if welcome_text or overview_text:
            combined_text = "\n\n".join(filter(None, [welcome_text, overview_text]))
            st.session_state.history.append({"role": "assistant", "text": combined_text})
        else:
            st.session_state.history.append({"role": "assistant", "text": "Welcome to Financial Analyst Copilot."})
    except requests.HTTPError as exc:
        error_details = exc.response.text if exc.response is not None else str(exc)
        st.session_state.history.append({"role": "assistant", "text": f"Unable to load welcome message from backend: {error_details}"})
    except requests.RequestException as exc:
        st.session_state.history.append({"role": "assistant", "text": f"Unable to connect to backend welcome API: {exc}"})
    st.session_state.welcome_loaded = True

with st.form("chat_form"):
    user_question = st.text_area("Your question", value=st.session_state.user_question, height=100)
    submitted = st.form_submit_button("Send", use_container_width=True)

if submitted and user_question.strip():
    st.session_state.history.append({"role": "user", "text": user_question})

    try:
        conversation_history = [
            {"role": item["role"], "content": item["text"]}
            for item in st.session_state.history[:-1]
        ]

        response = requests.post(
            f"{api_base_url.rstrip('/')}/orchestrator/ask-openai",
            json={
                "user_question": user_question,
                "api_base_url": api_base_url,
                "conversation_history": conversation_history,
            },
            stream=True,
            timeout=120,
        )
        response.raise_for_status()

        live_placeholder = st.empty()
        final_answer, _ = render_live_stream(response, live_placeholder)

        if final_answer:
            st.session_state.history.append({"role": "assistant", "text": final_answer})
        else:
            st.session_state.history.append(
                {"role": "assistant", "text": "The orchestrator returned no final response."}
            )
    except requests.HTTPError as exc:
        error_text = exc.response.text if exc.response is not None else str(exc)
        st.session_state.history.append(
            {"role": "assistant", "text": f"Error calling API: {error_text}"}
        )
    except requests.RequestException as exc:
        st.session_state.history.append(
            {"role": "assistant", "text": f"Connection error: {exc}"}
        )
    except Exception as exc:
        st.session_state.history.append(
            {"role": "assistant", "text": f"Unexpected error: {exc}"}
        )

for item in st.session_state.history:
    st.markdown(format_history_item(item), unsafe_allow_html=True)
